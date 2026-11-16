"""Development 6: real Thumb/C helpers, stock TIM2 and audio integration."""
import os
import unittest
from pathlib import Path
from tests.arm import *
from tests.audio import Audio
from tests.fixtures import reference
from tests.test_quantized_default import setup, MOD, VQNT
from tests.test_firmware_integration import images
from tests import test_settings_reload as r

U = 0x2002a620
VUNI, VCTR = 0x2002a618, 0x2002a619
KNOBS = (0x20021c68,0x20021c74,0x20021c6c,0x20021c7c,0x20021c78,0x20021c70)

def arm():
    a=Arm('shift_gestures','p1_session')
    setup(a,0,0);a.uc.mem_write(VUNI,b'\1\0')
    a.put(0x20001020,14);a.put(r.CARD,1)
    for addr in KNOBS:a.put(addr,2048)
    return a

def button(a,now,shift=4,rec=0,splice=0):
    a.put(r.SAMPLES,now&0xffffffff)
    return r.call(a,'unity_buttons',shift,rec,splice)

def mapped(a,x):
    return value(r.call(a,'unity_map',bits(x)))

class UnityHelpers(unittest.TestCase):
    def test_half_second_boundary_and_rollover(self):
        for start in (0,123456,0xffffd000):
            for elapsed,want in ((23999,0),(24000,1),(48000,1),(240000,1)):
                a=arm();button(a,start);button(a,start+elapsed,shift=0)
                self.assertEqual(a.get(U+40),want,(start,elapsed))
                self.assertEqual(a.uc.mem_read(MOD+5,2),b'\1\10' if want else b'\0\0')
                self.assertEqual(a.get(r.REC_REQUEST),0)
                self.assertEqual(a.get(0x200012e0),0)

    def test_every_knob_cancels_until_release_even_when_secondary_option_off(self):
        for vqnt in (0,1):
            for i,addr in enumerate(KNOBS):
                a=arm();a.uc.mem_write(VQNT,bytes([vqnt]))
                a.uc.mem_write(0x2002a0f5,b'\0\0');button(a,100)
                threshold=96 if i==4 else 8 if i==1 and vqnt else 48
                a.put(addr,2048+threshold);button(a,24099)
                self.assertEqual(a.get(U),1)
                a.put(addr,2049+threshold);button(a,24100)
                a.put(addr,2048);button(a,100000);button(a,100032,shift=0)
                self.assertEqual(a.get(U+40),0,(vqnt,i))

    def test_buttons_states_card_and_reload_cancel(self):
        for kind in ('rec','splice','reel','delete','card','mount','owned','pending','gesture'):
            a=arm();button(a,0)
            if kind in ('rec','splice'):
                button(a,100,rec=1 if kind=='rec' else 0,splice=1 if kind=='splice' else 0)
            else:
                addresses={'reel':(0x20001020,16),'delete':(0x20001020,12),
                           'card':(r.CARD,0),'mount':(r.STATE+240,1),
                           'owned':(r.OWNED,1),'pending':(r.PENDING,1)}
                if kind=='gesture':a.uc.mem_write(MOD+4,b'\1\1\2')
                else:a.put(*addresses[kind])
                button(a,100)
            a.put(0x20001020,14);a.uc.mem_write(MOD+4,bytes(3))
            button(a,50000,shift=0)
            self.assertEqual(a.get(U+40),0,kind)
        a=arm();a.put(r.STATE+240,2)  # a normal mount already in progress
        button(a,0);a.put(r.STATE+240,0);button(a,50000,shift=0)
        self.assertEqual(a.get(U+40),0,'finishing the mount cannot rearm this hold')

    def test_disabled_option_and_recording_release(self):
        a=arm();a.uc.mem_write(VUNI,b'\0');button(a,0);button(a,48000,shift=0)
        self.assertEqual(a.get(U+40),0)
        a=arm();a.put(0x20001020,4);a.put(0x2002139c,1)
        button(a,0);button(a,24000,shift=0);self.assertEqual(a.get(U+40),1)

    def test_mapping_monotonic_endpoints_and_unity_detent(self):
        a=arm();a.uc.mem_write(VCTR,b'\1')
        for vqnt in (0,1):
            for vsop in (0,1,2):
                for extended in (0,1):
                    setup(a,vsop,extended);a.uc.mem_write(VQNT,bytes([vqnt]))
                    unity=f32(212.5/(376 if extended else 328) if vsop==2 else 344.5/400)
                    lower,upper=.48,.52
                    last=-1.
                    for adc in range(4096):
                        x=f32(adc/4095);got=mapped(a,x)
                        self.assertGreaterEqual(got,last,(vqnt,vsop,extended,adc))
                        self.assertGreaterEqual(got,0.);self.assertLessEqual(got,1.)
                        if lower<=x<=upper:self.assertEqual(got,unity)
                        last=got
                    self.assertEqual(mapped(a,0.),0.);self.assertEqual(mapped(a,1.),1.)

    def test_common_notch_joins_continuously_and_survives_shift(self):
        a=arm();a.uc.mem_write(VCTR,b'\1')
        for vsop in (0,1,2):
            for extended in (0,1):
                for vqnt,scale in ((0,0),(0,3),(1,0),(1,3)):
                    setup(a,vsop,extended,scale);a.uc.mem_write(VQNT,bytes([vqnt]))
                    unity=f32(212.5/(376 if extended else 328) if vsop==2 else 344.5/400)
                    lower,upper=.48,.52
                    for x in (lower,.49,.5,.51,upper):
                        got=mapped(a,x)
                        if lower<=x<=upper:self.assertEqual(got,unity,(vsop,extended,vqnt,scale,x))
                        else:self.assertNotEqual(got,unity)
                    self.assertAlmostEqual(mapped(a,lower-1e-6),unity,delta=2e-6)
                    self.assertAlmostEqual(mapped(a,upper+1e-6),unity,delta=2e-6)
        # A gesture does not shift the configured mapping under the knob
        # while temporarily locking/freeing pitch.
        for vqnt in (0,1):
            setup(a,0,0,3);a.uc.mem_write(VQNT,bytes([vqnt]))
            before=mapped(a,.49)
            a.uc.mem_write(MOD+4,bytes([1,1,2,0]));self.assertEqual(mapped(a,.49),before)
            a.uc.mem_write(MOD+4,bytes(4));self.assertEqual(mapped(a,.49),before)

    def test_wider_noon_zone_is_also_the_reset_pickup_zone(self):
        for side,edge in ((.2,.481),(.8,.519)):
            a=arm();a.uc.mem_write(VCTR,b'\1');a.uc.mem_write(VQNT,b'\0')
            a.put(U+40,1);mapped(a,side);self.assertEqual(a.get(U+44),1)
            mapped(a,edge);self.assertEqual(a.get(U+44),0)
            self.assertEqual(a.get(U+60),1,'pickup enters the exact +1x notch')

    def test_reset_holds_and_picks_up_from_either_side(self):
        for center in (0,1):
            for side in (0.,1.):
                a=arm();a.uc.mem_write(VCTR,bytes([center]));a.put(U+40,1)
                target=.5 if center else 344.5/400
                self.assertEqual(mapped(a,side),f32(344.5/400));self.assertEqual(a.get(U+44),1)
                mapped(a,(side+target)/2);self.assertEqual(a.get(U+44),1)
                mapped(a,target+.02 if side==0 else target-.02)
                self.assertEqual(a.get(U+44),0,'a crossing can come from knob or CV')
        a=arm();a.put(U+40,1);mapped(a,.2)
        a.uc.mem_write(VUNI,b'\0');self.assertEqual(mapped(a,.2),f32(.2))
        self.assertEqual(a.get(U+44),0)

    def test_pickup_at_unity_and_mode_change_while_held(self):
        a=arm();a.put(U+40,1);mapped(a,.2)
        a.uc.mem_write(VCTR,b'\1');mapped(a,.2)
        self.assertEqual(a.get(U+44),1)
        mapped(a,.5);self.assertEqual(a.get(U+44),0)
        a.put(U+40,1);mapped(a,.5);self.assertEqual(a.get(U+44),1)
        mapped(a,.5);self.assertEqual(a.get(U+44),0)

    def test_new_option_parsers_writer_and_atomic_reload(self):
        for key,addr in (('vuni',VUNI),('vctr',VCTR)):
            a=Arm('options_keys','opt_parse')
            for text,want in ((f'{key} 1',1),(f'{key} 0 // off',0),(f'{key} 2',0),
                              (f'{key} 10',0),(f'{key} -1',0),(key,0)):
                a.uc.mem_write(addr,b'\0');a.uc.mem_write(0x20002000,bytes(128))
                a.uc.mem_write(0x20002000,text.encode()+b'\0');a.uc.reg_write(UC_ARM_REG_R11,0x20002000)
                a.run('opt_parse',[0x080232fc]);self.assertEqual(a.uc.mem_read(addr,1),bytes([want]))
            for text,want in ((f'{key} 1',1),(f'{key} 0',1),(f'{key} 2',0),(f'{key} 1\n{key} 0',0)):
                a=r.arm();r.stage(a,('header\n'+text+'\n').encode());r.call(a,'reload_commit')
                self.assertEqual(a.get(r.RESULT),1 if want else 2,text)
        a=r.arm();a.uc.mem_write(VUNI,b'\1\1');r.stage(a,b'header\noctl 3\n');r.call(a,'reload_commit')
        self.assertEqual(a.uc.mem_read(VUNI,2),b'\1\1','missing keys retain their values')
        a=r.arm();r.stage(a,b'header\nvuni 1\nvctr 1\n')
        self.assertEqual(a.uc.mem_read(VUNI,2),b'\0\0')
        r.call(a,'reload_commit');self.assertEqual(a.uc.mem_read(VUNI,2),b'\1\1')
        a=Arm('options_keys','opt_parse');a.uc.mem_write(VUNI,b'\1\1');seen={}
        def printf(a):
            p=a.uc.reg_read(UC_ARM_REG_R1);key=bytes(a.uc.mem_read(p,4)).decode()
            seen[key]=a.uc.reg_read(UC_ARM_REG_R2)
        a.calls={0x08034804:printf,0x080327a8:lambda a:None};a.run('opt_write',[0x08024566])
        self.assertEqual([seen['vuni'],seen['vctr']],[1,1])

    def test_c_wrappers_preserve_registers_flags_and_stack(self):
        for symbol in ('unity_button_hook','unity_map_hook'):
            a=arm();regs=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,
                         UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,
                         UC_ARM_REG_R8,UC_ARM_REG_R9,UC_ARM_REG_R10,UC_ARM_REG_R11,UC_ARM_REG_R12]
            for i,reg in enumerate(regs):a.uc.reg_write(reg,0x12340000+i)
            for i in range(32):a.uc.reg_write(UC_ARM_REG_S0+i,bits(i+.25))
            # Seed FPSCR via a real VMSR. Unicorn's direct register write alone
            # does not establish the active FP context before its first VPUSH.
            a.syms['fp_seed']=0x0805ff00
            a.uc.mem_write(0x0805ff00,bytes.fromhex('e1ee100a7047'))
            saved=a.uc.reg_read(UC_ARM_REG_R0)
            a.uc.reg_write(UC_ARM_REG_R0,0x01000010);a.run('fp_seed')
            a.uc.reg_write(UC_ARM_REG_R0,saved)
            a.uc.reg_write(UC_ARM_REG_APSR,0xa8000000)
            a.run(symbol)
            for i,reg in enumerate(regs):self.assertEqual(a.uc.reg_read(reg),0x12340000+i)
            for i in range(32):self.assertEqual(a.uc.reg_read(UC_ARM_REG_S0+i),bits(i+.25))
            self.assertEqual(a.uc.reg_read(UC_ARM_REG_APSR)&0xf8000000,0xa8000000)
            self.assertEqual(a.uc.reg_read(UC_ARM_REG_FPSCR),0x01000010)
            self.assertEqual(a.uc.reg_read(UC_ARM_REG_SP),SP)

@unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'),'requires official firmware')
class UnityIntegration(unittest.TestCase):
    def timer(self,enabled=1):
        h=r.ReloadIntegration();a=h.timer(images()[1]);a.put(r.CARD,1)
        a.uc.mem_write(VUNI,bytes([enabled,0]))
        a.uc.mem_write(0x2002a0f5,b'\1\1')
        for addr in KNOBS:a.put(addr,2048)
        return h,a

    def press(self,h,a):
        for _ in range(10):h.timer_tick(a,True)

    def release(self,h,a):
        for _ in range(10):h.timer_tick(a,False)

    def test_real_timer_short_tap_long_release_and_second_hold(self):
        h,a=self.timer();self.press(h,a);self.release(h,a)
        self.assertEqual(a.get(0x200012e0),1);self.assertEqual(a.get(U+40),0)
        for _ in range(1000):h.timer_tick(a,False)
        a.put(0x200012e0,0)
        for _ in range(2):
            self.press(h,a);a.put(r.SAMPLES,a.get(r.SAMPLES)+24000);h.timer_tick(a,True)
            self.assertEqual(a.get(U+40),0,'never reset while still held')
            self.release(h,a);self.assertEqual(a.get(U+40),1)
            self.assertEqual(a.get(0x200012e0),0,'reset release must not navigate')
            a.put(U+40,0)
            for _ in range(1000):h.timer_tick(a,False)

    def test_real_timer_existing_knob_gestures_cancel_reset(self):
        for index,addr in enumerate(KNOBS):
            h,a=self.timer();a.uc.mem_write(0x2002a607,b'\1');a.uc.mem_write(0x2002a0fa,b'\1')
            self.press(h,a);a.put(r.SAMPLES,a.get(r.SAMPLES)+48000);h.timer_tick(a,True)
            a.put(addr,2300);h.timer_tick(a,True)
            a.put(r.SAMPLES,a.get(r.SAMPLES)+48000);h.timer_tick(a,True);self.release(h,a)
            self.assertEqual(a.get(U+40),0,index)
            self.assertEqual(a.get(0x200012e0),0,index)

    def test_real_reload_after_long_hold_has_priority(self):
        h,a=self.timer();a.put(r.CARD,0)
        self.press(h,a);a.put(r.SAMPLES,a.get(r.SAMPLES)+48000);h.timer_tick(a,True)
        self.assertEqual(a.get(r.PHASE),2)
        a.syms['mounted']=0x08023136;a.uc.reg_write(UC_ARM_REG_R0,0)
        a.run('mounted',[0x08022f7e,0x0802313c,0x08023288])
        self.assertEqual(a.get(r.OWNED),1)
        a.put(r.PHASE,5);self.release(h,a)
        self.assertEqual(a.get(U+40),0);self.assertEqual(a.get(0x200012e0),0)

    def test_real_button_combinations_match_release_after_long_shift_wait(self):
        release=reference('rollback-mg204c/mg204-full.bin')
        h=r.ReloadIntegration()
        for button_gpio,mask in ((0x40021810,4096),(0x40021010,4)):
            for second_hold in (8000,160000):
                pair=[h.timer(release.read_bytes()),h.timer(images()[1])]
                for a in pair:
                    a.put(r.CARD,1);a.uc.mem_write(VUNI,b'\1')
                    for addr in KNOBS:a.put(addr,2048)
                    self.press(h,a);a.put(r.SAMPLES,a.get(r.SAMPLES)+48000);h.timer_tick(a,True)
                    a.put(button_gpio,mask)
                    for _ in range(10):h.timer_tick(a,True)
                    a.put(r.SAMPLES,a.get(r.SAMPLES)+second_hold);h.timer_tick(a,True)
                    a.put(button_gpio,0);self.release(h,a)
                self.assertEqual(pair[0].uc.mem_read(0x20000000,0x243c8),
                                 pair[1].uc.mem_read(0x20000000,0x243c8),
                                 (button_gpio,second_hold))
                self.assertEqual(pair[1].get(U+40),0)

    def test_real_timer_reset_during_recording_consumes_only_navigation(self):
        h,a=self.timer();a.put(0x20001020,4);a.put(r.REC,1);a.put(r.REC_REQUEST,1)
        self.press(h,a);a.put(r.SAMPLES,a.get(r.SAMPLES)+24000);h.timer_tick(a,True)
        self.release(h,a)
        self.assertEqual(a.get(U+40),1);self.assertEqual(a.get(0x200012e0),0)
        self.assertEqual(a.get(r.REC),1);self.assertEqual(a.get(r.REC_REQUEST),1)

    def test_reset_audio_preserves_reel_and_splice_metadata(self):
        a=Audio(images()[1]);setup(a.a,0,1,0);a.uc.mem_write(VUNI,b'\1')
        a.a.put(KNOBS[1],1000);a.blocks(100)
        addresses=(0x20001040,0x200012a0,0x20001064,0x2002215c,0x2002208c,0x20022160)
        before=[a.a.get(p) for p in addresses]
        a.a.put(U+40,1);a.blocks(1)
        self.assertEqual([a.a.get(p) for p in addresses],before)
        self.assertEqual(value(a.a.get(0x200220e0)),1.)
        self.assertEqual(a.a.get(0x200012e0),0)

    def test_noon_and_endpoints_real_audio_all_modes(self):
        for vsop in (0,1,2):
            for extended in (0,1):
                for vqnt in (0,1):
                    for scale in range(5):
                        a=Audio(images()[1]);setup(a.a,vsop,extended,scale)
                        a.uc.mem_write(VQNT,bytes([vqnt]));a.uc.mem_write(VCTR,b'\1')
                        endpoints=((4095,(8 if extended else 4) if vsop==2 else (4 if extended else 2)),
                                   (2048,1),(0,0 if vsop==2 else (-4 if extended else -2)))
                        for adc,want in endpoints:
                            a.a.put(KNOBS[1],adc);a.uc.mem_write(MOD+4,bytes(4));a.blocks(3)
                            self.assertEqual(value(a.a.get(0x200220e8)),want,(vsop,extended,vqnt,scale,adc))
                            if adc==2048:self.assertEqual(value(a.a.get(0x200220e0)),1.)

    def test_wide_unquantized_notch_real_audio_all_layouts_and_ranges(self):
        for vsop in (0,1,2):
            for extended in (0,1):
                for vqnt,scale in ((0,0),(0,3),(1,0)):
                    a=Audio(images()[1]);setup(a.a,vsop,extended,scale)
                    a.uc.mem_write(VQNT,bytes([vqnt]));a.uc.mem_write(VCTR,b'\1')
                    # The stock vsop 1 table itself has a semitone-wide 1x
                    # plateau; move far enough beyond that for the exit check.
                    for adc in (1900,1966,2000,2048,2095,2129,2400,2129,1966,1900):
                        a.a.put(KNOBS[1],adc);a.blocks(2)
                        target=value(a.a.get(0x200220e8))
                        if 1966<=adc<=2129:
                            self.assertEqual(target,1.,(vsop,extended,vqnt,scale,adc))
                            self.assertEqual(value(a.a.get(0x200220e0)),1.)
                        else:self.assertNotEqual(target,1.,(vsop,extended,vqnt,scale,adc))

    def test_original_mapping_quantized_and_free_gesture_match_initial_dev6_audio(self):
        prior=reference('rollback-dev6-initial/mg204-full.bin')
        for vsop in (0,1,2):
            for extended in (0,1):
                for scale in (1,2,3,4):
                    a=Audio(images()[1]);b=Audio(prior.read_bytes())
                    for x in (a,b):
                        setup(x.a,vsop,extended,scale);x.uc.mem_write(VCTR,b'\0')
                    for adc in (500,1800,1980,2048,2110,2700,4095):
                        for x in (a,b):x.a.put(KNOBS[1],adc)
                        self.assertEqual(a.blocks(4),b.blocks(4),(vsop,extended,scale,adc))
                        self.assertEqual(a.a.get(0x200220e8),b.a.get(0x200220e8))
                    for owner in (2,0):
                        for x in (a,b):
                            x.uc.mem_write(MOD+4,bytes([int(owner!=0),int(owner!=0),owner,0]))
                            x.a.put(KNOBS[1],2000)
                        self.assertEqual(a.blocks(4),b.blocks(4),(vsop,extended,scale,owner))

    def test_real_audio_reset_and_pickup_across_ranges_scales_and_directions(self):
        for vsop in (0,1,2):
            for extended in (0,1):
                for center in (0,1):
                    for scale in (0,3,4):
                        for start in (0,4095):
                            a=Audio(images()[1]);setup(a.a,vsop,extended,scale)
                            a.uc.mem_write(VUNI,bytes([1,center]));a.a.put(KNOBS[1],start);a.blocks(3)
                            a.a.put(U+40,1);a.blocks(1)
                            self.assertEqual(value(a.a.get(0x200220e8)),1.)
                            self.assertEqual(value(a.a.get(0x200220e0)),1.)
                            self.assertEqual(a.a.get(U+44),1)
                            pickup=.5 if center else 212.5/(376 if extended else 328) if vsop==2 else 344.5/400
                            a.a.put(KNOBS[1],round((start+pickup*4095)/2));a.blocks(2)
                            self.assertEqual(value(a.a.get(0x200220e0)),1.)
                            a.a.put(KNOBS[1],round(pickup*4095));a.blocks(2)
                            self.assertEqual(a.a.get(U+44),0)
                            a.a.put(KNOBS[1],4095 if start==0 else 0);a.blocks(3)
                            self.assertNotEqual(value(a.a.get(0x200220e8)),1.)

    def test_disabled_audio_matches_release(self):
        release=reference('rollback-mg204c/mg204-full.bin')
        for vsop,extended,vqnt,density in ((0,0,0,0),(1,1,1,0),(2,0,1,0),(2,1,0,1)):
            a=Audio(images()[1]);b=Audio(release.read_bytes())
            for x in (a,b):
                setup(x.a,vsop,extended,3);x.uc.mem_write(VQNT,bytes([vqnt]))
                x.uc.mem_write(0x2002a607,bytes([density]))
            for adc in (3500,4095,2048,400):
                for x in (a,b):x.a.put(KNOBS[1],adc)
                self.assertEqual(a.blocks(100),b.blocks(100),(vsop,extended,vqnt,density,adc))
            self.assertEqual(a.births,b.births)

    def test_real_audio_rates_match_across_full_splice_and_gene_paths(self):
        # Gene Size <= 199 selects separate stock Varispeed lookup copies.
        # Every lookup/scale must agree across this boundary, including the
        # expanded forward-only table and squared bidirectional magnitudes.
        for vsop in (0,1,2):
            for extended in (0,1):
                for vqnt in (0,1):
                    for scale in range(5):
                        engines=[]
                        for gene_size in (0,199,200,2000):
                            a=Audio(images()[1]);setup(a.a,vsop,extended,scale)
                            a.uc.mem_write(VQNT,bytes([vqnt]))
                            a.a.put(KNOBS[3],gene_size);engines.append(a)
                        for adc in (0,500,1200,2048,2700,3500,4095):
                            rates=[]
                            for a in engines:
                                a.a.put(KNOBS[1],adc);a.blocks(2)
                                rates.append(value(a.a.get(0x200220e8)))
                            self.assertEqual(rates,[rates[-1]]*4,
                                             (vsop,extended,vqnt,scale,adc,rates))

    def test_real_audio_unity_and_endpoints_in_both_gene_size_paths(self):
        for vsop in (0,1,2):
            for extended in (0,1):
                for vqnt in (0,1):
                    for scale in range(5):
                        for gene_size in (0,199,200):
                            a=Audio(images()[1]);setup(a.a,vsop,extended,scale)
                            a.uc.mem_write(VQNT,bytes([vqnt]))
                            a.uc.mem_write(VUNI,b'\1\1');a.a.put(KNOBS[3],gene_size)
                            for adc,want in ((0,0 if vsop==2 else (-4 if extended else -2)),
                                             (2048,1),
                                             (4095,(8 if extended else 4) if vsop==2 else (4 if extended else 2))):
                                a.a.put(KNOBS[1],adc);a.blocks(2)
                                self.assertEqual(value(a.a.get(0x200220e8)),want,
                                                 (vsop,extended,vqnt,scale,gene_size,adc))
                            a.a.put(U+40,1);a.blocks(1)
                            self.assertEqual(value(a.a.get(0x200220e8)),1.)
                            self.assertEqual(value(a.a.get(0x200220e0)),1.)

    def test_standard_range_full_splice_audio_matches_release(self):
        release=reference('rollback-mg204c/mg204-full.bin')
        for vsop in (0,1,2):
            for gene_size in (0,199):
                a=Audio(images()[1]);b=Audio(release.read_bytes())
                for x in (a,b):
                    setup(x.a,vsop,0,3);x.a.put(KNOBS[3],gene_size)
                for adc in (0,2048,3500,4095):
                    for x in (a,b):x.a.put(KNOBS[1],adc)
                    self.assertEqual(a.blocks(10),b.blocks(10),(vsop,gene_size,adc))

if __name__=='__main__':unittest.main()

