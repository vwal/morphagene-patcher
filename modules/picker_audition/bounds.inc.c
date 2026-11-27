/* Resolve the same 1-based splice numbers as D22's selector. All files used
 * here are read-only and owned by the foreground. The native writable FIL
 * and playback markers belong to the original performance throughout. */
#include <stdint.h>

typedef struct {
    unsigned frames, cue_pos, cue_count;
} AuditionWave;

typedef struct {
    unsigned end[299], count, embedded;
} AuditionMarkers;

/* D22 was reproduced and pinned by the D24 builder. Use its actual RIFF
 * validator, exact-read helper and signed-decimal legacy marker parser. */
#define audition_probe ((int (*)(void *, AuditionWave *))0x08054355)
#define audition_read_at ((int (*)(void *, unsigned, void *, unsigned))0x08054315)
#define audition_number ((int (*)(const char **, unsigned *))0x08054535)
#define audition_name ((void (*)(char *, unsigned, unsigned, int))0x08051e79)
#define marker_open ((int (*)(void *, const char *, unsigned))0x08032261)
#define marker_close ((int (*)(void *))0x080327a9)
#define marker_gets ((char *(*)(char *, int, void *))0x0803449d)

static void add_audition_marker(AuditionMarkers *m, unsigned frame, unsigned frames) {
    if (!frame || frame > 8388608u) return;
    m->embedded = 1;  /* even an explicit EOF marker supersedes spliceN.txt */
    if (frame >= frames || m->count == 299) return;
    unsigned i = 0;
    while (i < m->count && m->end[i] < frame) ++i;
    if (i < m->count && m->end[i] == frame) return;
    for (unsigned j = m->count; j > i; --j) m->end[j] = m->end[j-1];
    m->end[i] = frame;
    ++m->count;
}

static int audition_legacy_markers(unsigned bank, unsigned reel, unsigned frames,
                                   AuditionMarkers *m) {
    uint32_t fil[138];  /* this firmware's FatFs FIL, including sector cache */
    char path[32], line[64];
    audition_name(path, bank, reel, 1);
    int result = marker_open(fil, path, 1);
    if (result == 4) return 1;  /* FR_NO_FILE means the entire reel is one splice */
    if (result) return 0;
    while (marker_gets(line, sizeof(line), fil)) {
        const char *p = line;
        unsigned id, frame, enabled;
        if (audition_number(&p, &id) && *p == ' ' && audition_number(&p, &frame) &&
            *p == ' ' && audition_number(&p, &enabled) && enabled)
            add_audition_marker(m, frame, frames);
    }
    int failed = ((const unsigned char *)fil)[7] != 0;
    return !marker_close(fil) && !failed;
}

/* RIFF data may follow JUNK, LIST, or embedded cue chunks. Walk the chunk
 * headers within the physical file, matching the first data chunk accepted
 * by D22, including its tolerance for module-authored stale RIFF sizes. */
static int audition_data_offset(void *fil, unsigned frames, unsigned *offset) {
    unsigned size = ((const uint32_t *)fil)[3];
    unsigned pos = 12, chunk[2];
    while (pos <= size && size - pos >= sizeof(chunk)) {
        if (!audition_read_at(fil, pos, chunk, sizeof(chunk))) return 0;
        pos += sizeof(chunk);
        if (chunk[1] > size - pos) return 0;
        if (chunk[0] == 0x61746164u) {
            *offset = pos;
            return chunk[1] == frames * 8u;
        }
        pos += chunk[1];
        if ((chunk[1] & 1u) && pos < size) ++pos;
    }
    return 0;
}

int preview_bounds(void *fil, unsigned bank, unsigned reel, unsigned splice,
                   unsigned *byte_offset, unsigned *frames) {
    AuditionWave wave;
    unsigned data;
    if (!splice || splice > 300 || audition_probe(fil, &wave) != 1 ||
        !audition_data_offset(fil, wave.frames, &data)) return 0;
    AuditionMarkers marks;
    marks.count = marks.embedded = 0;
    for (unsigned i = 0; i < wave.cue_count; ++i) {
        unsigned cue[6];
        if (!audition_read_at(fil, wave.cue_pos + i * sizeof(cue), cue, sizeof(cue))) return 0;
        add_audition_marker(&marks, cue[1], wave.frames);
    }
    if (!marks.embedded && !audition_legacy_markers(bank, reel, wave.frames, &marks)) return 0;
    if (splice > marks.count + 1) return 0;
    unsigned start = splice > 1 ? marks.end[splice-2] : 0;
    unsigned end = splice <= marks.count ? marks.end[splice-1] : wave.frames;
    *byte_offset = data + start * 8u;
    *frames = end - start;
    return 1;
}
