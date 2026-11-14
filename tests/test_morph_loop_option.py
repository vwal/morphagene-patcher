"""Switchable Morph Loop: real parser, tables and audio engine."""
import os, unittest
from pathlib import Path
from tests.arm import *
from tests.test_settings_reload import arm,call,stage

TABLES={0x200003e0:0x40000000,0x200003e4:0x3fc00000,0x200003e8:0x3faaaaa8,
        0x200004f4:2,0x200004f8:3}
class MorphLoopOption(unittest.TestCase):
    def test_boot_parser_values(self):
        for text,want in [('mlop 1',1),('mlop 0',0),('mlop 2',0),('mlop 10',0),('mlop -1',0)]:
            a=Arm('options_keys','opt_parse')
            a.uc.mem_write(0x20002000,text.encode()+b'\0');a.uc.reg_write(UC_ARM_REG_R11,0x20002000)
            a.run('opt_parse',[0x80232fc]);self.assertEqual(a.uc.mem_read(0x2002a611,1),bytes([want]))
    def test_reload_on_off_atomic_tables(self):
        a=arm()
        for addr,val in TABLES.items():a.put(addr,val)
        for enabled in (1,0,1,0):
            a.put(0x20001290,0)
            stage(a,f'9 0 0\nmlop {enabled}\n'.encode())
            call(a,'reload_commit')
            for addr,original in TABLES.items():
                self.assertEqual(a.get(addr),(0x3f800000 if addr<0x20000400 else 1) if enabled else original)
            self.assertEqual(a.uc.reg_read(UC_ARM_REG_PRIMASK),0)
    @unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'),'set MGMOD_FIRMWARE')
    def test_real_audio_matches_both_previous_variants(self):
        from tests.audio import Audio
        from tests.test_firmware_integration import images
        _,new=images()
        prior=Path(os.environ['MGMOD_DEV4']).read_bytes()
        loop=bytearray(prior)
        for offset,val in {0x27630:0x3f800000,0x27634:0x3f800000,0x27638:0x3f800000,0x27744:1,0x27748:1}.items():
            struct.pack_into('<I',loop,offset,val)
        for gnsm in (0,1):
            for enabled in (0,1):
                for morph in (0,1000):
                    baseline=Audio(bytes(loop) if enabled else prior);current=Audio(new)
                    for engine in (baseline,current):
                        engine.a.put(0x20021c6c,morph);engine.a.put(0x200012d0,gnsm)
                    current.a.uc.mem_write(0x2002a611,bytes([enabled]))
                    self.assertEqual(current.blocks(450),baseline.blocks(450),(gnsm,enabled,morph))
