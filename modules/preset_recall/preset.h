/* Shared Development 7 preset ABI. No writable compiler-allocated globals. */
#ifndef MGMOD_PRESET_RECALL_H
#define MGMOD_PRESET_RECALL_H
#include <stdint.h>
#include <stddef.h>

#define PRESET_MAGIC 0x54535250u /* PRST */
#define PRESET_MORPH 0u
#define PRESET_GENE_SIZE 1u
#define PRESET_SLIDE 2u
#define PRESET_SPLICE 3u
#define PRESET_SRR 4u
#define PRESET_JITTER 5u
#define PRESET_WARBLE 6u
#define PRESET_FEEDBACK 7u
#define PRESET_EVOLUTION 8u
#define PRESET_TURING_RATE 9u
#define PRESET_SOS 10u
#define PRESET_VARISPEED 11u
#define PRESET_COUNT 12u
#define PRESET_MASK ((1u << PRESET_COUNT)-1u)

typedef struct {
    uint32_t seen_generation, target, last_physical, effective, held, initialized;
} PresetLane;
typedef struct {
    uint32_t magic, generation, recall_mask, saved_mask;
    uint32_t value[4]; /* mpos, gpos, spos: 0..100; splc: 1..300 */
    PresetLane lane[4];
    uint32_t aux[8]; /* selected-splice implementation owns these words */
} PresetState;
#define PRESET ((volatile PresetState *)0x2002a660)
_Static_assert(sizeof(PresetLane) == 24, "preset lane ABI");
_Static_assert(offsetof(PresetState, lane) == 32, "preset lane base ABI");
_Static_assert(offsetof(PresetState, aux) == 128, "preset splice auxiliary ABI");
_Static_assert(sizeof(PresetState) == 160, "preset arena ABI");

/* Dev8 extends the configuration without relocating the tested Dev7 state.
 * This arena belongs to settings_reload's existing scratch reservation.
 * aux[0..7]: tape_sos secondary effects; [8..11]: gene_shape secondary effects;
 * [12..15]: main S.O.S./Varispeed preset integration. */
typedef struct {
    uint32_t value[8];
    PresetLane lane[8];
    uint32_t aux[16];
} ExtendedPresets;
#define PRESET_EXT ((volatile ExtendedPresets *)0x2002ae90)
_Static_assert(sizeof(ExtendedPresets) == 288, "extended preset arena ABI");
_Static_assert(offsetof(ExtendedPresets, lane) == 32, "extended lane ABI");
_Static_assert(offsetof(ExtendedPresets, aux) == 224, "extended auxiliary ABI");
static inline uint32_t preset_value(unsigned id) {
    return id < 4 ? PRESET->value[id] : PRESET_EXT->value[id-4];
}
static inline volatile PresetLane *preset_lane(unsigned id) {
    return id < 4 ? &PRESET->lane[id] : &PRESET_EXT->lane[id-4];
}

#define PRESET_U32(a) (*(volatile uint32_t *)(a))
#define PRESET_U16(a) (*(volatile uint16_t *)(a))
#define PRESET_U8(a) (*(volatile uint8_t *)(a))

/* A publisher writes values/masks, then advances generation after the
 * successful load. Missing recall bits preserve the live lane. saved_mask
 * describes the latest file and is deliberately independent of live holds.
 * Runtime initialized bit0 means this lane has recalled a preset; bit1
 * tracks its SHIFT edit. The splice lane defines its own initialized bits.
 */
static inline unsigned preset_control(unsigned id, unsigned physical,
                                      unsigned legacy_effective) {
    if (PRESET->magic != PRESET_MAGIC || (id >= PRESET_SPLICE && id != PRESET_SOS))
        return legacy_effective;
    volatile PresetLane *lane = preset_lane(id);
    unsigned recalled = 0;
    if (lane->seen_generation != PRESET->generation) {
        lane->seen_generation = PRESET->generation;
        unsigned percent = preset_value(id);
        if ((PRESET->recall_mask & (1u << id)) && percent <= 100) {
            lane->target = (percent * 4095u + 50u) / 100u;
            lane->last_physical = physical;
            lane->effective = lane->target;
            lane->held = lane->initialized = 1;
            recalled = 1;
        }
    }
    if (!(lane->initialized & 1u)) return legacy_effective;

    static const uint16_t hold_flag[] = {94, 212, 213};
    static const uint16_t hold_value[] = {96, 216, 218};
    unsigned flag = 0x2002a000u + (id == PRESET_SOS ? 17 : hold_flag[id]);
    unsigned value = 0x2002a000u + (id == PRESET_SOS ? 18 : hold_value[id]);
    unsigned editing = PRESET_U32(0x2002a000) == 0x53484654u &&
                       PRESET_U8(0x2002a004) && PRESET_U8(0x2002a005) &&
                       PRESET_U8(0x2002a006) == (id == PRESET_SOS ? 1u : id+3u);
    if (recalled) PRESET_U8(flag) = 0; /* explicit recall supersedes an old hold */
    if (editing) {
        /* Existing effects have already consumed the physical knob. Replace
         * only the primary-control hold, leaving physical gesture references
         * intact so a preset cannot falsely claim SHIFT without movement. */
        if (!(lane->initialized & 2u) && lane->held) {
            PRESET_U16(value) = (uint16_t)lane->effective;
            PRESET_U8(flag) = 1;
        }
        lane->initialized |= 2u;
        lane->last_physical = physical;
        lane->effective = PRESET_U16(value);
        return lane->effective;
    }
    lane->initialized &= ~2u;
    if (lane->held && !recalled) {
        unsigned target = lane->target, last = lane->last_physical;
        unsigned distance = physical > target ? physical-target : target-physical;
        /* Real endpoint readings can stop around 56/4000. A wider endpoint
         * tolerance allows those knobs to pick up exact 0/100% presets. */
        unsigned margin = target == 0 || target == 4095 ? 128u : 48u;
        if (distance <= margin || (last < target && physical >= target) ||
            (last > target && physical <= target)) {
            lane->held = 0;
            PRESET_U8(flag) = 0;
            legacy_effective = physical;
        }
    }
    lane->last_physical = physical;
    lane->effective = lane->held ? lane->target : legacy_effective;
    return lane->effective;
}
#endif
