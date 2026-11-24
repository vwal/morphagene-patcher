# Development 2: forward 8x and independent Gene density

Built on the earlier +/-4x development version. The user confirmed the earlier
range works on their Morphagene. **These new changes are emulator-tested only.**

## Install and enable

Keep the previous `mgmod.bin` as a rollback. Copy this development version's
`mgmod.bin` to the card root, insert it, and power on. Let the update finish
and the module restart. The SD updater preserves calibration; no recalibration
is needed. It retires the update file as `mgmod.ok` before flashing.

Edit the existing lines (or add a missing mod key) in `options.txt`, preserving
its first line and other settings:

```text
vsop 2
vrng 1
octl 1
dens 1
```

Power-cycle after changing options. These are settings to merge, not a complete
replacement options file. All new behavior is opt-in: `vrng 0` and `dens 0`
remain the defaults. With `vsop 0` or `1`, `vrng 1` still gives the previous
bidirectional +/-4x range.

## Forward-only speed and scale lock

With `vsop 2` and `vrng 1`, the knob uses its full travel for forward playback:
stop at the lower end, then 1/16x through 8x, with equal travel per octave and
small endpoint dead zones. There is no reverse playback in this mode.

Hold SHIFT and move Varispeed to lock. With `octl 1`, the exact steps are:

`stop, 1/16, 1/8, 1/4, 1/2, 1, 2, 4, 8`.

The lock remains after releasing SHIFT. Moving the control about half an octave
away releases it. Fifths, semitones and custom scales (`octl 2/3/4`) also work.
`vrng 0` restores stock forward-only 4x behavior, including its scale-lock bypass.

The forward 1x position moves because the top range gains another octave.
This also changes the pitch span of an incoming CV; do not assume the extended
range preserves the stock V/oct calibration. There is no dedicated new 8x LED
color. Higher speeds can make aliasing more audible.

The tape recording head now follows clean Varispeed through 8x (without the
playback warble). It still writes every crossed sample position, so recording
at 8x does more work than at 4x. Hardware CPU headroom remains to be measured.

## Independent Gene density

`dens 1` selects a separate, free-running grain-start clock. Its initial rate
comes from `dstr`. In mg204+c6, 0 selects stock timing and 0.1–128.0 specifies Genes/sec. The default is 1.0 Gene/sec. Earlier releases defaulted to 8. The configured value persists in options.txt; settings-only reload recalls an explicit dstr, even if unchanged. Omit dstr to preserve the live rate. Hold **SHIFT + Gene Size** and turn:

- Fully CCW selects stock timing (introduced in mg204+c5). Just clockwise of the endpoint selects 0.1 Genes/sec (one every ten seconds).
- Center: about 8 Genes/sec.
- Right: 128 Genes/sec.

The mapping is exponential on each side of the 8/sec midpoint, with 257 rate
settings. The last gesture amount lasts until another adjustment, explicit dstr
recall or power-off; it is not saved to the card. Ordinary Gene Size holds
its pre-gesture value until you return the knob near that position (pickup).

Density changes how often Genes start. Gene Size sets their source length;
Varispeed sets their pitch and traversal speed; Slide sets the source position.
Morph continues to affect envelopes, stereo and pitch/scatter behavior, but its
normal interval no longer decides the launch rate. Smoothing remains available.
Changing Varispeed can change a Gene's audible duration; it does not change the
requested density. At stop, new births pause.

For a first audition, use a short Gene, forward 1x, low Morph and no clock or
recording. Sweep SHIFT + Gene Size from left to right: isolated grains become
closer, continuous, then overlapping. Return Gene Size to its pre-edit position
before changing the actual grain length.

### Limits and interactions

- There are four existing Gene slots. A scheduled birth waits if the next slot
  is still audible; no active Gene is deliberately cut off. Long Genes at high
  requested density therefore reach a lower actual density. This is a regular
  timing control, not random trigger probability or an unlimited grain cloud.
- With tape dubbing active and `mcap` nonzero, density also limits simultaneous
  audible Genes to two. The existing Morph cap still applies. This conservatively
  bounds the new overlap load; it does not certify real-time performance at 8x.
- When the stock external-clock-active flag is set, independent density is
  bypassed so clocked Gene Shift/time stretch keeps its existing scheduling.
  Slow clocks and plugging/unplugging still need a hardware check.
- `dens 1` takes priority over Turing's SHIFT + Gene Size rate assignment. Turing
  evolution and spread remain available, with its default/previous Genes-per-step
  value. Set `dens 0` to regain the Turing rate gesture.
- There is no separate density CV input or new density LED indication.

## Validation and hardware audition

The public tests execute assembled hooks and the actual mg204 audio routine.
They cover full control sweeps, exact forward scale steps, hysteresis/pickup,
rate lookups, unchanged bidirectional modes, density timing across pitch/Morph,
both reconstruction paths, busy voice deferral, stop and clock gating, and the
8x tape writer's positions, retention and wrap bounds. With the previous image
provided, density-off audio is compared byte-for-byte against that build.
Short-Gene tests also run 8x playback and sustained tape overdubbing at the
maximum density setting, including the stock record-stop transition.

Unicorn does not model real STM32 timing, SDRAM stalls, audio converters, or the
physical CV calibration. Begin with playback and density at 1x. Then test 8x
playback, followed by tape overdubbing on an expendable splice, initially at
low density and `mcap 3`. Check reverse +/-4x, SHIFT pickup, external clocks,
new/old splices, reels, and power cycles. Use `cpul 1` temporarily if diagnosing
glitches, then restore `cpul 0`. Back up audio before destructive overdub tests.

To return to the previous sound/control behavior without changing firmware:
use your previous `vsop 0/1`, `vrng 1`, and `dens 0`. The prior update image is
also included under `rollback-4x/` for an SD rollback.
