/* Organize doubles as the menu dial. Remember where it was parked on cancel,
 * so the first audio block cannot interpret a menu choice as a splice move.
 * Its existing >8 ADC-count movement threshold returns control to playback. */
#include "../preset_recall/preset.h"

#define ORG_ADC PRESET_U32(0x20021c70)
#define MODE PRESET_U32(0x20021338)
#define CARD PRESET_U32(0x20001290)
#define MOUNT PRESET_U16(0x20024278)
#define CANCELED 0x4f524743u

typedef struct {
    uint32_t magic, entry_adc, exit_adc, mount, preset_generation;
} OrganizeHandoff;
#define HANDOFF ((volatile OrganizeHandoff *)0x20028f8c)
_Static_assert(sizeof(OrganizeHandoff) == 20, "assembly RAM reservation");

static unsigned moved(unsigned a, unsigned b) {
    return a > b ? a - b > 8u : b - a > 8u;
}

void picker_end_organize(void) {
    unsigned physical = ORG_ADC;
    /* A successful commit sets MODE=0 before leaving the panel. Card removal
     * or a different mount likewise relinquishes control immediately. */
    if (MODE != 1 || CARD != 1 || MOUNT != PRESET_U16(0x20028f5a) ||
        (HANDOFF->magic != CANCELED && !moved(physical, HANDOFF->entry_adc))) {
        HANDOFF->magic = 0;
        return;
    }
    HANDOFF->exit_adc = physical;
    HANDOFF->mount = MOUNT;
    HANDOFF->preset_generation = PRESET->generation;
    /* Menu travel must not count as crossing a recalled primary or secondary
     * pickup target when ordinary movement resumes. Keep both holds intact. */
    if (PRESET->magic == PRESET_MAGIC) {
        preset_lane(PRESET_SPLICE)->last_physical = physical;
        preset_lane(PRESET_EVOLUTION)->last_physical = physical;
    }
    HANDOFF->magic = CANCELED;
}

unsigned picker_hold_after_cancel(void) {
    if (HANDOFF->magic == CANCELED && !MODE && CARD == 1 &&
        HANDOFF->mount == MOUNT && HANDOFF->preset_generation == PRESET->generation &&
        !moved(ORG_ADC, HANDOFF->exit_adc)) return 1;
    HANDOFF->magic = 0;
    return 0;
}

#include "timing.c.inc"
