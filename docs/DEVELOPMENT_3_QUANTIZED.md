# Development 3: quantized Varispeed by default

This version adds `vqnt 1`: ordinary Varispeed movement follows the scale in
`octl`, and SHIFT + Varispeed temporarily restores the existing continuous
lookup and glide. Releasing SHIFT returns immediately to the nearest scale
step, even if the knob does not move again. The free-pitch value is not latched.

Development 2's forward 8x range and independent density are included. The user
reported a successful first hardware audition of Development 2; broader testing
was still planned. Development 3's new behavior is emulator-tested and awaits
its own hardware audition.

## Enable it

Update from the included `mgmod.bin` using the existing SD updater. Calibration
is preserved. Merge these keys into the existing `options.txt`, preserving its
first line and your other settings, then power-cycle:

```text
vsop 2
vrng 1
vqnt 1
octl 3
dens 1
```

This example selects forward stop..8x, semitone quantization and independent
density. `dens` is independent of `vqnt`; keep `dens 0` for stock Gene timing.

| `octl` | Scale |
|---|---|
| 0 | Quantization disabled, including with `vqnt 1` |
| 1 | Octaves; easiest return to exact 1x |
| 2 | Octaves + equal-tempered fifths |
| 3 | Every semitone |
| 4 | Custom semitones from `scal`, plus root and octaves |

For example, `octl 4` with `scal 3,5,7,10` selects minor pentatonic relative
to 1x. These scale modes already worked in Development 2's extended forward
range. `root` is the separate Turing root-probability setting, not a scale tonic.

## Controls and range support

- Turn Varispeed normally to move between scale steps. Small movement within
  a step does not release the quantizer. Hysteresis reduces chatter at boundaries.
- Hold SHIFT and turn Varispeed to enter continuous adjustment. This gesture
  claims after more than 8 ADC counts of movement (about 0.2% of full travel),
  instead of the normal 48-count gesture threshold. It remains free while held.
- Release SHIFT to snap to the scale at the current knob/CV reading.
- A plain SHIFT tap retains splice navigation. Merely pressing SHIFT without
  moving Varispeed keeps the pitch quantized. Other SHIFT gestures, including
  density and S.O.S., also keep Varispeed quantized. The first knob to claim a
  gesture owns that hold, as before.
- Turning Varispeed with SHIFT consumes the gesture, so release does not navigate
  to another splice. The recording-release path has the same behavior.

| `vsop` | `vrng 0` | `vrng 1` |
|---|---|---|
| 0 or 1 | Bidirectional stock range, up to +/-2x | Bidirectional extended range, up to +/-4x |
| 2 | Forward stop..4x | Forward stop..8x |

`vqnt 1` works with all four range combinations. In the forward 8x range,
`octl 1` gives stop, 1/16, 1/8, 1/4, 1/2, 1, 2, 4 and 8x. Stop remains a step
in every scale. Reverse steps use the same pitch-class pattern as forward.

The quantizer acts on the combined knob/CV reading. Changing Varispeed CV while
SHIFT is held can claim the gesture just like a knob turn; the lower threshold
makes this more sensitive. Hardware CV calibration and noise behavior still
need checking. The expanded range retains Development 2's CV mapping.

The scale controls the base Varispeed rate. Morph chord ratios and playback
warble can still shift the audible pitch afterwards; disable those effects
when checking tuning with a tuner.

## Existing behavior and rollback

`vqnt 0` is the default when the key is missing. It keeps Development 2's
SHIFT-to-lock behavior, including a latched scale lock after release and
movement away to return to continuous control. Stock forward-only mode
(`vsop 2`, `vrng 0`) still bypasses that legacy SHIFT lock.

`octl 0` disables scale locking and quantization in either gesture mode.
Returning `vqnt` to 0 needs no firmware downgrade. The package also includes
Development 2's SD update in `rollback-dev2/`.

## Validation

Tests execute assembled Thumb code and the actual mg204 audio routine:

- Every one of 4096 control positions, all four scales, all three `vsop` values
  and both ranges, without SHIFT (98,304 quantizer cases).
- Lock hysteresis, continuous gesture, release without further knob movement,
  `octl 0`, other gestures, register/stack preservation and glide selection.
- Both gesture thresholds, plain-tap navigation and gesture navigation suppression,
  including the recording-release path.
- Actual audio rates in every range, exact octave endpoints and stop.
- Parser validation, boot defaults, settings writer and browser editor round-trips.
- With the prior image supplied, byte-identical audio with `vqnt 0` compared
  with Development 2, with and without density.

The prior extended-range, density, tape, update and memory-ledger tests remain
part of the suite. Emulator results do not measure hardware CPU timing. The
quantizer now runs on every audio block in this mode, so audition short Genes,
high density/Morph and tape dubbing as well as ordinary playback. Start by
checking 1x lock, SHIFT free adjustment and release, then your preferred scales.

See [Development 2](DEVELOPMENT_8X_DENSITY.md) for density and 8x tape details,
and [TESTING.md](TESTING.md) for reproducing the builds and tests.
