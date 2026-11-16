# Development 6, revision 3: +1× recall and +1× at noon

Private test build based on released mg204+c. Both new options default to **0**.
The published release, website, PDFs and earlier development packages are unchanged.
This build has emulator coverage; it awaits testing on the physical module.

## Installation and options

For an existing mg204+c installation, copy this package's `mgmod.bin` to the
card root and power-cycle. Confirm it becomes `mgmod.ok`. The package also
contains an audio update WAV and exact copies of the released firmware under
`rollback-mg204c/`. Use the usual audio installation/calibration procedure if
needed; see [installation](INSTALLING.md).

Add or edit these lines in your existing `options.txt`, keeping its first line
and other settings intact. Replace any existing copies of these keys; do not
append duplicates:

```
vuni 1 //SHIFT hold/release recalls exact forward +1x; default 0
vctr 1 //+1x at calibrated Varispeed noon; default 0
```

They are independent: either may be 0 while the other is 1. Both work at boot,
normal mounting and settings-only reload. A missing key during settings-only
reload preserves its current value; explicitly set 0 to disable it. Normal
firmware options writing preserves both settings. The published options editor
has not been changed for this private build; edit these two lines manually.

## SHIFT recall: `vuni 1`

With the SHIFT input unpatched, hold SHIFT alone for **at least half a second**
and release it. The release sets base Varispeed to exactly **forward +1×** from
any starting speed or direction. It does not reset the reel, splice, playheads,
recording state, or other sound controls. The reset release does not advance
to another splice. The speed stays unchanged until release: passing the
half-second threshold while still holding SHIFT does not reset it.

A short SHIFT tap keeps its normal navigation timing. Moving any of the six
knobs enough to exceed its existing gesture/noise threshold, or pressing REC
or SPLICE during the hold, cancels recall until SHIFT is fully released.
Cancellation remains in effect even if the knob returns to its starting point.
Existing SHIFT knob/button actions retain their meaning. REC/SPLICE combinations
can delete material; they are not neutral cancel gestures. Knob movement also
cancels recall when that knob's optional secondary function is disabled; in
that case normal SHIFT-release navigation still follows the existing behavior.

After reset, base speed holds at +1× until the calibrated Varispeed reading
reaches a small zone around, or crosses, the +1× pickup position. With `vctr 1`
that position is noon; with `vctr 0` it is the original unity position for the
selected layout/range. Knob and CV are summed before the firmware reads them,
so **Varispeed CV can cause pickup**, and modulation on any knob's control
channel can cancel the pending gesture. Pickup does not save a knob position
across power cycles. Large CV jumps across the pickup point can resume control
at the new value immediately.

The reset affects base Varispeed. Existing warble, Morph chord ratios and
Turing pitch choices keep their normal effects on the audible result.

### Card handling and SHIFT input

With no mounted card, the one-second SHIFT hold still arms settings-only
reload. Inserting a card during that armed hold gives reload priority and
cancels speed recall. Normal mounting/card-state changes during a hold also
cancel recall. **If you release without inserting a card**, an otherwise
eligible half-second hold recalls +1×. The one-second SHIFT arming light still
means settings reload is armed; it is not a new speed-reset indicator.

Firmware sees the SHIFT button and SHIFT gate input as the same signal. It
cannot distinguish a manual hold from a sufficiently long external gate, or
detect pulses hidden by a held button. **Use `vuni 0` for clocked/gated SHIFT
operation or when using a held SHIFT button to suppress incoming advances.**
With `vuni 1`, a SHIFT gate lasting half a second or more can recall +1× on
its falling edge. No separate external-clock cancellation is claimed.

## Noon mapping: `vctr 1`

With zero Varispeed CV, the calibrated midpoint of the knob is exact +1×.
With `vctr 1`, an explicit unity notch spans **48–52% of calibrated travel
in every mode**. With `vctr 0`, no noon notch or remapping is added, including
when `vuni 1` enables recall. Continuous slides retain their original response
until an intentional SHIFT recall holds unity for pickup.
The surrounding curve also centers the native or selected-scale unity step,
which can be wider than that explicit notch. The selected scale still controls
which pitches are available. Approaching a quantized step from opposite
sides retains the quantizer's normal hysteresis.

The curves are continuous and keep the original endpoints. The configured
curve stays the same during SHIFT + Varispeed's temporary free-pitch gesture;
the gesture does not move the underlying mapping. Soft pickup after a SHIFT
reset recognizes the common 48–52% center zone.

This works in every layout/range and scale. Physical pointer alignment depends
on the module's knob/calibration; the firmware reads the calibrated electrical
position, not the pointer itself.

| Layout | Full counterclockwise | Noon | Full clockwise |
|---|---:|---:|---:|
| Bidirectional, `vsop 0/1`, `vrng 0` | −2× | +1× | +2× |
| Bidirectional, `vsop 0/1`, `vrng 1` | −4× | +1× | +4× |
| Forward only, `vsop 2`, `vrng 0` | Stop | +1× | +4× |
| Forward only, `vsop 2`, `vrng 1` | Stop | +1× | +8× |

In bidirectional modes, the left half contains reverse speeds, stop, and
forward speeds below +1×. The precise stop position depends on the layout and
configured scale. The right half contains forward speeds above +1×. Both
endpoints and all available quantized pitches remain reachable; spacing changes.

This revision also fixes the separate stock lookup used with Gene Size near
fully counterclockwise. Previously that path missed the extended range: in
forward-only extended mode, a requested unity reset could produce approximately
0.677×. Both Gene Size paths now use the same range and unity calculations.
This range correction applies even when `vuni` and `vctr` are disabled.

The mapping applies to the combined knob/CV reading. **Nonzero CV can move
speed away from +1× even when the knob points at noon**, and CV sensitivity
changes with the mapping. Do not expect the original 1 V/oct response with
`vctr 1`. Enabling/disabling `vctr`, or changing the configured layout, range, or scale,
changes the mapping at the current control position and may change pitch
immediately. With `vctr 1`, scale changes can also change the continuous curve
used during temporary SHIFT free pitch.

## Hardware audition

See [the parameter table and test procedure](DEVELOPMENT_6_HARDWARE_TESTS.md)
for the priority hardware cases from your report.

1. First leave both options at 0 and check the controls you normally use.
2. Enable `vuni` only. From slow, fast and reverse playback, hold SHIFT for
   about 0.7 seconds, then release. Check forward original speed and no splice
   advance or playback restart. Short taps should still navigate normally.
3. Confirm speed remains held while approaching the original +1× position,
   and that crossing it restores normal control. Try SHIFT + Varispeed after
   waiting more than half a second: its existing function should still win.
4. Enable `vctr`. Check that a small turn either side of noon remains exactly
   +1× in both continuous and quantized operation. Check both endpoints in each layout/range
   you use. With `vqnt 1` and `octl 1`–`4`, confirm the unity step is centered and all expected pitches remain available.
   Verify stop is left of noon in bidirectional modes and fully left in
   forward-only modes. Repeat recall and pickup, now at noon.
5. Check a trusted-card settings reload with both enabled. Insertion should
   apply options and preserve playback without an extra speed-reset action.
   Changing `vctr` itself can change pitch as described above.
6. Audition recording/overdubbing and your usual dense/high-overlap patches.
   Emulator instruction counts do not measure real interrupt latency or prove
   glitch-free operation under every load.

To roll back, install `rollback-mg204c/mgmod.bin`. The old release ignores the
new option keys; remove them if desired. The released binary is preserved
byte-for-byte, not rebuilt with a different toolchain.

The first Development 6 build is preserved in `rollback-dev6-initial/` for A/B
comparison. Its complete source/package archive is also retained separately as
`morphagene-dev6-unity-initial.zip`.

Revision 2 is preserved in `rollback-dev6-rev2/`; its complete archive is
retained separately as `morphagene-dev6-unity-rev2.zip`.
