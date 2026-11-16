# Morphagene mg204+c2

[Open the patcher and options editor](https://vwal.github.io/morphagene-patcher/).
This release builds on the original mg204+c and Briskcat's Morphagene mods.
The owner confirmed the unity and optional preset features on hardware;
201 automated firmware tests pass, including combined playback/recording checks.

## Install

Build from the original official `mg204.wav`. Download `mg204+c2.wav` for the
initial audio install, or `mgmod.bin` if the SD updater is already installed.
For an SD update, copy `mgmod.bin` to the card root and reboot; success renames
it `mgmod.ok`. See [installation and recovery](INSTALLING.md) for audio flashing
and the required Varispeed calibration. Existing options remain compatible.

## Two ways back to original speed

Enable `vuni 1` to hold SHIFT alone for at least 0.5 seconds, then release for
exact **forward +1x** from any Varispeed position. Short taps still advance
splices, without an added delay. Moving any knob, pressing another button or
card/settings-reload activity cancels the reset. Keep the SHIFT input unpatched.
The combined Varispeed knob/CV reading picks up from unity; until then +1x holds.

Separately, `vctr 1` places +1x at calibrated noon in every layout, range and
scale. Its 48-52% notch is easy to find in continuous mode. Bidirectional stop
and reverse fit into the left half. With `vctr 0`, no extra flat zone is added.
Both options default to 0.

## Optional presets and pickup

All dialable values can be included in a prepared `options.txt`. Check only the
recalls you want. Explicit values apply at startup and settings-only reload,
even if identical to the previous file. Missing keys keep live values on reload.

| Key | Control | Range |
|---|---|---|
| `mpos` | Morph | 0-100% |
| `gpos` | Gene Size | 0-100% |
| `spos` | Slide | 0-100% |
| `vpos` | Varispeed | 0-100% |
| `sosp` | Primary S.O.S. mix | 0-100% |
| `splc` | Selected splice | 1-300 |
| `srrp` | SRR | 0-100% |
| `wrbp` | Warble | 0-100% |
| `jitp` | Jitter / Turing spread | 0-100% |
| `fbkp` | Tape / classic TLA feedback | 0-100% |
| `evop` | Turing evolution | 0-100% |
| `trst` | Turing Genes per step | 1, 2, 3, 4, 6, 8, 12, 16 |

Density (`dstr`) and input gain (`ingn`) were already configurable. Main Organize
is represented by splice selection. External clock and gates are not presets.

**Percentages represent virtual knob positions:** 0% fully CCW, 50% noon,
100% fully CW. The existing nonlinear curves apply; these are not percentages
of duration, pitch or effect strength. Varispeed uses its calibrated range.

- **Morph:** 10% selects the stock seamless-loop setting (9-11%). At 0%,
  `mlop 0` leaves a scheduling gap; `mlop 1` removes it. These values describe
  normal unclocked scheduling with `dens 0`; clock/density can change spacing.
- **Gene Size:** 0% and 1% are longest/full splice; 100% is shortest. Turning
  clockwise shortens Genes. The exact duration also depends on the reel,
  playback speed and clock.
- **Slide:** moves the window from the beginning toward the end of the splice.
- **Varispeed:** position before `vsop`/`vrng`/`vctr`, not speed percentage.
  `vpos 50` gives +1x with `vctr 1`. A later unity gesture replaces this hold;
  a later explicit `vpos` recall replaces a unity hold.
- **S.O.S.:** 0% is input, 100% Gene playback; `fbkp` is a separate feedback
  control. Stock `inop` still selects the recorded signal.
- **Effects:** 0% is off/no feedback or jitter; increasing strengthens the
  existing effect curve. Evolution is locked at 0% and fresh at 100%.

After recall, soft pickup continues from the preset: move the corresponding
control near or across the held position to take over. Secondary effects use
their matching SHIFT + knob gesture. Knob and CV are summed by the hardware,
so CV can trigger pickup. An already-near knob may pick up on the next block.

`fxsl` selects SRR, warble or bypass. SRR/warble retain separate amounts and
cannot run together. `tape` selects feedback mode; `sldm` enables Turing.
Independent density retains priority over the Turing rate gesture.

A `splc` above the reel's splice count selects its last splice while keeping the
configured number. `splc 300` can therefore recall the last splice on any
supported reel. `omod` retains ordinary boundary/immediate switching behavior.
Explicit splice selection intentionally changes playback location.

## Live recall and saving

Finish writes, remove the idle card, and wait for the SHIFT light to go out.
Hold SHIFT alone for one second until steady, then insert a prepared matching
card while holding. Two flashes mean success; three mean failure. Release SHIFT
after confirmation. The live reel stays loaded, and successful reload leaves
the card mounted for recording/saving. No arming while a card is mounted.

Keep WAVs, splice sidecars and reel names identical across cards. No reel-content
verification runs. Recording or edits make other copies stale; synchronize them
before another swap. Normal mounting remains available to load a card's reel.

Saves preserve **configured preset numbers, not later knob movements**. New
preset keys omitted from the latest successful file remain omitted. `dstr` has
its existing exception: module rewrites add it back, so recheck a card intended
to preserve live density. No gesture captures live knobs into the file.

Editor and module rewrites include `// firmware version 204+c2`. Keep the first
numeric state line intact; the version is a comment below it. These extensions
are not implemented by stock mg204. See [all options](OPTIONS.md) and
[version history](../CHANGELOG.md).

## Credits and limits

Built on [Briskcat's Morphagene mods](https://github.com/briskcat/morphagene-mods),
with upstream MIT notices retained. Our additions retain the existing
[Attribution - No Sale terms](../LICENSE), including the Make Noise exception.
This project contains carefully tested AI-generated code. Independent
customization. Not an official Make Noise release. Use at your own risk;
exact latency and every clock/CV/dense-patch combination remain unmeasured.
