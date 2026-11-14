# mg204+c: trusted-card settings and switchable Morph Loop

This release, developed as Development 5, includes all Development 4 features, removes full-reel SHA-256
verification, and includes Morph Loop in Full with the new `mlop 0/1` option.
**Default: `mlop 0` (original Morph gaps).** Set `mlop 1` to loop seamlessly
at the bottom of Morph. It works at startup and through settings-only reload.
Development 3 and Development 4 are retained unchanged in separate folders.

Hardware testing confirmed armed card insertion and changed options applying
without an audible playback interruption. Exact latency and all performance
combinations remain unmeasured. Emulator tests
compare `mlop 0` against Development 4 Full, and `mlop 1` against its static
Morph Loop variant. These checks do not simulate physical card timing.

## Install

For an already modified unit with the SD updater, copy `mgmod.bin` to the card
root and power-cycle. Success renames it `mgmod.ok`. First installations and
recovery use the generated update WAV; follow [INSTALLING.md](INSTALLING.md).
The single Full build includes Morph Loop. The old full_morph_loop build name
is only a compatibility alias, with the same bytes and the same OFF default.

## Advanced trusted-card reload

**No content verification.** You are responsible for identical reel names,
WAV contents and splice sidecars across prepared cards. Change only options.txt.
Equal capacity or equal file size does not prove a match. A mismatched card
can become a save destination, causing wrong saves or overwritten audio.

1. Finish recording and wait for ordinary card writes to complete. Remove the
   mounted card and wait for its normal mounted indication to go out.
2. With the card physically absent and logically unmounted, hold SHIFT alone
   for one second, until its LED is steady. Arming is never available while
   mounted. Other buttons, knob gestures or moving knob CV can cancel arming.
3. Keep SHIFT held and insert the prepared matching card. Two short flashes
   mean success; three mean failure. Keep the card inserted through confirmation,
   then release SHIFT.
4. Success keeps the live reel, splice selection, audio buffers and playback
   position; playback continues advancing normally. The card remains mounted
   for recording and saving. Settings themselves can change the sound.
5. Failure leaves settings unchanged and the card unmounted. Remove it and
   release SHIFT before retrying or using normal mounting.

Do not record, edit splices or change reels while the card is disconnected or
reload is pending. Such activity invalidates the saved reconnect state.
After recording/saving/editing on one card, synchronize updated WAVs, splice
sidecars and reel names to all copies before the next settings-only swap.
Stale same-size copies are **not detected**. A normal mount is the right choice
when you want the inserted card's reel loaded, including an older/different reel.
It retains the usual playback interruption and update behavior.

The reload itself makes no disk writes and does not check mgmod.bin. It reads
options, opens the existing live reel read/write without creation/truncation,
checks its byte length and restores the old file cursor using the new card's
filesystem handle. Normal persistence and saving resume after success.
There is no audio hash, background verification or mounted preparation scan.
Mounting/options reads/seek still take time. The tested settings-reload workflow
continued without an audible playback interruption; card speed and CPU load vary.
Keep the card inserted until confirmation. Without a usable detect switch,
removal after the final file access is discovered by later normal card I/O,
not by a physical-presence check at the settings commit.

## Settings and feedback

See [OPTIONS.md](OPTIONS.md) and the printable manual. All 28 recognized keys
can be staged and committed together at the audio-block boundary. Missing keys
retain their current values. Invalid/duplicate recognized keys reject the whole
reload. The first state line is ignored. Unknown keys are preserved/ignored as
appropriate. options.txt must be plain text, at most 16 KiB; significant lines
must fit in 127 characters. Long // comments are streamed.

The hardware arming correction uses the unmounted state and a successful
main-loop mount instead of the card-detect GPIO, which stayed low without a
card in the diagnostic report. Hold and LED durations use the sample clock,
independent of audio block size. A normal insertion before arming still loads
the card normally. The corrected build passed the hardware retest: SHIFT arming and changed
options on insertion worked without affecting audio playback.

The one-second arm indication is steady SHIFT; pending reload blinks fast;
two short flashes mean success, three mean failure. There is no preparation
blink after normal loads or saves in this build.

## Startup and recalled density

With `dens 1`, `dstr 8` sets independent density to 8 Genes/sec (the default).
Accepts **0.1-128**, with at most one decimal; `dstr 0.1` means one Gene every
ten seconds. The SHIFT + Gene Size range is also 0.1-128; the lower half is
exponential from 0.1 to 8, and the upper half retains its 8-128 mapping.

At startup, the first density enable uses dstr. On a successful settings-only
reload, an explicit `dstr` recalls that card's rate at the audio-block boundary,
**even when its saved value is unchanged**. This replaces any temporary knob
adjustment. **Omit dstr** to preserve the live interval and its phase. The web
editor provides **Recall density on settings-only reload**: checked includes
dstr; unchecked omits it automatically. Imports match the checkbox to whether
the file includes dstr. With dstr omitted, startup defaults to 8/sec. Firmware
options rewrites add dstr back, so review the file after normal mounting or an
options save. The writer keeps the configured value, not temporary knob adjustments.
Normal mounting retains its existing reel-load behavior.

Reload leaves the current reel, splice, audio buffers and playing Genes alone.
Existing Genes finish naturally; the next unclocked Gene is scheduled one new
interval after commit (ten seconds for 0.1), subject to Play, nonzero Varispeed
and available voices. External clock keeps priority. With `dens 0`, the recalled
rate is held for later enabling; it does not turn independent density on.
Invalid/duplicate settings or a failed reconnect leave the live rate unchanged.
Missing/invalid dstr at startup retains the 8/sec default.

This is an independent rate, not a conversion of the Morph knob. Stock gapless
Morph (around 8:30-9 o'clock), or Morph Loop fully counterclockwise, schedules
successive Genes according to their duration; it is not inherently 8/sec.

## Hardware audition

- Set dstr to 0.1, 0.5, 2.5, 8 and 128 with dens enabled; verify startup rates,
  temporary knob changes, and the configured rate returning after power-up.
  Swap matching cards with different dstr values and confirm the recalled rate,
  continued reel/playback position and mounted recording/saving. Reinsert a card
  with the same dstr after a knob adjustment: it must recall. Omit dstr: it must
  preserve the rate. At 0.1, wait ten seconds for a new Gene.
- Compare mlop 0 and 1 at low Morph, then switch live; test both envelope modes,
  external clock, short/long Genes, reverse/8x playback and overdubbing.
- Reload unchanged settings during a recognizable long reel; confirm no restart,
  splice jump, recording change, pattern reset or unexpected gap.
- Swap prepared cards, confirm successful recording/saving on the inserted card,
  and synchronize copies before swapping again.
- Missing reel or different size should fail. Do not expect same-size content,
  splice or catalog differences to be detected; test mismatches only on backups.
- Hold SHIFT with a card mounted: it must never arm this feature.
- Check normal mounting, failure recovery, normal SHIFT gestures and release.

## Website and printable guides

[The published patcher](https://vwal.github.io/morphagene-patcher/)
and this repository’s `web/` contain the browser patcher and editor. It holds only mod
patch data, not vendor firmware. Letter/A4 manuals and quick cards are in the
project's `output/pdf/` and copied into the standalone website package.
The site uses the Bitbox MkII visual format without a release-history section.
Briskcat is credited for upstream mods, patcher and original Morph Loop edits.

## Build and tests

Use Arm GNU Toolchain 14.2.rel1. See [TESTING.md](TESTING.md). On this Mac, the
Unicorn tests use the existing Intel Python under Rosetta; native ARM Unicorn
was not usable. The build itself runs with the regular Python installation.

## License

Copyright (c) 2026 vwal for the extended project's original additions. Free use,
modification and sharing are allowed with notices retained. Selling our additions,
including paid bundles, products containing them, and paid firmware services,
is prohibited except for the explicit Make Noise official-firmware/product
exception or separate written permission. Make Noise may commercially integrate
and distribute our additions in its official offerings with notices retained. Paid music-making, recordings
and performances remain allowed. Upstream's MIT rights and notices are retained.
See [complete license](../LICENSE) and [scope/examples](../LICENSING.md).
