# 204+c1 — Development 8: complete optional preset recall

Private experimental build based on the hardware-tested Development 7. The
previous builds and published mg204+c release are preserved. **204+c1** is the
name of the upcoming release; this Development 8 package is for testing and
has not been published.

All preset recalls are optional and **off when their keys are absent**. This
build retains the tested unity recall/noon mapping, Morph/Gene Size/Slide/splice
recall, and earlier extended features. It adds effect, feedback, Turing, primary
S.O.S. and Varispeed recalls. The bit-reduction-style effect is specifically
**sample-rate reduction (SRR)**; there is no separate bit-depth control.

## Install and edit

Copy this package's `mgmod.bin` to the card root, reboot, and confirm it becomes
`mgmod.ok`. Use `mg204-full.wav` for the usual first audio install or recovery;
see [installation](INSTALLING.md). The package includes the exact tested Dev7
firmware in `rollback-dev7/`.

Open [the private patcher/options editor](../web/index.html), load your current
`options.txt`, and check only the recalls you want. The private patcher also
builds a WAV/SD update from your original official WAV. Linked PDF manuals still
describe the published mg204+c release; this guide covers the experimental build.

Both editor and module-generated options identify the upcoming version with:

```text
// firmware version 204+c1
```

The numeric first line remains intact because it stores reel/gain metadata.
Do not replace that first line with the version comment. Older version comments
are replaced by the editor. Stock mg204 does not implement these extended keys.

## Available presets

| Key | Values | Recalled control |
|---|---|---|
| `mpos` | 0–100 | Main Morph position |
| `gpos` | 0–100 | Main Gene Size position |
| `spos` | 0–100 | Main Slide position |
| `splc` | 1–300 | Selected splice, counting from 1 |
| `srrp` | 0–100 | SHIFT + Morph SRR position |
| `jitp` | 0–100 | SHIFT + Slide jitter / Turing spread position |
| `wrbp` | 0–100 | SHIFT + Morph warble position |
| `fbkp` | 0–100 | SHIFT + S.O.S. overdub/classic TLA feedback position |
| `evop` | 0–100 | SHIFT + Organize Turing evolution position |
| `trst` | 1, 2, 3, 4, 6, 8, 12, 16 | Turing Genes per step |
| `sosp` | 0–100 | Main S.O.S. mix position |
| `vpos` | 0–100 | Calibrated Varispeed position before range/layout/noon mapping |

All values are integers. Percentages mean **virtual knob positions**, from
counterclockwise to clockwise, following the existing control curves. They are
not linear effect strengths, milliseconds, splice-relative time or speed ratios.
For example, `vpos 50` means the calibrated midpoint. With `vctr 1`, this gives
forward +1×; without `vctr`, its speed depends on `vsop`/`vrng` and quantization.
The actual knob pointer and calibrated midpoint may differ slightly.

`dstr` already recalls independent density (0.1–128 Genes/sec, default 8), and
`ingn` already sets input gain. There are no additional dialable controls left
without a preset mechanism: main Organize is covered by `splc` selection.
Buttons, external gates and clock timing are not position presets.

### Effect and mode interactions

- `fxsl 0` bypasses both effects while retaining their prepared amounts.
  `fxsl 1` selects SRR and `fxsl 2` selects warble. `srrp` and `wrbp` store separate amounts; the
  effects do not run simultaneously. Once either recall is used, switching
  `fxsl` restores that effect's last live amount. Editing one leaves the other
  bank unchanged. A recall can prepare the inactive effect for a later switch.
- `fbkp` activates the same feedback control as a SHIFT + S.O.S. edit. `tape`
  selects tape overdubbing or classic TLA behavior. `fbkp 0` means zero feedback;
  omitting the key preserves the existing state. `sosp` separately sets the
  primary listening/recording mix and does not select a feedback mode.
- `sldm 1` enables Turing mode. `jitp` supplies its spread, `evop` evolution, and
  `trst` Genes per step. Values may be prepared while Turing is disabled.
  Independent density (`dens 1`) and external-clock priority remain unchanged;
  SHIFT + Gene Size adjusts density while `dens 1` is enabled.
- An explicit `vpos` recall replaces an active +1× hold. A later `vuni` SHIFT
  hold/release resets to +1× and releases the old `vpos` hold; normal unity pickup
  then follows the actual knob/CV input. Omitted `vpos` leaves the live state.

## Startup, live reload and saving

At startup and normal card mounting, recalls apply after the reel load completes,
waiting until idle if recording or editing is active. A failed read does not
publish a preset. On settings-only reload, explicit values apply again even when
identical to the previous file; missing keys preserve live values and pickup.
Malformed, duplicate or numerically out-of-range preset values reject the live
reload before any settings change.

**A `splc` value above the loaded reel's splice count selects the last splice.**
The configured number stays unchanged in the file, so `splc 300` can mean “last
splice” on any supported reel. For example, `splc 8` selects splice 3 on a
three-splice reel, and splice 8 after a subsequent options read/normal card mount loads a reel
with ten splices. A manual reel-selection gesture alone does not reapply it.
An empty reel cannot select a splice; no invalid marker is accessed. This changes
Dev7's behavior, which rejected an oversized live-reload selection.

Splice recall uses normal `omod` timing: `omod 0` waits for the normal boundary;
`omod 1` switches immediately. Selecting another splice intentionally changes
playback location. Omitting `splc` preserves selection. The same reel remains
loaded during settings-only reload; prepared replacement cards must still have
matching audio files and splice layouts. Remove the idle card, hold SHIFT alone
for one second, and insert the matching card while continuing to hold SHIFT.

Normal saves retain **configured preset numbers, not later knob movements**.
Keys omitted from the latest successful file remain omitted in later saves.
Unchecking an editor recall removes its key. No gesture captures live settings
into the file. Density retains its previously documented save behavior.

## Pickup and existing controls

A primary preset holds until the combined knob/CV input comes near or crosses
the recalled position. Ordinary pickup is about 1.2% of the range, with about
3.1% at endpoints so real knobs can reach 0/100%. Secondary effects hold until
their own SHIFT + knob gesture reaches/crosses the recalled position. Turning
the primary knob alone does not change a recalled secondary effect. `trst`
picks up at/crossing the selected rate zone, then uses normal hysteresis.

SHIFT gestures continue to hold the primary control at its effective value.
After release, normal primary pickup resumes. Organize picks up at the selected
splice; short SHIFT navigation continues normally. Manual reel/count changes
release the splice-specific hold.

Knob and CV are combined by the hardware. **CV can trigger pickup**; it is not
added separately while the preset is held. No-knob-movement SHIFT holds and
existing button functions retain their previous meaning.

## Hardware test cases

Start with inputs unpatched and a familiar reel. Preserve a copy of your working
options file. Test one row at a time before combining settings.

| Test | Settings / action | Expected result |
|---|---|---|
| Baseline | Omit all twelve preset keys | Previous tested control behavior |
| SRR | `fxsl 1`, `srrp 50` | Same SRR as SHIFT + Morph near noon; main Morph stays independent |
| Warble bank | Add `wrbp 25`, switch `fxsl 2`, then `fxsl 1` by live reload | Separate amounts restored; only selected effect runs |
| Effect pickup | With a preset active, move its knob normally, then with SHIFT toward preset | Primary movement does not change effect; SHIFT edit takes over at pickup |
| Jitter | `sldm 0`, `jitp 40` | Prepared jitter; SHIFT + Slide pickup works without primary Slide jump |
| Turing | `sldm 1`, `dens 0`, `jitp 60`, `evop 0`, `trst 8` | Repeating spread with eight Genes per step; evolution/rate gestures pick up |
| Density priority | Above plus `dens 1`, `dstr 8` | SHIFT + Gene Size changes density; Turing rate recall remains available when applicable |
| Feedback | Try `fbkp 70` separately with `tape 0` and `tape 1` | Same feedback/retention as manual SHIFT + S.O.S. at 70%; check recorded result |
| Main mix | `sosp 65`, with and without `fbkp` | Main mix recalls independently; ordinary pickup and SHIFT feedback preserve it |
| Varispeed | `vpos 50`, `vctr 1`; test `vsop 0` and `2`, `vrng 0` and `1`, `vqnt 0` and `1` | +1× at recalled midpoint; knob/CV pickup resumes control |
| Noncentered pitch | `vctr 0`, `vpos 70`; test quantized and free modes | Uses the existing 70% speed mapping, with no added noon notch |
| Unity priority | `vuni 1`, `vpos 25`; recall, then SHIFT alone ≥0.5 s and release | Exact +1× replaces preset; physical/CV unity pickup works; explicit vpos reload wins again |
| Last splice | On a short reel: `splc 300`, test `omod 0` and `1` | Last splice selected with normal timing; saved value remains 300 |
| Partial/repeated reload | Pick up controls, reload same file, then a file omitting selected recalls | Included recalls reapply; omitted live states are preserved |
| Rewritten file | Download in editor, then let module save options | Version comment says 204+c1; first numeric line retained; omitted keys stay absent |

After isolated checks, test your normal recording, CV and dense patches.
Automated emulation checks control behavior and signal equivalence, but does
not establish the hardware CPU headroom of every effect/overdub combination.

## Rollback

Install `rollback-dev7/mgmod.bin` to return to the exact tested Dev7 build.
Remove Dev8 keys if desired; earlier firmware ignores them. The original
Development 7 folder and the published release remain unchanged.
