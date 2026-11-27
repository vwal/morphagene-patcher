"""Configurable detents through the c6 mapper and both real mg204 audio paths."""
import itertools
import os
import unittest

from tests.arm import Arm, value
from tests.audio import Audio
from tests.test_firmware_integration import images
from tests.test_quantized_default import MOD
from tests.test_unity_center import CURRENT, GENE, U, configure, mapped, rate

NTCH = 0x2002a61d
REVERSE = 52.5 / 400


def configure_notches(arm, config, centered, notches, recall=0):
    configure(arm, config, centered, recall)
    arm.uc.mem_write(NTCH, bytes([notches + 1]))


def reverse_center(config, centered, forward):
    # Locate the original -1x point on the selected curve before widening it.
    arm = Arm('shift_gestures', 'p1_session')
    configure_notches(arm, config, centered, forward)
    low, high = 0., .5
    for _ in range(20):
        mid = (low+high) / 2
        if mapped(arm, mid) < REVERSE:
            low = mid
        else:
            high = mid
    return (low+high) / 2


@unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'), 'requires official mg204')
class NotchAudio(unittest.TestCase):
    def test_signed_detents_and_endpoints_on_both_audio_paths(self):
        configs = itertools.product(range(3), range(2), ((0, 0), (1, 1), (1, 4)), range(2))
        for vsop, extended, (quantized, scale), centered in configs:
            config = vsop, extended, quantized, scale
            native = 212.5 / (376 if extended else 328) if vsop == 2 else 344.5/400
            forward = .5 if centered else native
            for notches in range(4):
                points = [(forward, 1., 1)]
                if vsop < 2:
                    points.append((reverse_center(config, centered, notches & 1), -1., 2))
                audio = Audio(images()[1])
                configure_notches(audio.a, config, centered, notches)
                for gene in (0, 420):
                    audio.a.put(GENE, gene)
                    for position, target, bit in points:
                        for offset in (0., -.019, .019):
                            got = rate(audio, round((position+offset)*4095), fresh=True)
                            self.assertEqual(audio.a.get(U+60), bool(notches & bit),
                                             (config, centered, notches, gene, position, offset))
                            if notches & bit:
                                self.assertEqual(got, target)
                                self.assertEqual(value(audio.a.get(CURRENT)), target)
                            elif offset == 0.:
                                self.assertEqual(got, target)
                            elif not quantized:
                                self.assertNotEqual(got, target)
                    first = 0. if vsop == 2 else (-4. if extended else -2.)
                    last = (8. if extended else 4.) if vsop == 2 else (4. if extended else 2.)
                    self.assertEqual(rate(audio, 0, fresh=True), first)
                    self.assertEqual(rate(audio, 4095, fresh=True), last)

    def test_enlarging_both_detents_preserves_scale_notes_and_stop(self):
        for vsop, extended, scale in itertools.product((0, 1, 2), (0, 1), (1, 2, 3, 4)):
            config = vsop, extended, 1, scale
            audio = Audio(images()[1])
            note_sets = []
            for notches in (0, 3):
                configure_notches(audio.a, config, 1, notches)
                notes = {rate(audio, adc, fresh=True) for adc in range(0, 4096, 3)}
                self.assertTrue({0., 1.}.issubset(notes), config)
                if vsop < 2:
                    self.assertIn(-1., notes, config)
                else:
                    self.assertGreaterEqual(min(notes), 0., config)
                note_sets.append(notes)
            self.assertEqual(*note_sets, config)

    def test_forward_only_ignores_reverse_bit_throughout_travel(self):
        for centered, extended in itertools.product((0, 1), repeat=2):
            config = 2, extended, 0, 0
            for first in (0, 1):
                audio = Audio(images()[1])
                sweeps = []
                for notches in (first, first | 2):
                    configure_notches(audio.a, config, centered, notches)
                    sweeps.append([rate(audio, adc, fresh=True) for adc in range(0, 4096, 9)])
                self.assertEqual(*sweeps, (centered, extended, first))

    def test_both_directions_land_on_exact_rates_during_shift_free_pitch(self):
        for vsop, extended, centered in itertools.product((0, 1), repeat=3):
            config = vsop, extended, 1, 4
            audio = Audio(images()[1])
            configure_notches(audio.a, config, centered, 3)
            forward = .5 if centered else 344.5/400
            reverse = reverse_center(config, centered, 1)
            for owner in (0, 2, 0):
                # The reverse and forward detents must agree on entry from
                # either side, including temporary free pitch while shifted.
                audio.uc.mem_write(MOD+4, bytes([bool(owner), bool(owner), owner, 0]))
                for position, target in ((reverse, -1.), (forward, 1.)):
                    for side in (-1, 1):
                        rate(audio, round((position + side*.035)*4095))
                        self.assertEqual(rate(audio, round((position + side*.018)*4095)), target)
                        self.assertEqual(value(audio.a.get(CURRENT)), target)

    def test_recall_with_forward_notch_disabled_uses_narrow_pickup(self):
        for centered, notches in itertools.product((0, 1), (0, 2)):
            audio = Audio(images()[1])
            configure_notches(audio.a, (0, 1, 0, 0), centered, notches, recall=1)
            center = .5 if centered else 344.5/400
            rate(audio, 100)
            audio.a.put(U+40, 1)
            self.assertEqual(rate(audio, 100), 1.)
            self.assertEqual(rate(audio, round((center-.012)*4095)), 1.)
            self.assertEqual(audio.a.get(U+44), 1)
            self.assertEqual(rate(audio, round(center*4095)), 1.)
            self.assertEqual(audio.a.get(U+44), 0)
            self.assertEqual(audio.a.get(U+60), 0)
            self.assertGreater(rate(audio, 4095), 1.)
