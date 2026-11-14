# Reproducible builds and public tests

Reference toolchain: **Arm GNU 14.2.rel1**. Official archive URLs and SHA-256
pins for macOS ARM/Intel and Linux ARM/Intel are in `tools/toolchain.json`.
Nothing is installed globally:

```bash
python3 tools/install_toolchain.py
export PATH="$(python3 tools/install_toolchain.py --print-bin):$PATH"
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-test.txt
python -m unittest discover -v
node tests/test_web.mjs
```

The settings-reload module also uses the reference toolchain's **GCC**, for the freestanding
settings parser. Use the complete pinned 14.2.rel1 toolchain on PATH; a different
GCC version can produce different firmware hashes even with the same binutils.

Use Python 3.11+ for this test workflow and Node 22. The builder itself remains
compatible with Python 3.9+. If the toolchain archive is already downloaded,
pass `--archive /path/to/archive.tar.xz`; the installer still checks its hash.
Unicorn is pinned to 2.1.4. No proprietary firmware is bundled with tests.

On the reviewed Apple Silicon environment, Unicorn's native ARM64 wheel
terminated with SIGILL when mapping memory. The x86_64 wheel under Rosetta
with `python3-intel64` ran the suite successfully. Use a separate Intel venv
for that workaround, or run the public tests on Linux. This is an emulator
host limitation, not a reason to modify a firmware binary.

## Integration with your own firmware

```bash
export MGMOD_FIRMWARE=/absolute/path/to/mg204.wav
python -m unittest discover -v
python -m mgmod check --firmware "$MGMOD_FIRMWARE"
```

Without that variable, only the stock-firmware integration cases are skipped.
With it, the suite verifies the official firmware fingerprint, runs its actual
startup and Varispeed lookup instructions with the patches applied, and checks
that the web bundle and local builds match. Do not commit the firmware or test
intermediates. The Pages workflow validates the options editor and deploys only `web/`; it
does not run firmware-dependent tests or upload generated firmware.
The separate test workflow runs vendor-independent host and assembled ARM tests;
firmware-dependent cases are skipped there.

Coverage includes:

- all 4096 calibrated control positions across standard/extended ranges and
  octave, fifth, chromatic and one custom scale, executed as assembled Thumb;
- held-lock hysteresis, pickup, register/stack preservation, forward-only bypass;
- all 4096 positions in the real mg204 lookup for each `vsop` and range;
- SD staging, CRC/length/vector rejection, rename failure and no-file startup;
- the real startup loop with dirty retained RAM, stopped before hardware init;
- mod parser/writer, all 101 `root` settings, web round-trips/default isolation;
- physical RAM collisions and host-side update packaging checks.

The flasher peripheral model, hardware timing, analogue
CV behavior and actual flash power-loss behavior are not covered by this new
suite. These tests complement, and do not replace, a hardware audition.

## Updating source and reference bundles

After an intentional firmware change, first run the tests. Build each remix,
record the printed image SHA-256 in its `remixes/*.py` manifest, and regenerate:

```bash
python -m mgmod webpatch --firmware "$MGMOD_FIRMWARE"
python -m mgmod check --firmware "$MGMOD_FIRMWARE"
python -m unittest discover -v
```

`web/remixes.js` includes only the project's changed/appended bytes. Never
commit `build/`. A successful `check` verifies reproducibility, not hardware
safety. New/changed firmware modules remain labelled **emulated** until their
behavior is tested on Morphagene.

Absolute stock code targets belong in each module's companion `.targets.S`
file, declared `.global` and `.thumb_set`. The main source declares their
`%function` type without assigning the address. The builder links the separate
symbol object so GAS cannot fold typed branches into untyped absolute
relocations rejected by newer linkers. Keep data addresses as `.equ` values.

## Development 2 validation

`tests/test_dev8.py` adds exhaustive forward 8x scale/lookup checks, density
settings and pickup, the real tape writer through 8x, and whole-audio tests.
`tests/audio.py` executes stock initialization and the audio routine; only the
large initial SDRAM fill loops are skipped (test buffers are supplied directly).
No hardware peripheral or wall-clock timing is simulated.

Set `MGMOD_PREVIOUS` to the decoded previous 4x image to additionally compare
its audio against the new build with density disabled. This optional historical
image is never bundled in public tests. Run `python3 tools/generate_tables.py`
to reproduce the forward and density lookup sources.

## Development 3 validation

`tests/test_quantized_default.py` sweeps all 4096 input positions with `vqnt 1`
in every scale, `vsop` and range combination, checks free-pitch gesture/release,
navigation, glide and `octl 0`, and executes the real audio path in every range.
Set `MGMOD_DEV2` to the previous Development 2 raw image for optional
byte-identical audio regression checks with `vqnt 0`, including density playback.

## Development 5 validation

Tests execute real compiled Thumb code, stock TIM2/audio and FatFs with synthetic
FAT16/FAT32 cards. Coverage includes 28 settings, atomic commit, mounted arming
rejection, recording/live-state races and media-read failures, fresh FIL reconnection and successful stock
recording writes/sync. Stale same-size cards are intentionally trusted. Idle
snapshot preparation must not read the card. Morph Loop tests compare both
switch values against the previous fixed-table variants at low/high Morph,
both envelopes, plus parser/writer/defaults and on/off toggling.

Use the existing pinned Arm GNU 14.2.rel1 toolchain and a working Unicorn build.
Set MGMOD_FIRMWARE to the official WAV/raw image; MGMOD_PREVIOUS to extended-4x
rollback; MGMOD_DEV2, MGMOD_DEV3 and MGMOD_DEV4 to those raw full images.
Run `python -m unittest discover -v`, `node tests/test_web.mjs`,
`node tests/test_web_firmware.mjs`, and
`python -m mgmod check --firmware "$MGMOD_FIRMWARE"`.
For `test_web_firmware.mjs`, set `MGMOD_FIRMWARE` to the official decoded raw
image and `MGMOD_WAV` to the original official WAV. First run
`python -m mgmod build full --firmware "$MGMOD_WAV" --output build/dev5`.
The browser test exercises the actual WAV/SD download handlers and checks the
public `mg204+c.wav` name; the required SD updater name remains `mgmod.bin`.
Regenerate `web/remixes.js` with `python -m mgmod webpatch` after firmware changes.
Source data and tests do not distribute vendor firmware. Hardware testing
confirmed SHIFT arming and changed options applying on insertion without an
audible playback interruption. Exact SD latency, clocked transitions and heavy
recording/overdub combinations still need separate measurement or audition.

Startup-density coverage executes all 1,280 supported dstr tenths in both
parsers, interval rounding, malformed/out-of-range rejection, duplicate and
missing reload values, writer round trips, explicit rate recall, preserved
rate/phase when omitted, dirty startup RAM, real audio birth spacing including
the full ten-second minimum, audio-boundary voice/playhead continuity, and
FAT16/FAT32 card recall followed by recording writes. Browser tests cover the same values.

Hardware-report regressions reproduce GPIOH13 stuck low while CARD_OK=0,
check the exact 48000-sample arming threshold independently of block count,
exercise the real SHIFT serial LED output and post-mount interception, preserve
the normal early/cancelled mount route, pace rejected-card probes, rearm after
actual FAT16/FAT32 mount failure, and reject actual media-read loss with the
detect pin still low. Post-read removal at the commit boundary is not detectable
from that pin; the normal subsequent card-I/O failure path remains responsible.
