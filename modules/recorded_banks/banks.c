/* mg204 reel storage. Paths are relative to drive 0. Only the main loop
 * calls FatFs. Audio/TIM2 continue during directory access. */
#include <stdint.h>

#define U32(a) (*(volatile uint32_t *)(a))
#define U8(a) (*(volatile uint8_t *)(a))
#define BANK U8(0x2002a61f)
#define COUNT U32(0x200012a0)
#define CURSOR U32(0x20001040)
#define FLAGS U32(0x20022074)
#define CARD U32(0x20001290)
#define MODE U32(0x20021338)
#define REC U32(0x20022108)
#define REC_REQUEST U32(0x20021320)
#define INVENTORY U8(0x20028f30)
#define AVAILABLE U8(0x20028f31)
#define HOLD_START U32(0x20001024)
#define NOW U32(0x20021c88)
#define CYCLE_START U32(0x20028f34)
enum { IDLE, REQUESTED, READY, FAILED };
#define REQUEST U8(0x20028f0d) /* 1..8 selected bank, 9 inventory request */
#define f_stat ((int (*)(const char *, void *))0x08033129)
#define f_open ((int (*)(void *, const char *, unsigned))0x08032261)
#define f_read ((int (*)(void *, void *, unsigned, unsigned *))0x080323fd)
#define f_seek ((int (*)(void *, unsigned))0x08032be9)
#define f_close ((int (*)(void *))0x080327a9)
enum { FR_NO_FILE = 4, AM_DIR = 0x10 };

/* These are the original bank helpers in the SHA-verified D15/D17 image.
 * rb_recount protects the opened file while compacting the selected bank. */
#define bank_get ((unsigned (*)(void))0x08052109)
#define make_name ((void (*)(char *, unsigned, unsigned, int))0x08051e79)
#define rb_recount ((int (*)(unsigned))0x080521b5)

static char *folder_name(char *p, unsigned bank) {
    *p++ = 'b'; *p++ = 'a'; *p++ = 'n'; *p++ = 'k';
    *p++ = '0' + bank;
    *p = 0;
    return p;
}

static int browsing(void) {
    return CARD == 1 && MODE == 1 && !REC && !REC_REQUEST;
}

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

/* Missing folders and non-reel entries are skipped. Propagate actual card
 * errors, so a partial inventory can never become the panel's color cycle. */
static int bank_has_audio(unsigned bank) {
    uint32_t info[8], file[138];
    info[6] = 0;
    char path[32];
    if (bank > 1) {
        folder_name(path, bank);
        int error = f_stat(path, info);
        if (error == FR_NO_FILE || (!error && !(info[2] & AM_DIR))) return 0;
        if (error) return -1;
    }
    for (unsigned n = 1; n <= 32; ++n) {
        make_name(path, bank, n, 0);
        int error = f_stat(path, info);
        if (error == FR_NO_FILE) continue;
        if (error) return -1;
        if ((info[2] & AM_DIR) || info[0] <= 44) continue;
        if (f_open(file, path, 1)) return -1;
        int result = recorded_data(file, info[0]);
        if (f_close(file)) return -1;
        if (result) return result;
    }
    return 0;
}

void rb_inventory(void) {
    if (!browsing() || FLAGS & ~0x80u) return;
    uint32_t start = HOLD_START;
    unsigned mask = 0, state = READY;
    for (unsigned bank = 1; bank <= 8; ++bank) {
        if (REQUEST != 9 || INVENTORY != REQUESTED || HOLD_START != start) return;
        int found = bank_has_audio(bank);
        if (found < 0) { state = FAILED; break; }
        if (found) mask |= 1u << (bank - 1);
    }
    uint32_t saved;
    __asm__ volatile ("mrs %0, primask\n cpsid i" : "=r"(saved) :: "memory");
    if (REQUEST == 9 && INVENTORY == REQUESTED && HOLD_START == start && browsing()) {
        uint32_t now = NOW;
        CYCLE_START = now - start >= 288000u ? now : start + 288000u;
        AVAILABLE = state == READY ? mask : 0;
        INVENTORY = state;
        REQUEST = 0;
    }
    __asm__ volatile ("msr primask, %0" :: "r"(saved) : "memory");
}

/* All arguments here are in RAM. TIM2 never performs directory or file I/O. */
unsigned rb_step(unsigned bank, unsigned mask, unsigned steps) {
    if (!(mask & ~(1u << (bank - 1)))) return 0;
    unsigned count = 0;
    for (unsigned bits = mask; bits; bits &= bits - 1) ++count;
    unsigned left = 1u + steps % count;
    do {
        bank = (bank & 7u) + 1;
        if (mask & (1u << (bank - 1))) --left;
    } while (left);
    return bank;
}

/* Called only on release. Recheck after FatFs I/O and publish browse state
 * together so the panel cannot observe indices from two different banks. */
unsigned rb_apply(unsigned target) {
    unsigned bank = bank_get();
    if (!bank || !target || target > 8 || target == bank || !browsing()) return 1;
    /* Let the stock dispatcher service pending I/O and revisit this request
     * on its next pass. A pending options rewrite can include the new bank. */
    if (FLAGS & ~0x80u) return 0;
    if (bank_has_audio(target) != 1) return 1;
    int count = rb_recount(target);
    if (count <= 0) return 1;
    uint32_t saved;
    __asm__ volatile ("mrs %0, primask\n cpsid i" : "=r"(saved) :: "memory");
    int still_browsing = browsing() && bank_get() == bank;
    int defer = still_browsing && (FLAGS & ~0x80u);
    if (still_browsing && !defer) {
        COUNT = (unsigned)count;
        CURSOR = 1;
        U32(0x200220ac) = (uint32_t)-100000;
        U8(0x20028f0e) = 1; /* Organize browses until SPLICE + REC confirms. */
        BANK = target;
        U8(0x20028f0f) = 1; /* keep its color briefly after release */
        FLAGS |= 0x80u;
    }
    __asm__ volatile ("msr primask, %0" :: "r"(saved) : "memory");
    return !defer;
}
