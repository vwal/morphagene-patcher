/* The panel arms a different-reel request on the final button press. The
 * audio scheduler can mark it ready; only the native foreground opens files.
 * Within the loaded reel, hand the choice directly to stock Organize. */
#define GENE_WAIT       PRESET_U32(0x20028fa0)
#define PICKER_PHASE    PRESET_U8(0x20028f58)
#define PICKER_MOUNT    PRESET_U16(0x20028f5a)
#define DEST_BANK       PRESET_U8(0x20028f5c)
#define DEST_REEL       PRESET_U8(0x20028f5d)
#define LIVE_BANK       PRESET_U8(0x20028ff0)
#define LIVE_REEL       PRESET_U8(0x20028ff1)
#define BANK_OPTION     PRESET_U8(0x2002a61f)
#define OMOD            PRESET_U32(0x200012b4)
#define SD_FLAGS        PRESET_U32(0x20022074)
#define NAV_REQUEST     PRESET_U32(0x200012e0)
#define SPLICE_REQUEST  PRESET_U32(0x20021cbc)
#define LIVE_COUNT      PRESET_U32(0x2002208c)

enum { WAIT_FOR_GENE = 1, READY_TO_LOAD = 2, COMMIT_PHASE = 7 };
extern unsigned picker_has_gene_to_wait_for(void);
#define d22_leave  ((void (*)(void))0x080542ad)
#define d22_commit ((int (*)(unsigned, unsigned, unsigned))0x08054c55)

static int same_reel(unsigned bank, unsigned reel) {
    return reel && bank == BANK_OPTION && bank == LIVE_BANK && reel == LIVE_REEL;
}

static int valid_picker(unsigned phase) {
    return PICKER_PHASE == phase && PICKER_MOUNT == MOUNT && CARD == 1 && MODE == 1 &&
           BANK_OPTION >= 1 && BANK_OPTION <= 8 &&
           !PRESET_U32(0x20022108) && !PRESET_U32(0x20021320);
}

/* Caller holds PRIMASK. Nothing here opens a file, clears a voice, changes
 * the active splice, or resets playback position. Native omod resolves the
 * requested splice at its usual point in the audio block. */
static void submit_live_splice(unsigned splice) {
    if (PRESET->magic == PRESET_MAGIC) {
        volatile PresetLane *lane = preset_lane(PRESET_SPLICE);
        lane->seen_generation = PRESET->generation;
        lane->held = 0;
    }
    PRESET_U8(0x2002a082) = 0;  /* release an older Turing Organize pickup */
    NAV_REQUEST = 0;
    SPLICE_REQUEST = splice;
    /* Park Organize even if a preset held it away from the physical position
     * before entry. The D23 leave hook records the pickup point on exit. */
    HANDOFF->magic = CANCELED;
    d22_leave();
}

static unsigned lock_timing(void) {
    unsigned saved;
    __asm__ volatile ("mrs %0, primask\n cpsid i" : "=r"(saved) :: "memory");
    return saved;
}

static void unlock_timing(unsigned saved) {
    __asm__ volatile ("msr primask,%0" :: "r"(saved) : "memory");
}

void picker_confirm_recording(unsigned splice) {
    unsigned saved = lock_timing();
    int local = same_reel(DEST_BANK, DEST_REEL);
    if (!valid_picker(6)) {
        d22_leave();
    } else if (local && splice && splice <= LIVE_COUNT && !(SD_FLAGS & ~0x80u)) {
        submit_live_splice(splice);
    } else {
        GENE_WAIT = !local && !OMOD ? WAIT_FOR_GENE : 0;
        PICKER_PHASE = COMMIT_PHASE;
    }
    unlock_timing(saved);
}

int picker_service_recording(unsigned bank, unsigned reel, unsigned splice) {
    if (!valid_picker(COMMIT_PHASE)) return -1;
    if (splice && same_reel(bank, reel)) {
        unsigned saved = lock_timing();
        int selected = -1;
        if (valid_picker(COMMIT_PHASE) && same_reel(bank, reel) && splice <= LIVE_COUNT) {
            selected = 0;
            if (!(SD_FLAGS & ~0x80u)) {
                submit_live_splice(splice);
                selected = 1;
            }
        }
        unlock_timing(saved);
        return selected;
    }
    if (splice && GENE_WAIT == WAIT_FOR_GENE) {
        if (picker_has_gene_to_wait_for()) return 0;
        /* The head stopped or there are no active Genes. Keep that decision
         * if the SD dispatcher has to retry after another foreground write. */
        unsigned saved = lock_timing();
        if (valid_picker(COMMIT_PHASE) && GENE_WAIT == WAIT_FOR_GENE) GENE_WAIT = READY_TO_LOAD;
        unlock_timing(saved);
    }
    return d22_commit(bank, reel, splice);
}
