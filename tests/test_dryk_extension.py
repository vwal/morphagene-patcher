"""Run the stock REC start/stop and both stereo writers with selectable take length."""
import os
import struct
import unittest

from unicorn import UC_HOOK_CODE

from tests.arm import bits, value
from tests.audio import Audio
from tests.test_firmware_integration import images

SOS = 0x20021c68
REC, REQUEST, HEAD = 0x20022108, 0x20021320, 0x2002210c
COUNT, MARKERS, CAPACITY = 0x2002208c, 0x2002215c, 0x20021ca4
LATCH, FLAGS = 0x2002a720, 0x20022074
LEFT, RIGHT = 0xd0000000, 0xd1000000


@unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'), 'requires official mg204')
class ReplacementTake(unittest.TestCase):
    def session(self, *, mode=2, dlen=1, adc=0, capacity=768, rate_adc=2048):
        audio = Audio(images()[1])
        audio.uc.mem_write(0x2002a619, bytes([1, mode, dlen]))
        audio.uc.mem_write(0x2002a611, b'\1')
        for address, val in {
            COUNT: 2, MARKERS+4: 256, MARKERS+8: 512, CAPACITY: capacity,
            0x20021fbc: bits(256), 0x20021fc0: bits(256),
            SOS: adc, 0x20021c74: rate_adc, 0x20021c78: 0, 0x20021c7c: 0,
            0x20021c6c: 0, 0x20001290: 1, 0x200012b4: 1,
        }.items():
            audio.a.put(address, val)
        for plane, level in ((LEFT, 1000), (RIGHT, -1300)):
            audio.uc.mem_write(plane, struct.pack('<770h', *([level]*770)))
        self.input(audio, -2400, 3200)
        audio.blocks(16)
        return audio

    @staticmethod
    def input(audio, left, right):
        audio.uc.mem_write(0x20028000, struct.pack('<16h', *([left, right]*8)))

    @staticmethod
    def frames(audio, plane, start, end):
        return struct.unpack(f'<{end-start}h', audio.uc.mem_read(plane+2*start, 2*(end-start)))

    @staticmethod
    def start(audio, splice):
        # Stock resolves both the selected splice and the REC command. Do not
        # preselect a write route or introduce an artificial recording state.
        audio.a.put(0x20021de4, splice)
        audio.a.put(0x20021cbc, splice)
        audio.a.put(FLAGS, 0)
        audio.a.put(REQUEST, 1)
        audio.blocks(1)

    @staticmethod
    def stop(audio):
        audio.a.put(REQUEST, 0)
        audio.blocks(4)

    def test_last_splice_short_take_replaces_prefix_leaves_tail_and_neighbors(self):
        audio = self.session()
        self.start(audio, 2)
        self.assertEqual(audio.a.get(LATCH), 2)
        audio.blocks(8)
        self.stop(audio)
        stop = audio.a.get(HEAD)
        self.assertTrue(256 < stop < 512)
        self.assertEqual(audio.a.get(LATCH), 0)
        self.assertEqual(audio.a.get(COUNT), 2)
        self.assertEqual(audio.a.get(MARKERS+8), 512)
        for plane, old, new in ((LEFT, 1000, -3600), (RIGHT, -1300, 4800)):
            self.assertEqual(self.frames(audio, plane, 0, 256), (old,)*256)
            self.assertEqual(self.frames(audio, plane, 256, stop), (new,)*(stop-256))
            self.assertEqual(self.frames(audio, plane, stop, 514), (old,)*(514-stop))

    def test_capacity_latches_at_last_frame_saturates_and_keeps_count(self):
        audio = self.session(capacity=540)
        self.input(audio, -30000, 30000)
        self.start(audio, 2)
        audio.blocks(70)
        self.assertEqual((audio.a.get(REC), audio.a.get(REQUEST), audio.a.get(LATCH)), (0, 0, 0))
        self.assertEqual((audio.a.get(COUNT), audio.a.get(MARKERS+8), audio.a.get(HEAD)), (2, 540, 540))
        for plane, old, full in ((LEFT, 1000, -1), (RIGHT, -1300, 1)):
            self.assertEqual(self.frames(audio, plane, 0, 256), (old,)*256)
            recorded = self.frames(audio, plane, 256, 540)
            self.assertTrue(all(sample*full >= 32766 for sample in recorded), (min(recorded),max(recorded)))
            self.assertEqual(self.frames(audio, plane, 540, 770), (old,)*230)

    def test_selection_uses_zero_retention_deadband_and_latches_in_both_directions(self):
        for adc, selected in ((185, True), (186, False), (4095, False)):
            with self.subTest(adc=adc):
                audio = self.session(adc=adc)
                self.start(audio, 2)
                self.assertEqual(audio.a.get(LATCH), 2 if selected else 0)
                audio.a.put(SOS, 4095 if selected else 0)
                audio.blocks(40)
                self.stop(audio)
                end = audio.a.get(MARKERS + 8)
                self.assertEqual(end > 512, selected)
                if selected:
                    self.assertEqual(self.frames(audio, LEFT, 256, end), (-3600,)*(end-256))

    def test_reverse_playback_and_short_genes_still_record_linear_time(self):
        audio = self.session(rate_adc=0)
        audio.a.put(0x20021c7c, 3800)
        audio.a.put(0x20021c78, 2700)
        audio.blocks(128)
        self.assertLess(value(audio.a.get(0x200220e0)), 0)
        self.start(audio, 2)
        audio.blocks(31)
        self.assertEqual(audio.a.get(HEAD), 512)
        self.input(audio, -1200, 1600)
        audio.blocks(10)
        self.stop(audio)
        end = audio.a.get(MARKERS+8)
        self.assertIn(end, (592, 593))
        self.assertEqual(self.frames(audio, LEFT, 256, 512), (-3600,)*256)
        self.assertEqual(self.frames(audio, RIGHT, 512, end), (2400,)*(end-512))

    def test_both_audio_engines_keep_recording_stereo_after_a_knob_move(self):
        audio = Audio(images()[1])
        audio.uc.mem_write(0x2002a61a, bytes([2, 1]))
        audio.a.put(0x20021c6c, 4095)
        audio.a.put(SOS, 0)
        self.input(audio, -2400, 3200)
        sites = (0x080291d8, 0x0802a4bc)
        seen = set()
        for address in sites:
            audio.uc.hook_add(UC_HOOK_CODE, lambda uc, pc, size, ctx: seen.add(pc),
                              begin=address, end=address)
        audio.blocks(100)
        self.start(audio, 1)
        self.assertEqual(audio.a.get(LATCH), 1)
        audio.blocks(140)
        audio.a.put(SOS, 4095)
        audio.blocks(600)
        self.stop(audio)
        self.assertEqual(seen, set(sites))
        stop = audio.a.get(HEAD)
        self.assertIn(stop, (5928, 5929))
        for plane, level in ((LEFT, -3600), (RIGHT, 4800)):
            self.assertEqual(self.frames(audio, plane, 0, stop), (level,) * stop)

    def test_new_splice_does_not_replace_last_splice(self):
        audio = self.session(capacity=768)
        audio.a.put(0x200012c4, 1)      # rsop 1: REC alone makes a new splice
        self.start(audio, 2)
        self.assertEqual(audio.a.get(LATCH), 0)
        audio.blocks(5)
        self.stop(audio)
        self.assertEqual((audio.a.get(COUNT), audio.a.get(MARKERS+8)), (3, 512))
        end = audio.a.get(MARKERS+12)
        self.assertGreater(end, 512)
        self.assertEqual(self.frames(audio, LEFT, 0, 512), (1000,)*512)
        self.assertEqual(self.frames(audio, LEFT, 512, end), (-3600,)*(end-512))

    def test_ineligible_routes_match_dlen_zero_on_both_channels(self):
        for mode, selected in ((0, 2), (1, 2), (2, 1)):
            with self.subTest(mode=mode, selected=selected):
                outcomes = []
                for dlen in (0, 1):
                    audio = self.session(mode=mode, dlen=dlen)
                    self.start(audio, selected)
                    self.assertEqual(audio.a.get(LATCH), 0)
                    heard = audio.blocks(40)
                    self.stop(audio)
                    self.assertEqual((audio.a.get(COUNT), audio.a.get(MARKERS+8)), (2, 512))
                    outcomes.append((heard, *(self.frames(audio, plane, 0, 770) for plane in (LEFT, RIGHT))))
                self.assertEqual(outcomes[0], outcomes[1])

    def test_editing_splices_while_recording_stops_before_writing_another_frame(self):
        audio = self.session()
        self.start(audio, 2)
        audio.blocks(8)
        last = audio.a.get(HEAD)
        audio.a.put(MARKERS+12, 640)
        audio.a.put(COUNT, 3)
        self.input(audio, -5000, 4000)
        audio.blocks(3)
        self.assertEqual((audio.a.get(REC), audio.a.get(LATCH), audio.a.get(HEAD)), (0, 0, last))
        self.assertEqual((audio.a.get(COUNT),audio.a.get(MARKERS+8),audio.a.get(MARKERS+12)),(3,512,640))
        self.assertEqual(self.frames(audio, LEFT, last, 641), (1000,)*(641-last))
