# Reel banks

The normal options reader selects the active directory. An omitted `bank` or
`bank 0` uses the stock root and reel controls. With `bank 1` through `bank 8`,
the root and `bank2` through `bank8` offer 32 slots each. Reels are named
`mg1.wav` through `mgw.wav`. Legacy `splice1.txt` through `splicew.txt` live
beside their matching WAVs. The updater and `options.txt` always use the root.

## Panel

Hold SPLICE, add REC, and hold both for about three seconds until REEL blinks.
Release both. Turn Organize to choose a bank, then a reel, then a splice.
At each step, hold SPLICE and tap REC to confirm. SHIFT cancels.
The picker shows the root and existing bank folders, including empty folders.
New Reel creates an empty reel when confirmed at the reel step.

The bank step keeps the performance audible. The default `audt 0` auditions the first
splice of a highlighted reel or the individual highlighted splice at forward +1×.
`audt 1` keeps the current performance audible throughout the picker.
Final confirmation follows `omod`. With 0 the current Gene finishes before the
switch. With 1 the switch starts immediately. A new reel always opens immediately.
A short initial chord opens the ordinary reel browser in the current bank.

## Storage details

Normal mount defers compaction until the options reader has selected a bank.
A sparse bank is compacted by moving each WAV and its optional legacy
splice file to the same slot. Normal mount tracks the saved file across a
renumber and uses reel 1 when the saved file is absent. An empty bank starts
at reel 1. A normal mount may create the folder selected by options.txt. The panel only offers folders already present. Embedded cue markers travel in the WAV.

The catalog checks the type and status of each entry before it moves files.
If a folder path is occupied by a regular file, there is an SD error, or a
legacy splice file has no matching WAV, a panel switch leaves the original
bank selected. An ordinary mount of such a bank stops before opening a reel.
To resolve an orphan on a computer, pair it with its WAV or move it outside
the bank. The two FAT directory renames for a WAV/marker pair are separate
operations. The orphan check prevents assigning markers to different audio
if power is lost between these writes.

SD operations run in the foreground. The button and audio interrupt handlers
only update selection, color, and request state. The 96 kHz counter is shared
with stock button timing. The bank gesture uses 288,000 ticks to the first
step. Internal storage occupies 0x20028f00 through 0x20028f2f. The reload
module maintains a separate opened-file identity at 0x20028ff0.

The panel gesture and color display are adapted from Carlos de Paula’s MIT
fork, commit `3305b8566641ed24bb176c98e243831bbf1e21f8`. Its original
copyright and license notice are in
[Briskcat-MIT.txt](../../LICENSES/Briskcat-MIT.txt).
