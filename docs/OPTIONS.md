# Settings (`options.txt`)

**mg204+c4** adds wet-only output for send/return use and a choice of fixed or extending overdubs. The previous **mg204+c3** fixed a settings-file read error that could change the Varispeed layout on a normal mount or at startup. See [the c3 release guide](RELEASE_MG204_C3.md).

The Morphagene keeps its settings in `options.txt` at the root of the SD card.
Normal mounting reads the file and then writes it back, including at power-up.
The settings-only reload reads it without writing; normal persistence resumes
after reconnect. With the mods
installed, a **Morphagene extended mods** section is added at the end of the file
the first time you power on. You don't have to create it.

**To change a setting:** edit the number after the key, save, put the card
back and mount it normally, or use the settings-only gesture to
preserve the live reel. This checkout's `web/` settings editor can also load your
`options.txt`, let you pick values from menus, and give the file back with
your stock settings kept. The published upstream editor does not include
these extended options.

In the editor, **Recall density on settings-only reload** includes `dstr` when
checked and removes it automatically when unchecked. Importing a file sets the
checkbox from the presence of an active `dstr` line. Unchecked preserves the
current density on settings-only reload, but startup then defaults to 8/sec.
The numeric field is disabled while unchecked and retains your value if you
check it again. Normal mounting and firmware options saves add `dstr` back;
review the file again before using it as a preserve-density card.

Leave the file's **first line** as it is; the Morphagene keeps its own state
there. Both editors and the module write
`// firmware version 204+c4` on a comment line below it.

For a settings-only reload, include one `dryk` line to choose the new routing. Include `dlen 0` or `dlen 1` to select the overdub length behavior. Omitting either setting preserves its live value.
A duplicate or malformed value rejects the entire live settings change. Each
setting defaults to 0 on power-up. In mode 2, fixed-length overdubs use the tape
head with fresh input at normal level, independent of `tape`, `inop` and
`fbkp`. Varispeed, Gene Size and Slide determine the tape head's travel.
For full-splice passes, use forward 1× and Gene Size fully CCW.

With `dryk 2` and `dlen 1`, the firmware checks S.O.S. when recording starts.
On the last or only splice, its zero-feedback zone (roughly the lowest 4.5% of
the effective knob/CV reading, including a recalled S.O.S. preset) selects one
continuous replacement. Fresh stereo input records forward at 1× from the
beginning of that splice, independent of Varispeed, Slide and Gene Size. A
15-second take over a 10-second splice gives 15 seconds of fresh audio. A
shorter take leaves its original length and remaining tail. A take started on
an earlier splice or above the zero-feedback zone uses fixed-length overdub
feedback. Moving S.O.S. during a take keeps the recording mode selected at
its start.

## The settings

All twelve preset keys below are optional and absent by default. Each has an
independent checkbox. Explicit values recall at startup and settings-only reload;
omitted values remain live on reload and stay omitted on future saves. Saves
keep configured presets, not later knob movements. Density has its separate,
previously documented rewrite behavior.

**Percentages are virtual knob positions:** 0% fully CCW, 50% noon, 100% fully CW.
They follow the existing curves, not linear percentages of duration, speed or
DSP strength. Included controls hold until their combined knob/CV input reaches
or crosses the recalled position; secondary effects use their SHIFT gesture.

| Key | Values | Default | What it does |
|---|---|---|---|
| `mpos` | Integer 0–100 | Omitted | Recall Morph; 10% (9-11%) selects stock seamless looping with unclocked scheduling/dens 0. 0% gaps with mlop 0 |
| `gpos` | Integer 0–100 | Omitted | Recall Gene Size: 0% and 1% full-splice/longest; 100% shortest. Nonlinear, not a length percentage |
| `spos` | Integer 0–100 | Omitted | Recall virtual Slide position with pickup |
| `splc` | Integer 1–300 | Omitted | Recall splice selection, obeying omod; above count selects the last while retaining the configured number |
| `vpos` | Integer 0–100 | Omitted | Calibrated Varispeed position before vsop/vrng/vctr; 50% is +1x with vctr 1 |
| `dryk` | 0, 1, 2 | 0 | 0 keeps c3 routing. 1 sends only Gene playback to both outputs and keeps normal recording controls. 2 sends only Gene playback and assigns primary S.O.S. to tape retention. |
| `dlen` | 0, 1 | 0 | 0 keeps existing-splice overdubs at their current length. With 1 and `dryk 2`, start a take at fully CCW on the last or only splice to replace it from the beginning. Holding REC beyond the old end extends the splice. A shorter take keeps the previous length and tail. Earlier splices retain their fixed windows. |
| `sosp` | Integer 0–100 | Omitted | Primary S.O.S. position. In modes 0 and 1, 0% selects input and 100% selects playback for the normal S.O.S. mix. In mode 2, 0% replaces each pass and 100% keeps it while recording fresh input. |
| `srrp` | Integer 0–100 | Omitted | SHIFT + Morph SRR position: 0 off, higher stronger; fxsl 1 |
| `wrbp` | Integer 0–100 | Omitted | SHIFT + Morph warble position: 0 off, higher stronger; fxsl 2; separate bank from SRR |
| `jitp` | Integer 0–100 | Omitted | SHIFT + Slide jitter/Turing spread: 0 off, higher wider scatter |
| `fbkp` | Integer 0–100 | Omitted | SHIFT + S.O.S. feedback for dryk 0/1. At 0% nothing is retained. At 100% retention is maximal. The tape option selects the recording mode. |
| `evop` | Integer 0–100 | Omitted | SHIFT + Organize Turing evolution: 0 locked, 100 fresh; nonlinear curve |
| `trst` | 1, 2, 3, 4, 6, 8, 12, 16 | Omitted | Turing Genes per step; independent density gesture keeps priority |
| `vuni` | 0, 1 | 0 | Hold SHIFT alone at least 0.5 seconds and release to recall forward +1× with automatic pickup. Use with SHIFT input unpatched; other controls cancel |
| `vctr` | 0, 1 | 0 | Exact +1× at calibrated noon, all layouts/ranges/scales; 48–52% explicit notch and centered unity cell only when vctr 1; preserves endpoints and compresses reverse/stop into the left half |
| `mlop` | 0, 1 | 0 | **0** stock Morph gaps; **1** seamless loop at minimum Morph. Included in Full |
| `dens` | 0, 1 | 0 | Independent density: startup rate from `dstr` (default 8 Genes/sec). Hold SHIFT and turn Gene Size to adjust 0.1–128 Genes/sec. Knob changes remain until adjusted again, recalled by dstr reload or powered off; they are not saved across power cycles. Takes priority over Turing rate |
| `dstr` | 0.1-128, at most one decimal | 8 | Startup/reload density in Genes/sec. Explicit `dstr` recalls the rate on settings-only reload, even if unchanged; omit to preserve the live rate. Requires `dens 1`; external clock takes priority. The configured value stays in options.txt |
| `vrng` | 0, 1 | 0 | **0** stock ranges; **1** +/-4x in `vsop 0/1`, stop to forward 8x with scale lock in `vsop 2` ([details](DEVELOPMENT_8X_DENSITY.md)) |
| `vqnt` | 0, 1 | 0 | **0** SHIFT + Varispeed locks; **1** quantized normally, SHIFT + Varispeed temporarily continuous; release snaps back. Uses `octl` / `scal` in every range |
| `tape` | 0, 1 | 1 | SHIFT + S.O.S.: **1** tape mode, **0** classic TLA feedback |
| `octl` | 0–4 | 1 | Varispeed scale: **1** octaves, **2** octaves + fifths, **3** semitones, **4** your scale from `scal`, **0** disables quantization in both gesture modes ([how it works](USING.md#shift--varispeed-scale-lock)) |
| `scal` | list of 1–11 | 0 (none) | Your scale for `octl 4`: semitones above the root, separated by commas or spaces, e.g. `3,5,7,10` (minor pentatonic). The root and its octaves are always on |
| `fxsl` | 0, 1, 2 | 1 | SHIFT + Morph: **1** sample-rate reduction, **2** tape warble, **0** off |
| `mcap` | 0–9 | 3 | Morph limit while tape mode is dubbing: **1–9** = 0.1–0.9, **0** = no limit. Above 5, or 0, can glitch with many Genes + dubbing + SRR |
| `sldm` | 0, 1 | 0 | Turing mode: **1** on, **0** off ([how to play it](USING.md#turing-mode-sldm-1)) |
| `tlen` | 1–16 | 8 | Turing mode loop length, in steps |
| `root` | 0–100 | 50 | Turing mode: chance in % that a step plays the root pitch instead of a chord ratio. `root 100` = no pitch changes |
| `ingn` | 0–3 | 0 | Input gain (REC held + SHIFT taps). Saved automatically about 3 s after you change it on the module; 0 = stock starting level |
| `mono` | 0, 1, 2 | 0 | Mono input: **2** auto, copies the left input onto the right only while nothing is playing into R in, so a mono source in L is heard and recorded on both channels and a stereo source stays stereo; **1** always copies L onto R (R in is ignored); **0** stereo, as stock ([details](../modules/mono_in/README.md)) |

At startup, invalid mod values are ignored and defaults remain. During a
dedicated settings-only reload, an invalid recognized value rejects the whole
transaction; missing keys retain their current values. SHIFT + Slide jitter starts
off unless recalled with jitp or adjusted manually.

## What the section looks like

```
//Morphagene extended mods
mlop 0 //0 stock gaps; 1 seamless loop at minimum Morph
vrng 0 //0 stock, 1 +/-4x bidirectional or 0-8x forward
vqnt 0 //0 SHIFT-to-lock; 1 quantized normally, SHIFT+Varispeed temporarily continuous
dens 0 //1: SHIFT+Gene Size controls independent density (0.1-128 Genes/sec)
tape 1 //SHIFT+S.O.S.: 0 classic TLA feedback (input + feedback x Gene playback), 1 tape mode (Varispeed tape head in the Slide/Gene Size window)
octl 1 //Varispeed scale: 0 off, 1 octaves, 2 octaves + fifths, 3 semitones, 4 custom scale (scal)
scal 0 //Custom scale for octl 4: semitones 1-11 above the root, e.g. 3,5,7,10 = minor pentatonic (root and octaves always on)
fxsl 1 //SHIFT+Morph effect: 0 off (Morph stays stock), 1 SRR (sample-rate reduction), 2 warble (tape wow and flutter on the Gene playback)
//SHIFT+Slide: Gene start jitter amount (left = off)
cpul 0 //CPU log, for troubleshooting only: 0 off, 1 on (writes cpulog.txt every 10 s; turn it off again afterwards)
mcap 3 //Morph cap while tape-dubbing: 0 none, 1-9 = Morph limited to 0.1-0.9 (CPU safety; 3 = 0.3)
sldm 0 //Turing mode: 0 off, 1 on: ...
root 50 //Turing: chance in percent that a step plays the root rather than a chord ratio (mcr1-mcr3)
tlen 8 //Turing loop length in steps, 1-16
ingn 0 //Input gain 0-3 (REC held + SHIFT taps); saved automatically a few seconds after a change
mono 0 //Mono input: 0 off (stereo), 1 left input copied to the right (heard and recorded on both channels; R in is ignored), 2 auto: only while nothing is playing into R in
```

## Varispeed changes back to forward only

The original `mg204+c` and `mg204+c2` releases can read `vsop 2` inside the
generated `vrng` comment as a second setting during a normal mount or at
power-up. This can overwrite either bidirectional layout in `options.txt`.

On those releases, edit the existing `vsop` line to `vsop 1` for bidirectional
1 V/oct or `vsop 0` for classic bidirectional. On the existing `vrng` line,
keep `vrng 0` or `vrng 1` and delete the trailing comment. Save the file and
mount the card. The workaround applies to that read. Those releases write the
old comment back, so remove it again before another normal mount or power-up.

With c3, set the desired layout once if the file already says `vsop 2`. The
module accepts the existing comment and replaces it on its next rewrite.

## Troubleshooting: the CPU log (`cpul`)

| Key | Values | Default | What it does |
|---|---|---|---|
| `cpul` | 0, 1 | 0 | **1** writes CPU statistics to `cpulog.txt` on the card, one line per second |

**Only turn this on when you're chasing glitches.** It writes to the card
every 10 seconds, so leave it off for normal use. To use it: set `cpul 1`,
play the patch that glitches for a minute, power off, and send `cpulog.txt`
with your bug report. Then set `cpul 0` again.

Flash prefetch, which speeds up the firmware and gives the CPU more
headroom, is always on and has no setting. An older `pfch` line in your file
is ignored.

## About the input gain save

The stock firmware already rewrites `options.txt` after every reel load. To
save a new input gain, the mod asks for that same rewrite. Several quick taps
make one write, and it never happens while recording. If the power goes off
during the rewrite (a fraction of a second), the file can come back incomplete.
The module then uses the default settings.

## Stock settings

The stock keys above the mod section (`vsop`, `inop`, `gnsm`, `pmod` and so
on) work exactly as described in Make Noise's manual. If an older build of
these mods left `gnsm 2` in your file, it now behaves like `gnsm 1` (smooth).
