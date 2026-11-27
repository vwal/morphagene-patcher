/* Development 8 selected-splice recall. Included by gene_shape.c.
 * Only the stock 1-based Organize/SHIFT request is changed. Stock omod decides
 * when that request becomes the playback splice; voices/playheads stay stock.
 * aux[0..3]: reel, splice count, latest request and play-through layout during pickup.
 */
#define SPLICE_REQUEST PRESET_U32(0x20021cbc)
#define SPLICE_COUNT PRESET_U32(0x2002208c)
#define ORGANIZE_ADC PRESET_U32(0x20021c70)
#define ORGANIZE_LAST PRESET_U32(0x200220ac)

static unsigned organize_cell(unsigned physical, unsigned count, unsigned thru) {
    unsigned low = PRESET_U32(0x20022080), high = PRESET_U32(0x20022078);
    if (low >= high || high > 4095) { low = 0; high = 4095; }
    float offset = physical <= low ? 0.f : (float)(physical-low);
    /* In the play-through layout, match the firmware's calibrated multiplication.
     * At exactly 95%, a rounded division can land on the other side. */
    float x = 1.f;
    if (physical < high)
        x = thru ? offset * *(volatile const float *)0x200220a0 : offset/(float)(high-low);
    if (thru) {
        if (x >= .95f) return 0; /* play-through has no absolute splice number */
        x *= 1.f/.95f;
    }
    /* Same first-splice bias and signed truncation as stock 0x080277b0. */
    int selected = (int)((float)count * (x-.001f)) + 1;
    return selected < 1 ? 1u : (unsigned)selected > count ? count : (unsigned)selected;
}

static unsigned organize_center(unsigned selected, unsigned count, unsigned thru) {
    unsigned low = PRESET_U32(0x20022080), high = PRESET_U32(0x20022078);
    if (low >= high || high > 4095) { low = 0; high = 4095; }
    float x = ((float)selected-.5f)/(float)count + .001f;
    if (thru) x *= .95f;
    unsigned value = low + (unsigned)(x*(float)(high-low) + .5f);
    return value > 4095 ? 4095 : value;
}

unsigned preset_organize(unsigned effective) {
    if (PRESET->magic != PRESET_MAGIC) return effective;
    preset_evolution_apply();
    volatile PresetLane *lane = &PRESET->lane[PRESET_SPLICE];
    unsigned count = SPLICE_COUNT, physical = ORGANIZE_ADC;
    unsigned reel = PRESET_U32(0x20001040), recalled = 0;
    if (physical > 4095) physical = 4095;

    /* Organize's normal reel-selection mode must remain available. A staged
     * recall waits for that mode to finish instead of changing the reel UI. */
    if (PRESET_U32(0x20021338)) return effective;
    if (!count || count > 300) { lane->held = 0; return effective; }
    if (lane->seen_generation != PRESET->generation) {
        lane->seen_generation = PRESET->generation;
        unsigned selected = PRESET->value[PRESET_SPLICE];
        if ((PRESET->recall_mask & (1u << PRESET_SPLICE)) &&
            selected >= 1 && selected <= 300) {
            /* A prepared card can be used with a shorter reel. Clamp only
             * this runtime selection, preserving the configured number for
             * subsequent recalls on reels that contain more splices. */
            if (selected > count) selected = count;
            /* Absolute recall supersedes an older queued navigation event,
             * including stock's -1 startup latch. Later SHIFT events are left
             * alone; this executes only when consuming an explicit recall. */
            PRESET_U32(0x200012e0) = 0;
            SPLICE_REQUEST = selected;
            /* Freeze at the effective reading already accepted this block,
             * so stock's >8-count movement detector cannot undo the recall. */
            lane->effective = effective > 4095 ? 4095 : effective;
            ORGANIZE_LAST = lane->effective;
            lane->last_physical = physical;
            lane->held = lane->initialized = 1;
            PRESET->aux[0] = reel;
            PRESET->aux[1] = count;
            PRESET_U8(0x2002a082) = 0; /* supersede old Turing Organize pickup */
            recalled = 1;
        }
    }
    if (!lane->held) return effective;
    if (PRESET->aux[0] != reel || PRESET->aux[1] != count) {
        /* Manual reel changes or splice edits end this reel-specific hold. */
        lane->held = 0;
        return effective;
    }
    unsigned selected = SPLICE_REQUEST;
    if (!selected || selected > count) { lane->held = 0; return effective; }
    unsigned thru = PRESET_U32(0x2002a0f0) == 0x5354504fu &&
                    PRESET_U8(0x2002a61e) == 1;
    if (recalled || selected != PRESET->aux[2] || thru != PRESET->aux[3]) {
        /* Follow manual or automatic navigation, and a live thru layout change,
         * without replacing the selection or releasing pickup on the mode change. */
        PRESET->aux[2] = selected;
        PRESET->aux[3] = thru;
        lane->target = organize_center(selected, count, thru);
        lane->last_physical = physical;
    }
    unsigned shift = PRESET_U8(0x2002a004);
    /* This hold already protects the primary selection after a Turing edit.
     * Requiring its legacy pickup as well would force a visit to the old
     * physical position before the preset splice could be picked up. It can
     * also be stale after sldm is switched off by an options-only reload. */
    if (!recalled && !shift) {
        unsigned target = lane->target, previous = lane->last_physical;
        if (organize_cell(physical, count, thru) == selected ||
            (previous < target && physical >= target) ||
            (previous > target && physical <= target)) {
            lane->held = 0;
            PRESET_U8(0x2002a082) = 0;
            /* Returning the physical reading lets the ordinary stock Organize
             * update/crossing behavior take over, including incoming CV. */
            return physical;
        }
    }
    lane->last_physical = physical;
    return lane->effective;
}
