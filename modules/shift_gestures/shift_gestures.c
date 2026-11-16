/* Development 6: optional unity recall and calibrated-midpoint mapping.
 * No allocation, globals, disk access or changes to reel/playhead state.
 * SHIFT button and jack share the firmware input: manual use only for vuni.
 */
#include <stdint.h>
#include "../preset_recall/preset.h"
#define U32(a) (*(volatile uint32_t *)(a))
#define U16(a) (*(volatile uint16_t *)(a))
#define U8(a) (*(volatile uint8_t *)(a))
#define VUNI U8(0x2002a618)
#define VCTR U8(0x2002a619)
#define MOD 0x2002a000
#define CARD U32(0x20001290)
#define SAMPLES U32(0x20021c88)
#define RELOAD 0x2002a820
typedef struct {
    uint32_t phase, started, knobs[6], card, mount;
    uint32_t request, held;
    float last_x;
    uint32_t config, force_glide, override;
} Unity;
#define S ((volatile Unity *)0x2002a620)
_Static_assert(sizeof(Unity) == 64, "unity assembly ABI");
static const uint32_t knobs[] = {
    0x20021c68, 0x20021c74, 0x20021c6c,
    0x20021c7c, 0x20021c78, 0x20021c70
};

/* Called before existing gesture dispatch, so REC/SPLICE have not been masked.
 * A cancelled candidate never rearms within the same hold. Debounced samples
 * use unsigned elapsed time, including sample-counter rollover.
 */
void unity_buttons(unsigned shift, unsigned rec, unsigned splice) {
    if (VUNI != 1 || U32(0x2002a0f0) != 0x5354504f ||
        U32(MOD) != 0x53484654) {
        S->phase = 0;
        return;
    }
    if (S->phase == 2) {
        if (!shift) S->phase = 0;
        return; /* already cancelled: no further ADC polling in this hold */
    }
    unsigned state = U32(0x20001020);
    if (!S->phase) {
        if (!shift) return;
        S->phase = 1;
        S->started = SAMPLES;
        S->card = CARD;
        S->mount = U32(RELOAD + 240);
        for (unsigned i=0; i<6; ++i) S->knobs[i] = U32(knobs[i]);
    }
    if (rec || splice || (state != 1 && state != 14 && state != 4) ||
        (U8(MOD + 4) && U8(MOD + 5)) || CARD != S->card ||
        U32(RELOAD + 240) == 2 || U32(RELOAD + 240) != S->mount || U32(RELOAD + 8) ||
        U32(RELOAD + 12)) S->phase = 2;
    for (unsigned i=0; i<6; ++i) {
        int delta = (int)U32(knobs[i]) - (int)S->knobs[i];
        int threshold = i == 4 ? 96 : i == 1 && U8(0x2002a610) == 1 ? 8 : 48;
        if (delta > threshold || delta < -threshold) S->phase = 2;
    }
    if (shift) return;
    if (S->phase == 1 && (uint32_t)(SAMPLES - S->started) >= 24000u &&
        (state == 14 || (state == 4 && U32(0x2002139c) == 1))) {
        S->request = 1;
        U8(MOD + 4) = U8(MOD + 5) = 1;
        U8(MOD + 6) = 8; /* consume this release, without splice navigation */
    }
    S->phase = 0;
}

static float unity_position(unsigned vsop, unsigned range) {
    return vsop == 2 ? (range ? 212.5f / 376.f : 212.5f / 328.f) : 344.5f / 400.f;
}

/* The lookup/quantizer has a cell around unity, not a single point. Merely
 * moving that point to noon leaves most of its cell on the clockwise side:
 * bidirectional mode has much more lookup range below +1 than above it.
 * Anchor both cell edges symmetrically as well. The intermediate segments
 * remain continuous, including while SHIFT temporarily bypasses quantization.
 */
static float centered_position(float x, float unity, unsigned vsop,
                               unsigned range, unsigned quantized,
                               unsigned mask) {
    float factor = vsop == 2 ? (range ? 376.f : 328.f) : 400.f;
    float a, b;
    if (quantized) {
        unsigned down = 1, up = 1;
        /* Root/octaves are always enabled, so each search ends by 12. */
        while (!(mask & (1u << (12u-down)))) ++down;
        while (!(mask & (1u << (up == 12 ? 0 : up)))) ++up;
        float step = vsop == 2 || !range ? 4.f : 2.f;
        /* Quantizers truncate at 1/16 index and break midpoint ties downward.
         * These are the first-unity and first-above-unity input thresholds. */
        float tie = 1.f / (16.f * factor);
        a = unity - (float)down * step / (2.f * factor) + tie;
        b = unity + (float)up * step / (2.f * factor) + tie;
    } else if (vsop == 2) {
        a = 212.f / factor;
        b = 213.f / factor;
    } else {
        a = 344.f / 400.f;
        b = (vsop == 1 && !range ? 348.f : 346.f) / 400.f;
    }
    /* Preserve the former cell's extent outside its explicit detent, sharing
     * that extent equally around the new 48..52% detent. Both neighbors exist
     * in every supported layout/range, so no artificial width cap is needed. */
    float old_side = quantized ? .495f : .48f;
    float width = .02f + .5f * old_side *
        ((unity-a)/unity + (b-unity)/(1.f-unity));
    float left = .5f-width, right = .5f+width;
    if (x < left) return a * x / left;
    if (x < .48f) return a + (unity-a) * ((x-left)/(.48f-left));
    if (x <= .52f) return unity;
    if (x < right) return unity + (b-unity) * ((x-.52f)/(right-.52f));
    return b + (1.f-b) * ((x-right)/(1.f-right));
}

/* A vpos recall supplies calibrated virtual knob position to every existing
 * layout/range/quantizer. Pickup compares the actual combined knob/CV input.
 * The latest explicit action wins: recall cancels unity hold, a later unity
 * gesture drops the preset hold and uses physical input for its own pickup. */
static uint32_t preset_varispeed(uint32_t input) {
    if (PRESET->magic != PRESET_MAGIC) return input;
    union { uint32_t u; float f; } x = {.u=input}, out;
    volatile PresetLane *lane = preset_lane(PRESET_VARISPEED);
    unsigned physical = (unsigned)(x.f * 1000000.f);
    unsigned recalled = 0;
    if (lane->seen_generation != PRESET->generation) {
        lane->seen_generation = PRESET->generation;
        unsigned percent = preset_value(PRESET_VARISPEED);
        if ((PRESET->recall_mask & (1u << PRESET_VARISPEED)) && percent <= 100) {
            lane->target = percent * 10000u;
            lane->last_physical = physical;
            lane->effective = lane->target;
            lane->held = lane->initialized = 1;
            S->held = S->request = 0;
            U8(MOD+7) = 0;
            U32(0x20021df8) = 0xc0000000;
            recalled = 1;
        }
    }
    if (!lane->initialized) return input;
    if (S->request || S->held) lane->held = 0;
    if (lane->held && !recalled) {
        unsigned target = lane->target, last = lane->last_physical;
        unsigned distance = physical > target ? physical-target : target-physical;
        unsigned margin = target == 0 || target == 1000000 ? 31250u : 11722u;
        if (distance <= margin || (last < target && physical >= target) ||
            (last > target && physical <= target)) {
            lane->held = 0;
            U8(MOD+7) = 0;
            U32(0x20021df8) = 0xc0000000;
        }
    }
    lane->last_physical = physical;
    lane->effective = lane->held ? lane->target : physical;
    if (!lane->held) return input;
    out.f = (float)lane->target / 1000000.f;
    return out.u;
}

/* The stock block also differentiates raw Varispeed before calibration, using
 * its 32-block motion history for the audio engine. Feed the equivalent virtual
 * ADC there, while retaining physical ADC RAM for gestures and pickup. Consume
 * a preset once at this earlier point and hand its normalized result to P5.
 * Extended auxiliary12/13: prepared normalized bits / one-block ready flag;
 * auxiliary14/15: equivalent ADC / active flag for the other audio raw reads. */
unsigned preset_varispeed_prepare(unsigned physical) {
    if (PRESET->magic != PRESET_MAGIC) return physical;
    PRESET_EXT->aux[13] = 0;
    PRESET_EXT->aux[15] = 0;
    volatile PresetLane *lane = preset_lane(PRESET_VARISPEED);
    if (!lane->initialized &&
        !(lane->seen_generation != PRESET->generation &&
          (PRESET->recall_mask & (1u << PRESET_VARISPEED)))) return physical;
    unsigned low = U32(0x20001294);
    union { uint32_t u; float f; } scale = {.u=U32(0x20021410)}, x, mapped;
    x.f = physical < low ? 0.f : (float)(physical-low)*scale.f;
    if (x.f < 0.f) x.f = 0.f;
    if (x.f > 1.f) x.f = 1.f;
    mapped.u = preset_varispeed(x.u);
    PRESET_EXT->aux[12] = mapped.u;
    PRESET_EXT->aux[13] = 1;
    if (!lane->held || !(scale.f > 0.f)) return physical;
    float virtual_adc = (float)low + mapped.f/scale.f;
    unsigned adc = virtual_adc <= 0.f ? 0 : virtual_adc >= 4095.f ? 4095 :
                   (unsigned)(virtual_adc+.5f);
    PRESET_EXT->aux[14] = adc;
    PRESET_EXT->aux[15] = 1;
    return adc;
}

/* Integer ABI keeps the assembly wrapper independent of soft/hard FP calling
 * conventions. s18 is already calibrated/clamped by stock code. The midpoint
 * detent spans 48..52% in every mode. The curve depends on configured options,
 * never the current gesture, so SHIFT's temporary free mode keeps that curve.
 */
uint32_t unity_map(uint32_t input) {
    if (PRESET->magic == PRESET_MAGIC && PRESET_EXT->aux[13]) {
        input = PRESET_EXT->aux[12];
        PRESET_EXT->aux[13] = 0;
    } else input = preset_varispeed(input);
    union { uint32_t u; float f; } x = {.u=input}, out;
    unsigned enabled = VUNI == 1, centered = VCTR == 1;
    S->force_glide = S->override = 0;
    if (!enabled && !centered) {
        if (S->config) {
            U32(0x20021df8) = 0xc0000000; /* invalidate stock Varispeed cache: -2 */
            U8(MOD + 7) = 0;
        }
        S->config = S->held = S->request = 0;
        return input;
    }
    unsigned vsop = U32(0x200012a8), range = U8(0x2002a606) == 1;
    if (vsop > 2) vsop = 0;
    unsigned scale = U8(0x2002a0f5);
    if (scale > 4) scale = 1;
    unsigned mask = scale == 2 ? 0x81u : scale == 3 ? 0xfffu :
                    scale == 4 ? (U16(0x2002a604) & 0xfffu) | 1u : 1u;
    unsigned quantized = U8(0x2002a610) == 1 && scale != 0;
    /* Non-overlapping, bounded fields; changing a custom scale also clears
     * the previous quantizer latch and stock lookup cache. ABI stays 64 B. */
    unsigned config = 0x80000000u | vsop | (scale << 2) | (mask << 5) |
                      (quantized << 17) | (range << 18) |
                      (centered << 19) | (enabled << 24);
    if (config != S->config) {
        S->config = config;
        S->last_x = x.f;
        U8(MOD + 7) = 0;
        U32(0x20021df8) = 0xc0000000;
    }
    float unity = unity_position(vsop, range);
    float pickup = centered ? .5f : unity;
    float margin = centered ? .02f : .00125f;
    if (!enabled) S->held = S->request = 0;
    else if (S->request) {
        S->request = 0;
        S->held = 1;
        U8(MOD + 7) = 0;
    } else if (S->held &&
               ((x.f >= pickup-margin && x.f <= pickup+margin) ||
                (S->last_x < pickup && x.f >= pickup) ||
                (S->last_x > pickup && x.f <= pickup))) {
        S->held = 0;
        U8(MOD + 7) = 0;
        U32(0x20021df8) = 0xc0000000;
    }
    S->last_x = x.f;
    if (S->held || (centered && x.f >= .48f && x.f <= .52f)) {
        S->override = S->force_glide = 1;
        U8(MOD + 7) = 0;
        U32(0x20021df8) = 0xc0000000;
        out.f = unity;
    } else if (centered) {
        out.f = centered_position(x.f, unity, vsop, range, quantized, mask);
    } else out = x;
    return out.u;
}
