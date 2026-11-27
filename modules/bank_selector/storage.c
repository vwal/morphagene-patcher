/* D22 panel inventory. All directory and metadata reads run in the foreground.
 * Only selector_commit may change the loaded bank or schedule a native open. */
#include <stdint.h>

#define U8(a)  (*(volatile uint8_t *)(a))
#define U16(a) (*(volatile uint16_t *)(a))
#define U32(a) (*(volatile uint32_t *)(a))
#define BANK             U8(0x2002a61f)
#define MODE             U32(0x20021338)
#define CARD             U32(0x20001290)
#define FLAGS            U32(0x20022074)
#define CURSOR           U32(0x20001040)
#define REEL_COUNT       U32(0x200012a0)
#define REC_ACTIVE       U32(0x20022108)
#define REC_REQUEST      U32(0x20021320)
#define MOUNT_GENERATION U16(0x20024278)
#define BROWSER_PHASE    U8(0x20028f58)
#define BROWSER_MOUNT    U16(0x20028f5a)
#define BROWSER_TOKEN    U32(0x20028f60)
#define LOADED_BANK      U8(0x20028ff0)
#define LOADED_SLOT      U8(0x20028ff1)
#define SPLICE_COUNT     U32(0x2002208c)
#define SPLICE_REQUEST   U32(0x20021cbc)
#define SPLICE_ACTIVE    U32(0x20021de4)
#define ORG_ACCEPTED     U32(0x200220ac)
#define ORG_ADC          U32(0x20021c70)
#define NAVIGATION       U32(0x200012e0)

#define f_stat  ((int (*)(const char *, void *))0x08033129)
#define f_open  ((int (*)(void *, const char *, unsigned))0x08032261)
#define f_read  ((int (*)(void *, void *, unsigned, unsigned *))0x080323fd)
#define f_seek  ((int (*)(void *, unsigned))0x08032be9)
#define f_close ((int (*)(void *))0x080327a9)
#define f_gets  ((char *(*)(char *, int, void *))0x0803449d)
#define make_name ((void (*)(char *, unsigned, unsigned, int))0x08051e79)
#define rb_recount ((int (*)(unsigned))0x080521b5)

/* SDRAM per channel: native startup writes this capacity at 0x08026926. */
enum { MAX_FRAMES = 8388608, MAX_SPLICES = 300, FR_NO_FILE = 4, FR_NO_PATH = 5, AM_DIR = 16 };
enum { PROBE_ERROR = -1, PROBE_EMPTY = 0, PROBE_OK = 1, PROBE_BLANK = 2 };
enum { NEW_REEL = 1000 };

typedef struct {
    unsigned frames, cue_pos, cue_count;
} Wave;

typedef struct {
    unsigned count, saw_embedded;
    uint32_t position[MAX_SPLICES - 1];
} Markers;

static int read_at(uint32_t *file, unsigned pos, void *dst, unsigned size) {
    unsigned actual;
    return (pos == file[2] || !f_seek(file, pos)) &&
           !f_read(file, dst, size, &actual) && actual == size;
}

static int probe_wave(uint32_t *file, Wave *wave) {
    uint32_t w[4];
    unsigned size = file[3];
    if (size < 44) return PROBE_EMPTY;
    if (!read_at(file, 0, w, 12)) return PROBE_ERROR;
    if (w[0] != 0x46464952u || w[2] != 0x45564157u || w[1] < 4) return PROBE_EMPTY;
    /* Module-authored marker edits can leave the outer RIFF length one or
     * more cue records ahead of, or behind, physical EOF. Like native mg204,
     * trust each complete chunk's own length up to the physical file bound.
     * A complete declared container can also have unrelated bytes appended. */
    unsigned declared_end = w[1] >= size - 8 ? size : w[1] + 8;
    unsigned end = size;
    unsigned pos = 12, format_ok = 0, have_fmt = 0, have_data = 0;
    wave->frames = wave->cue_count = wave->cue_pos = 0;
    while (pos < end) {
        if (end - pos < 8) {
            if (pos >= declared_end) break; /* trailing bytes outside RIFF */
            return PROBE_EMPTY;
        }
        if (!read_at(file, pos, w, 8)) return PROBE_ERROR;
        unsigned id = w[0], len = w[1];
        unsigned outside = pos >= declared_end;
        pos += 8;
        if (len > end - pos) {
            if (outside && id != 0x61746164u && id != 0x20657563u &&
                id != 0x20746d66u) break;
            return PROBE_EMPTY;
        }
        if (id == 0x20746d66u && !have_fmt) {
            have_fmt = 1;
            if (len < 16) return PROBE_EMPTY;
            if (!read_at(file, pos, w, 16)) return PROBE_ERROR;
            /* mg204's writable reel loader accepts stereo fl32. */
            format_ok = w[0] == 0x00020003u && w[1] && w[3] == 0x00200008u;
        } else if (id == 0x61746164u && !have_data) {
            have_data = 1;
            if (len & 7u) return PROBE_EMPTY;
            wave->frames = len / 8;
        } else if (id == 0x20657563u && !wave->cue_pos) {
            if (len < 4) return PROBE_EMPTY;
            if (!read_at(file, pos, w, 4)) return PROBE_ERROR;
            if (w[0] > (len - 4) / 24 || w[0] > 32767) return PROBE_EMPTY;
            wave->cue_pos = pos + 4;
            wave->cue_count = w[0];
        }
        pos += len;
        if ((len & 1u) && pos < end) ++pos;
    }
    if (!format_ok || !have_data || wave->frames > MAX_FRAMES) return PROBE_EMPTY;
    if (wave->frames) return PROBE_OK;
    /* A stock blank may have an end cue at zero. A nonzero cue on an empty
     * file could load outside its data under the stock legacy marker path. */
    for (unsigned n = 0; n < wave->cue_count; ++n) {
        uint32_t record[6];
        if (!read_at(file, wave->cue_pos + n*24, record, sizeof(record))) return PROBE_ERROR;
        if (record[1]) return PROBE_EMPTY;
    }
    return PROBE_BLANK;
}

/* Keep the same positive, unique in-range boundaries as the native loader.
 * An explicit EOF cue suppresses fallback to spliceN.txt but adds no extra
 * interval. Sample zero is implicit. Native uses RIFF dwPosition, not ID.
 * Unsorted authored cues are legal; do not discard a short opening region. */
static void mark(Markers *marks, unsigned frame, unsigned end) {
    if (!frame || frame > MAX_FRAMES) return;
    marks->saw_embedded = 1;
    if (frame >= end || marks->count >= MAX_SPLICES - 1) return;
    for (unsigned n = 0; n < marks->count; ++n)
        if (marks->position[n] == frame) return;
    marks->position[marks->count++] = frame;
}

static int span_count(uint32_t *file, Wave *w, Markers *marks) {
    unsigned pos = w->cue_pos;
    for (unsigned n = 0; n < w->cue_count; ++n, pos += 24) {
        uint32_t cue[6];
        if (!read_at(file, pos, cue, sizeof(cue))) return PROBE_ERROR;
        mark(marks, cue[1], w->frames);
    }
    return (int)marks->count + 1;
}

/* Same three decimal fields as the stock 64-byte f_gets loop: the second
 * field is a frame, and a nonzero third field enables that marker. */
static int number(const char **p, unsigned *value) {
    const char *s = *p;
    while (*s == ' ') ++s;
    unsigned negative = *s == '-';
    if (negative || *s == '+') ++s;
    unsigned n = 0;
    if (*s < '0' || *s > '9') return 0;
    do {
        unsigned d = (unsigned)(*s++ - '0');
        if (n > (UINT32_MAX - d) / 10) return 0;
        n = 10*n + d;
    } while (*s >= '0' && *s <= '9');
    *p = s;
    *value = negative ? 0u-n : n;
    return 1;
}

static int legacy_splices(uint32_t *file, const char *path, unsigned end, Markers *marks) {
    int err = f_open(file, path, 1);
    if (err == FR_NO_FILE) return 1;
    if (err) return PROBE_ERROR;
    char line[64];
    while (f_gets(line, sizeof(line), file)) {
        const char *p = line;
        unsigned id, frame, enabled;
        if (number(&p, &id) && *p == ' ' && number(&p, &frame) &&
            *p == ' ' && number(&p, &enabled) && enabled)
            mark(marks, frame, end);
    }
    int bad = ((uint8_t *)file)[7] != 0;
    return f_close(file) || bad ? PROBE_ERROR : (int)marks->count + 1;
}

static int reel_probe(const char *path, Wave *wave) {
    uint32_t file[138];
    if (f_open(file, path, 1)) return PROBE_ERROR;
    int result = probe_wave(file, wave);
    return f_close(file) ? PROBE_ERROR : result;
}

/* The root exists on every mounted card. Other banks are literal existing
 * directories. The picker never creates a directory, even at confirmation. */
static int folder_exists(unsigned bank) {
    if (bank < 1 || bank > 8) return -1;
    if (bank == 1) return 1;
    uint32_t info[8];
    info[6] = 0;
    char folder[] = "bank0";
    folder[4] += (char)bank;
    int err = f_stat(folder, info);
    if (err == FR_NO_FILE || err == FR_NO_PATH) return 0;
    if (err) return -1;
    return !!(info[2] & AM_DIR);
}

typedef struct {
    uint32_t all, recorded, blanks, reserved;
} ReelSlots;

/* Native bank compaction counts every WAV slot, including a damaged file.
 * Never repurpose a malformed WAV, an unpaired marker file, or a directory. */
static int scan(unsigned bank, ReelSlots *slots) {
    uint32_t info[8];
    char path[32];
    Wave wave;
    slots->all = slots->recorded = slots->blanks = slots->reserved = 0;
    if (folder_exists(bank) != 1) return PROBE_ERROR;
    info[6] = 0;
    for (unsigned n = 1; n <= 32; ++n) {
        uint32_t bit = 1u << (n-1);
        make_name(path, bank, n, 0);
        int err = f_stat(path, info);
        if (err && err != FR_NO_FILE) return PROBE_ERROR;
        if (!err) {
            if (info[2] & AM_DIR) {
                slots->reserved |= bit;
                continue;
            }
            slots->all |= bit;
            if (info[0] < 44) continue;
            int kind = reel_probe(path, &wave);
            if (kind < 0) return PROBE_ERROR;
            if (kind == PROBE_OK) slots->recorded |= bit;
            if (kind != PROBE_BLANK) continue;
        }
        /* A zero-frame WAV without its own markers can still import a
         * spliceN.txt. Leave that pair alone rather than offering it as new. */
        make_name(path, bank, n, 1);
        err = f_stat(path, info);
        if (err == FR_NO_FILE) {
            if (slots->all & bit) slots->blanks |= bit;
        } else if (err) return PROBE_ERROR;
        else if (!(slots->all & bit)) slots->reserved |= bit;
    }
    return PROBE_OK;
}

static unsigned new_target(const ReelSlots *slots) {
    unsigned blank = slots->blanks ? (unsigned)__builtin_ctz(slots->blanks) + 1 : 0;
    if (!slots->recorded && blank) return blank;
    if (slots->all == UINT32_MAX) return blank;
    /* rb_recount checks and compacts every slot in a sparse bank. An orphan
     * makes that operation unsafe. Dense banks append at count+1 directly. */
    if (slots->all & (slots->all+1u)) return slots->reserved ? 0 : NEW_REEL;
    if (slots->reserved & (slots->all+1u)) return 0;
    return NEW_REEL;
}

int selector_bank_mask(void) {
    unsigned mask = 0;
    for (unsigned bank = 1; bank <= 8; ++bank) {
        int present = folder_exists(bank);
        if (present < 0) return PROBE_ERROR;
        if (present) mask |= 1u << (bank-1);
    }
    return (int)mask;
}

int selector_reels(unsigned bank, uint32_t *mask) {
    ReelSlots slots;
    if (scan(bank, &slots) < 0) return PROBE_ERROR;
    *mask = slots.recorded;
    return new_target(&slots) ? 2 : 1;
}

int selector_splices(unsigned bank, unsigned slot) {
    if (bank < 1 || bank > 8 || slot < 1 || slot > 32) return PROBE_ERROR;
    char path[32];
    uint32_t file[138];
    Wave wave;
    Markers marks;
    marks.count = marks.saw_embedded = 0;
    make_name(path, bank, slot, 0);
    if (f_open(file, path, 1)) return PROBE_ERROR;
    int count = probe_wave(file, &wave);
    if (count == PROBE_BLANK) count = 0;
    if (count == PROBE_OK) count = span_count(file, &wave, &marks);
    if (f_close(file)) return PROBE_ERROR;
    if (count <= 0 || marks.saw_embedded) return count;
    make_name(path, bank, slot, 1);
    return legacy_splices(file, path, wave.frames, &marks);
}

typedef struct {
    uint32_t magic;
    uint16_t generation, splice;
    uint8_t bank, slot, create;
} Pending;
#define PENDING ((volatile Pending *)0x20028f80)
#define LOAD_MAGIC 0x31444c53u
#define CURSOR_MAGIC 0x31434c53u
#define END_MAGIC 0x31454c53u

static int valid_session(unsigned token) {
    return BROWSER_PHASE == 7 && BROWSER_TOKEN == token &&
           MOUNT_GENERATION == BROWSER_MOUNT && CARD == 1 && MODE == 1 &&
           !REC_ACTIVE && !REC_REQUEST && BANK >= 1 && BANK <= 8;
}

/* A final bank change publishes the same count/slot pair expected by mg204
 * recording and the short reel browser. Only sparse target catalogs need the
 * existing checked WAV + legacy-sidecar compaction; it keeps their pairing
 * and refuses to move an open reel. Browsing above is strictly read-only. */
int selector_commit(unsigned bank, unsigned slot, unsigned splice) {
    ReelSlots slots;
    unsigned token = BROWSER_TOKEN;
    if (!valid_session(token) || slot > 32 || (!!slot != !!splice)) return -1;
    if (FLAGS & ~0x80u) return 0;
    if (scan(bank, &slots) < 0) return -1;
    if (!slot) {
        slot = new_target(&slots);
        if (!slot) return -1;
    } else {
        if (!(slots.recorded & (1u << (slot-1))) || splice > MAX_SPLICES ||
            selector_splices(bank, slot) < (int)splice) return -1;
    }
    if (!valid_session(token)) return -1;
    if (FLAGS & ~0x80u) return 0;
    unsigned create = slot == NEW_REEL, count = 0, final_slot = 0;
    for (unsigned n = 0; n < 32; ++n) {
        if (slots.all & (1u << n)) ++count;
        if (n+1 == slot) final_slot = count;
    }
    if (create) final_slot = count + 1;
    if ((slots.all & (slots.all+1u)) && rb_recount(bank) != (int)count) return -1;
    uint32_t saved;
    __asm__ volatile ("mrs %0, primask\n cpsid i" : "=r"(saved) :: "memory");
    int result = -1;
    if (valid_session(token) && !(FLAGS & ~0x80u)) {
        PENDING->generation = MOUNT_GENERATION;
        PENDING->bank = bank;
        PENDING->slot = final_slot;
        PENDING->splice = splice;
        PENDING->create = create;
        PENDING->magic = CURSOR_MAGIC;
        REEL_COUNT = count;
        CURSOR = create ? NEW_REEL : final_slot;
        BANK = bank;
        MODE = 0;
        /* The native chord at 0x08025532 clears its UI and audio latches. */
        U32(0x200213c0) = U32(0x200213b4) = U32(0x200213a8) = U32(0x200012e4) = 0;
        FLAGS |= 0x1000; /* native existing-reel load also schedules options save */
        result = 1;
    }
    __asm__ volatile ("msr primask, %0" :: "r"(saved) : "memory");
    return result;
}

/* Called only after TIM2 accepts the ordinary exit/confirm chord, never on
 * a preview. A later SHIFT edge cannot change the already-confirmed action. */
void selector_capture_new(void) {
    if (CURSOR != NEW_REEL || CARD != 1 || REEL_COUNT >= 32) return;
    PENDING->generation = MOUNT_GENERATION;
    PENDING->bank = BANK;
    PENDING->slot = REEL_COUNT + 1;
    PENDING->create = 1;
    PENDING->splice = 0;
    PENDING->magic = CURSOR_MAGIC;
}

/* Native tests SHIFT again in the foreground before consuming cursor 1000.
 * After an explicit new-reel confirmation, take its checked CREATE_NEW
 * branch even if SHIFT changed between TIM2 and the main loop. Otherwise
 * native can save bank/cursor without ever changing the live writable FIL. */
int selector_open_cursor(void) {
    if (PENDING->magic != CURSOR_MAGIC) {
        PENDING->magic = 0;           /* supersede an interrupted older open */
        return 0;
    }
    if (PENDING->generation != MOUNT_GENERATION || CARD != 1 ||
        BANK != PENDING->bank || (PENDING->create && (REEL_COUNT >= 32 ||
        PENDING->slot != REEL_COUNT + 1))) {
        PENDING->magic = 0;
        return -1;
    }
    CURSOR = PENDING->create ? NEW_REEL : PENDING->slot;
    PENDING->magic = LOAD_MAGIC;
    return PENDING->create;
}

/* Native loading clears accepted knob readings twice: at the end of WAV
 * parsing and at the end of sample transfer. Apply the choice after those
 * resets only for this open, and release the pickup on the next knob move. */
int selector_finish_load(unsigned transferred) {
    if (PENDING->magic != (transferred ? END_MAGIC : LOAD_MAGIC)) return 0;
    unsigned splice = PENDING->splice;
    if (PENDING->generation == MOUNT_GENERATION && CARD == 1 &&
        PENDING->bank == LOADED_BANK && PENDING->slot == LOADED_SLOT) {
        if (!splice) {
            /* A new/blank reel has nothing to navigate. Let stock perform
             * its native empty-reel initialization and first-take behavior. */
            PENDING->magic = 0;
            return !transferred && SPLICE_COUNT != 0;
        }
        if (splice > SPLICE_COUNT) {
            PENDING->magic = 0;
            return !transferred; /* original open no longer contains this splice */
        }
        uint32_t saved;
        __asm__ volatile ("mrs %0, primask\n cpsid i" : "=r"(saved) :: "memory");
        /* Already consumed settings-file recalls belong to the old reel. Honor
         * this explicit panel selection; the next settings generation can
         * still publish its own splc in the normal way. */
        if (U32(0x2002a660) == 0x54535250u) {
            U32(0x2002a6c8) = U32(0x2002a664); /* splice lane seen_generation */
            U32(0x2002a6d8) = 0;               /* release previous preset pickup */
        }
        U8(0x2002a082) = 0;                    /* release older Turing pickup */
        NAVIGATION = 0;
        ORG_ACCEPTED = ORG_ADC;
        SPLICE_REQUEST = splice;
        SPLICE_ACTIVE = splice;
        PENDING->magic = transferred ? 0 : END_MAGIC;
        __asm__ volatile ("msr primask, %0" :: "r"(saved) : "memory");
    } else PENDING->magic = 0;
    return 0;
}
