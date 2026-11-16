"""Development 8: selected-splice clamping, Organize pickup and stock omod."""
import os
import unittest
from tests.arm import *
from tests.audio import Audio
from tests.test_firmware_integration import images

P=0x2002a660
L=P+32+3*24
REQUEST,COUNT,ACTIVE=0x20021cbc,0x2002208c,0x20021de4
ORG,ACCEPTED=0x20021c70,0x200220ac

def publish(a, selected, generation=1, mask=8):
    a.put(P,0x54535250);a.put(P+8,mask);a.put(P+12,mask)
    a.put(P+16+3*4,selected);a.put(P+4,generation)

def setup(a,count=3):
    for address,value in {COUNT:count,REQUEST:1,ORG:200,ACCEPTED:200,
        0x20022080:0,0x20022078:4095,0x200220a0:bits(1/4095),
        0x20001040:1,0x2002a000:0x53484654}.items():a.put(address,value)

def organize(a,physical=None,effective=None):
    if physical is not None:a.put(ORG,physical)
    if effective is None:effective=a.get(ORG)
    a.uc.reg_write(UC_ARM_REG_R0,effective)
    a.run('preset_organize')
    return a.uc.reg_read(UC_ARM_REG_R0)

class PresetSpliceHelpers(unittest.TestCase):
    def test_no_preset_is_identity_and_missing_key_keeps_live_selection(self):
        a=Arm('gene_shape','g2_size');setup(a)
        for adc in (0,200,2048,4095):self.assertEqual(organize(a,adc),adc)
        publish(a,3);self.assertEqual(organize(a,200),200)
        self.assertEqual(a.get(REQUEST),3);self.assertEqual(a.get(L+16),1)
        publish(a,1,2,mask=0)
        self.assertEqual(organize(a,1000),200)
        self.assertEqual(a.get(REQUEST),3);self.assertEqual(a.get(L+16),1)

    def test_pickup_uses_current_splice_cell_and_crossing(self):
        for count,selected,first,last in ((3,3,200,3500),(300,150,0,2041),
                                         (300,150,0,4095),(3,1,4095,0)):
            a=Arm('gene_shape','g2_size');setup(a,count)
            publish(a,selected);self.assertEqual(organize(a,first),first)
            self.assertEqual(a.get(REQUEST),selected)
            self.assertEqual(organize(a,last),last)
            self.assertEqual(a.get(L+16),0,(count,selected,first,last))

    def test_navigation_moves_pickup_target_without_recalling_old_splice(self):
        a=Arm('gene_shape','g2_size');setup(a);publish(a,3);organize(a,200)
        a.put(REQUEST,2)  # stock SHIFT navigation writes this request itself
        self.assertEqual(organize(a,200),200)
        self.assertEqual(a.get(REQUEST),2)
        self.assertEqual(organize(a,2048),2048)
        self.assertEqual(a.get(L+16),0)
        self.assertEqual(a.get(REQUEST),2)

    def test_shift_and_reel_ui_do_not_claim_pickup(self):
        a=Arm('gene_shape','g2_size');setup(a);publish(a,3);organize(a,200)
        a.uc.mem_write(0x2002a004,b'\1')
        self.assertEqual(organize(a,3500,effective=200),200)
        self.assertEqual(a.get(L+16),1)
        a.uc.mem_write(0x2002a004,b'\0');a.put(0x20021338,1)
        self.assertEqual(organize(a,3500),3500)
        publish(a,2,2);organize(a,3500)
        self.assertEqual(a.get(L),1,'defer recall while selecting a reel')
        a.put(0x20021338,0);organize(a,3500)
        self.assertEqual(a.get(L),2);self.assertEqual(a.get(REQUEST),2)

    def test_turing_legacy_hold_does_not_require_a_second_pickup(self):
        for sldm in (0,1):
            a=Arm('gene_shape','g2_size');setup(a)
            a.put(0x2002a0f0,0x5354504f);a.uc.mem_write(0x2002a0fa,b'\1')
            publish(a,3);organize(a,200)
            a.uc.mem_write(0x2002a082,b'\1')
            # Missing splc preserves the live preset even if sldm is disabled.
            publish(a,1,2,mask=0);a.uc.mem_write(0x2002a0fa,bytes([sldm]))
            self.assertEqual(organize(a,3500,effective=200),3500)
            self.assertEqual(a.get(L+16),0)
            self.assertEqual(a.uc.mem_read(0x2002a082,1),b'\0')
            self.assertEqual(a.get(REQUEST),3)

    def test_empty_reel_defers_and_metadata_change_releases(self):
        a=Arm('gene_shape','g2_size');setup(a,0);publish(a,3)
        organize(a);self.assertEqual(a.get(L),0);self.assertEqual(a.get(REQUEST),1)
        a.put(COUNT,3);organize(a);self.assertEqual(a.get(REQUEST),3)
        a.put(0x20001040,2)
        self.assertEqual(organize(a,1000),1000);self.assertEqual(a.get(L+16),0)
        publish(a,2,2);organize(a,1000);a.put(COUNT,2)
        self.assertEqual(organize(a,3000),3000);self.assertEqual(a.get(L+16),0)
        publish(a,3,3);organize(a,3000)
        self.assertEqual(a.get(REQUEST),2,'selection beyond this reel clamps to last splice')
        self.assertEqual(a.get(P+28),3,'configured selection remains unchanged')

    def test_short_reel_clamps_but_larger_reel_can_recall_original_number(self):
        a=Arm('gene_shape','g2_size');setup(a,3)
        publish(a,9);organize(a,200)
        self.assertEqual(a.get(REQUEST),3);self.assertEqual(a.get(P+28),9)
        self.assertEqual(organize(a,3500),3500);self.assertEqual(a.get(L+16),0)
        a.put(COUNT,10);a.put(0x20001040,2)
        publish(a,9,2);organize(a,200)
        self.assertEqual(a.get(REQUEST),9);self.assertEqual(a.get(P+28),9)
        a.put(COUNT,0);publish(a,300,3);organize(a,200)
        self.assertEqual(a.get(L),2,'empty reel defers without dereferencing markers')
        a.put(COUNT,1);organize(a,200)
        self.assertEqual(a.get(REQUEST),1);self.assertEqual(a.get(P+28),300)
        publish(a,0,4);organize(a,200)
        self.assertEqual(a.get(REQUEST),1,'zero never becomes a splice request')

    def test_calibrated_cell_pickup_does_not_release_in_neighbor(self):
        a=Arm('gene_shape','g2_size');setup(a,300)
        a.put(0x20022080,150);a.put(0x20022078,3900)
        publish(a,150);organize(a,100)
        self.assertEqual(organize(a,2000),100);self.assertEqual(a.get(L+16),1)
        self.assertEqual(organize(a,2023),2023);self.assertEqual(a.get(L+16),0)

@unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'),'requires official firmware')
class PresetSpliceAudio(unittest.TestCase):
    def engine(self,omod):
        a=Audio(images()[1]);setup(a.a)
        for address,value in {0x200012b4:omod,ACTIVE:1,0x20021c7c:0,
                              0x20021c74:3527}.items():a.a.put(address,value)
        a.uc.mem_write(0x2002215c,struct.pack('<4I',0,2000,4000,48000))
        a.blocks(20);a.call(0x8026d98)  # stock updates current Gene bounds
        return a

    def test_stock_omod_boundary_and_immediate_requests_preserve_audio_path(self):
        for omod in (0,1):
            a,b=self.engine(omod),self.engine(omod)
            publish(a.a,3)
            b.a.put(REQUEST,3)  # reference: the same ordinary stock request
            self.assertEqual(a.blocks(1),b.blocks(1))
            self.assertEqual(a.a.get(REQUEST),3)
            self.assertEqual(a.a.get(ACTIVE),1 if omod==0 else 3)
            self.assertEqual(a.blocks(500),b.blocks(500))
            self.assertEqual(a.a.get(ACTIVE),3)
            self.assertEqual(a.births,b.births)

    def test_real_shift_navigation_and_organize_pickup(self):
        a=self.engine(1);publish(a.a,2);a.blocks(1)
        self.assertEqual(a.a.get(REQUEST),2)
        a.a.put(0x200012e0,1);a.blocks(1)  # actual stock SHIFT release latch
        self.assertEqual(a.a.get(0x200012e0),0)
        self.assertEqual(a.a.get(REQUEST),3)
        a.blocks(2);self.assertEqual(a.a.get(ACTIVE),3)
        a.a.put(ORG,3500);a.blocks(2)
        self.assertEqual(a.a.get(L+16),0)
        self.assertEqual(a.a.get(REQUEST),3)
        a.a.put(ORG,2048);a.blocks(2)
        self.assertEqual(a.a.get(REQUEST),2)

    def test_real_turing_edit_keeps_splice_and_has_one_pickup(self):
        a=self.engine(1);a.uc.mem_write(0x2002a0fa,b'\1')
        publish(a.a,3);a.blocks(1)
        a.uc.mem_write(0x2002a004,b'\1\1\6')
        a.uc.mem_write(0x2002a082,b'\1');a.a.put(ORG,3500)
        a.blocks(2)
        self.assertEqual(a.a.get(REQUEST),3);self.assertEqual(a.a.get(L+16),1)
        self.assertGreater(value(a.a.get(0x2002a74c)),.5,'Turing evolution follows physical knob')
        a.uc.mem_write(0x2002a004,b'\0\1\6');a.blocks(1)
        self.assertEqual(a.a.get(REQUEST),3);self.assertEqual(a.a.get(L+16),0)
        self.assertEqual(a.uc.mem_read(0x2002a082,1),b'\0')
        a.a.put(ORG,2048);a.blocks(2)
        self.assertEqual(a.a.get(REQUEST),2)

    def test_explicit_recall_supersedes_only_preexisting_navigation(self):
        for queued in (0xffffffff,1):
            a=self.engine(1);a.a.put(0x200012e0,queued)
            publish(a.a,3);a.blocks(1)
            self.assertEqual(a.a.get(REQUEST),3)
            self.assertEqual(a.a.get(0x200012e0),0)
            # A later forward request must wrap to splice1 as stock normally
            # does, rather than being suppressed by an ongoing preset hold.
            a.a.put(0x200012e0,1);a.blocks(1)
            self.assertEqual(a.a.get(REQUEST),1)
            self.assertEqual(a.a.get(0x200012e0),0)
            publish(a.a,2,2,mask=0);a.a.put(0x200012e0,1);a.blocks(1)
            self.assertEqual(a.a.get(REQUEST),2,'missing splc does not cancel navigation')

    def test_clamped_recall_matches_last_splice_stock_request(self):
        for omod in (0,1):
            a,b=self.engine(omod),self.engine(omod)
            publish(a.a,300);b.a.put(REQUEST,3)
            self.assertEqual(a.blocks(501),b.blocks(501))
            self.assertEqual(a.a.get(REQUEST),3);self.assertEqual(a.a.get(ACTIVE),3)
            self.assertEqual(a.a.get(P+28),300)

if __name__=='__main__':unittest.main()
