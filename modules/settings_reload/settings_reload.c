/* mg204 only. No allocation, writable globals, libc or flash writes.
 * All disk access runs in application_main. Only reload_commit changes options.
 */
#include <stdint.h>
#include <stddef.h>
#include "../options_keys/preset_io.h"
#include "../preset_recall/preset.h"

#define U32(a) (*(volatile uint32_t *)(a))
#define U16(a) (*(volatile uint16_t *)(a))
#define U8(a)  (*(volatile uint8_t *)(a))
#define SAMPLES U32(0x20021c88)
#define CARD U32(0x20001290)
#define FLAGS U32(0x20022074)
#define REC U32(0x20022108)
#define REC_REQUEST U32(0x20021320)
#define PHASE_IDLE 0u
#define PHASE_TIMING 1u
#define PHASE_ARMED 2u
#define PHASE_REQUEST 3u
#define PHASE_READING 4u
#define PHASE_PARKED 5u
#define PHASE_READY 6u
#define PHASE_CLEANUP 7u
#define REEL U32(0x20001040)
#define REELS U32(0x200012a0)
#define DATA_START U32(0x20001064)
#define CID ((volatile uint32_t *)0x2002427c)

typedef struct {
    uint32_t phase, started, owned, pending, result, finished, absent;
    uint32_t seen, values[26];
    uint32_t valid, reel, reels, data_start, size, cluster, position;
    uint32_t cid[4], dir_sector, dir_offset;
    uint32_t reserved[7], dlen_value, snapshot_ready, live_file, scanning;
    uint32_t morph_loop_value; /* separate slot preserves the assembly state ABI */
    uint32_t density_start_value;
    uint32_t mount_ready; /* 1: owned fresh mount; 2: normal load in progress */
    uint32_t unity_value, center_value, dryk_value;
} Reload;
#define S ((volatile Reload *)0x2002a820)
_Static_assert(sizeof(Reload) <= 0x100, "reload state overlaps FIL");
#define FIL ((void *)0x2002a920)       /* 0x260 bytes; mg204 FIL is 552 bytes */
#define BUFFER ((char *)0x2002ab80)    /* 512 bytes */
#define LINE ((char *)0x2002ad80)      /* 128 significant bytes, comments streamed */
#define GOT ((uint32_t *)0x2002ae00)


typedef int (*Open)(void *, const char *, unsigned);
typedef int (*Read)(void *, void *, unsigned, uint32_t *);
typedef int (*Close)(void *);
typedef int (*Mount)(void *, const char *, unsigned);
typedef int (*Seek)(void *, uint32_t);
typedef void (*Name)(char *, unsigned);
typedef int (*Stat)(const char *, void *);
#define f_open ((Open)0x08032261)
#define f_read ((Read)0x080323fd)
#define f_close ((Close)0x080327a9)
#define f_mount ((Mount)0x0803219d)
#define f_lseek ((Seek)0x08032be9)
#define reel_name ((Name)0x08021f75)
#define splice_name ((Name)0x08022061)
#define f_stat ((Stat)0x08033129)

static int shifted(void) { return (U32(0x40020810) & 2u) != 0; }
static int quiet(void) { return !REC && !REC_REQUEST && !(FLAGS & ~0x80u); }
static int same_live_reel(void) {
    return S->valid && REEL == S->reel && REELS == S->reels &&
           DATA_START == S->data_start;
}
static uint32_t lock(void) {
    uint32_t p;
    __asm__ volatile("mrs %0, primask\n cpsid i" : "=r"(p) :: "memory");
    return p;
}
static void unlock(uint32_t p) {
    __asm__ volatile("msr primask, %0" :: "r"(p) : "memory");
}

static int presets_splice_valid(volatile PresetStage *stage) {
    if (!(stage->mask & 8u)) return 1;
    return stage->values[3] >= 1 && stage->values[3] <= 300;
}
/* Caller holds the audio/TIM2 lock. Publication is one generation, so all
 * explicit recalls apply together. Omitted controls keep live hold state but
 * are omitted from future options writes, matching the card just read. */
static void presets_publish(volatile PresetStage *stage) {
    volatile uint32_t *state = (volatile uint32_t *)0x2002a660;
    unsigned mask = stage->mask & PRESET_MASK;
    if (!mask && state[0] != PRESET_MAGIC) return;
    for (unsigned i=0; i<PRESET_COUNT; ++i)
        if (mask & (1u<<i)) {
            if (i < 4) PRESET->value[i] = stage->values[i];
            else PRESET_EXT->value[i-4] = stage->values[i];
        }
    state[2] = state[3] = mask;
    uint32_t generation = state[1]+1u;
    if (!generation) {
        for (unsigned i=0; i<PRESET_COUNT; ++i) preset_lane(i)->seen_generation = 0;
        generation = 1;
    }
    __asm__ volatile("dmb" ::: "memory");
    state[1] = generation;
    state[0] = PRESET_MAGIC;
}

/* TIM2: observe the hold without claiming existing SHIFT gestures. Only an
 * successful mount after the full hold claims it. GPIOH13 stays low on the
 * tested hardware even with no card: it cannot establish physical absence.
 * Use CARD_OK for eligibility and real main-loop mount results for insertion.
 * The sample clock makes timing independent of 8/16-frame audio block size.
 */
unsigned reload_tick(unsigned shift, unsigned rec, unsigned splice) {
    uint32_t now = SAMPLES;
    /* An offline recording/edit may no longer match the disk reel. Do not
     * silently reconnect it even if its request has finished before insertion. */
    if (!CARD && !quiet()) S->valid = S->snapshot_ready = 0;
    if (S->owned) {
        if (shift || shifted()) return 1;
        S->owned = 0; /* let the consumed SHIFT release finish stock state 14 */
        return 0;
    }
    if (S->phase >= PHASE_REQUEST) return 0;
    if (U32(0x2002a0f0) != 0x5354504fu || CARD || S->mount_ready == 2 || REC || REC_REQUEST ||
        !shift || !shifted() || rec || splice ||
        U32(0x20001020) != 14 || U8(0x2002a005)) {
        S->phase = PHASE_IDLE;
        return 0;
    }
    if (S->phase == PHASE_IDLE) {
        S->started = now;
        S->phase = PHASE_TIMING;
        S->result = 0;
    } else if ((uint32_t)(now - S->started) >= 48000u)
        S->phase = PHASE_ARMED;
    return 0;
}

/* After stock f_mount, before its updater/stop/reel-load path. No disk I/O or
 * audio restart here. Mount can yield to TIM2, so recheck the hold atomically.
 */
unsigned reload_mounted(unsigned result) {
    if (result) return 0;
    uint32_t p = lock();
    if (S->phase == PHASE_ARMED && !CARD && shifted() && quiet() &&
        U32(0x20001020) == 14 && !U8(0x2002a005)) {
        S->owned = 1;
        S->result = 0;
        S->mount_ready = 1;
        S->phase = PHASE_REQUEST;
        U8(0x2002a004) = 1;
        U8(0x2002a005) = 1;
        U8(0x2002a006) = 7; /* reserved reload owner; no knob gesture */
        unlock(p);
        return 1;
    }
    S->phase = PHASE_IDLE;
    S->mount_ready = 2; /* suppress arming while stock loads the normal reel */
    unlock(p);
    return 0;
}

#define KEY(a,b,c,d) ((uint32_t)(a) | ((uint32_t)(b)<<8) | ((uint32_t)(c)<<16) | ((uint32_t)(d)<<24))
typedef struct { uint32_t key, address; uint8_t min, max, width; } Option;
static const Option options[] = {
    {KEY('v','s','o','p'),0x200012a8,0,2,4},
    {KEY('p','m','o','d'),0x200012b0,0,2,4},
    {KEY('o','m','o','d'),0x200012b4,0,1,4},
    {KEY('c','v','o','p'),0x200012bc,0,1,4},
    {KEY('c','k','o','p'),0x200012c0,0,2,4},
    {KEY('r','s','o','p'),0x200012c4,0,1,4},
    {KEY('p','m','i','n'),0x200012c8,0,1,4},
    {KEY('i','n','o','p'),0x200012cc,0,1,4},
    {KEY('g','n','s','m'),0x200012d0,0,1,4},
    {KEY('m','c','r','1'),0x200012d4,0,0,4},
    {KEY('m','c','r','2'),0x200012d8,0,0,4},
    {KEY('m','c','r','3'),0x200012dc,0,0,4},
    {KEY('t','a','p','e'),0x2002a0f4,0,1,1},
    {KEY('o','c','t','l'),0x2002a0f5,0,4,1},
    {KEY('f','x','s','l'),0x2002a0f6,0,2,1},
    {KEY('m','o','n','o'),0x2002a0f7,0,2,1},
    {KEY('c','p','u','l'),0x2002a0f8,0,1,1},
    {KEY('m','c','a','p'),0x2002a0f9,0,9,1},
    {KEY('s','l','d','m'),0x2002a0fa,0,1,1},
    {KEY('r','o','o','t'),0x2002a0fb,0,100,1},
    {KEY('t','l','e','n'),0x2002a0fc,1,16,1},
    {KEY('i','n','g','n'),0x2002a0fd,0,3,1},
    {KEY('s','c','a','l'),0x2002a604,0,0,2},
    {KEY('v','r','n','g'),0x2002a606,0,1,1},
    {KEY('d','e','n','s'),0x2002a607,0,1,1},
    {KEY('v','q','n','t'),0x2002a610,0,1,1},
    {KEY('m','l','o','p'),0x2002a611,0,1,1},
    {KEY('d','s','t','r'),0x2002a614,0,0,4},
    {KEY('v','u','n','i'),0x2002a618,0,1,1},
    {KEY('v','c','t','r'),0x2002a619,0,1,1},
    {KEY('d','r','y','k'),DRYK_ADDRESS,0,2,1},
    {KEY('d','l','e','n'),DLEN_ADDRESS,0,1,1},
};
enum { OPTION_COUNT = sizeof(options)/sizeof(options[0]) };
_Static_assert(OPTION_COUNT <= 32, "too many options for seen mask");

/* Keep the original 26 staging words and assembly-visible state in place. */
static volatile uint32_t *staged_option(unsigned i) {
    switch (i) {
        case 26: return &S->morph_loop_value;
        case 27: return &S->density_start_value;
        case 28: return &S->unity_value;
        case 29: return &S->center_value;
        case 30: return &S->dryk_value;
        case 31: return &S->dlen_value;
        default: return &S->values[i];
    }
}

static int ws(char c) { return c == ' ' || c == '\t' || c == '\r'; }
static const char *space(const char *p) { while (ws(*p)) ++p; return p; }
static int integer(const char **p, uint32_t *value) {
    uint32_t n = 0, digits = 0;
    while (**p >= '0' && **p <= '9') {
        if (++digits > 8) return 0;
        n = n*10u + (unsigned)(*(*p)++ - '0');
    }
    *value = n;
    return digits != 0;
}
static int density_start(const char *p, uint32_t *out) {
    uint32_t whole, tenth = 0;
    const char *start = p;
    if (!integer(&p, &whole) || p-start > 3 || whole > 128) return 0;
    if (*p == '.') {
        ++p;
        if (*p < '0' || *p > '9') return 0;
        tenth = (unsigned)(*p++ - '0');
    }
    uint32_t n = whole*10u + tenth;
    if (*space(p) || n < 1 || n > 1280) return 0;
    *out = n;
    return 1;
}
static int ratio(const char *p, uint32_t *out) {
    int negative = 0;
    uint32_t whole, fraction = 0, denominator = 1;
    if (*p == '-' || *p == '+') negative = *p++ == '-';
    if (!integer(&p, &whole) || whole > 16) return 0;
    if (*p == '.') {
        ++p;
        if (*p < '0' || *p > '9') return 0;
        while (*p >= '0' && *p <= '9') {
            if (denominator >= 100000000u) return 0;
            fraction = fraction*10u + (unsigned)(*p++ - '0');
            denominator *= 10u;
        }
    }
    if (*space(p)) return 0;
    float f = (float)whole + (float)fraction / (float)denominator;
    if (f < 0.0625f || f > 16.0f) return 0;
    union { float f; uint32_t u; } bits = {.f = negative ? -f : f};
    *out = bits.u;
    return 1;
}
static int scale(const char *p, uint32_t *out) {
    uint32_t mask = 0, n, count = 0;
    for (;;) {
        p = space(p);
        if (!integer(&p, &n) || n > 11) return 0;
        ++count;
        if (n) mask |= 1u << n;
        const char *after = space(p);
        if (!*after) { *out = mask; return n || count == 1; }
        if (!n) return 0; /* canonical scal 0 means an empty custom mask */
        if (*after == ',') p = after + 1;
        else if (after != p) p = after;
        else return 0;
    }
}

/* Unknown keys are ignored for compatibility; malformed/duplicate recognized
 * keys reject the entire transaction. Missing keys retain their live values.
 */
int reload_parse_line(const char *line) {
    const char *p = space(line);
    if (!*p) return 1;
    int preset = preset_key(p);
    if (preset >= 0) {
        uint32_t value, bit = 1u << (unsigned)preset;
        if ((PRESET_LIVE->mask & bit) ||
            !preset_number(p, (unsigned)preset, &value)) return 0;
        PRESET_LIVE->values[preset] = value;
        PRESET_LIVE->mask |= bit;
        return 1;
    }
    uint32_t key = 0;
    for (unsigned i=0; i<4; ++i) {
        if (!p[i]) return 1;
        key |= (uint32_t)(uint8_t)p[i] << (8*i);
    }
    unsigned i;
    for (i=0; i<OPTION_COUNT && options[i].key != key; ++i) {}
    if (i == OPTION_COUNT) return 1;
    if (!ws(p[4]) || (S->seen & (1u<<i))) return 0;
    const char *after_key = p + 4;
    p = space(after_key);
    uint32_t n;
    if (i >= 9 && i <= 11) { if (!ratio(p, &n)) return 0; }
    else if (i == 27) { if (!density_start(p, &n)) return 0; }
    else if (i == 22) { if (!scale(p, &n)) return 0; }
    else if (i >= 30) { if (!mode_digit(after_key, options[i].max, &n)) return 0; }
    else if (!integer(&p, &n) || *space(p) ||
             n < options[i].min || n > options[i].max) return 0;
    *staged_option(i) = n;
    S->seen |= 1u<<i;
    return 1;
}

/* Read at most 16 KiB. Long comments are discarded in the stream; long
 * significant lines, NUL/control bytes and disk errors fail closed. Line 1
 * is deliberately ignored: it contains saved reel/gain metadata, not options.
 */
static int read_options(void) {
    PRESET_LIVE->mask = 0;
    PRESET_LIVE->ready = 0;
    if (f_open(FIL, "options.txt", 1)) return 0;
    unsigned total = 0, line = 0, used = 0, comment = 0, valid = 1;
    S->seen = 0;
    for (;;) {
        if (f_read(FIL, BUFFER, 512, GOT) || *GOT > 512) { valid = 0; break; }
        unsigned got = *GOT;
        if (total + got > 16384) { valid = 0; break; }
        total += got;
        for (unsigned j=0; j<got; ++j) {
            char c = BUFFER[j];
            if (!c || ((uint8_t)c < 32 && c != '\n' && c != '\r' && c != '\t')) {
                valid = 0; break;
            }
            if (c == '\n') {
                LINE[used] = 0;
                if (line && !reload_parse_line(LINE)) { valid = 0; break; }
                ++line; used = comment = 0;
            } else if (!comment) {
                if (c == '/' && used && LINE[used-1] == '/') {
                    --used; comment = 1;
                } else if (used < 127) LINE[used++] = c;
                else { valid = 0; break; }
            }
        }
        if (!valid || !got) break;
    }
    if (valid && used) {
        LINE[used] = 0;
        if (line && !reload_parse_line(LINE)) valid = 0;
    }
    if (f_close(FIL)) valid = 0;
    return valid && line && (S->seen || PRESET_LIVE->mask);
}

/* Called before FatFs's common write core (also used by f_printf), and before
 * a write-mode f_open. The live WAV and main-frame splice FIL are the only
 * targets. Options/log writes do not invalidate the reconnect snapshot. */
void reload_dirty(uintptr_t file) {
    if (S->phase != PHASE_READING && S->live_file &&
        (file == S->live_file || file == S->live_file-552u))
        S->valid = S->snapshot_ready = 0;
}

/* mg204's FatFs FIL: fs+0, id+4, flag+6, err+7, fptr+8, fsize+12,
 * sclust+16, clust+20, dsect+24, dir_sect+28, dir_ptr+32, cltbl+36,
 * sector buffer+40 (512 bytes). Capture only clean, idle mounted state.
 * CID is the four CMD2 response words saved by the stock SD driver.
 */
static void remember(void *fatfs, volatile uint32_t *file) {
    uint32_t primask = lock();
    S->live_file = (uintptr_t)file;
    if (!quiet() || U8((uintptr_t)file+7) ||
        (U8((uintptr_t)file+6) & 0x62u) != 2u) {
        S->valid = S->snapshot_ready = 0;
        unlock(primask);
        return;
    }
    if (file[0] != (uintptr_t)fatfs || file[2] > file[3]) {
        S->valid = S->snapshot_ready = 0;
        unlock(primask);
        return;
    }
    int same = same_live_reel() && S->size==file[3] && S->cluster==file[4] &&
        S->dir_sector==file[7] && S->dir_offset==file[8]-(uintptr_t)fatfs;
    for (unsigned i=0;i<4;++i) if (S->cid[i]!=CID[i]) same=0;
    if (!same) S->snapshot_ready=0;
    S->reel = REEL; S->reels = REELS; S->data_start = DATA_START;
    S->position = file[2]; S->size = file[3]; S->cluster = file[4];
    S->dir_sector = file[7]; S->dir_offset = file[8] - (uintptr_t)fatfs;
    for (unsigned i=0; i<4; ++i) S->cid[i] = CID[i];
    S->valid = 1;
    unlock(primask);
    /* Trusted-card workflow: no audio scan, hashing or SD I/O here. */
    S->snapshot_ready = 1;
}

static int reconnect(void *fatfs, volatile uint32_t *file) {
    (void)fatfs;
    if (!same_live_reel() || S->snapshot_ready!=1) return 0;
    reel_name(LINE, S->reel);
    /* Existing file only: never create or truncate a reel. Opening refreshes
     * the mount ID, FAT chain and directory pointers invalidated by remount. */
    if (f_open((void *)file, LINE, 3)) return 0;
    /* Size is a basic sanity check, NOT content verification. Users must keep
     * WAVs, splice sidecars and the complete reel-name inventory identical. */
    int valid = file[3] == S->size && S->position <= file[3];
    if (valid) valid = !f_lseek((void *)file, S->position) && file[2] == S->position;
    if (valid) return 1;
    f_close((void *)file);
    file[0] = 0;
    return 0;
}

/* Called at the common loop head, including while SHIFT is released and the
 * card is absent. Return 1 to defer stock dispatch until audio commits. */
unsigned reload_service(void *fatfs, volatile uint32_t *file) {
    if (S->mount_ready == 2) {
        /* Normal startup/mount has returned from stock reel loading. Never
         * recall a splice against the preceding reel's metadata. */
        uint32_t p = lock();
        if (!(PRESET_NORMAL->ready == 2 && CARD == 1 && !quiet())) {
            if (PRESET_NORMAL->ready == 2 && CARD == 1) {
                presets_publish(PRESET_NORMAL);
            }
            PRESET_NORMAL->ready = 0;
            S->mount_ready = 0;
        }
        unlock(p);
    }
    if (S->phase == PHASE_READY) return 1;
    if (S->phase == PHASE_CLEANUP) {
        f_close((void *)file);
        file[0] = 0;
        f_mount(0, "", 0);
        S->phase = PHASE_PARKED;
        return 0;
    }
    if (CARD == 1) { remember(fatfs, file); return 0; }
    if (!quiet()) { S->valid = S->snapshot_ready = 0; return 0; }
    if (S->phase == PHASE_PARKED) {
        /* A rejected card must not fall through to an ordinary reel load.
         * With no usable detect switch, poll availability in main, at most
         * ten times/sec. A failed mount after release permits a fresh attempt.
         * No probe, mount or other I/O ever runs in an interrupt.
         */
        if (!S->owned && (uint32_t)(SAMPLES-S->absent) >= 4800u) {
            S->absent = SAMPLES;
            int missing = f_mount(fatfs, "", 1);
            f_mount(0, "", 0);
            if (missing) S->phase = PHASE_IDLE;
        }
        return 0;
    }
    if (S->phase != PHASE_REQUEST) return 0;
    S->phase = PHASE_READING;
    int valid = 0, attached = 0;
    if (same_live_reel() && S->snapshot_ready==1 &&
        (S->mount_ready == 1 || !f_mount(fatfs, "", 1))) {
        valid = read_options();
        if (valid) valid = presets_splice_valid(PRESET_LIVE);
        if (valid) valid = attached = reconnect(fatfs, file);
    }
    uint32_t primask = lock();
    valid = valid && quiet() && same_live_reel();
    S->mount_ready = 0;
    S->absent = SAMPLES;
    if (valid) {
        /* The trusted replacement now owns the fresh on-disk identity. */
        S->cluster=file[4];S->dir_sector=file[7];
        S->dir_offset=file[8]-(uintptr_t)fatfs;
        for (unsigned i=0;i<4;++i) S->cid[i]=CID[i];
        S->phase = PHASE_READY;
        __asm__ volatile("dmb" ::: "memory");
        S->pending = 1;
        unlock(primask);
        return 1;
    } else {
        S->result = 2;
        S->finished = SAMPLES;
    }
    unlock(primask);
    if (attached) f_close((void *)file);
    file[0] = 0;
    f_mount(0, "", 0);
    S->phase = PHASE_PARKED;
    return 0;
}

/* Stock RAM tables are read by the Morph preset lookup. Change all five words
 * together between audio blocks; default 0 leaves the stock image untouched. */
static void morph_loop_apply(void) {
    unsigned enabled = U8(0x2002a611) == 1;
    if (enabled == U8(0x2002a612)) return;
    U32(0x200003e0) = enabled ? 0x3f800000u : 0x40000000u;
    U32(0x200003e4) = enabled ? 0x3f800000u : 0x3fc00000u;
    U32(0x200003e8) = enabled ? 0x3f800000u : 0x3faaaaa8u;
    U32(0x200004f4) = enabled ? 1u : 2u;
    U32(0x200004f8) = enabled ? 1u : 3u;
    U8(0x2002a612) = enabled;
}
void reload_commit(void) {
    uint32_t initial_mask = lock();
    morph_loop_apply();
    unlock(initial_mask);
    if (!S->pending) return;
    uint32_t primask = lock();
    /* The hardware detect pin cannot validate removal here. Media loss is
     * checked by actual mount/read/seek I/O in main; after the final I/O,
     * removal is handled by the stock card-access failure path. */
    if (S->phase == PHASE_READY && (!quiet() || !same_live_reel() ||
                                  !presets_splice_valid(PRESET_LIVE))) {
        S->pending = 0;
        S->result = 2;
        S->finished = SAMPLES;
        S->phase = PHASE_CLEANUP;
        unlock(primask);
        return;
    }
    if (!quiet()) { unlock(primask); return; }
    for (unsigned i=0; i<OPTION_COUNT; ++i) {
        if (!(S->seen & (1u<<i))) continue;
        uint32_t address = options[i].address, value = *staged_option(i);
        uint32_t previous = options[i].width == 4 ? U32(address) :
                            options[i].width == 2 ? U16(address) : U8(address);
        if (previous == value && i != 21) continue;
        if (options[i].width == 4) U32(address) = value;
        else if (options[i].width == 2) U16(address) = (uint16_t)value;
        else U8(address) = (uint8_t)value;
        if (i >= 9 && i <= 11) U32(0x20022124 + (i-9)*4) = value;
        if (i == 0 || i == 13 || i == 22 || i == 23 || i == 25 || i == 28 || i == 29)
            U8(0x2002a007) = 0; /* invalidate only a stale Varispeed lock */
        if (i == 21) {
            U8(0x2002a0fe) = 0; /* existing main hook applies codec gain */
            U8(0x2002a0ff) = 0;
        }
    }
    /* An explicit dstr recalls the card's rate, even if the configured value
     * is unchanged but the performer moved the density knob. Missing dstr
     * preserves both the live interval and its phase. Commit only after every
     * setting and the reel reconnection have passed validation. Existing
     * voices/playheads are untouched; the next birth waits one new interval.
     */
    if (S->seen & (1u << 27)) {
        uint32_t n = U32(0x2002a614);
        uint32_t interval = (480000u + n/2u) / n;
        U32(0x2002a800) = 1;
        U32(0x2002a808) = interval;
        U32(0x2002a80c) = interval;
    }
    presets_publish(PRESET_LIVE);
    morph_loop_apply();
    S->pending = 0;
    S->result = 1;
    S->finished = SAMPLES;
    if (S->phase == PHASE_READY) {
        CARD = 1; /* publish only after a fresh live FIL and settings are ready */
        S->phase = PHASE_PARKED;
    }
    unlock(primask);
}

unsigned reload_led_mask(unsigned mask) {
    unsigned on = 0, phase = S->phase, elapsed = SAMPLES - S->finished;
    if (phase == PHASE_IDLE || phase == PHASE_TIMING) return mask;
    if (phase == PHASE_ARMED) on = 1;
    else if (phase == PHASE_REQUEST || phase == PHASE_READING ||
             phase == PHASE_READY || S->pending)
        on = (SAMPLES / 6000u) & 1u;
    else if (S->result && elapsed < (S->result == 1 ? 19200u : 28800u))
        on = elapsed % 9600u < 4800u;
    else return mask;
    return (mask & ~1u) | on;
}
