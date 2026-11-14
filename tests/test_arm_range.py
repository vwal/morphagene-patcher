import math, random, unittest
from tests.arm import *

MOD, SETTINGS, RANGE, SCALE = 0x2002A000, 0x2002A0F0, 0x2002A606, 0x2002A604

class RangeHooks(unittest.TestCase):
    def test_rate_conversion_and_index_resolution(self):
        a=Arm('shift_gestures','p1_session')
        for extended in (0,1):
            a.uc.mem_write(RANGE,bytes([extended]))
            for mode in (0,1):
                for raw in range(400):
                    a.uc.reg_write(UC_ARM_REG_R5,raw)
                    a.uc.reg_write(UC_ARM_REG_R1,raw & ~(1 if mode==0 else 3))
                    a.run('range_index',[0x0802AAC8])
                    self.assertEqual(a.uc.reg_read(UC_ARM_REG_R1),raw & ~(1 if extended or mode==0 else 3))
                    self.assertEqual(a.get(SP+128),0x200220E8)
            for rate in [0,.125,.25,.5,1,2]+[f32(2**(i/48)) for i in range(-143,49)]:
                a.put(0x20001000,bits(rate))
                a.uc.reg_write(UC_ARM_REG_R11,0x20001000)
                a.uc.reg_write(UC_ARM_REG_R1,0x20001000)
                a.run('range_forward',[0x0802AAE0])
                expected=bits(f32(rate*rate)) if extended else bits(rate)
                self.assertEqual(a.uc.reg_read(UC_ARM_REG_R6),expected)
                a.run('range_reverse',[0x0802AD0A])
                self.assertEqual(a.uc.reg_read(UC_ARM_REG_S31),expected)
                self.assertEqual(a.uc.reg_read(UC_ARM_REG_SP),SP)

    def test_scale_sweeps_against_musical_model(self):
        a=Arm('shift_gestures','p1_session')
        a.put(MOD,0x53484654);a.put(SETTINGS,0x5354504F)
        a.uc.mem_write(MOD+4,bytes([1,1,2,0]))
        a.put(0x200012A8,0)
        masks={1:1,2:0x81,3:0xFFF,4:sum(1<<n for n in [0,3,5,7,10])}
        for extended in (0,1):
            a.uc.mem_write(RANGE,bytes([extended]))
            for mode,mask in masks.items():
                a.uc.mem_write(SETTINGS+5,bytes([mode]));a.uc.mem_write(SCALE,struct.pack('<H',mask&~1))
                candidates=[]
                for m in range(4,393,2 if extended else 4):
                    if m==200: candidates.append(m);continue
                    i=(m-200) if m>200 else (196-m)
                    if i<=0:continue
                    semi=(i-144)/(2 if extended else 4)
                    if semi.is_integer() and mask & (1<<(int(semi)%12)):candidates.append(m)
                seen=set()
                for adc in range(4096):
                    x=f32(adc/4095);u=math.trunc(f32(x*6400))
                    expected=min(candidates,key=lambda m:(abs(u-(m*16+8)),m))
                    a.uc.mem_write(MOD+7,b'\0')
                    a.uc.reg_write(UC_ARM_REG_R0,1000)
                    a.uc.reg_write(UC_ARM_REG_S18,bits(x))
                    a.uc.reg_write(UC_ARM_REG_R8,0x12345678)
                    a.run('p5_octave',[0x08027882,0x08028824])
                    actual=struct.unpack('<H',a.uc.mem_read(MOD+12,2))[0]
                    self.assertEqual(actual,expected,(extended,mode,adc))
                    self.assertEqual(a.uc.reg_read(UC_ARM_REG_R8),0x12345678)
                    self.assertEqual(a.uc.reg_read(UC_ARM_REG_SP),SP)
                    seen.add(actual)
                self.assertEqual(seen,set(candidates))
                if mode==1:self.assertEqual(len(seen),17 if extended else 9)

    def test_forward_only_bypasses_scale_lock(self):
        a=Arm('shift_gestures','p1_session');a.put(MOD,0x53484654)
        a.put(0x200012A8,2);a.uc.mem_write(MOD+4,bytes([1,1,2,0]))
        a.uc.mem_write(RANGE,b'\0');a.uc.reg_write(UC_ARM_REG_R0,1000)
        a.uc.reg_write(UC_ARM_REG_S18,bits(.9))
        a.run('p5_octave',[0x08027882,0x08028824])
        self.assertEqual(a.uc.reg_read(UC_ARM_REG_S18),bits(.9))

    def test_hysteresis_sweep_and_pickup(self):
        a=Arm('shift_gestures','p1_session');a.put(MOD,0x53484654);a.put(SETTINGS,0x5354504F)
        a.put(0x200012A8,1)
        for extended in (0,1):
            a.uc.mem_write(RANGE,bytes([extended]));a.uc.mem_write(SETTINGS+5,b'\3')
            a.uc.mem_write(MOD+4,bytes([1,1,2,0]));seen=[]
            for adc in range(4096):
                a.uc.reg_write(UC_ARM_REG_R0,1000);a.uc.reg_write(UC_ARM_REG_S18,bits(adc/4095))
                a.run('p5_octave',[0x08027882,0x08028824])
                m=struct.unpack('<H',a.uc.mem_read(MOD+12,2))[0]
                if not seen or m!=seen[-1]:seen.append(m)
            self.assertEqual(seen,sorted(seen));self.assertEqual(len(seen),193 if extended else 97)
            # Release, retain the locked rate through small ADC movement, then pick up.
            a.uc.mem_write(MOD+4,b'\0');a.put(0x20021C74,1000)
            a.run('p5_octave',[0x08027882,0x08028824])
            a.put(0x20021C74,1020);a.run('p5_octave',[0x08027882,0x08028824])
            self.assertEqual(a.uc.mem_read(MOD+7,1),b'\1')
            a.put(0x20021C74,1000+(115 if extended else 231)+1)
            a.uc.reg_write(UC_ARM_REG_S18,bits(.7));a.run('p5_octave',[0x08027882,0x08028824])
            self.assertEqual(a.uc.mem_read(MOD+7,1),b'\0')
            self.assertEqual(a.uc.reg_read(UC_ARM_REG_S18),bits(.7))
