# Development 7: optional prepared control and splice recall

Private experimental build based on **Development 6 revision 3**, which passed
your hardware tests. That package and the published mg204+c release are
preserved. This build adds four optional `options.txt` keys and corresponding
checkboxes in the private options editor. All four recalls are **off when their
keys are absent**. The Development 6 unity options remain available and default
to 0; see [unity recall and noon mapping](DEVELOPMENT_6_UNITY.md).

## Install and prepare

Copy this package's `mgmod.bin` to the card root, reboot, and confirm it becomes
`mgmod.ok`. The package also contains `mg204-full.wav` for the usual audio
installation/recovery procedure; see [installation](INSTALLING.md).

Use [the private patcher/options editor](../web/index.html) to load your current
`options.txt`. Enable only the recalls you want and save the resulting file.
The same editor can create a Development 7 WAV/SD update from your official
firmware WAV. Its linked PDF manuals describe the released version; this guide
describes the experimental additions.

Alternatively, keep the file's first line and other options, and add/edit:

```text
mpos 25 //Morph virtual knob position, percent
gpos 50 //Gene Size virtual knob position, percent
spos 30 //Slide virtual knob position, percent
splc 1  //First splice in the loaded reel
```

| Key | Accepted values | Meaning |
|---|---|---|
| `mpos` | Integer 0–100 | Morph position, counterclockwise to clockwise |
| `gpos` | Integer 0–100 | Gene Size position, counterclockwise to clockwise |
| `spos` | Integer 0–100 | Slide position, counterclockwise to clockwise |
| `splc` | Integer 1–300, within the loaded reel | Selected splice, counting from 1 |

These percentages represent the control's **virtual electrical position**.
They are not milliseconds, Gene-length percentages, or absolute sample-frame
positions. Normal control response, smoothing, Morph Loop and other options
continue to apply. Physical pointer alignment and endpoint tolerances may
differ slightly between modules.

## Startup, reload, and persistence

At startup or normal card mounting, explicit recalls are applied after the
normal reel load has finished. An invalid splice number is ignored; valid
control-position recalls still apply. A failed options read is not applied.
If the module is temporarily busy recording or handling an edit, publication
waits until it is idle. Without these keys, startup follows the normal controls.

On settings-only reload, all values are checked before any options change.
An invalid, duplicate, or out-of-range preset value rejects that entire reload,
including other settings in the file. A `splc` value must exist in the currently
loaded reel. An explicitly included value recalls again even if its configured
number has not changed since the last card; omitted keys preserve the live
control/selection and its pickup state.

The editor provides an independent recall checkbox for each parameter.
Unchecking removes that key while retaining its numeric choice in the editor.
Unlike `dstr`'s existing automatic writing behavior, these four keys **remain
omitted on subsequent options saves** when omitted from the latest successful
file. Normal saves retain configured preset numbers, not later knob movements.
No new gesture captures the live controls into the file.

The first line still selects/remembers the normal reel and gain state. The
new `splc` key selects within that reel; it does not load another reel.
Prepared replacement cards still need matching audio files and splice layouts,
as required by trusted-card reload.

## Control pickup and existing gestures

After a recall, the virtual position is held until the combined knob/CV reading
comes near or crosses it. Once picked up, the control behaves normally. If the
physical control is already near the recalled position, it can take over on the
following audio block. Ordinary position pickup uses about 1.2% of the ADC range;
the 0/100% endpoints allow about 3.1% so real knobs can reach pickup despite
endpoint tolerances. A crossing can also release pickup after a large jump.

The hardware sums knob and CV before the firmware reads them. **CV can trigger
pickup**. While a recalled position is held, it overrides that combined input;
CV is not separately added on top of the preset. After pickup, normal CV
response resumes. This is the same hardware limitation discussed for unity
recall.

SHIFT + Morph, SHIFT + Gene Size, and SHIFT + Slide keep their current
secondary functions. Their physical readings still adjust the secondary effect,
while the primary control holds its effective value. Releasing SHIFT preserves
the normal pickup behavior. Using these gestures should not make the primary
sound jump back to the physical knob position.

`splc` uses the existing splice request, so **`omod 0` waits for the normal
Gene/splice boundary and `omod 1` switches immediately**. Requesting another
splice intentionally changes playback location. The switch has the same playback behavior as ordinary splice selection and
does not load another reel. Organize holds until it reaches/crosses the selected splice's
region. SHIFT navigation continues from the selected splice and updates the
Organize pickup target. Manual reel changes or splice-count changes release
this reel-specific hold; normal reel selection remains available.

## Priority hardware tests

Keep CV/clock inputs unpatched for the first pass. Use a familiar reel with at
least two splices for splice tests. Begin with `sldm 0`, `fxsl 0`, and no active
recording. Other settings can stay as you normally use them.

| Test | File changes | Expected result |
|---|---|---|
| 1. Baseline | Omit all four new keys | Normal controls and the tested Development 6 features work as before |
| 2. Startup positions | `mpos 25`, `gpos 50`, `spos 30`; omit `splc` | Reboot with the knobs elsewhere: the three configured positions are recalled |
| 3. Individual pickup | Keep test 2's file | Move one knob toward/crossing its recalled position; only that control resumes normal tracking |
| 4. Endpoint pickup | Try `gpos 0`, `spos 0`, then `spos 100` | Exact virtual endpoint is recalled, and the physical knob can subsequently pick it up |
| 5. Repeat live recall | Change the knobs after pickup, then reload the same file | Included positions recall again; no reel reload is introduced |
| 6. Partial recall | Include only `spos 70` among the four new keys | Slide changes; Morph, Gene Size and splice selection retain their live state |
| 7. Boundary splice | `splc 2`, `omod 0` | Selection changes at the ordinary boundary, without loading a reel |
| 8. Immediate splice | `splc 1`, `omod 1` | Selection changes immediately; short SHIFT advances normally afterward |
| 9. Organize pickup | After test 7 or 8, turn Organize | Selection remains held until pickup; normal navigation then resumes |
| 10. Editor/save omission | Uncheck all four recalls, reload, then let the module save options | These keys stay absent; later reloads preserve the live values |
| 11. Gesture compatibility | Enable your usual density/effect settings and use SHIFT knob gestures after recall | Secondary controls work without an unintended primary-control jump |

For a rejection check, use `splc` greater than the current reel's count in a
settings-only reload together with a recognizable option change. Neither the
splice nor the other option should change. Restore a valid file afterward.

After the isolated checks, audition your normal CV, density, recording and
high-overlap patches. Emulator validation cannot establish physical knob
alignment or audio headroom on your module.

## Rollback

Install `rollback-dev6-r3/mgmod.bin` from the package to return to the exact
tested Development 6 revision 3 binary. The full original Development 6 folder
is unchanged. Remove the new keys if desired; earlier versions ignore them.
