"""Compare S.O.S. curves with separate, known incoming and existing signals."""
import os
import struct
import unittest

from tests import test_dry_fade as fade, test_dryk_extension as extension
from tests import test_preset_chunks as normal, test_settings_reload as live
from tests.arm import Arm
from tests.audio import Audio
from tests.test_dry_monitor import LEFT, PLANE_BYTES, RIGHT, SOS, set_mode
from tests.test_dry_performance import input_stereo, recording, start_take
from tests.test_firmware_integration import images
from tests.test_preset_options import printf_capture

SOSC = 0x2002a61c
# Positions on the active travel including its endpoint tolerance.
ADC = (185, 2048, 3911)
# Each pair is (incoming, existing); values are linear amplitude.
CURVES = (
    ((1, 0), (1, 1), (0, 1)),
    ((1, 0), (1, .5), (1, 1)),
    ((1, 1), (.5, 1), (0, 1)),
)


class CurveOptions(unittest.TestCase):
    def test_normal_mount_writer_and_missing_line(self):
        a = Arm('options_keys', 'opt_parse')
        calls = printf_capture(a)
        for source, expected in (('sosc 2', 2), ('dryk 3', 0), ('sosc 1', 1),
                                 ('sosc 0', 0), ('sosc 01', 0), ('sosc 3', 0)):
            a.uc.mem_write(SOSC-1, b'\x01\x02\xa5')
            normal.begin(a)
            normal.feed(a, '1 0 0\n'+source+'\r\n')
            self.assertEqual(bytes(a.uc.mem_read(SOSC-1, 3)), bytes([1, expected, 165]))
            calls.clear()
            a.run('opt_write', [0x08024566])
            emitted = [fmt % v for fmt, v in calls if fmt.startswith('sosc ')]
            self.assertEqual(len(emitted), 1)
            self.assertLessEqual(len(emitted[0].encode('ascii')), 63)
            normal.begin(a)
            normal.feed(a, '1 0 0\n'+emitted[0])
            self.assertEqual(a.uc.mem_read(SOSC, 1), bytes([expected]))

    def test_settings_only_reload_commits_mode_or_omitted_default_atomically(self):
        for source, expected, accepted in (
                ('sosc 0', 0, True), ('sosc 1', 1, True), ('sosc 2', 2, True),
                ('', 0, True), ('sosc 3', 2, False), ('sosc 01', 2, False),
                ('sosc 0\nsosc 1', 2, False), ('sosc 1\nmono 7', 2, False)):
            a = live.arm()
            a.uc.mem_write(SOSC-2, b'\0\1\2\xa5')
            live.stage(a, f'1 0 0\ndryk 3\n{source}\n'.encode())
            self.assertEqual(bytes(a.uc.mem_read(SOSC-2, 4)), bytes([0, 1, 2, 165]))
            self.assertEqual(a.get(live.PENDING), int(accepted), source)
            live.call(a, 'reload_commit')
            self.assertEqual(bytes(a.uc.mem_read(SOSC-2, 4)),
                             bytes([3 if accepted else 0, 1, expected, 165]), source)

    def test_successive_cards_with_only_a_curve_or_preset(self):
        a = live.arm()
        for line, expected in (('sosc 2', 2), ('sosp 50', 0), ('sosc 1', 1)):
            a.put(live.CARD, 0)
            live.stage(a, f'1 0 0\n{line}\n'.encode())
            self.assertEqual(a.get(live.PENDING), 1, line)
            live.call(a, 'reload_commit')
            self.assertEqual(a.uc.mem_read(SOSC, 1), bytes([expected]), line)


@unittest.skipUnless(os.getenv('MGMOD_FIRMWARE'), 'requires official mg204 firmware')
class CurveAudio(unittest.TestCase):
    def test_empty_first_take_through_native_rec_start_and_stop(self):
        fixture = extension.ReplacementTake()
        for mode in range(4):
            for curve in range(3):
                for adc in ADC:
                    with self.subTest(mode=mode, curve=curve, adc=adc):
                        audio = fixture.session(mode=mode, dlen=0, adc=adc)
                        audio.uc.mem_write(SOSC, bytes([curve]))
                        for address in (extension.COUNT, extension.MARKERS,
                                        extension.MARKERS+4, extension.MARKERS+8,
                                        extension.HEAD, 0x20022114):
                            audio.a.put(address, 0)
                        fixture.start(audio, 1)
                        audio.blocks(12)
                        fixture.stop(audio)
                        end = audio.a.get(extension.MARKERS+4)
                        self.assertEqual(audio.a.get(extension.COUNT), 1)
                        self.assertGreaterEqual(end, 96)
                        for plane, level in ((LEFT, -3600), (RIGHT, 4800)):
                            self.assertEqual(fixture.frames(audio, plane, 0, end), (level,) * end)

    def test_tape_writes_both_independent_contributions(self):
        fixture = fade.FadeRecording()
        # The next block flushes the write cache. Frame 1 is on the first tape pass.
        for curve, settings in enumerate(CURVES):
            for adc, (incoming, existing) in zip(ADC, settings):
                audio = fixture.session(adc, tape=0, input_only=1, existing=True)
                audio.uc.mem_write(SOSC, bytes([curve]))
                fixture.input(audio, 1600, 0)
                audio.blocks(2)
                left, right = [struct.unpack('<h', audio.uc.mem_read(p+2, 2))[0]
                               for p in (LEFT, RIGHT)]
                self.assertAlmostEqual(left, 2400*incoming + 1200*existing, delta=1)
                self.assertAlmostEqual(right, -2400*existing, delta=1)

    def test_protected_full_existing_curve_keeps_tape_length_at_ccw(self):
        fixture = extension.ReplacementTake()
        audio = fixture.session(mode=2, dlen=1, adc=0)
        audio.uc.mem_write(SOSC, b'\2')
        audio.blocks(1)
        fixture.start(audio, 2)
        self.assertEqual(audio.a.get(extension.LATCH), 0)
        audio.blocks(42)
        fixture.stop(audio)
        self.assertEqual(audio.a.get(extension.MARKERS+8), 512)

    def test_monitor_and_linear_recording_against_isolated_source_stems(self):
        def run(mode, curve, adc):
            audio = Audio(images()[1])
            set_mode(audio, mode)
            audio.uc.mem_write(SOSC, bytes([curve]))
            audio.a.put(SOS, adc)
            # Audio fixture supplies a sine on the left. Fresh input is only on the right.
            audio.uc.mem_write(RIGHT, bytes(PLANE_BYTES))
            input_stereo(audio, 0, 1600)
            audio.blocks(70)
            start = start_take(audio, append=True)
            out = struct.unpack('<384h', audio.blocks(24))
            take = tuple(struct.unpack('<192h', p) for p in recording(audio, start, 192))
            return (out[::2], out[1::2]), take

        ref_out, ref_take = run(0, 0, 2048)
        for stereo in (ref_out, ref_take):
            self.assertTrue(all(max(map(abs, channel)) > 100 for channel in stereo))
        wet_ref = run(3, 0, 2048)[0]
        for mode in (0, 1, 3):
            for curve, settings in enumerate(CURVES):
                for adc, (incoming, existing) in zip(ADC, settings):
                    with self.subTest(mode=mode, curve=curve, adc=adc):
                        out, take = run(mode, curve, adc)
                        for idx, gain in enumerate((existing, incoming)):
                            self.assertLessEqual(max(abs(x-y*gain) for x, y in
                                                     zip(take[idx], ref_take[idx])), 2)
                            if mode == 0:
                                self.assertLessEqual(max(abs(x-y*gain) for x, y in
                                                         zip(out[idx], ref_out[idx])), 2)
                            else:
                                self.assertEqual(out[idx], wet_ref[idx])
