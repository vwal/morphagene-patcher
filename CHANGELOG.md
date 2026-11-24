# Version history

## mg204+c6 — 2026-11-24

- With `dens 1`, `dstr 0` (or `0.0`) now selects stock Gene timing on power-up and settings-only reload. SHIFT + Gene Size remains available for independent density. Already-playing Genes finish when timing changes.
- Omitting `dstr` now starts at **1.0 Gene/sec** on power-up and preserves current timing on a settings-only reload. An explicit `dstr 8.0` still recalls eight starts per second. Edit an older card once if you want stock timing or the lower rate.
- Both card readers and both editors accept an explicit zero for all 45 settings. For `tlen`, `splc` and `trst`, it selects 1. For `mcr1`, `mcr2` and `mcr3`, it selects the smallest forward ratio, +0.0625.
- Updated the patcher, downloadable offline editor, and Letter/A4 guides and quick cards. The module and editors write `// firmware version 204+c6`.

## mg204+c5 — 2026-11-24

- Added `dryk 3` for wet-only performance recording. The recorder combines live input at real-time speed with the Gene playback you hear, including Varispeed, Morph, Gene Size and Slide. Overdub the current splice to feed the result back into playback, or record into a new splice to keep the original.
- Added three main S.O.S. curves. `sosc 0` (default, including when omitted) brings both sources to full level at noon. `sosc 1` keeps incoming audio full and varies existing audio. `sosc 2` keeps existing audio full and varies incoming audio. Normal monitoring follows the curve in `dryk 0`. Modes 1–3 keep a wet-only return. The first take on an empty reel always captures full input.
- **Upgrading from c4:** for the previous full-input tape overdub, choose `dryk 2` and `sosc 1`. To extend the last splice with `dlen 1`, start REC at fully CCW with `sosc 0` or `1`.
- With `dens 1`, SHIFT + Gene Size fully CCW selects stock Gene timing. Unshifted Gene Size still sets length. Move just clockwise for 0.1 Genes/sec, through 8 at noon to 128 fully clockwise. Omitting `dstr` on settings-only reload preserves the timing choice.
- Fixed card-removal detection on an empty, single-sector reel after the last splice is erased. Updated both editors, the Letter and A4 guides and quick cards, and the module and editor header to `// firmware version 204+c5`.

## mg204+c4 — 2026-11-22

- Added wet-only output for mixer sends. With `dryk 1`, recording follows the existing controls. With `dryk 2`, fresh input records at every S.O.S. setting and S.O.S. controls how much previous audio survives the overdub. The default is `dryk 0`.
- Fixed-length overdubs retain the loop length by default. With `dryk 2` and `dlen 1`, starting REC at fully counterclockwise S.O.S. on the last or only splice records a replacement from its start. Longer takes extend it and shorter takes preserve the tail.
- Added WAV and options-file drop areas, a downloadable single-file offline editor, all 12 stock settings alongside 32 enhancement controls, optional preset labels and reset with confirmation.
- Updated the Letter and A4 guides and quick cards. Rewritten options files now carry `// firmware version 204+c4`.

## mg204+c3 — 2026-11-21

- Fixed normal card mounts and startup changing `vsop 0` or `vsop 1` to
  forward-only playback. The options reader now skips wrapped portions of a
  line, including the old `vrng` comment that contained `vsop 2`. The module
  and editor write a shorter comment, and the editor replaces the old generated
  comment when a card file is imported and saved.
- The normal reader also keeps its place across wrapped comments containing a
  stray NUL byte.
- The module and editor identify rewritten files with `// firmware version 204+c3`.
  If an older release already saved `vsop 2`, select the desired layout once.

In hardware testing, `vsop 1` survived two consecutive power cycles and the
module wrote the `204+c3` header.

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
