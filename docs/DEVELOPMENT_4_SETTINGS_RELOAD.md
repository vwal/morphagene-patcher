> Historical Development 4 guide. For this build use [Development 5](DEVELOPMENT_5_LIVE_OPTIONS.md); it does not verify card contents.

# Development 4: settings-only reload

Development 4 includes Development 3's quantized Varispeed, forward 8x range
and independent density, and adds a dedicated `options.txt` reload that keeps
the returned card mounted for recording and saving. This is Development 4,
revision 3; compatible copies of a card can now carry different options.
The original Development 3 package is retained separately and unchanged.

**Status: emulator-tested; hardware audition required.** Tests execute the
compiled ARM code and mg204's actual audio and button routines. SD electrical
timing, physical LED appearance and uninterrupted audio on hardware remain
to be checked. Do the first audition outside a performance.

## Install

Copy this package's `mgmod.bin` to the card root and power-cycle normally.
The existing updater installs it and renames it `mgmod.ok`. No new option is
needed to enable reload. Existing settings and calibration are retained.
For audio installation/recovery, use `mg204-full.wav` as described in
[INSTALLING.md](INSTALLING.md). These locally built files contain your copy
of the vendor firmware; share the patcher/source, not the firmware images.

## Reload while the module stays powered

1. Stop recording and wait for SD writing and reel verification to finish
   (SHIFT returns to its normal steady mounted indication). Verification also
   runs after a normal reel load or save; let it finish before removing the card.
2. Remove the card and wait for the normal mounted-card SHIFT light to go out.
   Edit and save `options.txt` on your computer, preserving its first line,
   then eject the card from the computer. You may instead use a prepared copy
   with different options. Keep playback running, but do not record,
   edit splices or change reels while the card is out or the reload is pending.
3. With the card still out, hold **SHIFT alone**. Leave the knobs still.
   After about **one second**, the SHIFT LED becomes steady: reload is armed.
   **Arming is unavailable while a card is mounted**, even if SHIFT is held
   longer than one second. Wait for the old card to be recognized as removed.
4. Continue holding SHIFT and insert the card. Wait for **two short flashes**
   (success) or **three short flashes** (failure), then release SHIFT.
5. After success, the SHIFT LED returns to its normal mounted-card indication.
   **Leave the card inserted.** Recording and saving can resume immediately;
   another removal/insertion is not needed.

A fast repeating blink means the module is preparing or checking a reel
fingerprint, or the reload is waiting/reading. Verification reads the complete
current reel and may take time on large files; audio is intended to keep playing,
but physical SD/audio timing still needs hardware testing. Recording or
card edits while disconnected invalidate the reconnect snapshot; the operation
then fails without applying settings. This also covers recording started by CV
during the read or just before commit. `options.txt` is limited to 16 KiB.

An ordinary card insertion/SHIFT tap still uses the normal mount behavior.
Inserting before the armed LED appears also uses normal mounting. Holding
SHIFT at power-up does not select this feature. It becomes available after
the normal settings initialization has run at least once after power-up.

SHIFT knob gestures and other button combinations cancel arming. The reload
claims SHIFT only when the card is inserted after the full hold. Its release
does not advance the splice. As with the existing SHIFT gestures, moving CV
can look like a knob turn, so pause knob CV when arming if it prevents the
steady LED. Subsequent SHIFT gestures work normally with the card mounted.
On failure the card stays unmounted; normal mounting is blocked until physical
removal, preventing an accidental reel load or firmware update.

## What is preserved

The reload does not load, copy, save, stop or restart a reel. It leaves the reel
number, sample memory, splice markers, selected splice, playback position,
active voices and recorded material alone. Playback keeps advancing normally.
Existing Turing seeds, warble phase and density adjustment are not reset.
Changing a setting can of course change the sound or how those features run;
for example changing the Varispeed range changes pitch at the same knob value.

`options.txt` is read without changing it; its first line (saved reel/gain
metadata) is ignored. The existing live reel file is reopened for read/write
access without creating, truncating or loading it, and its file position is
restored. The reload itself makes no disk writes and never checks `mgmod.bin`.
Once mounted, normal firmware saving, settings persistence and enabled CPU
logging resume. Normal mounting still has the stock reel-copy behavior and
firmware updater.

The reconnect compares a SHA-256 content fingerprint of the complete current
reel WAV, its `splice*.txt` sidecar (including whether it is absent), and the
list of occupied reel names. Card hardware ID, capacity, directory placement
and FAT allocation do not have to match. The live reel selection and data
offset must remain unchanged. A missing, modified or outdated current reel,
changed splice sidecar or different reel list fails without a normal-mount
fallback. Other reels' audio is not scanned until they become the current reel.

## Using two or more options cards

Copy the reel WAVs and splice files to each card, preserving their names and
contents, then edit only `options.txt` to make each card's configuration.
An ordinary file copy is sufficient; sector cloning and equal capacities are
not required. Each card must use a filesystem supported by Morphagene.

Use the armed SHIFT insertion to change options while keeping the live reel
and playback position. After two success flashes, leave that card mounted;
normal recording, saving and reel controls work on it.

Saving affects **only the inserted card**. After recording or editing splices,
copy the updated reel and splice sidecar to the other cards before using them
for settings reloads of that reel. Keep added/deleted reel names synchronized
too. Old copies are rejected instead of silently becoming a save destination.

To load a different or older reel/card, use **ordinary mounting without the
armed gesture**. That retains the normal interruption, reel loading/copying
and saved-reel selection behavior. After a failed settings reload, remove the
card and release SHIFT before taking this normal path.

Validated values are staged separately, then committed together at the start
of an audio block. Input gain's codec command runs afterward in the main loop.
A changed pitch configuration invalidates an obsolete scale lock, but does
not reposition playback. Reloading unchanged settings preserves audio output
and playback state in the Development 3 regression comparisons.

## File rules

All nine documented stock mode settings, `mcr1`–`mcr3`, and all fourteen mod
settings are supported. The value ranges are the same as the settings editor.
Chord ratios accept signed ordinary decimals with up to eight fractional
digits, magnitude 0.0625–16; scientific notation is not accepted. `scal 0`
clears a custom mask; other scale entries are semitones 1–11 separated by
commas or whitespace. `//` comments and LF/CRLF files are supported.

Unlike startup, missing keys retain the current value. Unknown keys are ignored
for compatibility. A missing file, a mount/read/close/reconnect error, a duplicate or
invalid recognized key, a line longer than 127 significant characters, embedded
NUL/control characters or a file larger than 16 KiB rejects the whole reload.
At least one recognized setting and the first header line are required.
Long comments are streamed and do not count against the line limit.
Reel fingerprinting is bounded to 128 MiB per WAV and 16 KiB per splice sidecar.

On failure, active settings and playback remain unchanged and the card stays
unmounted. Remove the card, fix the file, and repeat the gesture. If recording
or edits happened while disconnected, use the ordinary mounting workflow to
resolve that reel state before attempting another settings reload.

## Hardware audition

- Play a long, recognizable reel. Change only `octl` or `vqnt` and reload.
  Confirm the pitch behavior changes without restarting the audio or selecting
  a different splice. Confirm SHIFT release does not advance a splice.
- Reload an unchanged file with quantization, density, mono auto, Turing and
  warble in use. Check for audio gaps, changed patterns or parameter resets.
- Try an invalid value and then a missing file: three flashes, no change.
- Alternate between two or more copied cards with different options, then
  record and save with the selected card still inserted.
  Confirm the intended reel contains the recording and its earlier material
  and splice markers remain intact. Repeat the reload and save cycle.
- Test a stale copy, a same-size WAV edit, changed splice file and missing reel: three flashes,
  no settings/playback change, card unmounted and no writes to that card.
- With CPU logging off and no pending saves, compare card contents before/after
  reload alone. No reload-induced writes or update installation should occur.
  Normal recording, settings persistence and logging may write after success.
- After a reload, try normal SHIFT navigation and knob gestures with the card
  still mounted. Confirm two flashes finish in the normal mounted LED state.
- Exercise recording started by CV after arming, and short Genes/high Morph/
  high density during the SD read. Hardware timing is not established by the
  emulator's successful functional tests.
- Hold SHIFT well past one second with a mounted card: normal controls only,
  no reload arming. Test ordinary mounting to switch to an incompatible reel.
- Time initial fingerprint preparation and alternate-card verification using
  your longest reel; confirm recording requests interrupt preparation cleanly.

## Rollback and build

The package's `rollback-dev3/mgmod.bin` reinstalls Development 3 through the
normal power-on update process. Its original folder is also untouched.

Build with **Arm GNU 14.2.rel1**, including its GCC (the new module has a
freestanding C parser and ARM assembly hooks):

```sh
python3 -m mgmod build full --firmware /path/to/mg204.wav --output build/dev4
```

See [TESTING.md](TESTING.md) for the complete validation commands and
[the module notes](../modules/settings_reload/README.md) for hook/state details.
