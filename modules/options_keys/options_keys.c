#include "preset_io.h"
#include "../preset_recall/preset.h"

void presets_normal_begin(void) {
    PRESET_NORMAL->mask = 0;
    PRESET_NORMAL->ready = 1;
    PRESET_NORMAL->scan_state = 1; /* first logical line is the stock header */
    PRESET_NORMAL->parse_allowed = 0;
    for (unsigned i=0; i<PRESET_COUNT; ++i) PRESET_NORMAL->values[i] = 0;
}

/* Stock fgets reads at most 63 characters, so one logical line can occupy
 * several parser iterations. Observe every read, including the header and
 * EOF, without changing the stock parser's chunk counter or buffer. Only
 * complete significant lines, or prefixes ending in a comment, may recall.
 * Bit 0 tracks the header; bit 1 suppresses continuation chunks. */
void presets_normal_chunk(const char *line, unsigned present) {
    PRESET_NORMAL->parse_allowed = 0;
    if (!present) return;
    unsigned length = 0, comment = 0;
    while (length < 63 && line[length] && line[length] != '\n') {
        if (line[length] == '/' && length && line[length-1] == '/')
            comment = 1;
        ++length;
    }
    unsigned state = PRESET_NORMAL->scan_state;
    unsigned complete = length < 63;
    PRESET_NORMAL->scan_state = complete ? 0 : state | 2u;
    if (state) return; /* neither the header nor any continuation is an option */
    if (complete || comment) {
        PRESET_NORMAL->parse_allowed = 1;
    } else {
        /* An overlong significant value is invalid, not a valid truncated
         * prefix. Like another invalid last occurrence, it disables its key. */
        while (preset_space(*line)) ++line;
        int index = preset_key(line);
        if (index >= 0) PRESET_NORMAL->mask &= ~(1u << (unsigned)index);
    }
}

void presets_normal_end(const uint8_t *file) {
    /* FatFs records a failed read in FIL.err, even if fgets returned NULL. */
    PRESET_NORMAL->ready = file[7] ? 0 : 2;
}
unsigned presets_normal_parse(const char *p) {
    while (preset_space(*p)) ++p;
    int index = preset_key(p);
    if (index < 0) return 0;
    uint32_t value, bit = 1u << (unsigned)index;
    PRESET_NORMAL->mask &= ~bit;
    if (preset_number(p, (unsigned)index, &value)) {
        PRESET_NORMAL->values[index] = value;
        PRESET_NORMAL->mask |= bit;
    }
    return 1;
}

/* Called before stock closes its rewritten file. Persist configured values,
 * never live knob positions; disabled/omitted recalls remain omitted. */
void presets_write(void *file) {
    typedef int (*Print)(void *, const char *, ...);
    Print print = (Print)0x08034805;
    static const char *const formats[PRESET_COUNT] = {
        "mpos %u //Recall Morph virtual knob position, 0-100 percent; omit to preserve live value.\n",
        "gpos %u //Recall Gene Size virtual knob position, 0-100 percent (not length); omit to preserve live value.\n",
        "spos %u //Recall Slide virtual knob position, 0-100 percent; omit to preserve live value.\n",
        "splc %u //Recall splice 1-300; above reel count selects last. Omit to preserve.\n",
        "srrp %u //Recall SRR virtual knob percent, 0-100; fxsl selects active effect.\n",
        "jitp %u //Recall jitter/Turing spread virtual knob percent, 0-100.\n",
        "wrbp %u //Recall warble virtual knob percent, 0-100; fxsl selects active effect.\n",
        "fbkp %u //Recall feedback virtual knob percent, 0-100; tape selects mode.\n",
        "evop %u //Recall Turing evolution virtual knob percent, 0-100.\n",
        "trst %u //Recall Turing Genes per step: 1,2,3,4,6,8,12,16; dens takes priority.\n",
        "sosp %u //Recall primary S.O.S. mix virtual knob percent, 0-100.\n",
        "vpos %u //Recall calibrated Varispeed position before mapping, 0-100 percent.\n"
    };
    unsigned staged = PRESET_NORMAL->ready == 2;
    unsigned mask = staged ? PRESET_NORMAL->mask :
        PRESET->magic == PRESET_MAGIC ? PRESET->saved_mask : 0;
    for (unsigned i=0; i<PRESET_COUNT; ++i)
        if (mask & (1u<<i)) print(file, formats[i],
            staged ? PRESET_NORMAL->values[i] : preset_value(i));
}
