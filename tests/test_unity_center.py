"""Centered effective unity cells, including native lookup plateaus and scales."""
import itertools
import os
import struct
import unittest

from tests.arm import Arm, bits, f32, value
from tests.audio import Audio
from tests.test_firmware_integration import images
from tests.test_quantized_default import setup, MOD, VQNT, SCALE, MASKS
from tests.test_settings_reload import call

U, VUNI, VCTR = 0x2002a620, 0x2002a618, 0x2002a619
ADC, GENE = 0x20021c74, 0x20021c7c
TARGET, CURRENT, CACHE = 0x200220e8, 0x200220e0, 0x20021df8
CONFIGS = tuple(itertools.product(range(3), range(2), range(2), range(5)))


def configure(a, config, centered=1, enabled=0):
    vsop, extended, quantized, scale = config
    setup(a, vsop, extended, scale)
    a.uc.mem_write(VQNT, bytes([quantized]))
    a.uc.mem_write(VUNI, bytes([enabled, centered]))


def mapped(a, x):
    return value(call(a, 'unity_map', bits(x)))


def rate(audio, adc, fresh=False):
    if fresh:
        audio.uc.mem_write(MOD+4, bytes(4))
        audio.a.put(CACHE, bits(-2))
    audio.a.put(ADC, adc)
    audio.blocks(1)
    return value(audio.a.get(TARGET))


def boundary(audio, predicate, minimum=0, maximum=4095):
    lo, hi = minimum, maximum+1
    while lo < hi:
        middle = (lo+hi)//2
        if predicate(rate(audio, middle, fresh=True)):
            hi = middle
        else:
            lo = middle+1
    return lo


class CenterMapping(unittest.TestCase):
    def test_vctr_off_is_identity_at_every_adc_even_with_vuni_enabled(self):
        a = Arm('shift_gestures', 'p1_session')
        for config in CONFIGS:
            configure(a, config, centered=0, enabled=1)
            for adc in range(4096):
                x = f32(adc/4095)
                self.assertEqual(mapped(a, x), x, (config, adc))
            self.assertEqual(a.get(U+44), 0)

    def test_curve_is_continuous_monotonic_and_unchanged_by_free_gesture(self):
        a = Arm('shift_gestures', 'p1_session')
        for config in CONFIGS:
            configure(a, config)
            previous = -1.
            for i in range(257):
                x = i/256
                a.uc.mem_write(MOD+4, bytes(4))
                y = mapped(a, x)
                self.assertGreaterEqual(y, previous, (config, x))
                previous = y
                # No discontinuous skip across the unity cell: free pitch can
                # still reach all intermediate rates on the configured curve.
                if 0 < x < 1:
                    self.assertLess(mapped(a, x+1e-6)-mapped(a, x-1e-6), 1e-4)
                a.uc.mem_write(MOD+4, bytes([1, 1, 2, 0]))
                self.assertEqual(mapped(a, x), y, (config, x, 'SHIFT'))
            self.assertEqual(mapped(a, 0), 0.)
            self.assertEqual(mapped(a, 1), 1.)
            self.assertEqual(mapped(a, .48), mapped(a, .52))

    def test_custom_scale_changes_invalidate_state_without_config_bit_aliases(self):
        a = Arm('shift_gestures', 'p1_session')
        seen = set()
        for vsop, extended, quantized in itertools.product(range(3), range(2), range(2)):
            for mask in (0, 2, 0x80, 0x800, 0xffe):
                configure(a, (vsop, extended, quantized, 4), enabled=1)
                a.uc.mem_write(SCALE, struct.pack('<H', mask))
                a.uc.mem_write(MOD+7, b'\1')
                mapped(a, .2)
                config = a.get(U+52)
                self.assertNotIn(config, seen)
                seen.add(config)
                self.assertEqual(a.uc.mem_read(MOD+7, 1), b'\0')
                # Bits outside the twelve pitch classes cannot collide with
                # configuration fields or change the effective scale.
                a.uc.mem_write(SCALE, struct.pack('<H', mask | 0xf000))
                mapped(a, .2)
                self.assertEqual(a.get(U+52), config)
        a.uc.mem_write(VUNI, bytes([2, 2]))
        self.assertEqual(mapped(a, .49), f32(.49))
        self.assertEqual(a.get(U+52), 0)


@unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'), 'set MGMOD_FIRMWARE for real audio')
class CenterAudio(unittest.TestCase):
    def test_static_cells_are_symmetric_in_both_audio_paths_all_options(self):
        for config in CONFIGS:
            for gene in (0, 420):
                audio = Audio(images()[1])
                configure(audio.a, config)
                audio.a.put(GENE, gene)
                lo = boundary(audio, lambda y: y >= 1)
                hi = boundary(audio, lambda y: y > 1)-1
                self.assertLessEqual(abs(lo+hi-4095), 1, (config, gene, lo, hi))
                self.assertLessEqual(lo, 1966)
                self.assertGreaterEqual(hi, 2129)
                self.assertEqual(rate(audio, 2048, fresh=True), 1.)
                self.assertEqual(value(audio.a.get(CURRENT)), 1.)
                vsop, extended, _, _ = config
                self.assertEqual(rate(audio, 0, fresh=True),
                                 0 if vsop == 2 else (-4 if extended else -2))
                self.assertEqual(rate(audio, 4095, fresh=True),
                                 (8 if extended else 4) if vsop == 2 else (4 if extended else 2))

    def test_directional_hysteresis_brackets_a_centered_cell(self):
        # A moving knob retains the current tone past a midpoint. Compare the
        # pair of directional sweeps, rather than falsely requiring each
        # history-dependent transition to occur at its no-history threshold.
        configs = [(vsop, extended, 1, scale)
                   for vsop, extended, scale in itertools.product(range(3), range(2), range(1, 5))]
        for config in configs:
            edges = []
            for direction in (1, -1):
                audio = Audio(images()[1])
                configure(audio.a, config)
                ones = []
                positions = range(0, 4096, 4) if direction == 1 else range(4092, -1, -4)
                for adc in positions:
                    if rate(audio, adc) == 1.:
                        ones.append(adc)
                self.assertTrue(ones, config)
                self.assertIn(2048, ones)
                edges.append((min(ones), max(ones)))
            up, down = edges
            self.assertGreaterEqual(up[0], down[0])
            self.assertGreaterEqual(up[1], down[1])
            # Hysteresis is measured in lookup units. The outside segments
            # have different slopes, so its physical margins need not be
            # mirror images; each sweep must bracket the symmetric static
            # cell in the correct direction and retain its central detent.
            audio = Audio(images()[1])
            configure(audio.a, config)
            lo = boundary(audio, lambda y: y >= 1)
            hi = boundary(audio, lambda y: y > 1)-1
            self.assertLessEqual(abs(lo+hi-4095), 1, (config, lo, hi))
            self.assertLessEqual(down[0], lo+4)
            self.assertGreaterEqual(up[0], lo-4)
            self.assertLessEqual(down[1], hi+4)
            self.assertGreaterEqual(up[1], hi-4)
            self.assertLessEqual(up[0], 1968)
            self.assertGreaterEqual(down[1], 2128)

    def test_nonideal_calibration_centers_on_calibrated_midpoint(self):
        for config in CONFIGS:
            audio = Audio(images()[1])
            configure(audio.a, config)
            offset, span = 91, 3900
            audio.a.put(0x20001294, offset)
            audio.a.put(0x20021410, bits(1/span))
            lo = boundary(audio, lambda y: y >= 1, offset, offset+span)
            hi = boundary(audio, lambda y: y > 1, offset, offset+span)-1
            self.assertLessEqual(abs(lo+hi-(2*offset+span)), 1, (config, lo, hi))
            for adc in (offset+span//2, 2048):
                self.assertEqual(rate(audio, adc, fresh=True), 1., (config, adc))

    def test_vctr_off_keeps_native_slides_through_noon(self):
        for vsop, extended, scale in itertools.product(range(3), range(2), range(5)):
            pair = [Audio(images()[1]), Audio(images()[1])]
            for enabled, audio in enumerate(pair):
                configure(audio.a, (vsop, extended, 0, scale), centered=0, enabled=enabled)
            targets = []
            for adc in range(1920, 2177, 8):
                result = [rate(audio, adc) for audio in pair]
                self.assertEqual(result[0], result[1], (vsop, extended, scale, adc))
                targets.append(result[0])
            self.assertGreater(len(set(targets)), 4, (vsop, extended, scale))

    def test_quantized_pitch_coverage_is_preserved(self):
        # Inspect the actual audio target for every other ADC count. The
        # narrowest configured scale cell is wider than two counts, so this
        # covers every selectable scale tone, including compressed reverse.
        for vsop, extended, scale in itertools.product(range(3), range(2), range(1, 5)):
            audio = Audio(images()[1])
            configure(audio.a, (vsop, extended, 1, scale))
            actual = {rate(audio, adc, fresh=True) for adc in range(0, 4096, 2)}
            actual.add(rate(audio, 4095, fresh=True))
            mask = MASKS[scale]
            if vsop == 2:
                expected = {0.}
                table = struct.unpack_from('<296f', images()[0], 0x25e10)
                for semitone in range(-48, (36 if extended else 24)+1):
                    if mask >> (semitone % 12) & 1:
                        expected.add(f32(2**(semitone/12)) if extended else table[196+4*semitone])
            else:
                # Native bidirectional tables round to float before the
                # expanded range squares their magnitude.
                table = struct.unpack_from('<200f', images()[0], 0x262b0)
                expected = {0.}
                for semitone in range(-72 if extended else -36, (24 if extended else 12)+1):
                    if mask >> (semitone % 12) & 1:
                        index = 144 + semitone*(2 if extended else 4)
                        magnitude = f32(table[index]**2) if extended else table[index]
                        expected.update((magnitude, -magnitude))
            self.assertEqual(actual, expected, (vsop, extended, scale))


if __name__ == '__main__':
    unittest.main()
