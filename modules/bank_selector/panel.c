/* TIM2 only reads controls and publishes menu actions. FatFs runs in the
 * foreground, with the currently open reel in place until the final chord. */
#include <stdint.h>
#include <stddef.h>

extern int selector_bank_mask(void);
extern int selector_reels(unsigned bank, uint32_t *mask);
extern int selector_splices(unsigned bank, unsigned slot);
extern int selector_commit(unsigned bank, unsigned slot, unsigned splice);

#define BANK_WORD(addr) (*(volatile uint32_t *)(addr))
#define BANK_BYTE(addr) (*(volatile uint8_t *)(addr))
#define BANK_GENERATION (*(volatile uint16_t *)0x20024278)
#define PANEL_MODE BANK_WORD(0x20021338)
#define PANEL_STATE BANK_WORD(0x20001020)
#define PANEL_ADC BANK_WORD(0x20021c70)
#define PANEL_LOW BANK_WORD(0x20022080)
#define PANEL_HIGH BANK_WORD(0x20022078)
#define PANEL_CARD BANK_WORD(0x20001290)
#define PANEL_NOW BANK_WORD(0x20021c88)
#define PANEL_FLAGS BANK_WORD(0x20022074)

enum panel_phase {
    PANEL_IDLE, SCAN_BANKS, CHOOSE_BANK, SCAN_REELS, CHOOSE_REEL,
    SCAN_SPLICES, CHOOSE_SPLICE, COMMIT_SPLICE, DRAIN_BUTTONS
};
typedef struct {
    uint8_t phase, consumed;
    uint16_t generation;
    uint8_t bank, reel;
    uint16_t splice;
    uint32_t token, mask;
    uint16_t choices;
    uint16_t can_blank;
} panel_state_t;
#define MENU (*(volatile panel_state_t *)0x20028f58)
_Static_assert(offsetof(panel_state_t, token) == 8, "storage ABI");
_Static_assert(sizeof(panel_state_t) <= 0x28, "panel RAM reservation");

static uint32_t panel_lock(void) {
    uint32_t saved;
    __asm__ volatile ("mrs %0, primask\n cpsid i" : "=r"(saved) :: "memory");
    return saved;
}
static void panel_unlock(uint32_t saved) {
    __asm__ volatile ("msr primask,%0" :: "r"(saved) : "memory");
}

static void panel_leave(void) {
    MENU.token++;
    PANEL_MODE = 0;
    PANEL_STATE = 19;  /* the next complete release returns to normal playback */
    MENU.phase = DRAIN_BUTTONS;
}
void panel_begin(void) {
    MENU.token++;
    MENU.generation = BANK_GENERATION;
    MENU.choices = 0;
    MENU.mask = 0;
    MENU.consumed = 1;  /* release every button used for entry */
    MENU.phase = SCAN_BANKS;
    PANEL_STATE = 18;
}

/* Calibrated integer position; avoid borrowing any floating-point registers
 * from the audio engine in the panel interrupt. */
static unsigned knob_position(unsigned *span) {
    unsigned raw = PANEL_ADC;
    unsigned low = PANEL_LOW, high = PANEL_HIGH;
    if (high <= low || high > 4095) { low = 0; high = 4095; }
    *span = high - low;
    if (raw <= low) return 0;
    return raw < high ? raw - low : *span;
}

/* Native short reel mode ordinarily resamples only after ADC movement. On
 * release or confirmation synchronize New with the physical position, even
 * when Organize has been stationary throughout the gesture. Existing-reel
 * previews retain their normal movement/acceptance behavior. The native
 * bin calculation at 0x080286d2 subtracts 0.001 before scaling by N+1. */
void panel_short_cursor(void) {
    if (PANEL_CARD != 1 || PANEL_MODE != 1) return;
    unsigned count = BANK_WORD(0x200012a0), span;
    if (!count || count > 32) return;
    unsigned knob = knob_position(&span);
    unsigned scaled = knob * 1000u;
    unsigned candidate = 1;
    if (scaled > span)
        candidate += (scaled - span) * (count + 1u) / (span * 1000u);
    if (candidate > count && count < 32)
        BANK_WORD(0x20001040) = 1000;   /* native New Reel preview */
    else if (BANK_WORD(0x20001040) == 1000)
        BANK_WORD(0x20001040) = candidate > count ? count : candidate;
}

static unsigned panel_choice(void) {
    unsigned count = MENU.choices, span;
    if (!count) return 0;   /* all of an empty bank selects New Reel */
    unsigned raw = knob_position(&span);
    unsigned width = span + 1;
    if (MENU.phase == CHOOSE_REEL && MENU.can_blank) {
        width = span - span / 20;       /* ceil(95% of calibrated travel) */
        if (raw >= width) return 0;
    }
    unsigned cell = raw * count / width;
    if (MENU.phase == CHOOSE_SPLICE) return cell + 1;
    uint32_t mask = MENU.mask;
    while (cell-- && mask) mask &= mask - 1;
    return mask ? (unsigned)__builtin_ctz(mask) + 1 : 0;
}

void panel_buttons(unsigned splice, unsigned rec, unsigned shift) {
    if (MENU.phase == DRAIN_BUTTONS) {
        if (!(splice | rec | shift)) {
            PANEL_STATE = 1;
            MENU.phase = PANEL_IDLE;
        }
        return;
    }
    if (shift || PANEL_CARD != 1 || BANK_GENERATION != MENU.generation ||
        PANEL_MODE != 1 || !BANK_BYTE(0x2002a61f)) {
        panel_leave();
        return;
    }
    if (!(splice | rec)) {
        MENU.consumed = 0;
        return;
    }
    if (MENU.consumed || !splice || !rec) return;
    MENU.consumed = 1;
    switch (MENU.phase) {
    case CHOOSE_BANK:   MENU.bank = panel_choice();   MENU.phase = SCAN_REELS; break;
    case CHOOSE_REEL:
        MENU.reel = panel_choice();
        MENU.splice = 0;
        MENU.phase = MENU.reel ? SCAN_SPLICES : COMMIT_SPLICE;
        break;
    case CHOOSE_SPLICE: MENU.splice = panel_choice(); MENU.phase = COMMIT_SPLICE; break;
    default: break;  /* overlapping confirmations never fall through to stock */
    }
}

void panel_service(void) {
    unsigned phase = MENU.phase;
    if (!(phase & 1) || phase > COMMIT_SPLICE) return;
    if (PANEL_CARD != 1 || MENU.generation != BANK_GENERATION ||
        PANEL_MODE != 1 || PANEL_FLAGS & ~0x80u) return;
    uint32_t token = MENU.token, mask = 0;
    int result = 0;
    switch (phase) {
    case SCAN_BANKS:
        result = selector_bank_mask();
        if (result > 0) mask = (uint32_t)result;
        break;
    case SCAN_REELS: result = selector_reels(MENU.bank, &mask); break;
    case SCAN_SPLICES: result = selector_splices(MENU.bank, MENU.reel); break;
    case COMMIT_SPLICE: result = selector_commit(MENU.bank, MENU.reel, MENU.splice); break;
    default: return;
    }
    uint32_t saved = panel_lock();
    if (token == MENU.token && phase == MENU.phase) {
        if (phase == COMMIT_SPLICE) {
            if (result) panel_leave();
        } else if (PANEL_CARD != 1 || MENU.generation != BANK_GENERATION ||
                   PANEL_MODE != 1 || result <= 0 ||
                   (phase == SCAN_REELS && !mask && result != 2)) {
            panel_leave();
        } else {
            unsigned count = 0;
            for (uint32_t bits = mask; bits; bits &= bits - 1) ++count;
            MENU.mask = mask;
            MENU.can_blank = phase == SCAN_REELS && result == 2;
            MENU.choices = phase == SCAN_SPLICES ? (unsigned)result : count;
            MENU.phase = phase + 1;
        }
    }
    panel_unlock(saved);
}

void panel_lights(void) {
    unsigned phase = MENU.phase;
    if (phase == DRAIN_BUTTONS || !phase) return;
    unsigned beat = PANEL_NOW % 96000u;
    unsigned reel = 8, splice = 8; /* native dark color index */
    unsigned choice = panel_choice();
    switch (phase) {
    case CHOOSE_BANK:
        reel = (beat % 48000u < 30000u) ? (choice & 7u) : 8;
        break;
    case CHOOSE_REEL:
        if (!choice && MENU.can_blank)
            reel = beat < 48000u ? 9 : 0; /* native pink/white New Reel colors */
        else if (MENU.choices > 1 || beat < 14400u || (beat >= 26400u && beat < 40800u))
            reel = choice & 7u;
        break;
    case CHOOSE_SPLICE:
        reel = MENU.reel & 7u;
        splice = choice & 7u;
        break;
    default: /* scanning; no incomplete choice is displayed */ break;
    }
    BANK_WORD(0x20001038) = reel;
    BANK_WORD(0x2000103c) = splice;
}
