"""Optional Organize play-through, real Thumb hooks and splice preset pickup."""
import os
import statistics
import struct
import unittest

from tests.arm import (
    Arm, bits, value, UC_HOOK_CODE, UC_ARM_REG_LR, UC_ARM_REG_PC,
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R4,
    UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_S0, UC_ARM_REG_S1, UC_ARM_REG_S21, UC_ARM_REG_SP,
)
from tests.test_preset_splice import (
    setup, publish, organize, REQUEST, COUNT, L, ORG, ACCEPTED,
)
from tests import test_preset_splice
from tests.audio import Audio
from tests.test_firmware_integration import images


SETTINGS = 0x2002a0f0
THRU = 0x2002a61e
MAGIC = 0x5354504f
EOS = 0x20021de8
NAV = 0x200012e0
REC = 0x20022108
REC_REQUEST = 0x20021320
REEL_MODE = 0x20021338
FULL, CLOCK = 0x20021e14, 0x20021cb0
TARGET, RATE = 0x200220e8, 0x200220e0


def enable(a, value=1, magic=MAGIC):
    a.put(SETTINGS, magic)
    a.uc.mem_write(THRU, bytes([value]))


def map_splice(a, position, count, previous):
    a.put(REQUEST, previous)
    a.uc.reg_write(UC_ARM_REG_S21, bits(position))
    a.uc.reg_write(UC_ARM_REG_R2, count)
    a.run('o1_map', [0x080277d2])
    return a.get(REQUEST)


class SpliceThruHooks(unittest.TestCase):
    def test_disabled_and_uninitialized_use_ordinary_full_travel(self):
        a = Arm('playback', 'o1_map')
        for value, magic in ((0, MAGIC), (255, MAGIC), (1, 0)):
            enable(a, value, magic)
            for position, expected in ((0, 1), (.5, 5), (.97, 10), (1, 10)):
                self.assertEqual(map_splice(a, position, 10, 2), expected)

    def test_every_splice_reachable_and_zone_keeps_valid_selection(self):
        a = Arm('playback', 'o1_map')
        enable(a)
        for count in (1, 3, 32, 300):
            for selected in range(1, count + 1):
                center = ((selected - .5) / count + .001) * .95
                self.assertEqual(map_splice(a, center, count, 0), selected)
            for zone in (.95, .98, 1.0):
                for previous, expected in ((0, 1), (count + 1, 1), (count, count)):
                    self.assertEqual(map_splice(a, zone, count, previous), expected)

    def test_eos_requires_fresh_trigger_accepted_zone_and_free_navigation(self):
        a = Arm('playback', 'o1_map')
        # A raw knob in the zone cannot override Organize held after a Turing edit.
        a.put(ORG, 4095)
        a.put(TARGET, bits(1))
        a.put(RATE, bits(1))
        a.put(0x20022080, 40)
        a.put(0x200220a0, bits(1/4000))
        keep = (UC_ARM_REG_R1, UC_ARM_REG_R3, UC_ARM_REG_R4,
                UC_ARM_REG_S0, UC_ARM_REG_S1, UC_ARM_REG_S21)
        for i, reg in enumerate(keep):
            a.uc.reg_write(reg, 0x41f00000 + i)
        sp = a.uc.reg_read(UC_ARM_REG_SP)
        for address, value, expected in (
            (ACCEPTED, 3840, 1), (ACCEPTED, 3839, 0),
            (EOS, 3, 0), (EOS, 2, 0), (EOS, 0, 0), (COUNT, 1, 0), (COUNT, 0, 0),
            (REC, 1, 0), (REC_REQUEST, 1, 0), (REEL_MODE, 1, 0),
            (NAV, 0xffffffff, 0xffffffff), (NAV, 1, 1), (SETTINGS, 0, 0), (THRU, 0, 0),
        ):
            enable(a)
            for variable, default in ((COUNT, 3), (REC, 0), (REC_REQUEST, 0),
                                     (REEL_MODE, 0), (EOS, 4), (ACCEPTED, 3840), (NAV, 0)):
                a.put(variable, default)
            if address == THRU:
                enable(a, value)
            else:
                a.put(address, value)
            a.run('e1_eos', [0x08024d32])
            self.assertEqual(a.get(NAV), expected, (address, value))
            self.assertEqual(a.uc.reg_read(UC_ARM_REG_R2), a.get(EOS))
            self.assertEqual(a.uc.reg_read(UC_ARM_REG_SP), sp)
            for i, reg in enumerate(keep):
                self.assertEqual(a.uc.reg_read(reg), 0x41f00000 + i)

    def test_short_gene_and_clock_eos_follow_effective_direction(self):
        a = Arm('playback', 'o1_map')
        setup(a, 3)
        a.put(ACCEPTED, 4095)
        for mode, rate, target, full, clock, step in (
            (1,-1,-1,0,0,1), (2,-1,-1,0,0,-1), (2,1,1,0,0,1),
            (2,0,0,0,0,0), (2,-.02,0,0,0,0), (2,-1,-1,1,0,0),
            (2,-1,-1,1,1,-1), (2,1,1,1,1,1),
        ):
            with self.subTest(mode=mode, rate=rate, full=full, clock=clock):
                enable(a, mode)
                for ptr, v in ((EOS,4),(NAV,0),(RATE,bits(rate)),(TARGET,bits(target)),
                               (FULL,full),(CLOCK,clock)):
                    a.put(ptr,v)
                a.run('e1_eos',[0x08024d32])
                self.assertEqual(a.get(NAV),step & 0xffffffff)

    def test_clamped_preset_picks_up_in_last_splice_cell_below_zone(self):
        a = Arm('gene_shape', 'g2_size')
        setup(a, 100)
        enable(a, 1)  # isolated gene_shape; the linked scheduler also enables this layout for thru 2
        publish(a, 300)
        organize(a, 4095)
        # A stationary knob in the play-through zone has no absolute splice cell.
        self.assertEqual(organize(a, 4010), 4095)
        self.assertEqual(a.get(L+16), 1)
        self.assertEqual(a.get(REQUEST), 100)
        self.assertEqual(organize(a, 3874), 3874)
        self.assertEqual(a.get(L+16), 0)

    def test_live_thru_change_retargets_held_splice_pickup(self):
        a = Arm('gene_shape', 'g2_size')
        setup(a, 300)
        enable(a, 0)
        publish(a, 150)
        organize(a, 250)
        original_target = a.get(L+4)
        enable(a)
        publish(a, 0, generation=2, mask=0)
        self.assertEqual(organize(a, 250), 250)
        self.assertEqual(a.get(L+16), 1)
        remapped_target = a.get(L+4)
        self.assertAlmostEqual(remapped_target, .95 * original_target, delta=1)
        self.assertEqual(organize(a, remapped_target), remapped_target)
        self.assertEqual(a.get(L+16), 0)
        self.assertEqual(a.get(REQUEST), 150)

    def test_pickup_agrees_with_firmware_rounding_at_calibrated_zone_edge(self):
        a = Arm('gene_shape', 'g2_size')
        setup(a, 100)
        enable(a)
        a.put(0x20022080, 100)
        a.put(0x20022078, 3900)
        a.put(0x200220a0, bits(1/3800))
        publish(a, 100)
        organize(a, 3900)
        # 3610 / 3800 rounds to the boundary, but stock's multiplication
        # by the saved scale puts this particular ADC count just below it.
        self.assertEqual(organize(a, 3711), 3900)
        self.assertEqual(a.get(L+16), 1)
        self.assertEqual(organize(a, 3710), 3710)
        self.assertEqual(a.get(L+16), 0)


@unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'), 'requires official firmware')
class SpliceThruAudio(unittest.TestCase):
    def timer_tick(self, engine):
        engine.uc.reg_write(UC_ARM_REG_R1, 0x20025000)
        engine.uc.reg_write(UC_ARM_REG_R3, 0)
        engine.uc.emu_start(0x08024d2b, 0x08024d56, count=300)
        self.assertEqual(engine.uc.reg_read(UC_ARM_REG_PC), 0x08024d56)

    def test_short_genes_route_eos_to_stock_navigation_and_wrap_from_preset(self):
        engine = test_preset_splice.PresetSpliceAudio().engine(1)
        a = engine.a
        a.uc.mem_write(0x2002215c, struct.pack('<4I', 0, 1200, 2400, 3600))
        engine.call(0x08026d98)  # refresh splice bounds after loading the short reel
        enable(a)
        a.put(ORG, 4095)
        a.put(0x20021c7c, 2000)  # short Gene, no external clock
        publish(a, 300)  # last of three existing splices
        engine.blocks(2)
        self.assertEqual(a.get(REQUEST), 3)
        a.put(EOS, 0)
        splices = []
        for _ in range(800):
            engine.blocks(1)
            if a.get(EOS) == 4:  # real event emitted by stock audio playback
                self.assertEqual(a.get(FULL), 0)
                self.timer_tick(engine)
                self.timer_tick(engine)
                self.assertEqual(a.get(NAV), 1)
                splices.append(a.get(REQUEST))
                if len(splices) == 5:
                    break
        self.assertEqual(splices, [3, 1, 2, 3, 1])

    def test_turing_edit_cannot_switch_play_through_on_by_turning_to_cw(self):
        engine = test_preset_splice.PresetSpliceAudio().engine(1)
        a = engine.a
        enable(a)
        engine.uc.mem_write(0x2002a0fa, b'\x01')  # Turing enabled
        publish(a, 2)
        engine.blocks(1)
        engine.uc.mem_write(0x2002a004, bytes((1, 1, 6)))  # SHIFT + Organize
        engine.uc.mem_write(0x2002a082, b'\x01')
        a.put(ORG, 4095)
        engine.blocks(2)
        self.assertEqual(a.get(REQUEST), 2)
        self.assertEqual(a.get(L+16), 1)
        self.assertLess(a.get(ACCEPTED), 3800)
        a.put(EOS, 4)
        a.put(CLOCK, 1)
        self.timer_tick(engine)
        self.assertEqual(a.get(NAV), 0)
        engine.uc.mem_write(0x2002a004, bytes((0, 1, 6)))
        a.put(ORG, a.get(L+4))
        engine.blocks(2)
        self.assertEqual(a.get(L+16), 0)
        a.put(ORG, 4095)
        engine.blocks(1)
        a.put(EOS, 4)
        a.put(CLOCK, 1)
        self.timer_tick(engine)
        self.assertEqual(a.get(NAV), 1)


@unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'), 'requires official firmware')
class ScheduledSplices(unittest.TestCase):
    def engine(self, bounds, mode=1, omod=0, morph=420, adc=3527, size=0):
        engine = Audio(images()[1])
        a = engine.a
        setup(a)
        for location, val in ((0x200012b4, omod), (test_preset_splice.ACTIVE, 1),
                              (0x20021c7c, size), (0x20021c78, 0), (0x20021c74, adc),
                              (0x20021c6c, morph), (ORG, 4095)):
            a.put(location, val)
        a.uc.mem_write(0x2002215c, struct.pack('<4I', *bounds))
        engine.call(0x08026d98)
        enable(a, mode)
        launches = []
        def voice(uc, pc, size, data):
            launches.append((engine.sample_index, uc.reg_read(UC_ARM_REG_R5),
                             uc.reg_read(UC_ARM_REG_R6), pc))
        for pc in (0x0802838a, 0x08029bb8):
            a.uc.hook_add(UC_HOOK_CODE, voice, begin=pc, end=pc)
        return engine, launches

    def real_timer(self, engine):
        # TIM2 peripheral reports its update flag. Buttons are unpressed,
        # Play is high, stock housekeeping and the EOSG countdown execute.
        engine.uc.mem_map(0x40000000, 0x1000)
        engine.a.put(0x40020010, 32)
        def timer_flag(uc, pc, size, data):
            uc.reg_write(UC_ARM_REG_R0, 1)
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
        engine.uc.hook_add(UC_HOOK_CODE, timer_flag, begin=0x0802dcd4, end=0x0802dcd4)

    def test_real_timer_and_voice_bounds_no_second_pass_and_reverse_wrap(self):
        bounds = [0, 4800, 11200, 15200]
        cases = [(1, 3527, 0, [1,2,3]), (1, 3527, 1, [1,2,3]),
                 (1, 569, 1, [1,2,3]), (2, 569, 0, [1,3,2]),
                 (2, 569, 1, [1,3,2]), (2, 3527, 1, [1,2,3])]
        for mode, adc, omod, order in cases:
            with self.subTest(mode=mode, adc=adc, omod=omod):
                engine, launches = self.engine(bounds, mode, omod, adc=adc, size=150)
                self.real_timer(engine)
                for _ in range(4300):
                    engine.blocks(1)
                    engine.call(0x08024718)
                    engine.call(0x08024718)
                    if len(launches) == 7:
                        break
                self.assertEqual(engine.a.get(FULL), 1)
                expected = [bounds[n-1:n+1] for n in order*2+order[:1]]
                self.assertEqual([[lo,hi] for _,lo,hi,_ in launches], expected)

    def test_short_genes_follow_reverse_eos_order_in_native_timer(self):
        bounds = [0, 10000, 26000, 38000]
        engine, launches = self.engine(bounds, mode=2, adc=569, size=2000)
        self.real_timer(engine)
        for _ in range(1000):
            engine.blocks(1)
            engine.call(0x08024718)
            engine.call(0x08024718)
            if len(launches) == 6:
                break
        self.assertEqual(engine.a.get(FULL), 0)
        self.assertEqual([lo for _,lo,_,_ in launches], [0,26000,10000]*2)

    def test_direction_change_at_next_birth_and_ordinary_playback_outside_zone(self):
        bounds = [0, 1200, 3200, 3900]
        engine, launches = self.engine(bounds, mode=2)
        engine.blocks(180)  # playing splice 2 forward
        self.assertEqual([lo for _,lo,_,_ in launches], [0,1200])
        engine.a.put(0x20021c74, 569)
        engine.blocks(360)
        self.assertLess(value(engine.a.get(RATE)), 0)
        self.assertEqual([lo for _,lo,_,_ in launches][:3], [0,1200,0])
        engine.a.put(ORG, 100)
        engine.blocks(650)
        self.assertEqual([lo for _,lo,_,_ in launches[-3:]], [0,0,0])

    def test_manual_navigation_overrides_next_automatic_whole_gene(self):
        bounds = [0, 1200, 3200, 3900]
        for omod in (0,1):
            with self.subTest(omod=omod):
                engine, launches = self.engine(bounds, mode=2, omod=omod)
                engine.blocks(165)   # splice 2 has begun
                engine.a.put(NAV, 0xffffffff)   # ordinary previous splice request
                engine.blocks(800)
                self.assertEqual([lo for _,lo,_,_ in launches[:5]], [0,1200,0,1200,3200])
                if omod:
                    self.assertLess(launches[2][0], 3200)
                else:
                    self.assertEqual(launches[2][0], 3200)

    def test_dense_full_genes_sequence_in_both_audio_paths(self):
        bounds = [0, 4800, 11200, 15200]
        engine, launches = self.engine(bounds, mode=2, morph=3500, adc=569)
        engine.uc.mem_write(0x2002a607, bytes([1]))
        engine.a.put(0x2002a614, 1280)  # 128 Genes/sec, subject to voice availability
        engine.blocks(5500)
        self.assertEqual(engine.paths, {'A','B'})
        slots = [bounds.index(lo)+1 for _,lo,_,_ in launches]
        self.assertGreater(len(slots), 8)
        self.assertEqual(slots, ([1,3,2]*len(slots))[:len(slots)])
        self.assertTrue(any(then-now < 4800 for now,then in zip(engine.births,engine.births[1:])))

    def test_minute_splice_pcm_advances_on_frame_2880000_and_wraps(self):
        length = 60 * 48000
        bounds = [0, length, length+1800, length+3200]
        engine, launches = self.engine(bounds)
        # Three unequal recordings with distinct amplitude. Run every frame
        # through both stereo outputs. No jumping phase or simulating wraps.
        for i, amplitude in enumerate((5000,9000,14000)):
            period = struct.pack('<80h', *([amplitude]*40 + [-amplitude]*40))
            frames = bounds[i+1] - bounds[i]
            data = (period*((frames+79)//80))[:2*frames]
            for plane in (0xd0000000, 0xd1000000):
                engine.uc.mem_write(plane+2*bounds[i], data)
        probes = [(length//2, 5800, 8000), (length-512, 5800, 8000),
                  (length+704, 11000, 14000), (length+2400, 17500, 21000),
                  (length+4104, 5800, 8000)]
        for target, low, high in probes:
            blocks = (target-engine.block_index*8)//8
            while blocks > 2000:
                engine.blocks(2000)
                blocks -= 2000
            pcm = engine.blocks(blocks)
            stereo = struct.unpack('<128h', pcm[-256:])
            for channel in (0,1):
                level = statistics.mean(abs(x) for x in stereo[channel::2])
                self.assertTrue(low < level < high, (target, channel, level))
        self.assertEqual([(t,lo,hi) for t,lo,hi,_ in launches], [
            (0,0,length), (length,length,length+1800), (length+1800,length+1800,length+3200),
            (length+3200,0,length)])


if __name__ == '__main__':
    unittest.main()
