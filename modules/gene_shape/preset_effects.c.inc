/* Development 8 secondary Gene controls. Included by gene_shape.c.
 * Post-process the ordinary SHIFT effects so their primary-control holds and
 * gesture ownership remain unchanged. No writable compiler globals. */
extern void preset_turing_init(void);

static void gene_effect_float(uint32_t address, float value) {
    union { float f; uint32_t u; } bits = {.f=value};
    PRESET_U32(address) = bits.u;
}

static void preset_jitter_apply(void) {
    if (PRESET->magic != PRESET_MAGIC) return;
    unsigned value = preset_secondary(PRESET_JITTER, PRESET_U32(0x20021c78),
                                     PRESET_U16(0x2002a0de), preset_editing(5));
    if (!(preset_lane(PRESET_JITTER)->initialized & 1u)) return;
    PRESET_U16(0x2002a0de) = (uint16_t)value;
    float x = value <= 48 ? 0.f : (float)(value-48u)*.00025f;
    float amount = x*x;
    if (amount > 1.f) amount = 1.f;
    gene_effect_float(0x2002a0e0, amount);
}

static void preset_evolution_apply(void) {
    if (PRESET->magic != PRESET_MAGIC) return;
    unsigned active = PRESET_U32(0x2002a0f0) == 0x5354504fu &&
                      PRESET_U8(0x2002a0fa) == 1;
    unsigned value = preset_secondary(PRESET_EVOLUTION, PRESET_U32(0x20021c70),
                                     PRESET_U32(0x20021c70),
                                     active && preset_editing(6));
    if (!(preset_lane(PRESET_EVOLUTION)->initialized & 1u)) return;
    /* Seed/initialize once before replacing evolution, including when sldm
     * is currently off so a later enable uses the recalled value. */
    preset_turing_init();
    float x = value <= 96 ? 0.f : (float)(value-96u)*.000260485f;
    if (x > 1.f) x = 1.f;
    gene_effect_float(0x2002a74c, x*x);
}

static void preset_turing_rate_apply(void) {
    if (PRESET->magic != PRESET_MAGIC) return;
    static const uint8_t rates[] = {1,2,3,4,6,8,12,16};
    volatile PresetLane *lane = preset_lane(PRESET_TURING_RATE);
    unsigned physical = PRESET_U32(0x20021c7c), recalled = 0;
    if (physical > 4095) physical = 4095;
    if (lane->seen_generation != PRESET->generation) {
        lane->seen_generation = PRESET->generation;
        unsigned rate = preset_value(PRESET_TURING_RATE), zone;
        for (zone=0; zone<8 && rates[zone]!=rate; ++zone) {}
        if ((PRESET->recall_mask & (1u << PRESET_TURING_RATE)) && zone<8) {
            lane->target = zone*512u+256u;
            lane->last_physical = physical;
            lane->effective = lane->target;
            lane->held = lane->initialized = 1;
            recalled = 1;
        }
    }
    if (!(lane->initialized & 1u)) return;
    preset_turing_init();
    unsigned editing = preset_editing(4) && PRESET_U8(0x2002a607) != 1 &&
                       PRESET_U32(0x2002a0f0) == 0x5354504fu &&
                       PRESET_U8(0x2002a0fa) == 1;
    if (lane->held && editing && !recalled) {
        unsigned target = lane->target, previous = lane->last_physical;
        /* Rate has eight coarse zones: reaching its zone is enough. A rapid
         * sweep can also pick it up by crossing the representative center. */
        if (physical/512u == target/512u ||
            (previous < target && physical >= target) ||
            (previous > target && physical <= target)) lane->held = 0;
    }
    lane->last_physical = physical;
    if (lane->held) lane->effective = lane->target;
    else if (editing) {
        /* Keep the ordinary rate_zone hysteresis result, rather than deriving
         * a fresh zone from the raw ADC and losing hysteresis on release. */
        unsigned zone = PRESET_U8(0x2002a755);
        if (zone > 7) zone = 7;
        lane->effective = zone*512u+256u;
    }
    unsigned zone = lane->effective/512u;
    if (zone > 7) zone = 7;
    PRESET_U8(0x2002a755) = (uint8_t)zone;
    PRESET_U8(0x2002a756) = rates[zone];
}
