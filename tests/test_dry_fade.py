"""Exercise the primary feedback curve and actual stereo recording on mg204."""
import os
import struct
import unittest

from tests.arm import Arm, UC_ARM_REG_R1, bits, value
from tests.audio import Audio
from tests.test_firmware_integration import images
from tests.test_preset_tape_effects import arm, feedback_amount, publish, target


MOD = 0x2002a000
DRYK = 0x2002a61a
BLOCK_MODE = MOD + 234
FADE_GAIN = MOD + 236
SOS = 0x20021c68
LEFT, RIGHT = 0xd0000000, 0xd1000000


def control_block(a, adc):
    a.put(SOS, adc)
    a.uc.reg_write(UC_ARM_REG_R1, SOS)
    a.run('p7_sos_block', [0x080276ca])
    return value(a.get(FADE_GAIN))


class FadeControl(unittest.TestCase):
    def test_first_timer_initialization_preserves_inflight_audio_routing(self):
        a = Arm('shift_gestures', 'p1_session')
        a.uc.mem_write(MOD + 232, bytes([2, 2, 2, 0]))
        a.put(FADE_GAIN, bits(.75))
        a.run('p1_session', [0x0802486e])
        self.assertEqual(a.get(MOD), 0x53484654)
        self.assertEqual(a.uc.mem_read(MOD + 232, 3), b'\2\2\2')
        self.assertEqual(a.get(FADE_GAIN), bits(.75))

    def test_all_adc_values_follow_sos_curve_without_touching_feedback_bank(self):
        a = arm()
        a.uc.mem_write(DRYK, b'\2')
        for adc in range(4096):
            self.assertEqual(control_block(a, adc), feedback_amount(adc))
        self.assertEqual(a.uc.mem_read(MOD + 16, 1), b'\0')
        self.assertEqual(a.get(MOD + 20), 0)
        for mode in (1, 0, 3, 255):
            a.uc.mem_write(DRYK, bytes([mode]))
            control_block(a, 1111)
            self.assertEqual(a.uc.mem_read(BLOCK_MODE, 1), bytes([int(mode == 1)]))

    def test_primary_preset_pickup_and_legacy_bank_remain_independent(self):
        a = arm()
        a.uc.mem_write(DRYK, b'\2')
        publish(a, {10: 75, 7: 20})  # sosp, fbkp
        self.assertEqual(control_block(a, 0), feedback_amount(target(75)))
        self.assertEqual(control_block(a, 1200), feedback_amount(target(75)))
        self.assertEqual(control_block(a, 3600), feedback_amount(3600))
        for mode in (1, 0, 2):
            a.uc.mem_write(DRYK, bytes([mode]))
            control_block(a, 3250)
            self.assertEqual(value(a.get(MOD + 20)), feedback_amount(target(20)))
        self.assertEqual(value(a.get(FADE_GAIN)), feedback_amount(3250))

    def test_density_voice_cap_applies_with_tape_disabled_and_no_shift_edit(self):
        a = Arm('gene_shape', 'density_prepare')
        a.uc.mem_write(0x2002a607, b'\1')
        a.uc.mem_write(BLOCK_MODE, b'\2')
        a.put(0x200220e0, bits(1.))
        a.put(0x20022108, 1)
        for cap, limit in ((3, 2), (0, 4)):
            a.uc.mem_write(0x2002a0f9, bytes([cap]))
            a.run('density_prepare')
            self.assertEqual(a.get(0x2002a810), limit)


@unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'), 'requires official mg204')
class FadeRecording(unittest.TestCase):
    def session(self, adc, tape, input_only, existing):
        audio = Audio(images()[1])
        audio.uc.mem_write(DRYK, b'\2')
        audio.uc.mem_write(0x2002a0f4, bytes([tape]))
        audio.a.put(0x200012cc, input_only)
        audio.a.put(SOS, adc)
        audio.a.put(0x2002208c, int(existing))
        audio.a.put(0x20022160, 64 if existing else 0)
        audio.a.put(0x20021fbc, bits(64) if existing else 0)
        for plane, level in ((LEFT, 1200), (RIGHT, -2400)):
            audio.uc.mem_write(plane, struct.pack('<65h', *([level]*65)))
        audio.blocks(8)
        audio.a.put(0x20021320, 1)
        audio.a.put(0x20022108, 1)
        audio.a.put(0x20022114, 1)
        return audio

    def input(self, audio, left, right):
        audio.uc.mem_write(0x20028000, struct.pack('<16h', *([left, right]*8)))

    def test_first_capture_in_both_channels_at_every_knob_setting(self):
        # Eight hardware frames per block, normal calibrated input gain 1.5.
        # Sentinel audio outside the take must remain untouched.
        for adc in (0, 2048, 4095):
            for tape, input_only in ((0, 0), (0, 1), (1, 0), (1, 1)):
                with self.subTest(adc=adc, tape=tape, inop=input_only):
                    audio = self.session(adc, tape, input_only, False)
                    self.input(audio, 3500, -1900)
                    audio.blocks(8)
                    self.assertEqual(audio.a.get(0x2002210c), 64)
                    for plane, level, sentinel in ((LEFT, 5250, 1200), (RIGHT, -2850, -2400)):
                        self.assertEqual(struct.unpack('<65h', audio.uc.mem_read(plane, 130)),
                                         (level,)*64 + (sentinel,))

    def test_new_splice_after_existing_audio_captures_raw_input(self):
        for adc in (0, 2048, 4095):
            audio = self.session(adc, tape=0, input_only=0, existing=True)
            # Stock's new-splice command starts at the last end marker and
            # assigns the next index, outside the existing tape windows.
            audio.a.put(0x2002210c, 64)
            audio.a.put(0x20022114, 2)
            self.input(audio, 3500, -1900)
            audio.blocks(4)
            self.assertEqual(audio.a.get(0x2002210c), 96)
            for plane, old, new in ((LEFT, 1200, 5250), (RIGHT, -2400, -2850)):
                self.assertEqual(struct.unpack('<96h', audio.uc.mem_read(plane, 192)),
                                 (old,) * 64 + (new,) * 32)

    def test_existing_splice_stereo_replacement_decay_and_stacking(self):
        for adc in (0, 2048, 4095):
            for tape, input_only in ((0, 0), (0, 1), (1, 0), (1, 1)):
                with self.subTest(adc=adc, tape=tape, inop=input_only):
                    audio = self.session(adc, tape, input_only, True)
                    audio.blocks(4)  # silent input, just over one turn of this short window
                    self.assertEqual(audio.uc.mem_read(MOD + 56, 1), b'\1')
                    window = audio.a.get(MOD + 48)
                    self.assertEqual(window, 16)
                    for plane, old in ((LEFT, 1200), (RIGHT, -2400)):
                        values = struct.unpack('<16h', audio.uc.mem_read(plane, 32))
                        if adc == 0:
                            self.assertEqual(values, (0,)*16)
                        elif adc == 4095:
                            self.assertEqual(values, (old,)*16)
                        else:
                            self.assertTrue(all(0 < abs(x) < abs(old) for x in values))
                    self.input(audio, 3500, -1900)
                    audio.blocks(14)
                    for plane, level, untouched in ((LEFT, 5250, 1200), (RIGHT, -2850, -2400)):
                        values = struct.unpack('<16h', audio.uc.mem_read(plane, 32))
                        if adc == 0:
                            self.assertEqual(values, (level,)*16)
                        elif adc == 4095:
                            self.assertTrue(all(abs(x) >= 4*abs(level) for x in values))
                        else:
                            self.assertTrue(all(abs(level) < abs(x) < 2*abs(level) for x in values))
                        self.assertEqual(struct.unpack('<49h', audio.uc.mem_read(plane+32, 98)),
                                         (untouched,)*49)
                    audio.a.put(0x20021320, 0)
                    audio.blocks(3)  # drain the last stock recording block
                    saved = [bytes(audio.uc.mem_read(plane, 130)) for plane in (LEFT, RIGHT)]
                    self.input(audio, 0, 0)
                    audio.blocks(20)
                    self.assertEqual(saved, [bytes(audio.uc.mem_read(p, 130)) for p in (LEFT, RIGHT)])
