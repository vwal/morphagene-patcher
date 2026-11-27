/* The foreground produces packed stereo frames. Only the audio interrupt
 * consumes them. The native reel's FIL, SDRAM and recording state stay with
 * D23 throughout the menu. audt=0 enables the read-only preview. */
#include <stdint.h>
#include <stddef.h>
#include "bounds.inc.c"

#define BYTE(a) (*(volatile uint8_t *)(a))
#define HALF(a) (*(volatile uint16_t *)(a))
#define WORD(a) (*(volatile uint32_t *)(a))
#define PHASE BYTE(0x20028f58)
#define MENU_VOLUME HALF(0x20028f5a)
#define MENU_BANK BYTE(0x20028f5c)
#define MENU_REEL BYTE(0x20028f5d)
#define MENU_TOKEN WORD(0x20028f60)
#define VOLUME HALF(0x20024278)
#define CARD WORD(0x20001290)
#define ADC WORD(0x20021c70)
#define NOW WORD(0x20021c88)
#define panel_choice ((unsigned (*)(void))0x08054769)

enum { RING = 2048, PRIME = 1024, PAGE = 256, DWELL = 11520, REELS = 4, SPLICES = 6 };
typedef struct {
    uint32_t file[138], raw[PAGE * 2], stereo[RING];
} Buffers;
typedef struct {
    volatile uint32_t active;
    unsigned key, token, since, adc, offset, frames, cursor;
    volatile uint32_t produced, consumed;
    uint16_t volume;
    uint8_t opened, attempted;
} Preview;
#define BUFS ((Buffers *)0x20025000)
#define P ((Preview *)0x20028fa8)
_Static_assert(sizeof(Buffers) == 0x2a28, "audition buffer ledger");
_Static_assert(offsetof(Preview, key) == 4 && sizeof(Preview) <= 0x30, "selector ABI");
#define BARRIER() __asm__ volatile ("" ::: "memory")

static int available(unsigned phase) {
    return (phase == REELS || phase == SPLICES) && !BYTE(0x20028fa4) &&
        BYTE(0x2002a61f) && CARD == 1 && VOLUME == MENU_VOLUME &&
        WORD(0x20021338) == 1 && !WORD(0x20022108) && !WORD(0x20021320) &&
        !(WORD(0x20022074) & ~0x80u);
}

static unsigned target(unsigned phase) {
    unsigned bank = MENU_BANK, choice = panel_choice();
    unsigned reel = phase == REELS ? choice : MENU_REEL;
    unsigned splice = phase == REELS ? 1 : choice;
    if (bank < 1 || bank > 8 || reel < 1 || reel > 32 || splice < 1 || splice > 300)
        return 0;
    return phase << 24 | bank << 16 | reel << 9 | splice;
}

/* A removed generation invalidates every FIL. Closing an object on a new
 * mount could only address the wrong medium. Close a valid read-only FIL in
 * main before changing the state it belongs to. */
static void close_reader(void) {
    if (P->opened) {
        if (CARD == 1 && P->volume == VOLUME) marker_close(BUFS->file);
        P->opened = 0;
    }
}

void preview_discard(void) {
    P->active = 0;
    BARRIER();
    close_reader();
    P->key = 0;
}

/* Convert normalized binary32 to signed PCM without touching any FPU state in
 * the interrupted native foreground. Clamp before conversion; malformed NaNs
 * are silent. A load is one complete little-endian sample from the file. */
static int pcm16(uint32_t bits) {
    unsigned exponent = (bits >> 23) & 255u;
    unsigned fraction = bits & 0x7fffffu;
    if (exponent < 112 || (exponent == 255 && fraction)) return 0;
    if (exponent >= 127) return bits >> 31 ? -32768 : 32767;
    int magnitude = (int)((fraction | 0x800000u) >> (135 - exponent));
    return bits >> 31 ? -magnitude : magnitude;
}

static int same_target(unsigned key) {
    unsigned phase = PHASE;
    if (!available(phase) || P->token != MENU_TOKEN || P->volume != VOLUME ||
        key >> 24 != phase) return 0;
    return ADC == P->adc || target(phase) == key;
}

static int start_reader(unsigned key) {
    unsigned bank = (key >> 16) & 15u, reel = (key >> 9) & 63u;
    char path[32];
    audition_name(path, bank, reel, 0);
    if (marker_open(BUFS->file, path, 1)) return 0;
    P->opened = 1;
    return preview_bounds(BUFS->file, bank, reel, key & 511, &P->offset, &P->frames);
}

/* Read once per foreground visit, with interrupts enabled. Short splices
 * are cached whole, so fast wraps never cause repeated SD seeks. For longer
 * splices produced-consumed is the count of ready frames, even at rollover. */
static int fill_page(void) {
    unsigned frames = P->frames, at = P->cursor, put = P->produced;
    unsigned free = RING - (put - P->consumed);
    unsigned count = frames - at;
    if (count > PAGE) count = PAGE;
    if (frames > RING && free < count) return 1;
    if (!audition_read_at(BUFS->file, P->offset + at * 8, BUFS->raw, count * 8)) return 0;
    for (unsigned i = 0; i < count; ++i) {
        unsigned left = (uint16_t)pcm16(BUFS->raw[i * 2]);
        unsigned right = (uint16_t)pcm16(BUFS->raw[i * 2 + 1]);
        BUFS->stereo[(put + i) & (RING - 1)] = left | (right << 16);
    }
    at += count;
    P->cursor = at == frames ? 0 : at;
    BARRIER();
    P->produced = put + count;
    if (frames <= RING && at == frames) close_reader();
    return 1;
}

void preview_service(void) {
    unsigned phase = PHASE;
    unsigned token = MENU_TOKEN, volume = VOLUME;
    unsigned adc = ADC;
    unsigned key = available(phase) ? target(phase) : 0;
    if (!key) {
        if (P->key) preview_discard();
        return;
    }
    if (key != P->key || token != P->token || volume != P->volume) {
        preview_discard();
        P->key = key;
        P->volume = (uint16_t)volume;
        P->token = token;
        P->since = NOW;
        P->attempted = 0;
        P->consumed = P->produced = P->cursor = 0;
    }
    P->adc = adc;
    if (!P->attempted) {
        if ((uint32_t)(NOW - P->since) < DWELL) return;
        P->attempted = 1;
        if (!start_reader(key)) {
            close_reader();
            return;
        }
    }
    if (!P->opened) return;
    if (!fill_page()) {
        P->active = 0;
        close_reader();
        return;
    }
    if (!same_target(key)) {
        preview_discard();
        return;
    }
    if (P->frames > RING ? P->produced - P->consumed >= PRIME : P->produced == P->frames) {
        BARRIER();
        P->active = 1;
    }
}

/* Interrupt-side, bounded by the size of this DMA block. Native output
 * remains in the unfilled suffix on underrun. Never call FatFs from here. */
void preview_output(int16_t *out, unsigned halfwords) {
    if (!P->active || !same_target(P->key)) return;
    unsigned at = P->consumed, frames = P->frames;
    unsigned count = halfwords >> 1;
    if (frames > RING) {
        unsigned ready = P->produced - at;
        if (count > ready) {
            count = ready;
            /* Stay with native audio until the foreground has a reserve of
             * frames again, rather than switching sources for every late page. */
            P->active = 0;
        }
    }
    BARRIER();
    for (unsigned i = 0; i < count; ++i) {
        unsigned sample = BUFS->stereo[at & (RING - 1)];
        out[2*i] = (int16_t)sample;
        out[2*i + 1] = (int16_t)(sample >> 16);
        ++at;
        if (frames <= RING && at == frames) at = 0;
    }
    P->consumed = at;
}
