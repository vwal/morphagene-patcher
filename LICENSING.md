# Licensing and provenance

The extended project's original additions are Copyright (c) 2026 vwal and use
the **Morphagene Extended Attribution - No Sale License 1.0** in [LICENSE](LICENSE).
This is a custom source-available license. It is not MIT or OSI open source.
The complete license controls; this page explains its intended application.

| Activity | Under this license |
|---|---|
| Make Noise incorporates our additions into official firmware/products, including commercial distribution | Expressly allowed by section 5, with notices retained |
| Use privately or professionally, study, modify | Allowed |
| Share copies or incorporate them in a free project | Allowed with copyright, attribution and license notices retained |
| Sell music, recordings, performances or lessons made using the firmware | Allowed; musical output does not inherit this license |
| Sell the patch, firmware, website or documentation | Prohibited without separate written permission |
| Put our additions in a paid bundle or paid software/hardware product | Prohibited, even if described as a free bonus |
| Charge to install, build, modify, update or host this firmware for others | Prohibited without separate written permission |
| Sell a module with our additions still installed | Prohibited for this community firmware; the Make Noise official-integration exception also allows resale of its official products |
| Use or redistribute the upstream work alone | Governed by upstream's MIT license, including its permission to sell |

## Make Noise exception

The manufacturer of the Morphagene is expressly permitted to integrate our work
into its official firmware and official products, including paid distribution,
without a license fee or asking again. Its contractors and authorized
distributors are covered solely for that official integration/distribution.
Official products carrying such an integration may be resold. Make Noise must
retain the applicable copyright/license notices, including upstream's MIT
notice. This exception does not generally authorize third parties to sell the
community release or extracted code. It does not imply Make Noise endorsement.

A voluntary donation cannot be required for access, delivery or a service.
Copyright remains with the respective holders. These terms do not revoke rights
already granted for earlier copies, claim others' independent work, or grant
rights in Make Noise's proprietary firmware.

## Upstream boundary

Briskcat's morphagene-mods at commit
`3c747c20fbbb0bd49ecf3d69a20bb813c4cc6baa` is the upstream baseline.
Its exact notice is retained in [LICENSES/Briskcat-MIT.txt](LICENSES/Briskcat-MIT.txt)
and reproduced in the main license. Existing MIT portions in modified files
remain MIT; the additional no-sale terms apply only to our own copyrightable
additions. Unchanged upstream files are not relicensed.

The splice play-through and reel bank adaptations also draw on Carlos de Paula’s
[fork at commit 3305b85](https://github.com/carlosedp/morphagene-mods/tree/3305b8566641ed24bb176c98e243831bbf1e21f8).
The fork carries the same MIT contributor notice preserved here.

Our changes relative to that baseline are recorded in the release's
`source.patch`; new and modified files are also identified in
`license-provenance.json`. That inventory is a provenance aid, not a claim that
every line in a modified file is ours or copyrightable. The site layout and PDF
format were adapted from vwal's Bitbox MkII project. Other people's notices must
be retained if their material is incorporated later.

The browser/audio encoder follows the format documented by Emilie Gillet's
[stm-audio-bootloader](https://github.com/pichenettes/stm-audio-bootloader).
That upstream attribution remains. The vendor's firmware and bootloader are
not relicensed by this project. A mod-code license is not permission to
redistribute generated files containing Make Noise's firmware.

## Distribution

Keep LICENSE and LICENSES/Briskcat-MIT.txt with source distributions. The website
ships their complete text in LICENSE.txt and Briskcat-MIT.txt. Each PDF embeds
the complete combined LICENSE.txt and includes a visible copyright/license
summary. Keep that attachment when redistributing PDFs; printed copies must
retain the notice and summary and be accompanied by the full terms as specified
in the license. Keep licenses/notices when distributing permitted derivatives.

Historical Development 3/4 packages are preserved unchanged. This notice
specifies this release's licensing and does not retroactively replace theirs.
The hardware binaries themselves have not changed as part of this licensing edit.
