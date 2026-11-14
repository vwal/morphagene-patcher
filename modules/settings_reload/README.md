# Trusted-card settings reload (Development 5)

Full-reel hashing was removed by explicit product choice: matching cards are
now the user's responsibility. This code never compares audio, splice sidecars
or occupied reel names. It retains basic file length and live-state checks.

Hooks remain at 0x0802312a / 0x08023136 (mount entry/result), 0x08022f7e (common main head),
0x0802484e (TIM2 buttons), 0x0802493e (SHIFT LED), 0x08027518 (audio entry),
0x08031124 (common FatFs write core), and 0x08032260 (open/truncate).
The following mono_in hook starts at 0x0802751c. Original prologues and
integer/FP registers/flags are preserved by the assembly wrappers.

TIM2 arms only with CARD_OK=0. Hold SHIFT alone 48000 sample-clock ticks
(one second), then insert while held. Ownership is claimed after a successful
stock mount, before the updater/stop/reel-load path. Knob gestures or button
combinations cancel arming. Mounted holds and normal loads cannot arm.

The November 14 hardware report found GPIOH13 held low even while unmounted:
raw GPIO cannot detect absence on that unit. All physical-detect gates have
therefore been removed from this module. Failed mount attempts leave an armed
hold waiting; a successful mount is the insertion signal. The tested hardware
advanced 16 samples per audio block, so all hold/LED/probe timing now uses the
48 kHz sample counter at 0x20021c88 rather than assuming 6000 blocks/second.
The first normal initialization must already have established settings magic.

At the main loop head, capture a clean, idle live FIL (main SP+844, FATFS
SP+1948). This snapshot involves no disk I/O. Writes to the live reel or its
companion splice FIL (live-552, main SP+292) invalidate it, including formatted
writes and truncate/open. Recording/card activity while disconnected invalidates
it too. After ordinary writes have synced, the next idle pass captures a new
snapshot without scanning the reel. Unrelated options/log writes do not dirty it.

On an owned insertion, reuse the successful mount, parse options into staging, open the
existing reel with mode 3 (read/write, no create), compare file size, and seek to
the old fptr. Reopening refreshes filesystem ID, cluster chain and directory
pointers even for a different card/layout. Seeking can read FAT/one data sector;
it does not read or hash the complete file. Only after success and a final
quiet/live-state check does the next audio block publish all options
and CARD_OK=1. No filesystem or codec work happens with interrupts disabled.
The input gain codec update is deferred to the existing main-loop hook.

State ABI at 0x2002A820: phase/start/owned/pending/result/finish/absent at +0..24;
seen mask +28; original 26 option values +32..135; valid +136; reel +140;
reels +144; data_start +148; size +152; cluster +156; position +160;
CID +164..179; directory sector +180; directory offset +184; reserved former
digest +188..219; snapshot_ready +220; live FIL pointer +224; reserved scanning
+228 (always zero); mlop staged value +232, dstr +236, mount_ready +240 (1 owned fresh mount,
2 normal load in progress). Preserving the earlier offsets avoids
changing the assembly ABI. Scratch FIL starts 0x2002A920, 512-byte buffer at
0x2002AB80, line buffer 0x2002AD80, read count 0x2002AE00.

28 recognized keys are validated, duplicate keys reject, missing keys retain
live values. First line is ignored; 16 KiB total and 127 significant characters
per line limits apply. Values commit under a short interrupt mask. The existing
audio hook also applies switchable Morph tables; see ../morph_loop/README.md.

Success: two SHIFT flashes, mounted. Failure: three, unmounted. Main probes
availability at most every 4800 samples while parked and unmounted; it permits
a fresh attempt after a failed mount and release of the owned hold. This keeps
a readable rejected card from falling through to a normal reel load. An invalid
or temporarily unreadable medium is indistinguishable from absence. Removal
after the final successful file I/O cannot be checked at the audio boundary;
the normal card-access failure path handles subsequent media loss. Normal mount keeps its stock interruption and
updater behavior. No content verification or full-reel preparation LED exists.
Hardware retesting confirmed SHIFT arming and changed options applying on card
insertion without an audible playback interruption. Exact SD latency and every
performance combination remain unmeasured. Tests execute real Thumb audio/TIM2 and FatFs on
synthetic FAT16/FAT32 sector devices; they intentionally accept stale same-size
copies and prove basic failure handling and recording write/sync after reconnect.
