"""Change only dryk at an audio boundary and compare every output frame."""
import os
import struct
import unittest

from tests.audio import Audio
from tests.test_firmware_integration import images
from tests.test_option_isolation import live_slots
from tests.test_settings_reload import PENDING, RESULT


@unittest.skipUnless(os.getenv('MGMOD_FIRMWARE'), 'requires official firmware')
class DryKillLiveAudio(unittest.TestCase):
    def test_switches_preserve_the_playing_reel_and_wet_signal(self):
        image = images()[1]
        live, mixed, wet = [Audio(image) for _ in range(3)]
        option = 0x2002a61a
        wet.uc.mem_write(option, b'\x01')
        input_block = struct.pack('<16h', *([6300, -2900] * 8))
        for audio in (live, mixed, wet):
            audio.a.put(0x20021c68, 1000)
            audio.uc.mem_write(0x20028000, input_block)
            audio.blocks(200)

        slot, seen, mask = live_slots()['dryk']
        for mode in (2, 3, 1, 0, 3, 2, 1, 0):
            with self.subTest(mode=mode):
                live.a.put(slot, mode)
                live.a.put(seen, mask)
                live.a.put(PENDING, 1)
                result = live.blocks(64)
                outputs = (mixed.blocks(64), wet.blocks(64))
                self.assertNotEqual(*outputs)
                self.assertEqual(result, outputs[int(mode != 0)])
                self.assertEqual(live.a.get(PENDING), 0)
                self.assertEqual(live.a.get(RESULT), 1)
                self.assertEqual(live.uc.mem_read(option, 1), bytes([mode]))
                self.assertEqual(live.births, mixed.births)
                for plane in (0xd0000000, 0xd1000000):
                    self.assertEqual(live.uc.mem_read(plane, 96000),
                                     mixed.uc.mem_read(plane, 96000))
