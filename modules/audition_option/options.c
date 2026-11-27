#include "../options_keys/preset_io.h"

#define AUDITION_OPTION (*(volatile uint8_t *)0x20028fa4u)
#define AUDITION_STAGE  (*(volatile uint8_t *)0x20028fa5u)

unsigned read_normal_option(const char *line) {
    const char *p = line;
    while (preset_space(*p)) ++p;
    if (p[0] == 'a' && p[1] == 'u' && p[2] == 'd' && p[3] == 't') {
        uint32_t value;
        if (mode_digit(p + 4, 1, &value)) AUDITION_OPTION = (uint8_t)value;
        return 1;
    }
    typedef unsigned (*NormalParse)(const char *);
    return ((NormalParse)0x0804cde9u)(line);
}

unsigned stage_live_option(const char *after_key) {
    uint32_t value;
    if (AUDITION_STAGE || !mode_digit(after_key, 1, &value)) return 0;
    AUDITION_STAGE = (uint8_t)(value + 1);
    return 1;
}
