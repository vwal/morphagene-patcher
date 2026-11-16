# Development 6 revision 3: hardware test cases

This is a private test build. The published mg204+c release is unchanged.

## Preparation

Install this package's `mgmod.bin`, reboot, and check that it becomes
`mgmod.ok`. Use the same familiar speech reel for comparison. Keep CV and clock
inputs unpatched, Morph fully counterclockwise, and set `mlop 0`, `tape 0`,
`dens 0`, `fxsl 0`, and `sldm 0` for these checks. These settings help keep other sound changes
out of the comparison; they are not requirements for using the new features.

Set `vuni 1` in every case. Keep the first line and unrelated settings in
`options.txt`. Replace existing keys rather than adding duplicates. The table
uses `vqnt 1` for normally quantized operation and `vqnt 0` for the original
normal control behavior (`vsop 1` retains its native semitone steps).

After applying each row, sweep Varispeed fully left and right before checking
noon. This releases any unity hold left from the previous test. Options may
be applied through the usual settings-only reload, or by rebooting.

## Priority cases

| Case | `vctr` | `vsop` | `vrng` | `vqnt` | `octl` | Purpose |
|---|---:|---:|---:|---:|---:|---|
| A | 1 | 2 | 1 | 1 | 2 | Forward extended range, octave/fifth steps |
| B | 1 | 2 | 0 | 1 | 2 | Forward standard range, octave/fifth steps |
| C | 1 | 1 | 1 | 1 | 2 | Bidirectional extended range, octave/fifth steps |
| D | 1 | 1 | 0 | 1 | 2 | Bidirectional standard range, octave/fifth steps |
| E | 1 | 2 | 1 | 0 | 1 | Forward extended range, normal continuous control |
| F | 1 | 2 | 0 | 0 | 1 | Forward standard range, normal continuous control |
| G | 1 | 0 | 1 | 0 | 2 | Bidirectional extended range, continuous control |
| H | 0 | 0 | 1 | 0 | 2 | Reset with original knob mapping; noon need not be unity |

For each case:

1. Start with **Gene Size fully counterclockwise**. In A–G, approach Varispeed
   noon slowly from each direction. Speech should return to original pitch
   and playback speed at noon. Check a small turn to either side: the explicit
   unity zone covers 48–52% of calibrated travel. Quantized steps can be wider,
   and their switching points retain normal hysteresis.
2. Move Varispeed well away from noon. Hold SHIFT alone for about **0.7 seconds**,
   then release. Playback should immediately return to exact forward +1×,
   without advancing a splice or restarting playback. Repeat from the other
   side and from reverse playback where available.
3. After reset, move slowly toward noon in A–G. Speed should stay at +1× until
   pickup, then follow the control after leaving the unity step. In H, pickup
   is near the original unity position, not noon. CV remains disconnected.
4. In H, sweep slowly through noon before using SHIFT recall: there should be
   **no added flat zone**. The original continuous response remains active.
5. Repeat the noon and reset checks with **Gene Size at noon**. Pitch/speed
   should agree with the fully counterclockwise test. The sound can become
   granular; compare the pitch of the speech within each Gene.

Cases A and E directly exercise the missed small-Gene-Size lookup path.
Cases B and F are important controls because that specific bug affected the
extended range only.

## Additional coverage

- Repeat C with `vsop 0`, and G with `vrng 0` and then `vsop 1`.
- Repeat A or C with `octl 1`, `octl 3`, and your usual `octl 4` custom scale.
  Noon and reset should remain +1×. `octl 0` should disable the optional scale
  snap without disabling noon or reset.
- Hold SHIFT for more than half a second while adjusting a knob. The existing
  knob gesture should win; releasing SHIFT should not recall unity.
- A short SHIFT tap should still navigate immediately. Finish by testing your
  usual playback, recording, and settings-only card reload workflow.

For any remaining mismatch, record the case letter, Gene Size position,
whether the pointer is at noon or SHIFT has just been released, and whether
both sound and the Varispeed unity indication agree. Physical pointer alignment
can differ slightly from the calibrated midpoint; this build does not measure
the pointer position independently.
