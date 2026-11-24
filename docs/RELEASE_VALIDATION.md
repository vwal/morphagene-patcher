# mg204-c6 release validation

The owner confirmed the stock-timing refinement resolved the reported playback repeat on the module. The release application matched the tested Development 13 image byte for byte outside the fixed-size version comment. The module and both editors now write `// firmware version 204-c6`.

- Both CLI build names reproduced a 202,752-byte application with Arm GNU 14.2.rel1. SHA-256 is `ed03290645a49cecf1ad5f280ed8c17de152a48c039d2bfa1a5d03b3305d7617`.
- All 259 firmware tests passed locally with private reference images. Density checks covered all 1,281 supported values, the 1.0 Gene/sec startup default, explicit zero and omitted lines on settings-only reload, timing while Genes remain active and transitions between the shifted knob and card settings.
- Both firmware readers accepted a test card with all 45 settings explicitly zero. The 12 optional presets were active. The six positive-only settings assumed their documented minima.
- The browser generated the same SD update as the CLI. The browser and CLI update WAVs both decoded to the verified release application.
- The editor checks exercised 4,858 field/value cases and 8,056 wrapped chunks. Chrome verified importing, editing, saving and reopening a card file in the offline editor, reset confirmation, and building an SD update from the official WAV on the hosted editor test page.
- Both 13-page guides and single-page quick cards were rendered in Letter and A4. Each includes the full license.

---

# mg204+c5 release validation

The owner tested the dry-kill modes and stock-timing gesture on a Morphagene. A byte comparison against the tested Development 12 application found differences only in the options version comment and its padding. The module writer and both editors identify rewritten files with `// firmware version 204+c5`.

- Both CLI build names reproduced the 201,728-byte application with Arm GNU 14.2.rel1. SHA-256 is `f6ce230987d415901f07f18984cc879440323e3ad4290149caccae5bd6e0fc5a`.
- All 257 firmware tests passed locally with the stock firmware and private references. Coverage includes stereo recording sources, S.O.S. gain curves, whole-splice timing, settings reload and empty-reel card removal.
- The browser SD download matched the CLI file byte for byte. Both the browser and CLI update WAVs decoded to the release application.
- Editor tests covered 45 controls, 4,857 field/value cases and 10,615 wrapped chunks. Chrome exercised firmware and settings-file drops, reset confirmation, and settings import/export from a downloaded editor with network access disabled.
- The 13-page guide and single-page quick card were rendered and checked in US Letter and A4. Each PDF includes the complete license.

---

# mg204+c4 release validation

The owner tested the new recording modes on a Morphagene. The release image matches the tested revision byte for byte outside the fixed-size string that writes `// firmware version 204+c4` to `options.txt`.

- Arm GNU 14.2.rel1 produced the same application for both release aliases. The 201,728-byte raw image has SHA-256 `8ae6bf2aefe8061efdf06d5063d05fb058571d891be076b8b866d3e127e0bb31`.
- All 235 local firmware tests passed with the stock and private reference images available. Recording checks cover wet-only output, feedback endpoints, fixed-length overdubs and the contents and splice markers of saved extended takes.
- The browser patched the official mg204 WAV locally. The SD update matched the CLI build byte for byte and the decoded update WAV matched the release image.
- The options tests covered all 44 controls, 4,853 field/value pairs and 10,624 wrapped chunks. Both the module writer and editor produce the c4 header.
- Browser checks exercised both file drop areas, rejected invalid input and downloaded the standalone HTML without navigating away. The downloaded editor worked offline, including import, reset confirmation and export.
- The 13-page guides and one-page quick cards were rendered and reviewed in both US Letter and A4.

---

# mg204+c3 release validation

The 198,656-byte application built with Arm GNU 14.2.rel1 has SHA-256
`6fa86c9c4af564f75fa724780cfb504d95db8a562f3d88071ea84344552bceed`.

- On November 21, 2026, the owner confirmed that `vsop 1` survived two
  consecutive power cycles on a Morphagene and that the module wrote
  `// firmware version 204+c3` in `options.txt`.
- All 208 automated firmware tests passed with the stock and private reference
  images available. The browser editor and firmware download checks also passed.
- On normal mounts and live reloads, ARM emulation checked 4,863 inputs
  across all 42 settings, including all 2,048 custom scales, 1,280 density
  values and 1,318 preset selections. Chord ratios were sampled across signs,
  precision and range endpoints. The memory checks verified each setting's
  destination and write width.
- On module-written files, checks covered 97 per-setting printed widths.
  The longest setting and its value occupied 28 bytes before the comment.
  The only generated comment that changed another setting on c2 was on
  `vrng`. On c3, all six Varispeed layout/range combinations persisted
  across repeated full-file reads and rewrites, including files generated by c2.
- The editor generated 4,811 field/value pairs and checked 10,926 wrapped
  chunks. Both writers produced `// firmware version 204+c3`. The browser
  and CLI SD updates matched byte for byte, and both WAVs decoded to the
  application hash above.
- The Letter and A4 references and quick cards were rendered and reviewed.

See the [test guide](TESTING.md#mg204c3-settings-regression-checks) and
[c3 update instructions](RELEASE_MG204_C3.md).

---

# mg204+c2 release validation

Release preparation: 2026-11-15. Public name: `mg204+c2`.
The owner confirmed the unity and all-control preset features on hardware.
The released raw image differs from the tested Development 8 image by exactly
one byte: the options header comment changes `204+c1` to `204+c2`.

Raw application: 198,656 bytes; SHA-256
`5dd01fb87b3f514a61663aa0f9dc393ca3a986836e874a0b7c38c5f3f6527488`.

## Confirmed results

- Complete local firmware suite: **201 tests, no skips**, 238.548 seconds.
  Includes real audio playback/recording comparisons, unity mapping and reset,
  all twelve optional recalls, parser/writer behavior and trusted-card reload.
- Both `full` and `full_morph_loop` reproduce the same release hash with
  Arm GNU 14.2.rel1. The two CLI names are compatibility aliases.
- Browser option tests pass, including 1,310 percentage/splice values, all
  density values, Turing steps, checkbox omission, round trips and c2 headers.
- The official WAV decodes correctly; browser-generated raw and SD data match
  the local build. Its `mg204+c2.wav` download decodes back to that same image.
  Corrupted input is rejected.
- Browser UI checked: grouped controls, numeric selection, independent recall
  omission, c2 snippet header and collapsed version history. Narrow layout fits
  without horizontal overflow.
- Letter/A4 manuals (11 pages each) and quick cards (1 page each) rendered and
  visually reviewed. Each embeds the complete combined license as `LICENSE.txt`.
- Existing experimental packages remain untouched. Original public mg204+c
  remains in Git history. Vendor-containing firmware stays outside Git.

## Limits

Hardware reports confirm the tested behavior; they do not establish worst-case
latency, every CV/clock/dense-patch combination or power-loss behavior. Trusted
matching cards remain the user's responsibility. See the
[release guide](RELEASE_MG204_C2.md) for controls, pickup and card requirements.

---

# mg204+c release validation

Release preparation: 2026-11-14. Public name: `mg204+c`.
The firmware bytes are identical to the corrected Development 5 build tested
on the owner's Morphagene. Publication changes branding, documentation,
browser download naming and deployment configuration.

Raw application: 188,416 bytes; SHA-256
`5c150c24540517af487693c53f5b4e7fa9b9dc5c33147ba6ab801ded60912335`.

## Confirmed results

- Owner's hardware retest: SHIFT arming works; inserting the card while armed
  and still holding SHIFT applies changed options without affecting audio
  playback. This is a listening report, not a measured worst-case latency.
- Full local instruction-level/host suite: 89 tests, no skips, 74.302 seconds.
  Includes real stock TIM2/audio and FAT16/FAT32 execution, sample-clock arming,
  settings transactions, file reconnection, write/sync, density and Morph Loop.
- Both `full` and `full_morph_loop` reproduce the same reference hash with
  Arm GNU 14.2.rel1. They are compatibility names for mg204+c.
- Browser tests: official WAV decoding, raw and SD output equivalence, audio
  encoding, actual download handlers and `mg204+c.wav` filename, corrupt-input
  rejection, options round trips, all 1,280 density values and recall checkbox.
- Letter/A4 manuals (8 pages each) and quick cards (1 page each) rendered and
  visually reviewed. Each embeds the full combined license as `LICENSE.txt`.
- Original upstream MIT notice retained verbatim. Public files contain source
  and patch data; generated vendor-containing firmware is excluded.

## Limits

Exact SD latency, every card model, clocked Morph Loop transitions and heavy
recording/overdub/CPU-load combinations are not established by these results.
Prepared matching cards remain the user's responsibility: no reel-content,
splice-sidecar or reel-name inventory comparison is performed.
Physical power-loss and peripheral behavior are outside the emulator model.
