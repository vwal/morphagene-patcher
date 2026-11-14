# Settings (`options.txt`)

**Development 5:** trusted-card reload and `mlop 0/1`; see [the live workflow](DEVELOPMENT_5_LIVE_OPTIONS.md). Card contents are not verified.

The Morphagene keeps its settings in `options.txt` at the root of the SD card.
Normal mounting reads the file and then writes it back, including at power-up.
The Development 5 reload reads it without writing; normal persistence resumes
after reconnect. With the mods
installed, a **Morphagene Study mods** section is added at the end of the file
the first time you power on. You don't have to create it.

**To change a setting:** edit the number after the key, save, put the card
back and mount it normally, or use Development 5's settings-only gesture to
preserve the live reel. This checkout's `web/` settings editor can also load your
`options.txt`, let you pick values from menus, and give the file back with
your stock settings kept. The published upstream editor does not include
these development options.

In the editor, **Recall density on settings-only reload** includes `dstr` when
checked and removes it automatically when unchecked. Importing a file sets the
checkbox from the presence of an active `dstr` line. Unchecked preserves the
current density on settings-only reload, but startup then defaults to 8/sec.
The numeric field is disabled while unchecked and retains your value if you
check it again. Normal mounting and firmware options saves add `dstr` back;
review the file again before using it as a preserve-density card.

Leave the file's **first line** as it is; the Morphagene keeps its own state
there.

## The settings

| Key | Values | Default | What it does |
|---|---|---|---|
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
Development 5 dedicated reload, an invalid recognized value rejects the whole
transaction; missing keys retain their current values. SHIFT + Slide
(jitter) has no setting: it's off until you turn it up.

## What the section looks like

```
//Morphagene extended mods
mlop 0 //0 stock gaps; 1 seamless loop at minimum Morph
vrng 0 //0 stock; 1 extended +/-4x (vsop 0/1), forward 8x (vsop 2)
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
