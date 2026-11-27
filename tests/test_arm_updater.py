import os, struct, unittest, zlib
from pathlib import Path
from tests.arm import *
from mgmod import stock
from mgmod.card import MIN_IMAGE, card_file

def image(length=MIN_IMAGE, reset=0x08021415):
    data=bytearray(length)
    struct.pack_into('<II',data,0,0x20030000,reset)
    return bytes(data)

def raw_card(data):
    return bytes(data)+b'MGMD'+struct.pack('<II',len(data),zlib.crc32(data))

class UpdaterHooks(unittest.TestCase):
    def run_update(self,data,rename_result=0):
        a=Arm('sd_updater','upd_hook');events=[]
        a.uc.mem_write(0x2002A610,b'\xff'*16)
        a.uc.mem_write(0x2002A660,b'\xff'*160)
        a.uc.mem_write(0x2002AE10,b'\xff'*128)
        a.uc.mem_write(0x2002AE90,b'\xff'*288)
        def result(code):
            def f(a):a.uc.reg_write(UC_ARM_REG_R0,code)
            return f
        def read(a):
            length=min(len(data),a.uc.reg_read(UC_ARM_REG_R2))
            a.uc.mem_write(a.uc.reg_read(UC_ARM_REG_R1),data[:length])
            a.put(a.uc.reg_read(UC_ARM_REG_R3),length)
            a.uc.reg_write(UC_ARM_REG_R0,0)
        def rename(a):events.append('rename');a.uc.reg_write(UC_ARM_REG_R0,rename_result)
        a.calls={0x08032260:result(0 if data is not None else 4),0x080323FC:read,
                 0x080327A8:result(0),0x080333DC:result(4),0x08033848:rename}
        a.run('upd_hook',[0x0802328C,0x2002B400],count=30000000)
        return a,events

    def test_good_image_is_staged_and_retired_before_flash(self):
        data=card_file(image());a,events=self.run_update(data)
        self.assertEqual(a.uc.reg_read(UC_ARM_REG_PC),0x2002B400)
        self.assertEqual(events,['rename'])
        self.assertEqual(a.uc.mem_read(0xD0000000,len(data)),data)
        self.assertEqual(a.uc.reg_read(UC_ARM_REG_R1),MIN_IMAGE)
        self.assertEqual(a.uc.mem_read(0x08020000,16),bytes(16))

    def test_invalid_updates_never_reach_flash_or_rename(self):
        good=raw_card(image());bad_crc=bytearray(good);bad_crc[-1]^=1
        bad_magic=bytearray(good);bad_magic[-12]^=1
        bad_length=bytearray(good);bad_length[-8]^=4
        bad_stack=bytearray(image());bad_stack[0]^=4
        cases=[raw_card(image(8)),raw_card(image(MIN_IMAGE-4)),raw_card(image(0x40004)),
               raw_card(image(reset=0x08021414)),raw_card(image(reset=0x08020001)),
               raw_card(image(reset=0x08020000+MIN_IMAGE+1)),
               raw_card(image(reset=0x0805FFFF)),raw_card(bad_stack),
               bytes(bad_crc),bytes(bad_magic),bytes(bad_length),good[:-1]]
        for index,data in enumerate(cases):
            with self.subTest(case=index):
                a,events=self.run_update(data)
                self.assertEqual(a.uc.reg_read(UC_ARM_REG_PC),0x0802328C)
                self.assertFalse(events)
                self.assertEqual(a.uc.mem_read(0x08020000,16),bytes(16))

    def test_missing_file_and_rename_failure(self):
        a,events=self.run_update(None)
        self.assertEqual(a.uc.reg_read(UC_ARM_REG_PC),0x0802328C)
        self.assertEqual(a.get(0x2002A0F0),0x5354504F)
        self.assertEqual(a.uc.mem_read(0x2002A606,2),b'\0\0')
        self.assertEqual(a.uc.mem_read(0x2002A610,2),b'\0\0')
        self.assertEqual(a.uc.mem_read(0x2002A618,8),bytes(8))
        self.assertEqual(a.uc.mem_read(0x2002A660,160),bytes(160))
        self.assertEqual(a.uc.mem_read(0x2002AE10,128),bytes(128))
        self.assertEqual(a.uc.mem_read(0x2002AE90,288),bytes(288))
        a,events=self.run_update(card_file(image()),rename_result=7)
        self.assertEqual(a.uc.reg_read(UC_ARM_REG_PC),0x0802328C)

    @unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'),'set MGMOD_FIRMWARE for stock startup integration')
    def test_real_reset_clears_retained_ram_before_hardware_init(self):
        data=bytearray(stock.load(os.environ['MGMOD_FIRMWARE']))
        struct.pack_into('<I',data,0x1454,0x2002B800)
        a=Arm('sd_updater','upd_hook');a.uc.mem_write(0x08020000,bytes(data))
        a.uc.mem_write(0x20000000,b'\xA5'*0x30000)
        a.uc.reg_write(UC_ARM_REG_SP,0x20030000)
        # The new reset hook is a literal change in the actual startup loop.
        a.syms['reset']=0x08021414
        a.run('reset',[0x0802143A],count=400000)
        self.assertEqual(a.uc.mem_read(0x200243C8,0xB800-0x43C8),bytes(0xB800-0x43C8))
        self.assertEqual(a.uc.mem_read(0x2002B800,4),b'\xA5'*4)
