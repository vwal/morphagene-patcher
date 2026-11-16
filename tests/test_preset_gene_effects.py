"""Development 8 secondary Gene presets use the ordinary SHIFT effect curves."""
import os
import unittest
from tests.arm import *
from tests.audio import Audio
from tests.test_firmware_integration import images

P,E,MOD=0x2002a660,0x2002ae90,0x2002a000
JITTER,EVOLUTION,RATE=5,8,9
ADC={JITTER:0x20021c78,EVOLUTION:0x20021c70,RATE:0x20021c7c}
OWNER={JITTER:5,EVOLUTION:6,RATE:4}
RATES=(1,2,3,4,6,8,12,16)

def lane(key):return E+32+(key-4)*24
def target(percent):return (percent*4095+50)//100

def publish(a,values):
    a.put(P,0x54535250)
    a.put(P+8,sum(1<<key for key in values))
    for key,value in values.items():a.put(E+(key-4)*4,value)
    a.put(P+4,a.get(P+4)+1)

def arm():
    a=Arm('gene_shape','g2_size')
    a.put(MOD,0x53484654);a.put(0x2002a0f0,0x5354504f)
    a.uc.mem_write(0x2002a0fa,b'\1')
    a.put(0x20022078,4095);a.put(0x200220a0,bits(1/4095))
    a.put(0x200220ac,200)
    return a

def hook(a,key,physical,editing=False):
    a.put(ADC[key],physical)
    a.uc.mem_write(MOD+4,bytes([1,1,OWNER[key]]) if editing else bytes(3))
    if key==JITTER:
        a.uc.reg_write(UC_ARM_REG_R6,0x20021c68)
        a.run('gs_slide',[0x8027978])
    elif key==EVOLUTION:
        a.uc.reg_write(UC_ARM_REG_R4,0x20021c68)
        a.run('o1_organize',[0x80276f4])
    else:
        a.uc.reg_write(UC_ARM_REG_R0,physical)
        a.run('size_hold')

def effect(a,key):
    if key==JITTER:return a.get(MOD+224)
    if key==EVOLUTION:return a.get(0x2002a74c)
    return bytes(a.uc.mem_read(0x2002a755,2))

class GeneEffectPresets(unittest.TestCase):
    def test_percent_presets_exactly_match_stock_shift_effect_curves(self):
        for key in (JITTER,EVOLUTION):
            for percent in range(101):
                reference,recalled=arm(),arm()
                hook(reference,key,target(percent),True)
                publish(recalled,{key:percent});hook(recalled,key,4095 if percent==0 else 0)
                self.assertEqual(effect(recalled,key),effect(reference,key),(key,percent))
                self.assertEqual(recalled.get(lane(key)+16),1)
                self.assertEqual(recalled.get(lane(key)+12),target(percent))

    def test_secondary_pickup_requires_own_shift_gesture_and_missing_key_preserves_it(self):
        for key in (JITTER,EVOLUTION):
            a=arm();publish(a,{key:75});hook(a,key,0)
            recalled=effect(a,key)
            hook(a,key,4095)
            self.assertEqual(effect(a,key),recalled)
            self.assertEqual(a.get(lane(key)+16),1)
            publish(a,{RATE:4} if key!=RATE else {JITTER:20})
            hook(a,key,0)  # return the primary knob before starting its SHIFT edit
            hook(a,key,1000,True)
            self.assertEqual(effect(a,key),recalled)
            self.assertEqual(a.get(lane(key)+16),1)
            hook(a,key,target(75),True)
            self.assertEqual(a.get(lane(key)+16),0)
            hook(a,key,3500,True);manual=effect(a,key)
            hook(a,key,0)
            self.assertEqual(effect(a,key),manual)
            publish(a,{key:75});hook(a,key,0)
            self.assertEqual(effect(a,key),recalled)
            self.assertEqual(a.get(lane(key)+16),1)

    def test_inactive_evolution_recalls_before_later_turing_initialization(self):
        a=arm();a.uc.mem_write(0x2002a0fa,b'\0')
        publish(a,{EVOLUTION:0});hook(a,EVOLUTION,3500)
        self.assertEqual(a.get(0x2002a740),0x474e5254)
        self.assertEqual(effect(a,EVOLUTION),bits(0))
        a.uc.mem_write(0x2002a0fa,b'\1');a.run('preset_turing_init')
        self.assertEqual(effect(a,EVOLUTION),bits(0))
        hook(a,EVOLUTION,1000,True)
        self.assertEqual(effect(a,EVOLUTION),bits(0),'far physical edit remains held')
        hook(a,EVOLUTION,56,True)
        self.assertEqual(a.get(lane(EVOLUTION)+16),0)

    def test_all_turing_rates_pick_up_by_zone_and_keep_hysteresis(self):
        for zone,rate in enumerate(RATES):
            a=arm();publish(a,{RATE:rate});hook(a,RATE,4095 if zone==0 else 0)
            self.assertEqual(effect(a,RATE),bytes([zone,rate]))
            hook(a,RATE,4095 if zone==0 else 0)
            self.assertEqual(effect(a,RATE),bytes([zone,rate]),'ordinary Gene Size motion is not pickup')
            hook(a,RATE,zone*512+256,True)
            self.assertEqual(a.get(lane(RATE)+16),0)
            if zone<7:
                hook(a,RATE,(zone+1)*512+16,True)
                self.assertEqual(effect(a,RATE),bytes([zone,rate]),'stock32-count hysteresis remains')
                hook(a,RATE,(zone+1)*512+40,True)
                self.assertEqual(effect(a,RATE),bytes([zone+1,RATES[zone+1]]))
                hook(a,RATE,0)
                self.assertEqual(effect(a,RATE),bytes([zone+1,RATES[zone+1]]))

    def test_density_gesture_does_not_pick_up_turing_rate(self):
        a=arm();publish(a,{RATE:8});hook(a,RATE,0)
        a.uc.mem_write(0x2002a607,b'\1');a.put(0x2002a614,80)
        hook(a,RATE,2800,True)
        self.assertEqual(effect(a,RATE),bytes([5,8]))
        self.assertEqual(a.get(lane(RATE)+16),1)
        self.assertGreater(a.get(0x2002a808),0,'existing density gesture still runs')
        a.uc.mem_write(0x2002a607,b'\0');hook(a,RATE,2800,True)
        self.assertEqual(a.get(lane(RATE)+16),0)

@unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'),'requires official firmware')
class GeneEffectPresetAudio(unittest.TestCase):
    def test_recalled_effects_match_equivalent_manual_effects_in_real_audio(self):
        for jitter,evolution,rate in ((0,0,1),(45,50,8),(100,100,16)):
            manual=arm()
            hook(manual,JITTER,target(jitter),True)
            hook(manual,EVOLUTION,target(evolution),True)
            hook(manual,RATE,RATES.index(rate)*512+256,True)
            reference,recalled=Audio(images()[1]),Audio(images()[1])
            for a in (reference,recalled):
                a.uc.mem_write(0x2002a0fa,b'\1')
                a.a.put(0x20021c6c,1000);a.a.put(0x20021c7c,2000)
                a.a.put(0x20021c78,0)
            reference.a.put(MOD+224,manual.get(MOD+224))
            reference.uc.mem_write(0x2002a740,bytes(manual.uc.mem_read(0x2002a740,192)))
            publish(recalled.a,{JITTER:jitter,EVOLUTION:evolution,RATE:rate})
            self.assertEqual(recalled.blocks(600),reference.blocks(600),(jitter,evolution,rate))
            self.assertEqual(recalled.births,reference.births)
            self.assertEqual(recalled.a.get(MOD+224),reference.a.get(MOD+224))

if __name__=='__main__':unittest.main()
