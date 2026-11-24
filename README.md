# Morphagene mg204-c6

[Open the firmware patcher and options editor](https://vwal.github.io/morphagene-patcher/).

An unofficial Morphagene mg204 extension by vwal, built on
[Briskcat’s Morphagene mods](https://github.com/briskcat/morphagene-mods).
The browser patcher processes your own official `mg204.wav` locally and downloads
`mg204-c6.wav` for audio installation or `mgmod.bin` for an existing SD updater.
No firmware is uploaded. This repository contains source and patch data only.

- **New in c6.** Set `dens 1` and `dstr 0` for stock Gene timing at startup or on a settings-only reload. SHIFT + Gene Size still gives you independent density on demand. An omitted `dstr` starts at 1.0 Gene/sec on power-up and preserves live timing on reload. If your c5 card already says `dstr 8.0`, edit that line to choose a different startup behavior. [Settings and zero values](docs/OPTIONS.md)
- **Introduced in c5.** Record live input alongside performed Gene playback on a wet-only return with `dryk 3`. Choose a main S.O.S. curve with `sosc`. For c4-style tape overdubs with full input, use `dryk 2, sosc 1`. SHIFT + Gene Size fully CCW now selects stock timing with independent density enabled. Card removal is recognized after erasing the last splice on a single-sector reel. [Recording and timing reference](docs/OPTIONS.md)
- **Introduced in c4.** Use a wet-only mixer return with the usual recording controls (`dryk 1`) or use S.O.S. to fade older layers (`dryk 2`). Overdubs can keep their length or extend the last splice. Dry kill and extending overdubs default to off. [Recording and settings](docs/OPTIONS.md)
- Drop the official WAV or your options file into the patcher. Download the standalone HTML editor for offline use. Both editors cover stock and enhanced controls and can reset to defaults after confirmation.
- c3 fixes the Varispeed layout reverting to forward only on a normal card
  mount or power-up. If an older release saved `vsop 2`, restore your preferred
  layout once. See the [c3 update instructions](docs/RELEASE_MG204_C3.md).
- Optional SHIFT hold/release return to exact forward +1x, with soft pickup.
- Optional +1x at calibrated noon, across all layouts/ranges/scales, with a 48-52% notch.
- Optional presets for every dialable control plus splice selection; independent
  checkboxes, startup/live recall, soft pickup and last-splice fallback.
- Expanded Varispeed: +/-4x, or forward stop-to-8x.
- Optional normal pitch quantization and custom scales.
- Independent Gene density from 0.1 to 128 Genes/sec. The shifted knob still gives 8 Genes/sec at noon.
- Morph Loop included and disabled by default (`mlop 0`; enable with `mlop 1`).
- Settings-only reload: remove the idle card, wait for its SHIFT light to go out,
  hold SHIFT alone for one second until steady, then insert a matching card while
  holding SHIFT. Preserves the live reel/playback position and leaves the card
  mounted. Arming is unavailable while mounted. Two flashes mean success.
- Briskcat’s tape/TLA feedback, playback effects, jitter/Turing patterns,
  saved input gain, mono input, SD updater and other improvements.

Trusted-card reload does **not** compare reel contents. Keep WAVs, splice files
and reel names identical; change only options.txt. Recording/saving/editing can
make other copies stale: synchronize them before the next settings-only swap.
Normal mounting still loads a card’s reel in the usual way.

## Guides

The website includes Letter/A4 manuals and quick cards. Source documentation:
[c6 recording guide, pp. 12–13](web/morphagene-manual-letter.pdf#page=12),
[options](docs/OPTIONS.md), [controls](docs/USING.md),
[installation/recovery](docs/INSTALLING.md), and [build/tests](docs/TESTING.md).

On a Morphagene, the owner confirmed that recalling stock Gene timing resolved a repeating phrase after reboot. Earlier hardware checks covered dry kill, the stock-timing gesture, unity recall and presets. The firmware
suite exercises card reads and rewrites alongside playback and recording.
Separate browser checks cover the options editor and generated firmware.
The [version history](CHANGELOG.md) records changes since the original release.

This project contains carefully tested AI-generated code.  
Independent customization. Not an official Make Noise release.

## Development

Use the pinned Arm GNU 14.2.rel1 toolchain; see the test guide. The `full` and
`full_morph_loop` CLI names are compatibility aliases for the same c6 image.
CLI files retain their internal `mg204-full.*` names. Keep generated firmware
private; it contains Make Noise code and must not be committed here.

`web/` is the static site. Run `python3 tools/make_site.py` after changing
the editor or release version. It rebuilds the site and the downloadable
[single-file options editor](web/morphagene-options-editor.html). The standalone
includes the form, editor scripts, theme, styles and license for offline use.
The generator reads `tools/offline_editor.html.in`.
Run `node tests/test_web.mjs` to verify that both editions match.
`tools/make_manual.py` generates the printable guides with Liberation Sans,
ReportLab and pypdf. GitHub Pages deploys `web/` on pushes to `main`.
Local development packaging scripts also reference preserved development
folders outside this repository; they are not needed to use or deploy the site.

## Credits and license

Briskcat created the upstream mods, browser patcher and encoder; its MIT
copyright and permission notice are retained. Audio encoding derives from
Émilie Gillet’s [stm-audio-bootloader](https://github.com/pichenettes/stm-audio-bootloader).

Our original additions: Copyright (c) 2026 vwal,
[Attribution - No Sale License 1.0](LICENSE), with [scope/examples](LICENSING.md).
Free use, modification and sharing with notices retained; no sales, paid bundles,
paid products containing our additions, or paid firmware services. **Make Noise
may integrate and commercially distribute our additions in its official firmware
and products**, with notices retained, as specified in section 5. Paid musical
performances and recordings remain allowed. Upstream MIT rights are unchanged.
This is source available, not an OSI open-source license for the combined work.
Morphagene and Make Noise are trademarks of Make Noise. This project is unofficial
and not endorsed by Make Noise.
