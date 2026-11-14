# Extended Varispeed build (experimental)

**Development 2:** forward-only 8x and scale lock (`vsop 2`, `vrng 1`), plus
independent density (`dens 1`, SHIFT + Gene Size). See [behavior, installation
and limitations](DEVELOPMENT_8X_DENSITY.md). Earlier upstream hardware status below does not
apply to these new changes.

This branch adds an optional bidirectional +/-4x range and maintenance fixes.
It is built from mg204 and tested in an emulator, **not yet tested on hardware**.
The normal range remains the default.

## Enable the new range

Edit the existing stock `vsop` line and add/update `vrng` in the SD card's
`options.txt`, preserving the first line and your other settings:

```text
vsop 0
vrng 1
octl 1
```

Power-cycle after changing the file. `vsop 1` also supports the new range.
Use `vrng 0` to restore the standard range without changing firmware.
`vsop 2` remains the stock forward-only mode (up to 4x), ignores `vrng`, and
still bypasses the SHIFT scale lock.

| Property | `vrng 0` | `vrng 1` |
|---|---|---|
| Maximum forward/reverse speed | +/-2x | +/-4x |
| Slowest nonzero continuous magnitude | about 1/8x | about 1/64x |
| Stop and +/-1x control positions | Stock | Unchanged |
| Octave-lock magnitudes | 1/4, 1/2, 1, 2 | 1/32, 1/16, 1/8, 1/4, 1/2, 1, 2, 4 |
| Chromatic lock positions including stop | 97 | 193 |
| SHIFT lock release distance | 231 ADC counts | 115 ADC counts |

This is a wider logarithmic mapping: the stock magnitude is squared and its
sign retained. It doubles the pitch interval for the same knob/CV movement.
It does **not** merely multiply every rate by two, so unity and stop do not
move. Existing CV sequences will span twice the pitch interval; in `vsop 1`,
re-adjust the attenuverter for V/oct tracking (approximately half the previous
CV depth). More range means less physical knob travel per semitone.

`octl 1` through `4` all work in the new bidirectional range, including custom
scales. Octaves remain exact. Other notes inherit the stock lookup table's
rounded coefficients; squaring them produces negligible tuning rounding.
The existing LED code is unchanged: no new dedicated 4x colour is promised.

## Installing and recovering

Use `build/mgmod.bin` for SD installation, since your module already has the
SD updater. Copy it to the card root, safely eject, then power on. The updater
retires it to `mgmod.ok` before programming, so that filename alone is not a
post-flash success check. Confirm that the module boots and that the new
`vrng` line is written to `options.txt`.

Keep the original `mg204.wav` and your previously working Full update. The
bootloader and calibration sectors are not modified. Audio installation is
still the recovery method if the application cannot boot; an unusable
application cannot run its SD updater. Do not distribute built images/WAVs,
because they include the manufacturer's firmware.

## First hardware check

Back up the card before recording tests. Start with playback, no CV, low Morph,
and no SHIFT effect. Test `vrng 0` first, then `vrng 1`:

1. Check forward/reverse, center stop, unity, and the +/-4x endpoints.
2. With a recorded steady pitch, check octave, fifth, chromatic and custom
   scale locks; confirm pickup on release and no unintended splice changes.
3. Exercise short Genes, high Morph, clocking, and splice/reel transitions.
4. Only then test tape overdubbing at 4x. Keep `mcap 3`; tape recording writes
   more sample positions per audio frame at high speed and can exceed the CPU
   budget with other expensive features. Playback and tape-head limits are
   both 4x; the existing tape limit has not been raised.
5. If glitches occur, temporarily enable `cpul 1`, capture the problematic
   patch, then disable it. Emulator instruction tests do not measure SDRAM
   stalls or establish a hardware CPU margin.

A full audio-session regression harness is still future work. The public
suite here covers the changed hooks, real stock rate lookup, and startup;
it does not reproduce the original author's private whole-session suite.

## Maintenance changes

- SD update files must contain at least the complete mg204 base image
  (0x28400 bytes). Their Thumb reset address must be past the vector area and
  inside the actual supplied image, not merely inside a flash sector.
  Host-side SD packaging applies the same rules. CRC checks and sector guards
  remain in place.
- Stock startup's BSS-clear endpoint is extended from 0x200243c8 to
  0x2002b800. All reserved mod RAM is cleared on every application reset,
  before hardware initialization/interrupts, including boots with no SD card.
  The stack region above that address is untouched. Cached tape code must
  therefore be recopied after an update/reset.
- The web editor preserves all integer `root` values from 0 to 100. Each file
  load starts from documented defaults, so missing options cannot inherit
  values from a previously loaded file. Stock/unknown lines and the first
  line are preserved. The new range is exposed in its settings editor.
- Single-digit mod settings reject malformed/multidigit values instead of
  silently accepting only their first digit.
- All MOD, SETTINGS and absolute-RAM claims are checked in the same physical
  address space. Out-of-arena and duplicate module claims are rejected.
- Absolute branch targets are typed in separate `.targets.S` objects. This
  works with both Arm GNU 14.2.rel1 and newer binutils 2.47. The compatibility
  change alone was checked against both original reference hashes and was
  byte-for-byte identical.
