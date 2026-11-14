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
