/* Development 8 option staging; scratch belongs to settings_reload's arena.
 * Normal parsing and live reload use separate transactions. Neither writes
 * audio state until the complete file and loaded reel have been validated.
 */
#ifndef PRESET_IO_H
#define PRESET_IO_H
#include <stdint.h>
#include "../preset_recall/preset.h"
typedef struct {
    uint32_t mask, values[PRESET_COUNT], ready;
    uint32_t scan_state, parse_mode; /* normal fgets logical-line tracking */
} PresetStage;
_Static_assert(sizeof(PresetStage) == 64, "preset stage allocation");
#define PRESET_NORMAL ((volatile PresetStage *)0x2002ae10)
#define PRESET_LIVE   ((volatile PresetStage *)0x2002ae50)

static inline int preset_space(char c) {
    return c == ' ' || c == '\t' || c == '\r';
}
static inline int preset_key(const char *p) {
    static const char keys[PRESET_COUNT][5] = {"mpos", "gpos", "spos", "splc",
        "srrp", "jitp", "wrbp", "fbkp", "evop", "trst", "sosp", "vpos"};
    for (unsigned i=0; i<PRESET_COUNT; ++i) {
        unsigned j=0;
        while (j<4 && p[j] && p[j] == keys[i][j]) ++j;
        if (j == 4 && (!p[4] || p[4] == '\n' || preset_space(p[4]))) return (int)i;
    }
    return -1;
}
/* Integer percentages are virtual control positions, not time/length units.
 * The caller has already identified a key. Accept one complete integer with
 * optional whitespace/comment, including the full 300-splice range. */
static inline int preset_number(const char *p, unsigned index, uint32_t *out) {
    if (!preset_space(p[4])) return 0;
    p += 4;
    while (preset_space(*p)) ++p;
    unsigned n=0, digits=0;
    while (*p >= '0' && *p <= '9') {
        if (++digits > 3) return 0;
        n = n*10u + (unsigned)(*p++-'0');
    }
    while (preset_space(*p)) ++p;
    if (!digits || (*p && *p != '\n' && !(p[0]=='/' && p[1]=='/'))) return 0;
    if (n > (index == 3 ? 300u : 100u) || (index == 3 && n == 0)) return 0;
    if (index == PRESET_TURING_RATE && n != 1 && n != 2 && n != 3 &&
        n != 4 && n != 6 && n != 8 && n != 12 && n != 16) return 0;
    *out = n;
    return 1;
}
#endif
