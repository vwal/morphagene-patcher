/* Development 8: percent presets for secondary SHIFT controls.
 * Call after the existing gesture updates, before using their effect target.
 * Physical ADC/gesture references remain unchanged. */
#ifndef MGMOD_PRESET_EFFECTS_H
#define MGMOD_PRESET_EFFECTS_H
#include "preset.h"

static inline unsigned preset_secondary(unsigned id, unsigned physical,
                                        unsigned legacy_effective,
                                        unsigned editing) {
    if (PRESET->magic != PRESET_MAGIC || id < 4 || id >= PRESET_COUNT)
        return legacy_effective;
    if (physical > 4095) physical = 4095;
    volatile PresetLane *lane = preset_lane(id);
    unsigned recalled = 0;
    if (lane->seen_generation != PRESET->generation) {
        lane->seen_generation = PRESET->generation;
        unsigned percent = preset_value(id);
        if ((PRESET->recall_mask & (1u << id)) && percent <= 100) {
            lane->target = (percent*4095u + 50u)/100u;
            lane->last_physical = physical;
            lane->effective = lane->target;
            lane->held = lane->initialized = 1;
            recalled = 1;
        }
    }
    if (!(lane->initialized & 1u)) return legacy_effective;
    /* Moving the primary knob alone must never change a recalled effect.
     * Only its claimed SHIFT gesture can take over the secondary value. */
    if (editing && lane->held && !recalled) {
        unsigned target = lane->target, previous = lane->last_physical;
        unsigned distance = physical > target ? physical-target : target-physical;
        unsigned margin = target == 0 || target == 4095 ? 128u : 48u;
        if (distance <= margin || (previous < target && physical >= target) ||
            (previous > target && physical <= target)) lane->held = 0;
    }
    lane->last_physical = physical;
    if (lane->held) lane->effective = lane->target;
    else if (editing) lane->effective = legacy_effective;
    return lane->effective;
}

static inline unsigned preset_editing(unsigned owner) {
    return PRESET_U32(0x2002a000) == 0x53484654u &&
           PRESET_U8(0x2002a004) && PRESET_U8(0x2002a005) &&
           PRESET_U8(0x2002a006) == owner;
}
#endif
