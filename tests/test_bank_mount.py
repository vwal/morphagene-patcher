"""Follow the normal mg204 card-mount code through the first opened reel."""
import os
import struct
import unittest

from tests.arm import (
    Arm, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R7, UC_ARM_REG_R8,
    UC_ARM_REG_R11, UC_ARM_REG_SP,
)
from tests.test_empty_card import FILE, FS, HEADER, MAIN_SP, PATH
from tests.test_firmware_integration import images
from tests.test_reload_filesystem import FatDisk
from tests.test_settings_reload import CLOSE, FLAGS, MOUNT, OPEN, READ, STAT, call

BANK = 0x2002A61F
REEL = 0x20001040
COUNT = 0x200012A0
LIMIT = 0x2000128C
SCRATCH_FILE = PATH + 1024
DATA = PATH + 128
TRANSFERRED = PATH + 768


class Mount:
    def __init__(self, options, fat32=False):
        self.arm = a = Arm('shift_gestures', 'p1_session')
        original, firmware = images()
        a.uc.mem_write(0x08020000, firmware)
        a.uc.mem_write(0x20000000, original[0x27250:0x28400])
        a.uc.ctl_remove_cache(0x08020000, 0x08060000)
        a.syms.update(mount=MOUNT, open=OPEN, close=CLOSE, read=READ, stat=STAT,
                      mkdir=0x080334d4, write=0x08032688, start=0x08023288)
        self.disk = FatDisk(a, fat32=fat32)
        self.disk.file(0, b'OPTIONS TXT', self.disk.options_cluster, options)
        a.put(LIMIT, 33)  # stock initialization at 0x08022c18
        a.put(REEL, 1)
        assert call(a, 'mount', FS, self.path(''), 1) == 0

    def path(self, name):
        self.arm.uc.mem_write(PATH, name.encode('ascii') + bytes(1))
        return PATH

    def directory(self, name):
        assert call(self.arm, 'mkdir', self.path(name)) == 0

    def write(self, name, payload):
        a = self.arm
        assert call(a, 'open', SCRATCH_FILE, self.path(name), 10) == 0
        a.uc.mem_write(DATA, payload)
        assert call(a, 'write', SCRATCH_FILE, DATA, len(payload), TRANSFERRED) == 0
        assert a.get(TRANSFERRED) == len(payload)
        assert call(a, 'close', SCRATCH_FILE) == 0

    def run_mount(self, stop):
        a = self.arm
        for reg, value in ((UC_ARM_REG_SP, MAIN_SP), (UC_ARM_REG_R7, FLAGS),
                           (UC_ARM_REG_R8, LIMIT), (UC_ARM_REG_R11, MAIN_SP + 228),
                           (UC_ARM_REG_R0, 0)):
            a.uc.reg_write(reg, value)
        # Real updater, options parser, bank selection and stock first WAV open.
        a.run('start', [stop], count=2000000)
        assert a.uc.reg_read(UC_ARM_REG_PC) == stop

    def boot(self):
        a = self.arm
        self.run_mount(0x08023722)
        assert a.uc.reg_read(UC_ARM_REG_R0) == 0
        return bytes(a.uc.mem_read(MAIN_SP + 132, 32)).split(b'\0')[0].decode()

    def read(self, handle):
        a = self.arm
        assert call(a, 'read', handle, DATA, 512, TRANSFERRED) == 0
        return bytes(a.uc.mem_read(DATA, a.get(TRANSFERRED)))

    def contents(self, name):
        a = self.arm
        assert call(a, 'open', SCRATCH_FILE, self.path(name), 1) == 0
        result = self.read(SCRATCH_FILE)
        assert call(a, 'close', SCRATCH_FILE) == 0
        return result


@unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'), 'requires official mg204')
class NormalBankMount(unittest.TestCase):
    def test_options_choose_bank_before_slot_compaction(self):
        for fat32 in (False, True):
            with self.subTest(fat32=fat32):
                m = Mount(b'1 45875 0\nbank 2\n', fat32)
                m.directory('bank2')
                m.write('bank2/mgw.wav', HEADER + b'bank two')
                m.write('bank2/splicew.txt', b'local markers')
                m.write('splice9.txt', b'root markers')
                self.assertEqual(m.boot(), 'bank2/mg1.wav')
                self.assertEqual(m.read(FILE), HEADER + b'bank two')
                self.assertEqual(m.arm.get(COUNT), 1)
                self.assertEqual(m.contents('bank2/splice1.txt'), b'local markers')
                self.assertEqual(m.contents('mg9.wav'), m.disk.reel)
                self.assertEqual(m.contents('splice9.txt'), b'root markers')
                self.assertEqual(call(m.arm, 'stat', m.path('mg1.wav'), 0), 4)

    def test_normal_mount_old_card_defaults_back_to_root(self):
        m = Mount(b'1 45875 0\n')
        # Simulate an ordinary insertion following a card which enabled bank 8.
        m.arm.uc.mem_write(BANK, bytes([8]))
        m.directory('bank8')
        m.write('bank8/mg1.wav', HEADER + b'bank eight')
        self.assertEqual(m.boot(), 'mg1.wav')
        self.assertEqual(m.arm.uc.mem_read(BANK, 1), bytes(1))
        self.assertEqual(m.read(FILE), m.disk.reel)
        self.assertEqual(m.contents('bank8/mg1.wav'), HEADER + b'bank eight')

    def test_256_reels_on_one_card(self):
        m = Mount(b'1 45875 0\nbank 1\n', fat32=True)
        slots = '123456789abcdefghijklmnopqrstuvw'
        for bank in range(1, 9):
            prefix = '' if bank == 1 else f'bank{bank}/'
            if prefix:
                m.directory(prefix[:-1])
            for slot in slots:
                m.write(f'{prefix}mg{slot}.wav', HEADER + f'{bank}/{slot}'.encode())
        for bank in range(1, 9):
            with self.subTest(bank=bank):
                prefix = '' if bank == 1 else f'bank{bank}/'
                m.write('options.txt', f'32 45875 0\nbank {bank}\n'.encode())
                self.assertEqual(m.boot(), f'{prefix}mgw.wav')
                self.assertEqual(m.arm.get(COUNT), 32)
                self.assertEqual(m.read(FILE), HEADER + f'{bank}/w'.encode())
                self.assertEqual(call(m.arm, 'close', FILE), 0)

    def test_old_selection_falls_back_in_smaller_or_new_bank(self):
        for existing in (False, True):
            with self.subTest(existing=existing):
                m = Mount(b'27 45875 0\nbank 5\n')
                if existing:
                    m.directory('bank5')
                    m.write('bank5/mg1.wav', HEADER + b'original bank five')
                self.assertEqual(m.boot(), 'bank5/mg1.wav')
                if existing:
                    self.assertEqual(m.read(FILE), HEADER + b'original bank five')
                self.assertEqual(m.contents('mg9.wav'), m.disk.reel)
                self.assertEqual(call(m.arm, 'stat', m.path('bank5/mgr.wav'), 0), 4)

    def test_normal_mount_cannot_replace_a_file_with_a_bank_folder(self):
        m = Mount(b'1 45875 0\nbank 3\n')
        m.write('bank3', b'file already using this name')
        m.run_mount(0x08022f96)  # return after the stock unmount path
        self.assertEqual(m.arm.get(0x20001290), 0)
        self.assertEqual(m.arm.get(FILE), 0)
        self.assertEqual(call(m.arm, 'mount', FS, m.path(''), 1), 0)
        self.assertEqual(m.contents('bank3'), b'file already using this name')
        self.assertEqual(m.contents('mg9.wav'), m.disk.reel)
        self.assertEqual(call(m.arm, 'stat', m.path('mg1.wav'), 0), 4)

    def test_complete_boot_reads_selected_wav_and_legacy_splice_file(self):
        m = Mount(b'1 45875 0\nbank 2\n')
        m.directory('bank2')
        samples = struct.pack('<2f', 0.75, -0.75) * 32
        header = bytearray(HEADER)
        struct.pack_into('<I', header, 4, 36 + len(samples))
        struct.pack_into('<I', header, 40, len(samples))
        wav = bytes(header) + samples
        m.write('bank2/mg1.wav', wav)
        sectors = []
        for name in ('splice1.txt', 'bank2/splice1.txt'):
            m.write(name, b'0 24000\n16 24000\n')
            self.assertEqual(call(m.arm, 'open', SCRATCH_FILE, m.path(name), 1), 0)
            sectors.append(m.disk.sector(m.arm.get(SCRATCH_FILE + 16)))
            self.assertEqual(call(m.arm, 'close', SCRATCH_FILE), 0)
        m.disk.reads.clear()
        m.run_mount(0x080237dc)  # stock completed RIFF/sidecar parsing and mounted the reel
        self.assertEqual(m.arm.get(0x20001290), 1)
        self.assertEqual(m.arm.get(FILE + 12), len(wav))
        self.assertEqual(m.arm.get(0x20001064), 44)
        self.assertIn((sectors[1], 1), m.disk.reads)
        self.assertNotIn((sectors[0], 1), m.disk.reads)
        self.assertEqual(m.contents('bank2/mg1.wav'), wav)
