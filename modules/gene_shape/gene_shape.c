#include "../preset_recall/preset.h"
#include "../preset_recall/effects.h"
#include "preset_effects.c.inc"

unsigned preset_gene_size(unsigned effective) {
    preset_turing_rate_apply();
    return preset_control(PRESET_GENE_SIZE, PRESET_U32(0x20021c7c), effective);
}

unsigned preset_slide(unsigned effective) {
    preset_jitter_apply();
    return preset_control(PRESET_SLIDE, PRESET_U32(0x20021c78), effective);
}

#include "preset_splice.c.inc"
