import math, os, unittest
from pathlib import Path
from tests.arm import *
from tests.audio import Audio
from tests.test_firmware_integration import images

MOD, SETTINGS, RANGE, SCALE, VQNT = 0x2002A000, 0x2002A0F0, 0x2002A606, 0x2002A604, 0x2002A610
MASKS = {1:1, 2:0x81, 3:0xfff, 4:sum(1<<n for n in [0,3,5,7,10])}

def setup(a, vsop, extended, scale=1):
    a.put(MOD,0x53484654);a.put(SETTINGS,0x5354504f);a.put(0x200012a8,vsop)
    a.uc.mem_write(RANGE,bytes([extended]));a.uc.mem_write(VQNT,b'\1')
    a.uc.mem_write(SETTINGS+5,bytes([scale]));a.uc.mem_write(SCALE,struct.pack('<H',MASKS.get(scale,1)&~1))

def snap(a, adc):
    a.put(0x20021c74,adc);a.uc.reg_write(UC_ARM_REG_R0,1000)
    a.uc.reg_write(UC_ARM_REG_S18,bits(adc/4095))
    a.run('p5_octave',[0x8027882,0x8028824])
    return struct.unpack('<H',a.uc.mem_read(MOD+12,2))[0]

class QuantizedDefault(unittest.TestCase):
    def test_parser_validation(self):
        a=Arm('options_keys','opt_parse')
        for line,want in [('vqnt 1',1),('vqnt 0 // default',0),('vqnt 2',0),('vqnt 10',0),
                          ('vqnt -1',0),('vqnt x',0),('vqnt',0),('vqnt 1\r\n',1)]:
            a.uc.mem_write(VQNT,b'\0');a.uc.mem_write(0x20002000,bytes(128))
            a.uc.mem_write(0x20002000,line.encode()+b'\0');a.uc.reg_write(UC_ARM_REG_R11,0x20002000)
            a.run('opt_parse',[0x80232fc]);self.assertEqual(a.uc.mem_read(VQNT,1),bytes([want]),line)

    def test_all_positions_scales_and_ranges_without_shift(self):
        a=Arm('shift_gestures','p1_session')
        for vsop in (0,1,2):
            for extended in (0,1):
                for scale,mask in MASKS.items():
                    setup(a,vsop,extended,scale);a.uc.mem_write(MOD+4,bytes(4))
                    if vsop==2:
                        top=340 if extended else 292;factor=6016 if extended else 5248
                        candidates=[0]+[i for i in range(4,top+1,4) if mask>>(((i-196)//4)%12)&1]
                    else:
                        factor=6400;candidates=[]
                        for i in range(4,393,2 if extended else 4):
                            if i==200:candidates.append(i);continue
                            delta=i-200 if i>200 else 196-i
                            semi=(delta-144)/(2 if extended else 4)
                            if delta>0 and semi.is_integer() and mask>>(int(semi)%12)&1:candidates.append(i)
                    seen=set()
                    for adc in range(4096):
                        u=int(f32(f32(adc/4095)*factor))-(256 if vsop==2 else 0)
                        want=min(candidates,key=lambda i:(abs(u-(16*i+8)),i))
                        a.uc.mem_write(MOD+7,b'\0')
                        a.uc.reg_write(UC_ARM_REG_R9,0x13572468);a.uc.reg_write(UC_ARM_REG_R10,0x12345678)
                        got=snap(a,adc);seen.add(got)
                        self.assertEqual(got,want,(vsop,extended,scale,adc))
                        self.assertEqual(a.uc.mem_read(MOD+7,1),b'\1')
                        self.assertEqual(a.uc.reg_read(UC_ARM_REG_SP),SP)
                        self.assertEqual(a.uc.reg_read(UC_ARM_REG_R9),0x13572468)
                        self.assertEqual(a.uc.reg_read(UC_ARM_REG_R10),0x12345678)
                    self.assertEqual(seen,set(candidates))

    def test_hysteresis_bypass_release_and_other_gestures(self):
        a=Arm('shift_gestures','p1_session')
        for vsop in (0,1,2):
            for extended in (0,1):
                setup(a,vsop,extended);a.uc.mem_write(MOD+4,bytes(4))
                # Center of the 1x plateau: stock/extended bidirectional 86%, forward depends on range.
                unity=round(4095*((196.5+16)/(376 if extended else 328) if vsop==2 else .86125))
                locked=snap(a,unity)
                for delta in [1,-2,3,-1,0]:self.assertEqual(snap(a,unity+delta),locked)
                for owner in [0,1,3,4,5,6]:
                    a.uc.mem_write(MOD+4,bytes([1,int(owner!=0),owner,1]))
                    snap(a,unity+20);self.assertEqual(a.uc.mem_read(MOD+7,1),b'\1',owner)
                a.uc.mem_write(MOD+4,bytes([1,1,2,1]));snap(a,unity+75)
                self.assertEqual(a.uc.mem_read(MOD+7,1),b'\0')
                self.assertEqual(a.uc.reg_read(UC_ARM_REG_S18),bits((unity+75)/4095))
                a.put(SP+192,bits(.1));a.run('p6_glide',[0x8027be4]);self.assertEqual(a.get(SP+192),bits(.1))
                # Release without any further knob movement snaps immediately.
                a.uc.mem_write(MOD+4,b'\0');snap(a,unity+75)
                self.assertEqual(a.uc.mem_read(MOD+7,1),b'\1')
                a.run('p6_glide',[0x8027be4]);self.assertEqual(a.get(SP+192),bits(1))
                a.uc.mem_write(SETTINGS+5,b'\0');snap(a,unity)
                self.assertEqual(a.uc.mem_read(MOD+7,1),b'\0')
                self.assertEqual(a.uc.reg_read(UC_ARM_REG_S18),bits(unity/4095))

    def test_shift_claim_threshold_and_navigation(self):
        for inverse,threshold in [(0,48),(1,8)]:
            a=Arm('shift_gestures','p1_session');setup(a,2,1)
            a.uc.mem_write(VQNT,bytes([inverse]));a.put(0x20001020,14)
            for adr in (0x20021c68,0x20021c6c,0x20021c70,0x20021c74,0x20021c78,0x20021c7c):a.put(adr,2000)
            def session():
                a.uc.reg_write(UC_ARM_REG_R12,1);a.uc.reg_write(UC_ARM_REG_R2,0);a.uc.reg_write(UC_ARM_REG_R3,0)
                a.run('p1_session',[0x802486e])
            session();a.put(0x20021c74,2000+threshold);session()
            self.assertEqual(a.uc.mem_read(MOD+5,2),b'\0\0')
            # A plain tap still navigates.
            a.uc.reg_write(UC_ARM_REG_R12,0);a.run('p3_state14',[0x80251e0,0x80251e6])
            self.assertEqual(a.uc.reg_read(UC_ARM_REG_PC),0x80251e0)
            a.put(0x20021c74,2001+threshold);session()
            self.assertEqual(a.uc.mem_read(MOD+5,2),b'\1\2')
            a.uc.reg_write(UC_ARM_REG_R12,0);a.run('p3_state14',[0x80251e0,0x80251e6])
            self.assertEqual(a.uc.reg_read(UC_ARM_REG_PC),0x80251e6)
            # The recording-release path also suppresses navigation after a gesture.
            a.put(0x200012e0,0);a.uc.reg_write(UC_ARM_REG_R0,0x2002139c);a.uc.reg_write(UC_ARM_REG_R2,1)
            a.run('p4_record_tap',[0x80248fc]);self.assertEqual(a.get(0x200012e0),0)

@unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'),'requires official firmware')
class QuantizedAudio(unittest.TestCase):
    def test_real_audio_quantized_free_and_release_in_every_range(self):
        for vsop in (0,1,2):
            for extended in (0,1):
                a=Audio(images()[1]);setup(a.a,vsop,extended)
                adc=2850 if vsop==2 else 3500
                a.a.put(0x20021c74,adc);a.blocks(4)
                rate=value(a.a.get(0x200220e0));self.assertGreater(rate,0)
                self.assertAlmostEqual(math.log2(rate),round(math.log2(rate)),places=6)
                a.uc.mem_write(MOD+4,bytes([1,1,2,1]));a.blocks(600)
                free=value(a.a.get(0x200220e0));self.assertNotEqual(free,rate)
                self.assertEqual(a.uc.mem_read(MOD+7,1),b'\0')
                a.uc.mem_write(MOD+4,b'\0');a.blocks(2)
                self.assertEqual(value(a.a.get(0x200220e0)),rate)
                # Endpoints include stop and the exact top octave.
                a.a.put(0x20021c74,4095);a.blocks(2)
                self.assertEqual(value(a.a.get(0x200220e0)),(8 if extended else 4) if vsop==2 else (4 if extended else 2))
                a.a.put(0x20021c74,0 if vsop==2 else 2048);a.blocks(2)
                self.assertEqual(value(a.a.get(0x200220e0)),0)

    def test_disabled_matches_development2_audio(self):
        path=os.environ.get('MGMOD_DEV2')
        if not path:self.skipTest('set MGMOD_DEV2 to prior development image')
        prior=Path(path).read_bytes()
        for vsop,extended,density in [(0,0,0),(1,1,0),(2,1,0),(2,1,1)]:
            a=Audio(images()[1]);b=Audio(prior)
            for x in (a,b):
                x.a.put(0x2002A614, 80)  # match Development 2 density
                x.a.put(0x200012a8,vsop);x.uc.mem_write(RANGE,bytes([extended]));x.uc.mem_write(0x2002A607,bytes([density]))
            self.assertEqual(a.blocks(900),b.blocks(900),(vsop,extended,density))
            self.assertEqual(a.births,b.births)
