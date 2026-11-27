"""Dev8: compiled parsers, persistence and atomic normal/live publication."""
import unittest
from tests.arm import *
from tests import test_settings_reload as r

P, MAGIC = 0x2002a660, 0x54535250
NORMAL, LIVE, EXT = 0x2002ae10, 0x2002ae50, 0x2002ae90
COUNT = 0x2002208c
KEYS = ('mpos', 'gpos', 'spos', 'splc', 'srrp', 'jitp', 'wrbp',
        'fbkp', 'evop', 'trst', 'sosp', 'vpos')
VALUES = (12,34,56,300,21,43,65,87,9,16,11,99)
STEPS = (1,2,3,4,6,8,12,16)
ALL = (1 << len(KEYS))-1

def value_addr(i): return P+16+4*i if i<4 else EXT+4*(i-4)
def lane_addr(i): return P+32+24*i if i<4 else EXT+32+24*(i-4)
def preset_data(values=VALUES):
    return b'9 123 0\n'+''.join(f'{k} {v}\n' for k,v in zip(KEYS,values)).encode()


def normal_line(a, text):
    a.uc.mem_write(0x20002000, bytes(128))
    a.uc.mem_write(0x20002000, text.encode()+b'\0')
    r.call(a, 'presets_normal_parse', 0x20002000)


def staged(a, data):
    a.put(r.CARD, 0)
    r.stage(a, data)


def printf_capture(a):
    seen = []
    def printf(a):
        addr = a.uc.reg_read(UC_ARM_REG_R1)
        text = bytearray()
        while a.uc.mem_read(addr, 1) != b'\0':
            text.extend(a.uc.mem_read(addr, 1)); addr += 1
        seen.append((text.decode(), a.uc.reg_read(UC_ARM_REG_R2)))
        a.uc.reg_write(UC_ARM_REG_R0, len(text))
    a.calls = {0x08034804: printf, 0x080327a8: lambda a:a.uc.reg_write(UC_ARM_REG_R0,0)}
    return seen


class PresetOptionHooks(unittest.TestCase):
    def test_all_supported_integers_and_normal_last_line_semantics(self):
        a = Arm('options_keys', 'opt_parse')
        for index, key in enumerate(KEYS):
            for value in (STEPS if index == 9 else range(1 if index == 3 else 0, 301 if index == 3 else 101)):
                r.call(a, 'presets_normal_begin')
                normal_line(a, f'{key}\t{value} // recall\r\n')
                self.assertEqual(a.get(NORMAL), 1 << index)
                self.assertEqual(a.get(NORMAL+4+index*4), value)
                self.assertEqual(a.get(P), 0, 'normal parse cannot change audio state')
            for bad in ('-1', '1.5', '301' if index == 3 else '101', '1000', '1garbage', ''):
                r.call(a, 'presets_normal_begin')
                normal_line(a, f'{key} 50')
                normal_line(a, f'{key} {bad}')
                self.assertEqual(a.get(NORMAL), 0, (key, bad))
            last = 16 if index == 9 else 25
            normal_line(a, f'{key} 12')
            normal_line(a, f'{key} {last}')
            self.assertEqual(a.get(NORMAL+4+index*4), last)
            normal_line(a, f'{key}_future 40')
            self.assertEqual(a.get(NORMAL+4+index*4), last)
            self.assertEqual(a.get(NORMAL), 1 << index)
        r.call(a, 'presets_normal_begin')
        normal_line(a, 'splc 0')
        self.assertEqual(a.get(NORMAL), 1 << 3)
        self.assertEqual(a.get(NORMAL+4+3*4), 1)

    def test_turing_enum_rejects_every_unsupported_small_integer(self):
        a = Arm('options_keys', 'opt_parse')
        for value in range(101):
            r.call(a, 'presets_normal_begin')
            normal_line(a, 'trst 8')
            normal_line(a, f'trst {value}')
            self.assertEqual(a.get(NORMAL), 1<<9 if value == 0 or value in STEPS else 0, value)
            if value == 0:
                self.assertEqual(a.get(NORMAL+4+9*4), 1)

    def test_version_wrapper_names_custom_firmware_without_touching_state(self):
        a = Arm('options_keys', 'opt_parse')
        regs = (UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R4, UC_ARM_REG_R5,
                UC_ARM_REG_R6, UC_ARM_REG_R7, UC_ARM_REG_R8, UC_ARM_REG_R9,
                UC_ARM_REG_R10, UC_ARM_REG_R11, UC_ARM_REG_R12)
        for i,reg in enumerate(regs):a.uc.reg_write(reg,0x12340000+i)
        a.uc.reg_write(UC_ARM_REG_APSR,0xA8000000)
        a.run('opt_version',[0x080243c2])
        addr=a.uc.reg_read(UC_ARM_REG_R1)
        header = b'// firmware version 204+c7\n\0'
        self.assertEqual(bytes(a.uc.mem_read(addr,len(header))),header)
        self.assertEqual(a.uc.reg_read(UC_ARM_REG_R0),SP+1396)
        self.assertEqual(a.uc.reg_read(UC_ARM_REG_SP),SP)
        self.assertEqual(a.uc.reg_read(UC_ARM_REG_APSR)&0xF8000000,0xA8000000)
        for i,reg in enumerate(regs):self.assertEqual(a.uc.reg_read(reg),0x12340000+i)

    def test_file_boundary_wrappers_keep_live_registers_and_reject_read_error(self):
        a = Arm('options_keys', 'opt_parse')
        a.put(NORMAL, 15); a.put(P, MAGIC)
        a.uc.reg_write(UC_ARM_REG_R4, 0x12345678)
        a.uc.reg_write(UC_ARM_REG_R9, 0xabcdef01)
        a.run('opt_preset_begin', [0x080232f8])
        self.assertEqual(a.get(NORMAL), 0)
        self.assertEqual(a.get(NORMAL+52), 1)
        self.assertEqual(a.uc.reg_read(UC_ARM_REG_R4), 0x12345678)
        self.assertEqual(a.uc.reg_read(UC_ARM_REG_R9), 0xabcdef01)
        self.assertEqual(a.uc.reg_read(UC_ARM_REG_R5), 0x73746570)
        self.assertEqual(a.uc.reg_read(UC_ARM_REG_R6), 0x726d6f64)
        for error in (0, 1, 7):
            a.uc.mem_write(SP+1396+7, bytes([error]))
            a.uc.reg_write(UC_ARM_REG_R0, 0)
            a.run('opt_preset_end', [0x080236ce])
            self.assertEqual(a.get(NORMAL+52), 0 if error else 2)
            self.assertEqual(a.uc.reg_read(UC_ARM_REG_R9), 0)
            self.assertEqual(a.uc.reg_read(UC_ARM_REG_R0), SP+1396)
            self.assertEqual(a.uc.reg_read(UC_ARM_REG_SP), SP)
        self.assertEqual(a.get(P), MAGIC)

    def test_writer_keeps_only_configured_keys_never_live_knob_values(self):
        a = Arm('options_keys', 'opt_parse')
        a.put(P, MAGIC); a.put(COUNT, 3)
        for i, value in enumerate((23, 45, 67, 300)):a.put(P+16+4*i, value)
        a.uc.mem_write(P+32, b'\xff'*96)  # runtime controls are not persisted
        calls = printf_capture(a)
        for i,value in enumerate(VALUES[4:],4):a.put(value_addr(i),value)
        a.uc.mem_write(EXT+32,b'\xff'*256)
        values=(23,45,67,300)+VALUES[4:]
        masks=list(range(16))+[1<<i for i in range(4,12)]+[ALL]+[ALL ^ (1<<i) for i in range(12)]
        for mask in masks:
            a.put(P+12, mask); calls.clear()
            a.run('opt_write', [0x08024566])
            presets = [(fmt.split()[0], value) for fmt, value in calls if fmt.split()[0] in KEYS]
            self.assertEqual(presets, [(key, values[i]) for i,key in enumerate(KEYS) if mask & (1<<i)])
            self.assertEqual(a.uc.reg_read(UC_ARM_REG_SP), SP)
        # A normal load may rewrite before publication: use its newly parsed
        # file, including omission, instead of resurrecting the old mask.
        a.put(NORMAL+52, 2); a.put(NORMAL, 1); a.put(NORMAL+4, 18)
        calls.clear(); a.run('opt_write', [0x08024566])
        self.assertEqual([(fmt.split()[0],v) for fmt,v in calls if fmt.split()[0] in KEYS], [('mpos',18)])
        for i,v in enumerate(VALUES):a.put(NORMAL+4+4*i,v)
        for mask in [ALL,0]+[ALL ^ (1<<i) for i in range(12)]:
            a.put(NORMAL,mask);calls.clear();a.run('opt_write',[0x08024566])
            self.assertEqual([(fmt.split()[0],v) for fmt,v in calls if fmt.split()[0] in KEYS],
                             [(k,VALUES[i]) for i,k in enumerate(KEYS) if mask&(1<<i)])


class PresetTransactions(unittest.TestCase):
    def test_preset_only_reload_atomic_commit_and_same_value_recall(self):
        a = r.arm(); a.put(COUNT, 3)
        data = preset_data()
        staged(a, data)
        self.assertEqual(a.get(r.PENDING), 1)
        self.assertEqual(a.get(P), 0)
        r.call(a, 'reload_commit')
        self.assertEqual(a.get(P), MAGIC)
        self.assertEqual(a.get(P+4), 1)
        self.assertEqual(a.get(P+8), ALL)
        self.assertEqual([a.get(value_addr(i)) for i in range(12)], list(VALUES))
        staged(a, data); r.call(a, 'reload_commit')
        self.assertEqual(a.get(P+4), 2, 'explicit identical values recall again')

    def test_every_new_key_supports_live_boundaries_and_independent_publication(self):
        a=r.arm();a.put(COUNT,1)
        for i,key in enumerate(KEYS):
            for v in (STEPS if key=='trst' else (1,300) if key=='splc' else (0,100)):
                before=(bytes(a.uc.mem_read(P,160)),bytes(a.uc.mem_read(EXT,288)))
                staged(a,f'header\n{key} {v}\n'.encode())
                self.assertEqual(a.get(r.PENDING),1,(key,v))
                self.assertEqual((bytes(a.uc.mem_read(P,160)),bytes(a.uc.mem_read(EXT,288))),before)
                r.call(a,'reload_commit')
                self.assertEqual(a.get(P+8),1<<i,(key,v))
                self.assertEqual(a.get(P+12),1<<i,(key,v))
                self.assertEqual(a.get(value_addr(i)),v,(key,v))
        for key in KEYS:
            before=(bytes(a.uc.mem_read(P,160)),bytes(a.uc.mem_read(EXT,288)))
            staged(a,f'header\n{key} 1\n{key} 1\n'.encode());r.call(a,'reload_commit')
            self.assertEqual(a.get(r.RESULT),2,key)
            self.assertEqual((bytes(a.uc.mem_read(P,160)),bytes(a.uc.mem_read(EXT,288))),before)

    def test_omitted_keys_preserve_runtime_but_stay_omitted_on_save(self):
        a = r.arm(); a.put(COUNT, 3)
        staged(a, preset_data()); r.call(a,'reload_commit')
        runtime = bytes(range(128)); a.uc.mem_write(P+32, runtime)
        ext_runtime = bytes(i%251 for i in range(256)); a.uc.mem_write(EXT+32, ext_runtime)
        staged(a, b'header\nmpos 80\n'); r.call(a,'reload_commit')
        self.assertEqual(a.get(P+8), 1); self.assertEqual(a.get(P+12), 1)
        self.assertEqual(a.uc.mem_read(P+32, 128), runtime)
        self.assertEqual(a.uc.mem_read(EXT+32, 256), ext_runtime)
        self.assertEqual([a.get(value_addr(i)) for i in range(12)], [80,*VALUES[1:]])
        staged(a, b'header\nvuni 1\n'); r.call(a,'reload_commit')
        self.assertEqual(a.get(P+8), 0); self.assertEqual(a.get(P+12), 0)
        self.assertEqual(a.uc.mem_read(P+32, 128), runtime)
        self.assertEqual(a.uc.mem_read(EXT+32, 256), ext_runtime)

    def test_invalid_or_duplicate_preset_rejects_every_setting(self):
        for bad in (b'splc 301', b'splc 0x', b'mpos 101', b'gpos -1', b'spos 1.5',
                    b'mpos 2\nmpos 2', b'splc 1\nsplc 2', b'srrp 101',
                    b'jitp -1', b'wrbp 1.5', b'fbkp 1000', b'evop 20junk',
                    b'trst 5', b'trst 0x', b'trst 16\ntrst 16', b'sosp 101', b'vpos 101'):
            a = r.arm(); a.put(COUNT, 3); a.put(r.STOCK, 0)
            staged(a, b'header\nvsop 2\nmpos 50\n'+bad+b'\n')
            r.call(a,'reload_commit')
            self.assertEqual(a.get(r.PENDING), 0, bad)
            self.assertEqual(a.get(r.RESULT), 2, bad)
            self.assertEqual(a.get(r.STOCK), 0, bad)
            self.assertEqual(a.get(P), 0, bad)
        a = r.arm(); a.put(COUNT, 3)
        staged(a, b'header\nmpos_future 50\nsplc_extra 2\nmpos 30\n')
        r.call(a,'reload_commit')
        self.assertEqual(a.get(P+8), 1)
        self.assertEqual(a.get(P+16), 30)

    def test_splice_count_change_keeps_configured_number_for_runtime_clamp(self):
        a = r.arm(); a.put(COUNT, 3); a.put(r.STOCK, 0)
        staged(a, b'header\nvsop 2\nmpos 50\nsplc 3\n')
        self.assertEqual(a.get(r.PENDING), 1)
        a.put(COUNT, 2); r.call(a,'reload_commit')
        self.assertEqual(a.get(r.RESULT), 1)
        self.assertEqual(a.get(r.STOCK), 2)
        self.assertEqual(a.get(P), MAGIC)
        self.assertEqual(a.get(P+28), 3)

    def test_normal_load_publishes_only_after_completion_and_valid_card(self):
        for card, read_ok, file_ok, count, expected in ((1,2,1,3,ALL),(1,2,1,2,ALL),
                (1,2,0,0,ALL),(0,2,0,3,0),(1,0,1,3,0)):
            a = r.arm(); a.put(r.CARD, card); a.put(r.LIVE, r.FS if file_ok else 0)
            a.put(COUNT,count); a.put(NORMAL,ALL); a.put(NORMAL+52,read_ok)
            for i,v in enumerate(VALUES):a.put(NORMAL+4+i*4,v)
            r.call(a,'reload_service',r.FS,r.LIVE)
            self.assertEqual(a.get(P),0,'no completion token yet')
            a.put(r.STATE+240,2); r.call(a,'reload_service',r.FS,r.LIVE)
            self.assertEqual(a.get(P+8),expected,(card,read_ok,file_ok,count))
            if expected:self.assertEqual([a.get(value_addr(i)) for i in range(12)],list(VALUES))
            self.assertEqual(a.get(NORMAL+52),0)
            generation=a.get(P+4)
            r.call(a,'reload_service',r.FS,r.LIVE)
            self.assertEqual(a.get(P+4),generation,'exactly one recall per load')

    def test_generation_wrap_and_legacy_empty_file(self):
        a=r.arm(); staged(a,b'header\nvsop 0\n');r.call(a,'reload_commit')
        self.assertEqual(a.get(P),0,'no preset history keeps runtime disabled')
        a.put(P,MAGIC);a.put(P+4,0xffffffff)
        for i in range(12):a.put(lane_addr(i),1)
        staged(a,b'header\nmpos 50\n');r.call(a,'reload_commit')
        self.assertEqual(a.get(P+4),1)
        self.assertEqual([a.get(lane_addr(i)) for i in range(12)],[0]*12)

    def test_busy_normal_completion_defers_without_losing_recalls(self):
        a=r.arm();a.put(r.CARD,1);a.put(r.LIVE,r.FS)
        a.put(NORMAL,1);a.put(NORMAL+4,75);a.put(NORMAL+52,2)
        a.put(r.STATE+240,2);a.put(r.REC_REQUEST,1)
        r.call(a,'reload_service',r.FS,r.LIVE)
        self.assertEqual(a.get(P),0)
        self.assertEqual(a.get(NORMAL+52),2)
        self.assertEqual(a.get(r.STATE+240),2)
        a.put(r.REC_REQUEST,0);r.call(a,'reload_service',r.FS,r.LIVE)
        self.assertEqual(a.get(P+16),75)
        self.assertEqual(a.get(P+4),1)
        self.assertEqual(a.get(r.STATE+240),0)


if __name__ == '__main__':unittest.main()
