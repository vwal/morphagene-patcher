# Using the mods

For overdubbing and loop recording, pages 12–13 of the full guide explain how `dens`, `dstr`, `inop`, `dryk` and `sosc` interact. The examples cover a clean phrase, recording overlapping Genes into a new splice, and fading layers on a wet-only mixer return. [US Letter](../web/morphagene-manual-letter.pdf#page=12) · [A4](../web/morphagene-manual-a4.pdf#page=12)

For whole-splice speech, try forward +1×, Slide and Gene Size fully CCW, and Morph near 9 o’clock with the clock unpatched. Use `dens 1, dstr 0` to start there with ordinary timing. Hold SHIFT and turn Gene Size clockwise to introduce independent launches. A settings-only reload can recall stock timing while the existing Genes finish. [Gene timing at startup and reload](OPTIONS.md#gene-timing-at-startup-and-reload).

Most performance gestures use **SHIFT**: hold SHIFT and turn a knob. When you
let go of SHIFT after a turn, the module **doesn't** jump to the next splice,
and SHIFT + SPLICE / REC deletes are blocked for that hold, so a gesture can't
delete audio. A plain SHIFT tap still moves to the next splice, as stock.

After a gesture, the knob you turned **holds its old value** until you turn it
back near where it was (pickup). That way the sound doesn't jump when you let go of SHIFT.

| Gesture | What it does | Setting |
|---|---|---|
| SHIFT + S.O.S. | Tape mode or classic TLA feedback | `tape` |
| SHIFT + Morph | Sample-rate reduction or tape warble | `fxsl` |
| SHIFT + Varispeed | Lock to a scale (`vqnt 0`) or temporarily adjust continuously (`vqnt 1`) | `vqnt`, `octl`, `scal` |
| SHIFT + Slide | Random Gene start positions (jitter) | always on |
| SHIFT + Gene Size | Independent density: startup timing from `dstr` (0 for stock, default 1.0 Gene/sec); turn fully CCW for stock timing, then slightly clockwise for 0.1–128 Genes/sec. Knob rate remains until adjusted again, recalled by dstr reload or powered off; not saved across power cycles. Reload recalls explicit `dstr`; omit to keep the live rate. Overrides Turing rate | `dens 1` |
| SHIFT + Organize / Gene Size / Slide | Turing mode controls | `sldm 1` |
| REC held + SHIFT taps | Input gain (stock), now remembered | `ingn` |
| (no gesture) | Mono input: L on both channels | `mono 2` (auto) or `mono 1` |

Settings are in `options.txt`; see [OPTIONS.md](OPTIONS.md).

## Banks and splice selection

Set `bank 1` in the root `options.txt` and mount the card normally. Bank 1 uses existing root reels. For more banks, create folders named `bank2` through `bank8` on the card. Each bank holds up to 32 reels. Recording another splice keeps it on the current reel. On matched cards used for settings-only reload, keep the reel and its markers in the same bank and slot.

1. Hold **SPLICE first**, add **REC**, and keep both held for about three seconds until **REEL blinks**. Release both.
2. Turn **Organize** to the bank. Confirm with a short **SPLICE → REC** chord. Release both between confirmations.
3. Turn Organize to a recorded reel and confirm. A sole recorded reel double-flashes. For a new recording, choose the pink/white **New Reel** and confirm. It fills the reel step in an empty bank, or the top 5% clockwise when a blank or free slot is available in a populated bank.
4. For a recorded reel, choose its splice and confirm. A single splice spans the whole dial. Tap **SHIFT** to cancel while browsing.

With `audt 0` or no audition setting, pause on a reel to hear its first splice, or on a splice to hear it loop forward at +1×. The original performance keeps running underneath. Cancel returns to its current position. Use `audt 1` to keep that performance audible while preparing a change. Final confirmation uses `omod 0` for the current Gene transition or `omod 1` for an immediate switch. Different reels take their usual SD load time. New Reel opens on confirmation at the reel step.

For the usual current-bank reel browser, release the initial chord before the long hold completes. That browser keeps its native audition. `bank 0` (default) uses the root and the ordinary browser.

## Play through a reel

Set `thru 1` and turn Organize into its last 5% clockwise to advance and wrap through splices. With `thru 2`, reverse Varispeed steps to the previous splice and wraps from first to last. Below the play-through zone, Organize still selects every splice manually. Start with full-length Genes and ordinary timing to hear complete phrases. Shorter Genes can advance the sequence faster. The default `thru 0` leaves the whole dial available for manual selection.

## Return to 1:1 and optional presets

With `vuni 1`, hold SHIFT alone for at least 0.5 seconds, then release for exact
forward +1x from any Varispeed position. Short taps still navigate splices.
Knob movement, another button or card/reload activity cancels the reset. Keep
the SHIFT input unpatched. Speed holds until the combined knob/CV input picks up.

With `vctr 1`, +1× sits at calibrated noon in every layout, range and scale. Bidirectional layouts fit stop and reverse into the left half. Use `ntch 0` for a continuous sweep, `1` for the forward unity notch, `2` for reverse, or `3` for both. A reverse notch applies only in bidirectional layouts. Each added notch spans about 4% of knob travel. Quantization still snaps according to the selected scale. Omitting `ntch` at startup keeps the c6 behavior, including the forward 48–52% notch when centered.

All dialable control values can be optionally recalled; see [all keys](OPTIONS.md).
Included values use soft pickup from the preset position. Secondary amounts
are picked up with their corresponding SHIFT + knob gesture. Omitted keys
preserve live state on settings-only reload; saves retain configured values,
not later live adjustments. A splice preset above the reel count selects the
last splice. Existing density/gain keys remain available.

## SHIFT + S.O.S.: tape mode (default)

In `dryk 0/1`, turning SHIFT + S.O.S. or recalling `fbkp` activates the separate feedback control. Without either, ordinary recording follows `inop` and the main `sosc` curve. Modes 2 and 3 use the main curve directly.

While you overdub an existing splice:
- **A virtual tape head** writes into the Slide / Gene Size window. It moves at
  the Varispeed rate, so it plays backwards in reverse and pauses at zero speed.
- **SHIFT + S.O.S. sets how much of the old recording stays** with each pass
  (like tape feedback). At 100% with silent input, nothing changes.
- **Plain S.O.S.** sets the listening mix in mode 0. Mode 1 keeps the return wet only.
- **Morph is capped at 0.3 while dubbing** to stay within the CPU budget. Change it with `mcap`.

## SHIFT + S.O.S.: classic TLA feedback (`tape 0`)

In modes 0/1 with classic feedback active and `inop 0`, the recorded signal becomes your input **plus** the Gene playback, and
SHIFT + S.O.S. sets how much playback is fed back. Use this for
sound-on-sound with TLA, without tape mode's moving head.

## SHIFT + Morph: SRR or warble

- **SRR (`fxsl 1`, default):** sample-rate reduction on the Gene playback.
  Turn right for more; fully left is off.
- **Warble (`fxsl 2`):** tape wow and flutter on the Gene playback speed,
  up to about 1.4 semitones. It's cheaper on CPU than SRR.
- **`fxsl 0`:** off. Morph stays stock.

The input itself isn't affected, so with feedback or TLA the effect builds
up pass by pass. Optional srrp and wrbp recall separate amounts at startup/live reload; otherwise
amounts start at their normal defaults. fxsl 0 bypasses both effects and removes
any lingering warble offset.

## SHIFT + Varispeed: scale lock

**Development 3:** set `vqnt 1` to quantize by default, with SHIFT + Varispeed
temporarily continuous and release snapping back. This works in every stock
and expanded range, including forward 8x. Other SHIFT gestures keep pitch
quantized. `octl 0` disables either mode. See [details](DEVELOPMENT_3_QUANTIZED.md).
The latched behavior below describes the default `vqnt 0`.

While SHIFT is held, Varispeed snaps to the nearest step of a scale, so you
can transpose the reel without a CV quantizer. Choose the scale with `octl`:

| `octl` | Steps |
|---|---|
| 1 (default) | Octaves: −2, −1, −½, −¼, stop, ¼, ½, 1, 2 |
| 2 | Octaves + fifths |
| 3 | Every semitone |
| 4 | Your own scale, listed in `scal` |
| 0 | Off |

For `octl 4`, list the semitones above the root that you want, e.g.
`scal 3,5,7,10` (minor pentatonic) or `scal 2,4,5,7,9,11` (major). The root
and its octaves are always included.

Every scale is relative to normal speed (1×), works forward and in reverse,
and goes from about ⅛× up to 2× with `vrng 0`. With `vrng 1`, the range
extends to about 1/64× through 4×; octave mode reaches 1/32× through 4×.
Stop is always a step. See [the extended-range guide](EXTENDED_RANGE.md). The steps are in tune
(equal temperament).

The lock stays after you let go of SHIFT. To release it, turn Varispeed about
half an octave away. In semitone mode the steps are close together on the
knob, so turn slowly; if you mostly want to get back to normal speed, the
default `octl 1` is easiest.

## SHIFT + Slide: jitter

Each new Gene starts at a random offset around the Slide position. Fully left
is off; turn right for a wider spread across the splice.

## Turing mode (`sldm 1`)

A repeating loop of random choices, like a Turing Machine. Each step decides a
Gene's pitch (chord ratio), stereo and position scatter, so the randomness
repeats as a pattern.

1. **Set up:** set `sldm 1` in `options.txt` and power on. Gene Size at about
   1 o'clock (short Genes). Morph low for a melody (one Gene at a time),
   higher for chords.
2. **Lock the loop:** hold SHIFT and turn Organize fully left. The pattern now
   repeats.
3. **Let it mutate:** SHIFT + Organize up from the left. Steps sometimes get a
   new random choice. Fully right is normal randomness (stock).
4. **New pattern:** SHIFT + Organize fully right, then back to fully left.

| Control | In Turing mode |
|---|---|
| SHIFT + Organize | Evolution: fully left = locked, fully right = stock randomness |
| SHIFT + Gene Size | Genes per step: 1, 2, 3, 4, 6, 8, 12 or 16 |
| SHIFT + Slide | Spread: start jitter, repeated by each step when locked |
| `tlen` | Loop length, 1–16 steps (default 8) |
| `root` | Chance in % that a step plays the root pitch (default 50; `root 100` = no pitch changes) |

Pitches come from the stock chord ratios `mcr1`–`mcr3` in `options.txt`.
Organize doesn't move the selected splice while SHIFT is held. There's no LED
feedback for Turing mode.

## Input gain: remembered automatically

Set the input gain as on a stock Morphagene: hold **REC** and tap **SHIFT**.
Each tap steps through the four levels. The mod saves your choice to
`options.txt` about 3 seconds after your last tap, and restores it at
power-up. It never saves while recording; it waits until you stop.

You can also set it directly with `ingn` in `options.txt` (0–3; 0 is the
stock starting level).

## Mono input (`mono 1`)

With `mono 2` (auto), a mono source patched into L only is heard on both
outputs and recorded on both channels, as on Beads, Clouds or Mimeophon. A
stereo source into both inputs stays stereo. The Morphagene can't detect
whether R is patched, so auto listens instead: once R in has been silent for
half a second, L is faded onto R; as soon as anything plays into R, it fades
back to stereo within a few milliseconds.

`mono 1` copies L onto R all the time and ignores R in. `mono 0` (the
default) is stereo, as stock.

## Working in the background

These need nothing from you:

- **SD-card updates.** Later updates install from `mgmod.bin` on the card in a
  few seconds, with no audio cable ([INSTALLING.md](INSTALLING.md#3-later-updates-sd-card)).
- **Overdub stays in its splice.** A fix: with playback stopped and another
  splice selected, stock could start an overdub outside the selected splice.
  Now it stays inside it.
- **Faster flash access.** The firmware runs with the processor's flash
  prefetch on, which gives the CPU 10–17% more headroom per audio block, so
  high-Morph patches glitch less.
- **CPU log (troubleshooting only).** Off by default; see
  [OPTIONS.md](OPTIONS.md#troubleshooting-the-cpu-log-cpul).

## If something seems off

- **A SHIFT tap doesn't change splice:** a knob (or CV on it) moved while SHIFT
  was held, so it counted as a gesture. Tap again without touching the knobs.
- **Glitches at high Morph:** see the CPU note in the [README](../README.md#known-limits).
- **Go back to stock any time:** see [INSTALLING.md](INSTALLING.md#going-back-to-stock).
