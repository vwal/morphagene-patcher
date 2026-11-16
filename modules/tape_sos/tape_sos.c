#include "../preset_recall/preset.h"
#include "../preset_recall/effects.h"

#define EFFECT_FLOAT(a) (*(volatile float *)(a))
#define EFFECT_BANK_MAGIC 0x58464d42u /* BMFX */

unsigned preset_morph(unsigned effective) {
    return preset_control(PRESET_MORPH, PRESET_U32(0x20021c6c), effective);
}

static float morph_effect_amount(unsigned adc) {
    if (adc <= 96) return 0.f;
    if (adc > 4095) adc = 4095;
    return (float)(adc-96) * .000250062516f; /* stock SHIFT+Morph law */
}

static unsigned morph_effect_position(float amount) {
    if (amount <= 0.f) return 0;
    if (amount >= 1.f) return 4095;
    return (unsigned)(amount * 3999.f + 96.5f);
}

/* aux0: bank magic; aux1: selected bank (0 SRR, 1 warble).
 * aux2/3: exact target-amount float bits; aux4/5: virtual knob ADC positions.
 * Only opt-in effect history enables banking. Until then fxsl keeps its
 * previous shared-amount behavior, including after unrelated preset recalls.
 */
unsigned preset_morph_effects(unsigned passthrough) {
    if (PRESET->magic != PRESET_MAGIC) return passthrough;
    volatile PresetLane *srr = preset_lane(PRESET_SRR);
    volatile PresetLane *warble = preset_lane(PRESET_WARBLE);
    unsigned generation = PRESET->generation;
    unsigned recalled = (srr->seen_generation != generation &&
                         (PRESET->recall_mask & (1u << PRESET_SRR))) ||
                        (warble->seen_generation != generation &&
                         (PRESET->recall_mask & (1u << PRESET_WARBLE)));
    if (PRESET_EXT->aux[0] != EFFECT_BANK_MAGIC && !recalled) return passthrough;
    unsigned mode = PRESET_U32(0x2002a0f0) == 0x5354504fu ?
                    PRESET_U8(0x2002a0f6) : 1;
    unsigned selected = mode == 2;
    unsigned physical = PRESET_U32(0x20021c6c);
    if (physical > 4095) physical = 4095;
    unsigned editing = mode != 0 && preset_editing(3);
    if (PRESET_EXT->aux[0] == EFFECT_BANK_MAGIC && !editing &&
        selected == PRESET_EXT->aux[1] && srr->seen_generation == generation &&
        warble->seen_generation == generation) {
        /* Normal primary-knob motion cannot edit an effect. Keep pickup's
         * history current without recalculating two unchanged effect laws. */
        srr->last_physical = warble->last_physical = physical;
        PRESET_U32(0x2002a064) = PRESET_EXT->aux[2+selected];
        return passthrough;
    }
    if (PRESET_EXT->aux[0] != EFFECT_BANK_MAGIC) {
        unsigned bits = PRESET_U32(0x2002a064);
        unsigned position = morph_effect_position(EFFECT_FLOAT(0x2002a064));
        PRESET_EXT->aux[2] = PRESET_EXT->aux[3] = bits;
        PRESET_EXT->aux[4] = PRESET_EXT->aux[5] = position;
        PRESET_EXT->aux[1] = selected;
        PRESET_EXT->aux[0] = EFFECT_BANK_MAGIC;
    }
    for (unsigned bank=0; bank<2; ++bank) {
        unsigned id = bank ? PRESET_WARBLE : PRESET_SRR;
        volatile PresetLane *lane = preset_lane(id);
        unsigned active = bank == selected;
        if (active && selected != PRESET_EXT->aux[1] && (lane->initialized & 1u)) {
            /* Restore that effect's last live amount, which may have changed
             * after the original preset was picked up. A new explicit recall
             * below still takes precedence over this mode-switch hold. */
            lane->target = lane->effective = PRESET_EXT->aux[4+bank];
            lane->last_physical = physical;
            lane->held = 1;
        }
        unsigned position = preset_secondary(id, physical,
            active && editing ? physical : PRESET_EXT->aux[4+bank], active && editing);
        if (lane->initialized & 1u) {
            union { float f; uint32_t u; } amount = {.f=morph_effect_amount(position)};
            PRESET_EXT->aux[2+bank] = amount.u;
            PRESET_EXT->aux[4+bank] = position;
        } else if (active && editing) {
            /* An effect without its own preset retains normal direct editing.
             * Keep its exact legacy float for later fxsl switches. */
            PRESET_EXT->aux[2+bank] = PRESET_U32(0x2002a064);
            PRESET_EXT->aux[4+bank] = physical;
        }
    }
    PRESET_U32(0x2002a064) = PRESET_EXT->aux[2+selected];
    PRESET_EXT->aux[1] = selected;
    return passthrough;
}

unsigned preset_feedback_effect(unsigned passthrough) {
    if (PRESET->magic != PRESET_MAGIC) return passthrough;
    unsigned physical = PRESET_U32(0x20021c68);
    if (physical > 4095) physical = 4095;
    unsigned editing = preset_editing(1);
    volatile PresetLane *lane = preset_lane(PRESET_FEEDBACK);
    if ((lane->initialized & 1u) && lane->seen_generation == PRESET->generation &&
        !editing && PRESET_U8(0x2002a010) == 1) {
        lane->last_physical = physical;
        return passthrough;
    }
    unsigned position = preset_secondary(PRESET_FEEDBACK, physical, physical, editing);
    if (!(lane->initialized & 1u)) return passthrough;
    float amount = (float)position * .00026350463f;
    if (amount > 1.04884f) amount = 1.f;
    else {
        amount -= .04884f;
        if (amount < 0.f) amount = 0.f;
    }
    EFFECT_FLOAT(0x2002a014) = amount;
    PRESET_U8(0x2002a010) = 1; /* same opt-in latch as SHIFT+S.O.S. */
    return passthrough;
}

#include "preset_sos.c.inc"
