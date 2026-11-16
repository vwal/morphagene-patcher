"""Dev8 main S.O.S./Varispeed: pickup, unity priority and actual audio."""
import os
import unittest
from tests.arm import *
from tests.audio import Audio
from tests.test_firmware_integration import images
from tests.test_settings_reload import call
from tests.test_preset_controls import control_arm, MOD, target
from tests.test_unity import arm, mapped, U, VUNI, VCTR

P, EXT, MAGIC = 0x2002a660, 0x2002ae90, 0x54535250
SOS, VS = 0x20021c68, 0x20021c74


def publish(a, values):
    for index, value_ in values.items():
        a.put(P+16+4*index if index<4 else EXT+4*(index-4), value_)
    a.put(P+8, sum(1<<i for i in values))
    a.put(P+12, sum(1<<i for i in values))
    a.put(P+4, a.get(P+4)+1)
    a.put(P, MAGIC)


def lane(i):return EXT+32+(i-4)*24


class MainPresets(unittest.TestCase):
    def test_sos_all_percentages_and_pickup(self):
        a=control_arm(0)
        for percent in range(101):
            publish(a,{10:percent});a.put(SOS,1000)
            self.assertEqual(call(a,'preset_sos',1000),target(percent))
        publish(a,{10:50});a.put(SOS,1000)
        self.assertEqual(call(a,'preset_sos',1000),2048)
        a.put(SOS,2200)
        self.assertEqual(call(a,'preset_sos',2200),2200)
        publish(a,{})
        a.put(SOS,2500)
        self.assertEqual(call(a,'preset_sos',2500),2500)

    def test_sos_feedback_edit_keeps_recalled_primary_and_single_pickup(self):
        a=control_arm(0);a.put(SOS,1000);publish(a,{10:75})
        self.assertEqual(call(a,'preset_sos',1000),3071)
        a.uc.mem_write(MOD+4,bytes([1,1,1]));a.put(SOS,3500)
        a.uc.mem_write(MOD+17,b'\1');a.uc.mem_write(MOD+18,struct.pack('<H',1000))
        self.assertEqual(call(a,'preset_sos',1000),3071)
        self.assertEqual(struct.unpack('<H',a.uc.mem_read(MOD+18,2))[0],3071)
        a.uc.mem_write(MOD+4,bytes(3));a.put(SOS,3000)
        self.assertEqual(call(a,'preset_sos',3071),3000)
        self.assertEqual(a.uc.mem_read(MOD+17,1),b'\0')

    def test_varispeed_all_percentages_omission_and_combined_input_pickup(self):
        a=arm();a.uc.mem_write(VUNI,b'\0\0')
        for percent in range(101):
            publish(a,{11:percent})
            self.assertAlmostEqual(mapped(a,.13),percent/100,places=6)
        publish(a,{11:50});self.assertEqual(mapped(a,.2),.5)
        publish(a,{})
        self.assertEqual(mapped(a,.3),.5)
        self.assertAlmostEqual(mapped(a,.53),.53,places=6)
        self.assertEqual(a.get(lane(11)+16),0)
        for percent, physical in ((0,.015),(100,.98)):
            publish(a,{11:percent});mapped(a,physical)
            self.assertAlmostEqual(mapped(a,physical),physical,places=6)
            self.assertEqual(a.get(lane(11)+16),0)

    def test_varispeed_unity_and_recall_latest_explicit_action_wins(self):
        a=arm();a.uc.mem_write(VCTR,b'\1')
        publish(a,{11:25});mapped(a,.8)
        self.assertEqual(a.get(lane(11)+16),1)
        a.put(U+40,1);unity=mapped(a,.8)
        self.assertEqual(a.get(U+44),1)
        self.assertEqual(a.get(lane(11)+16),0)
        self.assertEqual(mapped(a,.7),unity)
        mapped(a,.5);self.assertEqual(a.get(U+44),0)
        a.put(U+40,1);mapped(a,.8)
        publish(a,{11:25});self.assertNotEqual(mapped(a,.8),unity)
        self.assertEqual(a.get(U+44),0)
        self.assertEqual(a.get(lane(11)+16),1)

    def test_varispeed_early_prepare_preserves_first_recall_until_next_block(self):
        a=arm();a.uc.mem_write(VUNI,b'\0\0')
        a.put(0x20001294,100);a.put(0x20021410,bits(1/3800))
        publish(a,{11:50})
        # A near-target physical position must not cause a second pickup when
        # the same block reaches the later pitch lookup.
        self.assertEqual(call(a,'preset_varispeed_prepare',2020),2000)
        self.assertEqual(mapped(a,(2020-100)/3800),.5)
        self.assertEqual(a.get(lane(11)+16),1)
        self.assertEqual(a.get(EXT+224+4*15),1)
        self.assertEqual(call(a,'preset_varispeed_prepare',2020),2020)
        self.assertAlmostEqual(mapped(a,(2020-100)/3800),(2020-100)/3800,places=6)
        self.assertEqual(a.get(lane(11)+16),0)
        self.assertEqual(a.get(EXT+224+4*15),0)

    def test_recall_applies_before_range_noon_and_scale_mapping(self):
        for centered in (0,1):
            for vsop in (0,1,2):
                for extended in (0,1):
                    a,b=arm(),arm()
                    for x in (a,b):
                        x.uc.mem_write(VCTR,bytes([centered]))
                        x.put(0x200012a8,vsop)
                        x.uc.mem_write(0x2002a606,bytes([extended]))
                    for percent in (0,25,50,75,100):
                        publish(a,{11:percent})
                        self.assertEqual(mapped(a,.15),mapped(b,percent/100),
                                         (centered,vsop,extended,percent))


@unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'),'real audio firmware required')
class MainPresetAudio(unittest.TestCase):
    def test_varispeed_audio_motion_history_and_pickup_keep_physical_adc(self):
        for quantized in (0,1):
            a,b=Audio(images()[1]),Audio(images()[1])
            for audio in (a,b):
                audio.a.put(0x200012a8,2)
                audio.a.uc.mem_write(0x2002a606,b'\1')
                audio.a.uc.mem_write(0x2002a610,bytes([quantized]))
                audio.a.put(0x20021c7c,0)
                audio.a.put(0x20001294,100)
                # This calibration represents exactly .5 at raw 2100. A
                # one-ULP-below midpoint may straddle a stock lookup boundary.
                audio.a.put(0x20021410,bits(1/4000))
            a.a.put(VS,2100);b.a.put(VS,500);publish(b.a,{11:50})
            for physical in (500,1500,1800):
                b.a.put(VS,physical)
                self.assertEqual(a.blocks(40),b.blocks(40),(quantized,physical))
                self.assertEqual(b.a.get(VS),physical)
                self.assertEqual(a.a.get(0x20024124),b.a.get(0x20024124))
                self.assertEqual(a.a.get(0x200220b0),b.a.get(0x200220b0))
                self.assertEqual(b.a.get(lane(11)+16),1)
            b.a.put(VS,2100)
            self.assertEqual(a.blocks(1),b.blocks(1))
            self.assertEqual(b.a.get(lane(11)+16),0)
            a.a.put(VS,2800);b.a.put(VS,2800)
            self.assertEqual(a.blocks(80),b.blocks(80))

    def test_sos_effective_position_matches_physical_mix_and_recording(self):
        for tape in (0,1):
            for recording in (False,True):
                a,b=Audio(images()[1]),Audio(images()[1])
                for audio in (a,b):
                    audio.a.uc.mem_write(0x2002a0f4,bytes([tape]))
                    audio.a.uc.mem_write(0x20028000,struct.pack('<32h',*([3000,-2000]*16)))
                    if recording:
                        audio.a.put(0x20021320,1);audio.a.put(0x20022108,1)
                        audio.a.put(0x20022114,1)
                        audio.a.uc.mem_write(MOD+16,b'\1');audio.a.put(MOD+20,bits(.75))
                a.a.put(SOS,target(65));b.a.put(SOS,500);publish(b.a,{10:65})
                self.assertEqual(a.blocks(240),b.blocks(240),(tape,recording))
                for base in (0xd0000000,0xd1000000):
                    self.assertEqual(a.uc.mem_read(base,96000),b.uc.mem_read(base,96000))
                self.assertEqual(a.a.get(0x20022114),b.a.get(0x20022114))

    def test_varispeed_actual_lookup_with_unity_options_disabled_or_enabled(self):
        for center,vsop,extended,vqnt in ((0,0,0,0),(0,2,1,1),(1,0,1,0),(1,2,1,1)):
            for gene in (0,2000):
                a,b=Audio(images()[1]),Audio(images()[1])
                for audio in (a,b):
                    audio.a.uc.mem_write(VCTR,bytes([center]))
                    audio.a.put(0x200012a8,vsop)
                    audio.a.uc.mem_write(0x2002a606,bytes([extended]))
                    audio.a.uc.mem_write(0x2002a610,bytes([vqnt]))
                    audio.a.put(0x20021c7c,gene)
                    audio.a.put(0x20021410,bits(1/4000))
                a.a.put(VS,2000);b.a.put(VS,500);publish(b.a,{11:50})
                self.assertEqual(a.blocks(180),b.blocks(180),(center,vsop,extended,vqnt,gene))
                self.assertEqual(a.a.get(0x200220e8),b.a.get(0x200220e8))

if __name__=='__main__':unittest.main()
