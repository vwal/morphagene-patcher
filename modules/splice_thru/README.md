# Splice play-through

Set `thru 1` to use the last 5% of Organize for forward splice advance, or `thru 2` to follow the Varispeed playback direction.
Turning into this zone continues from the selected splice. A full-splice Gene advances when the next Gene takes its bounds. Short or externally clocked Genes advance at EOSG. Forward and reverse steps wrap at the ends of the reel. Short Genes can
therefore step the reel faster than full-splice playback. The other 95% of the
control still selects every splice.

Automatic advance pauses during recording, in the ordinary reel browser, and on
reels with fewer than two splices. It follows the Organize position accepted
by the playback engine, so adjusting Turing evolution with SHIFT leaves the
play-through state where it was. A recalled `splc` still follows `omod` and
uses the rescaled Organize positions for pickup. During bank selection the original performance keeps its current play-through setting. Setting `thru 0` (the
default) restores the original Organize range.

Adapted from [Carlos de Paula’s splice_thru](https://github.com/carlosedp/morphagene-mods/tree/7184795/modules/splice_thru).
The original mod and documentation are copyright © 2026 the morphagene-mods
contributors, under the [MIT license](../../LICENSES/Briskcat-MIT.txt).
The fork reports a hardware test of the original implementation. This port
changes the default and storage location, preserves pending manual navigation,
and integrates the c6 splice presets. See [the emulation tests](../../tests/test_splice_thru.py).
