"""Stock Gene timing at the shifted endpoint and re-entry into numeric density."""
import os
import struct
import unittest

from tests import test_settings_reload as live
from tests.arm import Arm, UC_ARM_REG_R0, bits, value
from tests.audio import Audio
from tests.test_firmware_integration import images
from tests.test_unity_center import configure

MOD = 0x2002a000
STATE, ACTIVE, INTERVAL, REMAINING = range(0x2002a800, 0x2002a810, 4)
DENS, DSTR = 0x2002a607, 0x2002a614
SIZE, CLOCK, SPEED = 0x20021c7c, 0x20021cb0, 0x200220e0


class Endpoint(unittest.TestCase):
    def test_hysteresis_phase_and_clock_priority(self):
        a = Arm('gene_shape', 'g2_size')
        a.uc.mem_write(DENS, bytes([1]))
        a.put(SPEED, bits(1))
        a.put(DSTR, 80)
        a.run('density_prepare')
        def adjust(adc):
            a.uc.reg_write(UC_ARM_REG_R0, adc)
            a.run('density_adjust')
            a.run('density_prepare')
            return a.get(INTERVAL), a.get(ACTIVE)

        self.assertEqual(adjust(97), (480000, 1))
        for adc in (96, 0, 117, 127, 102):
            self.assertEqual(adjust(adc), (0, 0))
            self.assertEqual(a.get(REMAINING), 0)
        self.assertEqual(adjust(128), (480000, 1))
        self.assertEqual(a.get(REMAINING), 480000)
        a.put(REMAINING, 43210)
        for adc in (126, 106, 97, 192):
            self.assertEqual(adjust(adc), (480000, 1))
            self.assertEqual(a.get(REMAINING), 43210)
        self.assertEqual(adjust(2048), (6000, 1))
        self.assertEqual(a.get(REMAINING), 6000)
        a.put(CLOCK, 1)
        for adc in (0, 128, 4095):
            self.assertEqual(adjust(adc)[1], 0)
        a.put(CLOCK, 0)
        a.run('density_prepare')
        self.assertEqual((a.get(ACTIVE), a.get(INTERVAL)), (1, 375))
        self.assertEqual(adjust(0), (0, 0))
        for speed in (0, -1, 1):
            a.put(SPEED, bits(speed))
            a.run('density_prepare')
            self.assertEqual(a.get(ACTIVE), 0)
        self.assertEqual(a.get(DSTR), 80)

    def test_reload_preserves_detent_or_recalls_explicit_ten_second_interval(self):
        a = live.arm()
        a.uc.mem_write(DENS, bytes([1]))
        a.put(STATE, 1)  # a performed endpoint, interval and countdown zero
        a.put(DSTR, 80)
        for line, expected in (('dryk 3', 0), ('dstr 0.1', 480000)):
            a.put(live.CARD, 0)
            live.stage(a, f'1 0 0\n{line}\n'.encode())
            self.assertEqual(a.get(live.PENDING), 1)
            live.call(a, 'reload_commit')
            self.assertEqual(a.get(INTERVAL), expected)
            self.assertEqual(a.get(REMAINING), expected)
            self.assertEqual(a.get(DSTR), 1 if expected else 80)


@unittest.skipUnless(os.getenv('MGMOD_FIRMWARE'), 'requires official mg204 firmware')
class EndpointAudio(unittest.TestCase):
    def test_panel_gesture_from_ccw_and_pickup_of_shorter_genes(self):
        timer = live.ReloadIntegration()
        a = timer.timer(images()[1])
        a.put(live.CARD, 1)
        a.put(SPEED, bits(1))
        a.uc.mem_write(DENS, bytes([1]))
        a.syms['size_hook'] = 0x08027808

        def block(adc, shift):
            a.put(SIZE, adc)
            timer.timer_tick(a, shift)
            a.uc.reg_write(UC_ARM_REG_R0, 0x20021c68)
            a.run('size_hook', [0x0802780c])
            return a.uc.reg_read(UC_ARM_REG_R0)

        for initial in (0, 2000):
            for _ in range(12):
                block(initial, False)
            for _ in range(12):
                block(initial, True)
            self.assertEqual(block(512, True), initial)
            self.assertEqual(a.uc.mem_read(MOD+6, 1), bytes([4]))
            self.assertEqual(block(0, True), initial)
            self.assertEqual((a.get(INTERVAL), a.get(ACTIVE)), (0, 0))
            for _ in range(12):
                self.assertEqual(block(0, False), initial)
            self.assertEqual(a.get(0x200012e0), 0)  # consumed gesture did not advance splice
            if initial:
                self.assertEqual(block(800, False), initial)
            self.assertEqual(block(initial, False), initial)

    def test_full_fifteen_second_splice_matches_stock_through_the_loop(self):
        stock, shifted = (Audio(images()[1]) for _ in range(2))
        length = 15*48000
        # Only the last two seconds contain a right-channel tone.
        tone = struct.pack('<120h', *([4000]*60 + [-4000]*60)) * 800
        for engine in (stock, shifted):
            configure(engine.a, (0, 0, 0, 0), centered=1)
            for addr, val in ((0x20022160, length), (0x20021fbc, bits(length)),
                              (0x20021c74, 2048), (0x20021c78, 0),
                              (SIZE, 0), (0x20021c6c, 420), (DSTR, 1)):
                engine.a.put(addr, val)
            engine.uc.mem_write(0xd1000000, bytes((length-96000)*2) + tone)
        shifted.uc.mem_write(DENS, bytes([1]))
        # Emulate the SHIFT gesture already claimed in the timer, covered above.
        # Primary size was fully CCW and remains there throughout.
        shifted.uc.mem_write(MOD+4, bytes([1, 1, 4]))
        shifted.a.put(SIZE, 256)
        self.assertEqual(shifted.blocks(1), stock.blocks(1))
        shifted.a.put(SIZE, 0)
        self.assertEqual(shifted.blocks(1), stock.blocks(1))
        self.assertEqual((shifted.a.get(INTERVAL), shifted.a.get(ACTIVE)), (0, 0))
        shifted.uc.mem_write(MOD+4, bytes(3))
        for second in range(16):
            expected, actual = stock.blocks(6000), shifted.blocks(6000)
            self.assertTrue(actual == expected, f'stereo PCM differs in second {second+1}')
            if second in (11, 14):
                right = struct.unpack('<96000h', actual)[1::2]
                self.assertEqual(any(abs(sample) > 100 for sample in right), second == 14)
        self.assertEqual(shifted.births, stock.births)
        self.assertEqual(shifted.births, [0, length])
        self.assertEqual(value(shifted.a.get(SPEED)), 1.0)

    def test_short_genes_keep_their_length_and_resume_at_point_one_hz(self):
        stock, edited = (Audio(images()[1]) for _ in range(2))
        for engine in (stock, edited):
            engine.a.put(SIZE, 2300)
            engine.a.put(0x20021c6c, 3800)
            engine.a.put(DSTR, 1)
        edited.uc.mem_write(DENS, bytes([1]))
        edited.uc.mem_write(MOD+208, struct.pack('<H', 2300))
        edited.uc.mem_write(MOD+4, bytes([1, 1, 4]))
        edited.a.put(SIZE, 0)
        self.assertTrue(stock.blocks(800) == edited.blocks(800))
        self.assertEqual(edited.births, stock.births)
        self.assertTrue(edited.births)
        self.assertEqual(edited.a.get(INTERVAL), 0)
        before = len(edited.births)
        start = edited.sample_index
        edited.a.put(SIZE, 176)  # clockwise out of the stock detent
        stock.uc.mem_write(DENS, bytes([1]))  # first use reads dstr 0.1
        for _ in range(10):
            self.assertTrue(stock.blocks(6000) == edited.blocks(6000))
        self.assertEqual(edited.births[before:], [start+480000])
        self.assertEqual(edited.births, stock.births)
