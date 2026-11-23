"""Wet output selects the stereo Gene bus without modifying recording."""
import os
import struct
import unittest
from functools import lru_cache

from unicorn import UC_HOOK_CODE
from mgmod.card import card_file
from tests.audio import Audio
from tests.fixtures import reference
from tests.test_firmware_integration import images
from tests.test_preset_tape_effects import publish


DRYK = 0x2002A61A
TAPE = 0x2002A0F4
INOP = 0x200012CC
SOS = 0x20021C68
MORPH = 0x20021C6C
INPUT = 0x20028000
LEFT, RIGHT = 0xD0000000, 0xD1000000
PLANE_BYTES = 48000 * 2
SIGNAL = struct.pack('<16h', *([3500, -1900] * 8))
MIX_SITES = (0x08028EF4, 0x0802A1C2)


@lru_cache(None)
def c3_image():
    wrapped = reference('rollback-mg204+c3/mgmod.bin').read_bytes()
    image = wrapped[:-12]
    assert card_file(image) == wrapped
    return image


def set_mode(audio, mode):
    audio.uc.mem_write(DRYK, bytes([mode]))


def planes(audio):
    return tuple(bytes(audio.uc.mem_read(address, PLANE_BYTES)) for address in (LEFT, RIGHT))


def record(audio):
    # As on the module, set the record request, active flag and target splice.
    for address in (0x20021320, 0x20022108, 0x20022114):
        audio.a.put(address, 1)


@unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'), 'requires official firmware')
class DryMonitor(unittest.TestCase):
    def test_wet_return_before_the_first_gesture_timer_tick(self):
        for mode in (1, 2):
            audio = Audio(images()[1])
            audio.a.put(0x2002a000, 0)
            set_mode(audio, mode)
            audio.a.put(SOS, 0)
            for address in (LEFT, RIGHT):
                audio.uc.mem_write(address, bytes(PLANE_BYTES))
            audio.uc.mem_write(INPUT, SIGNAL)
            self.assertEqual(audio.blocks(4), bytes(4 * 32))

    def test_silent_reel_rejects_stereo_input_from_first_sample_at_both_sos_ends(self):
        for mode in (0, 1, 2):
            audio = Audio(images()[1])
            set_mode(audio, mode)
            for address in (LEFT, RIGHT):
                audio.uc.mem_write(address, bytes(PLANE_BYTES))
            audio.a.put(MORPH, 4095)
            audio.uc.mem_write(INPUT, SIGNAL)
            seen = set()
            for address in MIX_SITES:
                audio.uc.hook_add(UC_HOOK_CODE, lambda uc, pc, size, data: seen.add(pc),
                                  begin=address, end=address)
            monitor = bytearray()
            for sos in (0, 4095):
                audio.a.put(SOS, sos)
                monitor.extend(audio.blocks(300))
            self.assertEqual(seen, set(MIX_SITES))
            self.assertEqual(any(monitor), mode == 0, mode)

    def test_wet_playback_has_the_same_level_with_or_without_input_at_every_sos_setting(self):
        for mode in (1, 2):
            reference_audio, with_input = Audio(images()[1]), Audio(images()[1])
            for audio in (reference_audio, with_input):
                set_mode(audio, mode)
                audio.a.put(MORPH, 4095)
                publish(audio.a, {4: 30})  # stereo Gene samples after SRR
                # Distinct reel channels also expose channel duplication or swaps.
                audio.uc.mem_write(RIGHT, bytes(PLANE_BYTES))
            reference_audio.a.put(SOS, 0)
            with_input.uc.mem_write(INPUT, SIGNAL)
            for sos in (4095, 2048, 0):
                with_input.a.put(SOS, sos)
                expected = reference_audio.blocks(300)
                actual = with_input.blocks(300)
                self.assertEqual(expected, actual, (mode, sos))
                self.assertTrue(any(actual))
                stereo = struct.unpack(f'<{len(actual) // 2}h', actual)
                self.assertNotEqual(stereo[::2], stereo[1::2])

    def test_empty_reel_does_not_monitor_the_input(self):
        for mode in (0, 1, 2, 255):
            audio = Audio(images()[1])
            set_mode(audio, mode)
            audio.a.put(0x2002208C, 0)   # splice count
            audio.a.put(0x20022160, 0)   # end marker
            audio.a.put(0x2002A000, 0)   # first audio block before SHIFT UI initialization
            for address in (LEFT, RIGHT):
                audio.uc.mem_write(address, bytes(PLANE_BYTES))
            audio.a.put(SOS, 0)
            audio.uc.mem_write(INPUT, SIGNAL)
            self.assertEqual(any(audio.blocks(200)), mode not in (1, 2), mode)

    def test_mode_zero_matches_c3_and_mode_one_preserves_its_recordings(self):
        for tape, inop, feedback in ((0, 0, False), (0, 1, False), (0, 0, True),
                                     (0, 1, True), (1, 0, True), (1, 1, True)):
            case = tape, inop, feedback
            baseline, normal, wet = Audio(c3_image()), Audio(images()[1]), Audio(images()[1])
            set_mode(wet, 1)
            for audio in (baseline, normal, wet):
                audio.uc.mem_write(TAPE, bytes([tape]))
                audio.a.put(INOP, inop)
                audio.a.put(SOS, 1000)
                audio.a.put(MORPH, 3000)
                if feedback:
                    publish(audio.a, {7: 60})
                audio.blocks(250)
                audio.uc.mem_write(INPUT, SIGNAL)
                record(audio)
            before = planes(baseline)
            original_output = baseline.blocks(400)
            self.assertEqual(normal.blocks(400), original_output, case)
            self.assertNotEqual(wet.blocks(400), original_output, case)
            original_recording = planes(baseline)
            self.assertTrue(all(a != b for a, b in zip(before, original_recording)), case)
            for audio in (normal, wet):
                self.assertEqual(planes(audio), original_recording, case)
                for address in (0x20022108, 0x2002210C, 0x20022114):
                    self.assertEqual(audio.a.get(address), baseline.a.get(address), case)
