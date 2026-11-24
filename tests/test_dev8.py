import math, os, unittest
from pathlib import Path
from tests.arm import *
from tests.test_firmware_integration import images
from tests.audio import Audio

MOD=0x2002A000
class Forward8(unittest.TestCase):
    def test_all_scale_positions_and_exact_octaves(self):
        a=Arm('shift_gestures','p1_session');a.put(MOD,0x53484654);a.put(0x2002A0F0,0x5354504f)
        a.put(0x200012a8,2);a.uc.mem_write(0x2002A606,b'\1');a.uc.mem_write(MOD+4,bytes([1,1,2,0]))
        for scale,mask in [(1,1),(2,0x81),(3,0xfff),(4,0x4a9)]:
            a.uc.mem_write(0x2002A0F5,bytes([scale]));a.uc.mem_write(0x2002A604,struct.pack('<H',mask&~1))
            choices=[0]+[4+4*n for n in range(85) if mask>>(n%12)&1];seen=set()
            for adc in range(4096):
                x=f32(adc/4095);u=int(f32(x*6016))-256
                want=min(choices,key=lambda i:(abs(u-(16*i+8)),i))
                a.uc.mem_write(MOD+7,b'\0');a.uc.reg_write(UC_ARM_REG_S18,bits(x));a.uc.reg_write(UC_ARM_REG_R0,1000)
                a.run('p5_octave',[0x08027882,0x08028824])
                got=struct.unpack('<H',a.uc.mem_read(MOD+12,2))[0];self.assertEqual(got,want,(scale,adc));seen.add(got)
                a.run('forward_lookup',[0x080278cc])
                rate=value(a.get(0x200220e8));self.assertEqual(rate,0 if not got else f32(2**((got-196)/48)))
                self.assertEqual(a.uc.reg_read(UC_ARM_REG_SP),SP)
            self.assertEqual(seen,set(choices))
            if scale==1:self.assertEqual({0 if not i else 2**((i-196)/48) for i in seen},{0,.0625,.125,.25,.5,1,2,4,8})
    def test_latched_forward_lock_and_release(self):
        a=Arm('shift_gestures','p1_session');a.put(MOD,0x53484654);a.put(0x2002A0F0,0x5354504f)
        a.put(0x200012a8,2);a.uc.mem_write(0x2002A606,b'\1');a.uc.mem_write(0x2002A0F5,b'\1')
        a.uc.mem_write(MOD+4,bytes([1,1,2,0]));a.uc.reg_write(UC_ARM_REG_S18,bits(.7));a.uc.reg_write(UC_ARM_REG_R0,1000)
        a.run('p5_octave',[0x8027882]);locked=a.uc.reg_read(UC_ARM_REG_S18)
        a.uc.mem_write(MOD+4,b'\0');a.put(0x20021c74,3000)
        for adc in [3000,3010,2990,3100]:
            a.put(0x20021c74,adc);a.uc.reg_write(UC_ARM_REG_S18,bits(.73));a.run('p5_octave',[0x8027882]);self.assertEqual(a.uc.reg_read(UC_ARM_REG_S18),locked)
        a.put(0x20021c74,3300);a.run('p5_octave',[0x8027882]);self.assertEqual(a.uc.mem_read(MOD+7,1),b'\0')

class DensityHooks(unittest.TestCase):
    def test_density_setting_parser(self):
        a=Arm('options_keys','opt_parse')
        for line,expect in [('dens 1',1),('dens 0',0),('dens 2',0),('dens 10',0),('dens x',0),('dens',0),('dens 1 // on',1)]:
            a.uc.mem_write(0x2002A607,b'\0');a.uc.mem_write(0x20002000,bytes(100));a.uc.mem_write(0x20002000,line.encode()+b'\0')
            a.uc.reg_write(UC_ARM_REG_R11,0x20002000);a.run('opt_parse',[0x80232fc]);self.assertEqual(a.uc.mem_read(0x2002A607,1),bytes([expect]))
    def test_density_knob_mapping_and_pickup(self):
        a=Arm('gene_shape','g2_size');a.put(MOD,0x53484654);a.uc.mem_write(0x2002A607,b'\1');a.put(0x200220e0,bits(1))
        a.uc.mem_write(MOD+4,bytes([1,1,4]));a.uc.mem_write(MOD+208,struct.pack('<H',2000))
        prev=480001
        for adc in range(4096):
            a.uc.reg_write(UC_ARM_REG_R0,adc);a.run('size_hold')
            self.assertEqual(a.uc.reg_read(UC_ARM_REG_R0),2000)
            interval = a.get(0x2002A808)
            if adc < 128:  # upward sweep from the stock-timing endpoint
                self.assertEqual(interval, 0)
                continue
            index = (max(0, adc-192)*128//1856 if adc < 2048
                     else min(3968, adc-64)*256//3968)
            want=round(480000*80**(-index/128)) if index<128 else round(96000*2**(-index/32))
            self.assertEqual(interval,want);self.assertLessEqual(interval,prev);prev=interval
        a.uc.mem_write(MOD+4,b'\0')
        for adc,expected in [(3000,2000),(2010,2010),(2500,2500)]:
            a.uc.reg_write(UC_ARM_REG_R0,adc);a.run('size_hold');self.assertEqual(a.uc.reg_read(UC_ARM_REG_R0),expected)
    def test_clock_bypass_and_tape_voice_limit(self):
        a=Arm('gene_shape','g2_size');a.put(0x2002A614,10);a.uc.mem_write(0x2002A607,b'\1');a.put(0x200220e0,bits(1));a.run('density_prepare');self.assertEqual(a.get(0x2002A804),1)
        a.put(0x20021cb0,1);a.run('density_prepare');self.assertEqual(a.get(0x2002A804),0)
        a.put(0x20021cb0,0);a.put(0x200220e0,0);a.run('density_prepare');self.assertEqual(a.get(0x2002A804),0)
        a.put(0x200220e0,bits(8));a.put(0x20022108,1);a.uc.mem_write(MOD+16,b'\1');a.uc.mem_write(0x2002A0F4,b'\1');a.uc.mem_write(0x2002A0F9,b'\3')
        a.run('density_prepare');self.assertEqual(a.get(0x2002A810),2)

class Tape8(unittest.TestCase):
    def test_real_tape_engine_reaches_eight_and_wraps(self):
        for speed in [0,.5,1,4,8,-8,12]:
            a=Arm('tape_sos','eng_prepare');a.put(MOD,0x53484654);a.uc.mem_write(MOD+16,b'\1');a.put(MOD+20,bits(.5))
            for adr,n in {0x2002A0F0:0x5354504f,0x20022114:1,0x2002208c:1,0x2002215c:10,0x20022160:90,0x20021f90:bits(32),0x20022154:0,0x200220e0:bits(speed),0x200220fc:0xd0000000,0x20022100:0xd0010000}.items():a.put(adr,n)
            a.uc.mem_write(0x2002A0F4,b'\1');a.uc.mem_write(0xd0000000,b'\xe8\x03'*128);a.uc.mem_write(0xd0010000,b'\xe8\x03'*128)
            a.uc.reg_write(UC_ARM_REG_R0,0);a.uc.reg_write(UC_ARM_REG_R1,0);a.run('eng_prepare')
            rate=max(-8,min(8,speed));self.assertEqual(value(a.get(MOD+60)),rate)
            a.uc.mem_write(MOD+88,b'\x08');a.uc.mem_write(MOD+0x90,bytes(64));a.run('eng_flush',count=100000)
            self.assertEqual(a.get(MOD+32),10+int(8*rate)%32)
            left=struct.unpack('<128h',a.uc.mem_read(0xd0000000,256));self.assertEqual(left[:10],(1000,)*10);self.assertEqual(left[42:],(1000,)*86)
            if speed==8:self.assertEqual(left[10:42],(250,)*32)
            if speed==0:self.assertEqual(left,(1000,)*128)

@unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'),'requires official firmware')
class AudioIntegration(unittest.TestCase):
    def test_density_spacing_independent_of_pitch_and_morph(self):
        image=images()[1]
        for adc,morph in [(2600,420),(3500,2000),(4095,4000)]:
            a=Audio(image);a.a.put(0x2002A614,80);a.uc.mem_write(0x2002A607,b'\1');a.a.put(0x20021c74,adc);a.a.put(0x20021c6c,morph);a.blocks(2400)
            self.assertGreaterEqual(len(a.births),4)
            self.assertEqual([y-x for x,y in zip(a.births,a.births[1:])],[6000]*(len(a.births)-1),(adc,morph,a.births))
    def test_forward_audio_reaches_eight_and_stops(self):
        a=Audio(images()[1]);a.a.put(0x200012a8,2);a.uc.mem_write(0x2002A606,b'\1');a.uc.mem_write(0x2002A607,b'\1')
        a.a.put(0x20021c74,4095);a.blocks(800)
        self.assertEqual(value(a.a.get(0x200220e8)),8)
        self.assertEqual(value(a.a.get(0x200220e0)),8)
        a.a.put(0x20021c74,0);a.blocks(800)
        self.assertEqual(value(a.a.get(0x200220e8)),0)
        self.assertEqual(value(a.a.get(0x200220e0)),0)
        self.assertEqual(a.a.get(0x2002A804),0)

    def test_dense_long_grains_defer_busy_voices(self):
        a=Audio(images()[1]);a.uc.mem_write(0x2002A607,b'\1');a.blocks(4);a.a.put(0x2002A808,375);a.a.put(0x2002A80c,375)
        a.a.put(0x20021c6c,3500);a.blocks(3000)
        self.assertEqual(a.a.get(0x20022088),4);self.assertIn('B',a.paths)
        self.assertGreater(len(a.births),10)
        self.assertTrue(any(y-x>375 for x,y in zip(a.births,a.births[1:])))
    def test_short_genes_at_eight_with_playback_and_tape_recording(self):
        for recording in [False,True]:
            a=Audio(images()[1]);a.a.put(0x200012a8,2);a.uc.mem_write(0x2002A606,b'\1');a.uc.mem_write(0x2002A607,b'\1')
            a.a.put(0x20021c74,4095);a.a.put(0x20021c7c,4095);a.a.put(0x20021c6c,4000);a.blocks(300)
            a.a.put(0x2002A808,375);a.a.put(0x2002A80c,375)
            if recording:
                # Stock UI sets the record request latch as well as REC_ACTIVE.
                # Without it the stock stop logic correctly ends the take.
                a.a.put(0x20021320,1)
                a.a.put(0x20022108,1);a.a.put(0x20022114,1);a.uc.mem_write(MOD+16,b'\1');a.a.put(MOD+20,bits(.75))
                before=bytes(a.uc.mem_read(0xd0000000,96000))
            a.blocks(1000)
            self.assertEqual(value(a.a.get(0x200220e0)),8)
            self.assertGreater(len(a.births),15)
            if recording:
                self.assertEqual(a.a.get(0x20022108),1)
                self.assertEqual(a.a.get(0x2002A810),2)
                self.assertGreaterEqual(a.a.get(0x2002210c),0)
                self.assertLess(a.a.get(0x2002210c),48000)
                self.assertNotEqual(bytes(a.uc.mem_read(0xd0000000,96000)),before)
                a.a.put(0x20021320,0);a.blocks(2)
                self.assertEqual(a.a.get(0x20022108),0)

    def test_density_disabled_matches_prior_firmware_audio(self):
        path=os.environ.get('MGMOD_PREVIOUS')
        if not path:self.skipTest('MGMOD_PREVIOUS optional prior 4x image')
        image=images()[1];prior=Path(path).read_bytes()
        for morph in [0,420,2000,4000]:
            a=Audio(image);b=Audio(prior)
            for x in [a,b]:x.a.put(0x20021c6c,morph);x.uc.mem_write(0x2002A606,b'\1')
            self.assertEqual(a.blocks(1200),b.blocks(1200),morph)
            self.assertEqual(a.births,b.births)
