"""Execute the bank hooks with fault-injectable FatFs directory operations."""
import os
import unittest

from tests.arm import (
    Arm, SP, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0,
    UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R6,
    UC_ARM_REG_R7, UC_ARM_REG_R12, UC_ARM_REG_SP,
)
from tests.test_settings_reload import call, CARD, FLAGS, REC, REC_REQUEST

BANK, RB = 0x2002a61f, 0x20028f00
MODE, COUNT, CURSOR = 0x20021338, 0x200012a0, 0x20001040
NOW, T0, COLOR, LIVE_ID = 0x20021c88, 0x20001024, 0x20001038, 0x20028ff0
BUFFER = 0x20028000
DIR = object()


class Directory:
    def __init__(self, arm):
        self.files = {}
        self.errors = {}
        self.log = []
        self.a = arm
        arm.calls.update({0x08033128: self.stat, 0x080334d4: self.mkdir,
                          0x08033848: self.rename, 0x080333dc: self.unlink})

    def path(self, reg):
        address = self.a.uc.reg_read(reg)
        return bytes(self.a.uc.mem_read(address, 32)).split(b'\0')[0].decode()

    def error(self, action, name, default=0):
        self.log.append((action, name))
        return self.errors.get((action, name), default)

    def stat(self, a):
        name = self.path(UC_ARM_REG_R0)
        error = self.error('stat', name, 0 if name in self.files else 4)
        info = a.uc.reg_read(UC_ARM_REG_R1)
        if info and not error:
            a.put(info + 8, 0x10 if self.files[name] is DIR else 0x20)
        a.uc.reg_write(UC_ARM_REG_R0, error)

    def mkdir(self, a):
        name = self.path(UC_ARM_REG_R0)
        error = self.error('mkdir', name, 8 if name in self.files else 0)
        if not error:
            self.files[name] = DIR
        a.uc.reg_write(UC_ARM_REG_R0, error)

    def rename(self, a):
        src, dst = self.path(UC_ARM_REG_R0), self.path(UC_ARM_REG_R1)
        error = self.error('rename', src, 8 if dst in self.files else 0)
        if not error:
            self.files[dst] = self.files.pop(src)
        a.uc.reg_write(UC_ARM_REG_R0, error)

    def unlink(self, a):
        name = self.path(UC_ARM_REG_R0)
        error = self.error('unlink', name, 0 if name in self.files else 4)
        if not error:
            del self.files[name]
        a.uc.reg_write(UC_ARM_REG_R0, error)


def setup(bank=1):
    a = Arm('reel_banks', 'rb_name')
    a.put(0x2002a0f0, 0x5354504f)
    a.uc.mem_write(BANK, bytes([bank]))
    a.put(CARD, 1)
    a.put(MODE, 1)
    return a, Directory(a)


def byte(a, address):
    return a.uc.mem_read(address, 1)[0]


def hold(a, tick, *, rec=1, splice=1, shift=0):
    a.put(NOW, tick)
    a.put(SP + 4, rec | splice | shift)
    for reg, value in ((UC_ARM_REG_R2, rec), (UC_ARM_REG_R3, splice),
                       (UC_ARM_REG_R12, shift), (UC_ARM_REG_LR, tick)):
        a.uc.reg_write(reg, value)
    a.stops = {0x080248fc, 0x0802526e}
    a.uc.emu_start(a.syms['rb_hold'] | 1, 0, count=2000)
    assert a.uc.reg_read(UC_ARM_REG_PC) in a.stops
    assert a.uc.reg_read(UC_ARM_REG_SP) == SP
    assert a.uc.reg_read(UC_ARM_REG_LR) == tick


def drain(a, mounted=1):
    a.uc.reg_write(UC_ARM_REG_R6, mounted)
    a.uc.reg_write(UC_ARM_REG_R7, FLAGS)
    a.run('rb_main', [0x08022fc2, 0x08022f96], count=100000)


class ReelBanks(unittest.TestCase):
    def test_stock_names_and_bank_names_with_boundaries(self):
        a, _ = setup()
        for bank in range(9):
            a.uc.mem_write(BANK, bytes([bank]))
            for n, letter in enumerate('123456789abcdefghijklmnopqrstuvw', 1):
                for fn, stem, suffix in [('rb_name', 'mg', '.wav'), ('rb_splice', 'splice', '.txt')]:
                    a.uc.mem_write(BUFFER - 1, b'x' * 34)
                    self.assertEqual(call(a, fn, BUFFER, n), 0)
                    prefix = f'bank{bank}/' if bank > 1 else ''
                    name = f'{prefix}{stem}{letter}{suffix}'.encode()
                    self.assertEqual(bytes(a.uc.mem_read(BUFFER-1, 34)),
                                     b'x' + name.ljust(32, b'\0') + b'x')

    def test_boot_follows_saved_physical_reel_across_compaction(self):
        for saved, selected in ((4, 2), (8, 3), (3, 1), (27, 1)):
            a, disk = setup(2)
            disk.files = {'bank2': DIR, 'bank2/mg2.wav': b'first',
                          'bank2/mg4.wav': b'second', 'bank2/mg8.wav': b'third'}
            a.put(CURSOR, saved)
            self.assertEqual(call(a, 'rb_boot_catalog'), 3)
            self.assertEqual(a.get(CURSOR), selected)

    def test_full_bank_at_cw_does_not_keep_reloading_reel_32(self):
        a, _ = setup(8)
        for bank, original, expected, limit in ((8, 32, 0x0802888e, 32),
                                                (8, 31, 0x08028708, 32),
                                                (0, 32, 0x08028708, 33)):
            a.uc.mem_write(BANK, bytes([bank]))
            a.uc.reg_write(UC_ARM_REG_R7, original)
            a.uc.reg_write(UC_ARM_REG_R0, 33)
            a.run('rb_browse_limit', [0x0802888e, 0x08028708])
            self.assertEqual(a.uc.reg_read(UC_ARM_REG_PC), expected)
            self.assertEqual(a.uc.reg_read(UC_ARM_REG_R0), limit)

    def test_gesture_rollover_led_release_and_empty_bank(self):
        a, disk = setup(7)
        start = 0xfffe0000
        a.put(T0, start)
        for offset, target in [(287999, 0), (288000, 8), (383999, 8), (384000, 1)]:
            tick = (start + offset) & 0xffffffff
            hold(a, tick)
            self.assertEqual(byte(a, RB+12), target)
            if target:
                a.run('rb_led', [0x080249cc])
                self.assertEqual(a.get(COLOR), target & 7)
        tick = (start + 385000) & 0xffffffff
        hold(a, tick, rec=0)
        self.assertEqual(byte(a, RB+13), 1)
        self.assertEqual(disk.log, [])
        drain(a)
        self.assertEqual((byte(a, BANK), a.get(CURSOR), a.get(COUNT)), (1, 1000, 0))
        self.assertEqual(a.get(FLAGS), 0x80)
        self.assertEqual(byte(a, RB+14), 1)
        hold(a, tick + 10)
        self.assertEqual(byte(a, RB+12), 0)
        for frame, expected in ((tick+143999, 1), (tick+144000, 6)):
            a.put(NOW, frame)
            a.put(COLOR, 6)
            a.run('rb_led', [0x080249cc])
            self.assertEqual(a.get(COLOR), expected)

    def test_gesture_opt_out_short_hold_shift_cancel_and_card_absent(self):
        for case in ('disabled', 'short', 'shift_cancel', 'absent', 'invalid', 'magic'):
            a, disk = setup(0 if case == 'disabled' else 1)
            if case == 'absent': a.put(CARD, 0)
            if case == 'invalid': a.uc.mem_write(BANK, b'\xff')
            if case == 'magic': a.put(0x2002a0f0, 0)
            a.put(T0, 100)
            hold(a, 288099 if case == 'short' else 288100)
            if case == 'shift_cancel':
                hold(a, 288101, shift=1)
                hold(a, 288102)
            hold(a, 288103, rec=0, splice=0)
            self.assertEqual((byte(a, RB+12), byte(a, RB+13)), (0, 0), case)
            self.assertEqual(disk.log, [])

    def test_ignores_apply_during_record_card_change_or_busy_operation(self):
        for address, value in ((REC, 1), (REC_REQUEST, 1), (FLAGS, 1), (FLAGS, 0x1000),
                               (MODE, 0), (CARD, 0)):
            a, disk = setup(1)
            a.put(address, value)
            call(a, 'rb_apply', 4)
            self.assertEqual(byte(a, BANK), 1)
            self.assertEqual(disk.log, [])

    def test_select_recount_delete_pair_and_keep_other_directories(self):
        a, disk = setup(1)
        disk.files = {'mg1.wav': b'root', 'bank3': DIR, 'bank3/mg1.wav': b'one',
                      'bank3/splice1.txt': b'markers-one', 'bank4/mg1.wav': b'other',
                      'bank3/mgw.wav': b'thirty-two', 'bank3/splicew.txt': b'markers-32'}
        call(a, 'rb_apply', 3)
        self.assertEqual((byte(a, BANK), a.get(COUNT), a.get(CURSOR)), (3, 2, 1))
        self.assertEqual(disk.files['bank3/mg2.wav'], b'thirty-two')
        self.assertEqual(disk.files['bank3/splice2.txt'], b'markers-32')
        a.uc.mem_write(LIVE_ID, bytes([1, 1]))
        self.assertEqual(call(a, 'rb_delete_hook', 1), 1)
        self.assertEqual(bytes(a.uc.mem_read(LIVE_ID, 2)), bytes(2))
        self.assertEqual(disk.files, {'mg1.wav': b'root', 'bank3': DIR,
                                     'bank4/mg1.wav': b'other', 'bank3/mg1.wav': b'thirty-two',
                                     'bank3/splice1.txt': b'markers-32'})

    def test_missing_directory_is_created_only_for_a_missing_entry(self):
        for error in (0, 1, 3, 5, 7):
            a, disk = setup()
            if error:
                disk.errors['stat', 'bank2'] = error
            call(a, 'rb_apply', 2)
            self.assertEqual(byte(a, BANK), 1 if error else 2)
            self.assertEqual(('mkdir', 'bank2') in disk.log, not error)
        for blocked in ('file', 'read_only', 'mkdir_race'):
            a, disk = setup()
            if blocked == 'file':
                disk.files['bank2'] = b'user file'
            else:
                disk.errors['mkdir', 'bank2'] = 8 if blocked == 'mkdir_race' else 10
            call(a, 'rb_apply', 2)
            self.assertEqual(byte(a, BANK), 1)
            self.assertEqual(a.get(FLAGS), 0)

    def test_failed_scan_or_rename_does_not_select_or_cross_link(self):
        for case in ('orphan', 'read_error', 'rename_error', 'protected_open'):
            a, disk = setup()
            disk.files = {'mg1.wav': b'root', 'bank2': DIR,
                          'bank2/mg2.wav': b'audio', 'bank2/splice2.txt': b'markers'}
            if case == 'orphan':
                disk.files['bank2/splice1.txt'] = b'unrelated'
            if case == 'read_error':
                disk.errors['stat', 'bank2/mgw.wav'] = 1
            if case == 'rename_error':
                disk.errors['rename', 'bank2/mg2.wav'] = 7
            if case == 'protected_open':
                a.uc.mem_write(LIVE_ID, bytes([2, 2]))
            before = disk.files.copy()
            a.put(CURSOR, 7)
            call(a, 'rb_apply', 2)
            self.assertEqual(disk.files, before, case)
            self.assertEqual((byte(a, BANK), a.get(CURSOR), a.get(FLAGS)), (1, 7, 0))

    def test_card_removal_discards_a_deferred_gesture(self):
        a, disk = setup()
        a.put(T0, 17)
        hold(a, 288017)
        hold(a, 288018, rec=0, splice=0)
        self.assertEqual(byte(a, RB+13), 2)
        drain(a, 0)
        drain(a, 1)
        self.assertEqual((byte(a, BANK), a.get(FLAGS), disk.log), (1, 0, []))


@unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'), 'requires official mg204')
class ReelBankDelete(unittest.TestCase):
    def test_native_delete_preserves_other_banks_and_compacts_legacy_markers(self):
        from tests.test_bank_mount import Mount
        from tests.test_empty_card import HEADER, MAIN_SP
        for fat32 in (False, True):
            with self.subTest(fat32=fat32):
                m = Mount(b'2 45875 0\nbank 2\n', fat32)
                m.directory('bank2')
                m.directory('bank3')
                m.write('bank3/mg2.wav', b'other bank')
                for n in (1, 2, 3):
                    m.write(f'bank2/mg{n}.wav', HEADER + bytes([n]))
                    m.write(f'bank2/splice{n}.txt', f'marker {n}'.encode())
                self.assertEqual(m.boot(), 'bank2/mg2.wav')
                a = m.arm
                a.syms['native_delete'] = 0x08024340
                a.uc.reg_write(UC_ARM_REG_SP, MAIN_SP)
                a.uc.reg_write(UC_ARM_REG_R7, FLAGS)
                a.run('native_delete', [0x08024352], count=2000000)
                self.assertEqual(a.get(COUNT), 2)
                self.assertEqual(bytes(a.uc.mem_read(LIVE_ID, 2)), bytes(2))
                for n, old_slot in ((1, 1), (2, 3)):
                    self.assertEqual(m.contents(f'bank2/mg{n}.wav'), HEADER + bytes([old_slot]))
                    self.assertEqual(m.contents(f'bank2/splice{n}.txt'), f'marker {old_slot}'.encode())
                self.assertEqual(m.contents('mg9.wav'), m.disk.reel)
                self.assertEqual(m.contents('bank3/mg2.wav'), b'other bank')
                for old in ('bank2/mg3.wav', 'bank2/splice3.txt'):
                    self.assertEqual(call(a, 'stat', m.path(old), 0), 4)


if __name__ == '__main__':
    unittest.main()
