#include "preset_io.h"
#include "../preset_recall/preset.h"

/* Consumed by opt_parse before it dispatches mod or stock keys. */
enum { ORDINARY_KEYS = 0, INCLUDE_PRESETS = 1, SKIP_CHUNK = 2 };

void presets_normal_begin(void) {
    PRESET_U8(SOSC_ADDRESS) = 0; /* A file without sosc selects the default curve. */
    PRESET_NORMAL->mask = 0;
    PRESET_NORMAL->ready = 1;
    PRESET_NORMAL->scan_state = 1; /* first logical line is the stock header */
    PRESET_NORMAL->parse_mode = ORDINARY_KEYS;
    for (unsigned i=0; i<PRESET_COUNT; ++i) PRESET_NORMAL->values[i] = 0;
}

/* Stock fgets reads at most 63 characters, so one logical line can occupy
 * several parser iterations. Observe every read, including the header and
 * EOF, without changing the stock parser's chunk counter. Only the
 * first chunk of an option line can dispatch keys. Presets additionally need
 * a complete significant value. Bit 0 identifies the header, bit 1 a
 * continuation of the previous chunk. */
void presets_normal_chunk(const char *line, unsigned present) {
    PRESET_NORMAL->parse_mode = ORDINARY_KEYS;
    if (!present) return;
    /* opt_prepare_read fills all 64 bytes with 0xff. FatFs appends a NUL
     * after the bytes it read, even when some of those bytes are NUL too. */
    unsigned length = 63;
    while (length && line[length]) --length;
    unsigned state = PRESET_NORMAL->scan_state;
    unsigned complete = length < 63 || line[62] == '\n';
    PRESET_NORMAL->scan_state = complete ? 0 : state | 2u;
    if (state) {
        PRESET_NORMAL->parse_mode = SKIP_CHUNK;
        return;
    }
    unsigned comment = 0;
    for (unsigned i=0; i<length; ++i) {
        if (!line[i]) {
            PRESET_NORMAL->parse_mode = SKIP_CHUNK;
            return;
        }
        if (i && line[i] == '/' && line[i-1] == '/') comment = 1;
    }
    if (complete || comment) {
        PRESET_NORMAL->parse_mode = INCLUDE_PRESETS;
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
    /* Stock treats a zero chord ratio as reverse. Handle only complete zero
     * tokens here, keeping its existing parsing of all other ratios. Keep the
     * stock option word and the audio engine's working ratio in sync. */
    if (p[0] == 'm' && p[1] == 'c' && p[2] == 'r' &&
        p[3] >= '1' && p[3] <= '3' && explicit_zero(p+4, 1)) {
        unsigned offset = 4u * (unsigned)(p[3] - '1');
        PRESET_U32(0x200012d4u + offset) = MIN_CHORD_BITS;
        PRESET_U32(0x20022124u + offset) = MIN_CHORD_BITS;
        return 1;
    }
    if (p[0] == 't' && p[1] == 'l' && p[2] == 'e' && p[3] == 'n' &&
        explicit_zero(p+4, 0)) {
        PRESET_U8(0x2002a0fcu) = 1;
        return 1;
    }
    unsigned dryk = p[0] == 'd' && p[1] == 'r' && p[2] == 'y' && p[3] == 'k';
    unsigned dlen = p[0] == 'd' && p[1] == 'l' && p[2] == 'e' && p[3] == 'n';
    unsigned sosc = p[0] == 's' && p[1] == 'o' && p[2] == 's' && p[3] == 'c';
    if (dryk || dlen || sosc) {
        uint32_t mode;
        if (mode_digit(p+4, dryk ? 3u : sosc ? 2u : 1u, &mode)) {
            volatile uint8_t *dest = (volatile uint8_t *)(dryk ? DRYK_ADDRESS : sosc ? SOSC_ADDRESS : DLEN_ADDRESS);
            *dest = (uint8_t)mode;
        }
        return 1;
    }
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
        "fbkp %u //SHIFT+S.O.S. 0-100. Used in dry-kill modes 0 and 1.\n",
        "evop %u //Recall Turing evolution virtual knob percent, 0-100.\n",
        "trst %u //Recall Turing Genes per step: 1,2,3,4,6,8,12,16; dens takes priority.\n",
        "sosp %u //Primary S.O.S. position for the selected sosc curve.\n",
        "vpos %u //Recall calibrated Varispeed position before mapping, 0-100 percent.\n"
    };
    print(file, "dryk %u //0 normal, 1 wet, 2 tape feedback, 3 Gene feedback.\n",
          (unsigned)*(volatile uint8_t *)DRYK_ADDRESS);
    print(file, "sosc %u //0 crossfade, 1 full input, 2 full existing.\n",
          (unsigned)PRESET_U8(SOSC_ADDRESS));
    print(file, "dlen %u //0 fixed, 1 extend last splice at CCW in dryk 2.\n",
          (unsigned)*(volatile uint8_t *)DLEN_ADDRESS);
    unsigned staged = PRESET_NORMAL->ready == 2;
    unsigned mask = staged ? PRESET_NORMAL->mask :
        PRESET->magic == PRESET_MAGIC ? PRESET->saved_mask : 0;
    for (unsigned i=0; i<PRESET_COUNT; ++i)
        if (mask & (1u<<i)) print(file, formats[i],
            staged ? PRESET_NORMAL->values[i] : preset_value(i));
}
