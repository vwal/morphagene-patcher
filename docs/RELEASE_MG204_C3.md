# Morphagene mg204+c3

This update fixes Varispeed changing to forward-only playback after a normal
card mount or power-up. The earlier firmware could read part of a long comment
on the `vrng` line as a second `vsop` setting. The c3 reader tracks line
boundaries for stock options, extended options and presets.

## Updating an existing card

1. Build the update from the official Make Noise `mg204.wav`. For a unit
   with the SD updater installed, put `mgmod.bin` at the card root and
   power-cycle. A successful update renames it to `mgmod.ok`. For a first
   installation, use `mg204+c3.wav` and follow the [audio procedure](INSTALLING.md).
2. Check the existing `vsop` line in `options.txt`. If an earlier release
   saved `2`, restore `vsop 0` for classic bidirectional or `vsop 1` for
   bidirectional 1 V/oct. Keep `vsop 2` if you want forward-only playback.
   Leave `vrng` set to your preferred range.
3. Save the file and mount the card normally. The module accepts the old
   generated comment and writes the shorter one at the next rewrite. The
   editor also replaces that comment on import and save. Both writers put
   `// firmware version 204+c3` below the module's numeric state line.

See the [settings reference](OPTIONS.md) for parameter ranges and
[performance controls](USING.md) for the panel gestures. The
[c2 guide](RELEASE_MG204_C2.md#optional-presets-and-pickup) details presets
and soft pickup. Changes by release are in the [version history](../CHANGELOG.md).
