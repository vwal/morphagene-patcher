/* Select the sole recorded WAV on an explicit bank switch, including banks
 * containing empty WAVs created during earlier switches. In the D19 image
 * recorded_data was inlined into bank_has_audio. This file keeps D18's
 * tested RIFF reader verbatim and calls the already linked bank helpers. */
#include <stdint.h>

#define U32(a) (*(volatile uint32_t *)(a))
#define U16(a) (*(volatile uint16_t *)(a))
#define U8(a)  (*(volatile uint8_t *)(a))
#define BANK U8(0x2002a61f)
#define COUNT U32(0x200012a0)
#define CURSOR U32(0x20001040)
#define FLAGS U32(0x20022074)
#define MOUNT_GENERATION U16(0x20024278)
#define AWAIT_CONFIRM U8(0x20028f0e)
#define ORGANIZE_ACCEPTED U32(0x200220ac)
#define SHOW_BANK_COLOR U8(0x20028f0f)

#define f_stat ((int (*)(const char *, void *))0x08033129)
#define f_open ((int (*)(void *, const char *, unsigned))0x08032261)
#define f_read ((int (*)(void *, void *, unsigned, unsigned *))0x080323fd)
#define f_seek ((int (*)(void *, unsigned))0x08032be9)
#define f_close ((int (*)(void *))0x080327a9)
#define bank_get ((unsigned (*)(void))0x08052109)
#define make_name ((void (*)(char *, unsigned, unsigned, int))0x08051e79)
#define bank_has_audio ((int (*)(unsigned))0x0805322d)
#define rb_recount ((int (*)(unsigned))0x080521b5)
#define browsing ((int (*)(void))0x080531d5)

/* Read only RIFF metadata. Stock can leave a WAV header or cue metadata on
 * an erased reel. File size alone cannot distinguish this from a take. */
static int read_exact(void *file, void *buf, unsigned size) {
    unsigned actual;
    return !f_read(file, buf, size, &actual) && actual == size;
}

static int recorded_data(uint32_t *file, unsigned size) {
    uint32_t words[4];
    if (!read_exact(file, words, 12)) return -1;
    if (words[0] != 0x46464952 || words[2] != 0x45564157) return 0; /* RIFF WAVE */
    if (words[1] < 4 || words[1] > size - 8) return 0;
    unsigned end = words[1] + 8, pos = 12, frame = 0;
    while (end - pos >= 8) {
        if (!read_exact(file, words, 8)) return -1;
        uint32_t id = words[0], length = words[1];
        pos += 8;
        if (length > end - pos) return 0;
        if (id == 0x20746d66 && length >= 16) { /* fmt */
            if (!read_exact(file, words, 16)) return -1;
            /* Keep the probe independent of the native decoder and require
             * a real format/channel count, sample rate and block size. */
            if (!(words[0] & 0xffff) || !(words[0] >> 16) || !words[1]) return 0;
            frame = words[3] & 0xffff;
        }
        if (id == 0x61746164 && frame && length >= frame) return 1; /* data */
        pos += length;
        if (pos == end) break;
        pos += length & 1;                      /* RIFF chunks are word aligned */
        if (pos != file[2] && f_seek(file, pos)) return -1;
    }
    return 0;
}

/* Called only after recount has compacted this bank to slots 1..count.
 * Return -1 on failure, 0 for normal clamping, otherwise the sole recorded
 * slot among several files. A single-file bank has passed bank_has_audio()
 * and the normal clamp already gives it slot 1 on the whole dial. */
static int recorded_slot(unsigned bank, unsigned count) {
    if (count == 1) return 0;
    unsigned found = 0;
    uint32_t info[8], file[138];
    info[6] = 0;
    char path[32];
    for (unsigned slot = 1; slot <= count; ++slot) {
        make_name(path, bank, slot, 0);
        if (f_stat(path, info)) return -1;
        if (info[0] <= 44) continue;
        if (f_open(file, path, 1)) return -1;
        int result = recorded_data(file, info[0]);
        if (f_close(file) || result < 0) return -1;
        if (result) {
            if (found) return 0;
            found = slot;
        }
    }
    return found ? (int)found : -1;
}

/* D18's foreground apply sequence. Publish the recorded-slot information
 * in the original confirmation byte in the same critical section, after
 * validating that the selection, mount, and pending card work still agree.
 * Its other consumers accept any nonzero value until confirmation. */
int bank_apply_existing(unsigned target) {
    unsigned bank = bank_get();
    uint16_t volume = MOUNT_GENERATION;
    if (!bank || !target || target > 8 || target == bank || !browsing()) return 1;
    if (FLAGS & ~0x80u) return 0;
    if (bank_has_audio(target) != 1) return 1;
    int count = rb_recount(target);
    if (count <= 0 || count > 32) return 1;
    int sole = recorded_slot(target, (unsigned)count);
    if (sole < 0) return 1;
    uint32_t saved;
    __asm__ volatile ("mrs %0, primask\n cpsid i" : "=r"(saved) :: "memory");
    int still_browsing = browsing() && bank_get() == bank && MOUNT_GENERATION == volume;
    int defer = still_browsing && (FLAGS & ~0x80u);
    if (still_browsing && !defer) {
        COUNT = (unsigned)count;
        CURSOR = sole ? (unsigned)sole : 1;
        ORGANIZE_ACCEPTED = (uint32_t)-100000;
        AWAIT_CONFIRM = (uint8_t)(1 + sole);
        BANK = (uint8_t)target;
        SHOW_BANK_COLOR = 1;
        FLAGS |= 0x80u;
    }
    __asm__ volatile ("msr primask, %0" :: "r"(saved) : "memory");
    return !defer;
}
