import unittest
from tests.arm import *

class OptionHooks(unittest.TestCase):
    def test_range_parser_rejects_bad_values(self):
        a=Arm('options_keys','opt_parse')
        for line,expected in [('vrng 1',1),('vrng 0 // standard',0),('vrng 2',0),('vrng 10',0),
                              ('vrng x',0),('vrng -1',0),('vrng',0),('vrng 1\r\n',1)]:
            a.uc.mem_write(0x2002A606,b'\0')
            a.uc.mem_write(0x20002000,bytes(128))
            a.uc.mem_write(0x20002000,line.encode()+b'\0')
            a.uc.reg_write(UC_ARM_REG_R11,0x20002000)
            a.run('opt_parse',[0x080232FC,0x0802332A])
            self.assertEqual(a.uc.mem_read(0x2002A606,1),bytes([expected]),line)
            self.assertEqual(a.uc.reg_read(UC_ARM_REG_PC),0x080232FC)

    def test_root_range_and_stock_passthrough(self):
        a=Arm('options_keys','opt_parse')
        for n in range(101):
            a.uc.mem_write(0x20002000,f'root {n}\n\0'.encode());a.uc.reg_write(UC_ARM_REG_R11,0x20002000)
            a.run('opt_parse',[0x080232FC,0x0802332A])
            self.assertEqual(a.uc.mem_read(0x2002A0FB,1),bytes([n]))
        a.uc.mem_write(0x20002000,b'vsop 1\n\0');a.uc.reg_write(UC_ARM_REG_R11,0x20002000)
        a.run('opt_parse',[0x080232FC,0x0802332A])
        self.assertEqual(a.uc.reg_read(UC_ARM_REG_PC),0x0802332A)

    def test_writer_emits_range(self):
        a=Arm('options_keys','opt_parse');a.put(0x2002A0F0,0x5354504F)
        calls=[]
        def printf(a):
            p=a.uc.reg_read(UC_ARM_REG_R1);data=bytearray()
            while True:
                ch=a.uc.mem_read(p,1);p+=1
                if ch==b'\0':break
                data+=ch
            calls.append((data.decode(),a.uc.reg_read(UC_ARM_REG_R2)))
            a.uc.reg_write(UC_ARM_REG_R0,len(data))
        a.calls={0x08034804:printf,0x080327A8:lambda a:a.uc.reg_write(UC_ARM_REG_R0,0)}
        for enabled in (0,1):
            a.uc.mem_write(0x2002A606,bytes([enabled]));a.uc.mem_write(0x2002A607,bytes([enabled]));a.uc.mem_write(0x2002A610,bytes([enabled]));a.uc.mem_write(0x2002A611,bytes([enabled]));calls.clear()
            a.run('opt_write',[0x08024566])
            range_lines = [fmt % value for fmt, value in calls if fmt.startswith('vrng ')]
            self.assertEqual(len(range_lines), 1)
            self.assertTrue(range_lines[0].startswith(f'vrng {enabled} //'))
            self.assertTrue(range_lines[0].endswith('\n'))
            # Cards rewritten by this firmware may also be read by an older version.
            self.assertLessEqual(len(range_lines[0].encode('ascii')), 63)
            self.assertEqual([value for fmt,value in calls if fmt.startswith('dens ')],[enabled])
            self.assertEqual([value for fmt,value in calls if fmt.startswith('vqnt ')],[enabled])
            self.assertEqual([value for fmt,value in calls if fmt.startswith('mlop ')],[enabled])
            self.assertEqual(a.uc.reg_read(UC_ARM_REG_SP),SP)
