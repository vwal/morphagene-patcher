# Version history

## mg204+c2 — 2026-11-15

- Optional return to exact forward 1:1: hold SHIFT alone for at least half a
  second and release. Soft pickup resumes Varispeed from unity; short SHIFT
  taps retain ordinary splice navigation.
- Optional +1x at calibrated noon, across full-range/bidirectional layouts,
  standard/extended ranges and all quantized scales. A 48-52% notch is available
  in continuous mode too; disabled centered mapping adds no flat zone.
- Optional presets for all dialable controls: Morph, Gene Size, Slide,
  Varispeed, primary S.O.S., feedback, SRR, warble, jitter/Turing spread,
  Turing evolution and Genes per step, alongside existing density/input gain.
  Included values recall at startup/live reload and use soft pickup; omitted
  values preserve live state on reload. Normal saves retain configured values.
- Splice recall follows normal `omod` timing. A selection above the reel count
  chooses the last splice while preserving the configured number.
- Separate SRR/warble amounts, effects-off bypass with warble pitch cleanup,
  and consistent held-control behavior across the audio engine.
- Reorganized editor with per-preset checkboxes, clear percentage meanings,
  classic/V-oct layout explanations and updated Letter/A4 manuals and quick cards.
- Editor and module options rewrites identify `firmware version 204+c2`.

Owner hardware tests passed. The complete firmware suite passes 201 tests,
including combined all-preset playback and recording comparisons. The c2 image
differs from the tested Development 8 image only in the version comment.

## mg204+c — Initial release

Expanded +/-4x and forward 8x Varispeed, normal/SHIFT quantization with custom
scales, independent density from 0.1-128 Genes/sec with configurable startup/live
recall, switchable Morph Loop, and trusted-card settings-only reload that keeps
the live reel and leaves the card mounted. Built on Briskcat's MIT-licensed
feedback, SRR/warble, jitter/Turing, gain, mono, SD-updater and other mods.

The original release remains in Git history. Development numbers identify
private test builds, not additional public releases.
