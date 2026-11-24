"""Exercise mg204's timed card check on a cached, header-only reel."""
import os
import struct
import unittest

from mgmod import registry, stock
from mgmod.module import branch_w
from tests.arm import Arm, SP, UC_ARM_REG_PC, UC_ARM_REG_R6, UC_ARM_REG_R7, UC_ARM_REG_SP
from tests.test_reload_filesystem import FatDisk
from tests.test_settings_reload import (
    CARD, FLAGS, HASH_READY, MOD, OPEN, PHASE, RESULT, SAMPLES, SETTINGS, SHIFT,
    call, tick,
)

# The real main stack frame holds the mounted filesystem and the active WAV.
MAIN_SP = SP - 4096
FILE, FS = MAIN_SP + 844, MAIN_SP + 1948
PATH = 0x20028000
PERIOD = 192000
HEADER = struct.pack('<4sI4s4sIHHIIHH4sI', b'RIFF', 36, b'WAVE', b'fmt ',
                     16, 3, 2, 48000, 384000, 8, 32, b'data', 0)


def mounted_reel(fat32=False, data=HEADER):
    a = Arm('settings_reload', 'reload_mount')
    img = stock.load(os.environ['MGMOD_FIRMWARE'])
    a.uc.mem_write(0x08020000, img)
    a.uc.mem_write(0x20000000, img[0x27250:0x28400])
    for address, _, symbol in registry.module('settings_reload').hooks:
        a.uc.mem_write(address, branch_w(address, a.syms[symbol]))
    a.uc.ctl_remove_cache(0x08020000, 0x08060000)
    a.uc.mem_write(PATH, b'\0mg9.wav\0')
    a.syms.update(mount=0x0803219c, open=OPEN, seek=0x08032be8,
                  write=0x08032688, sync=0x080326e0, idle=0x08022fbc)
    disk = FatDisk(a, fat32=fat32)
    disk.file(1, b'MG9     WAV', disk.reel_cluster, data)
    # Use the real driver status check with a permanently low detect pin.
    # Model a hardware transfer failure separately when the card is pulled.
    del a.calls[0x0802f8e4]
    a.uc.mem_write(0x2000063c, bytes(1))
    a.put(0x40021c10, 0)
    a.put(SETTINGS, 0x5354504f)
    a.put(MOD, 0x53484654)
    a.put(0x20001020, 14)
    a.put(0x20001040, 9)
    a.put(0x20001064, 44)
    a.put(0x200012a0, 1)
    a.put(CARD, 1)
    assert call(a, 'mount', FS, PATH, 1) == 0
    assert call(a, 'open', FILE, PATH + 1, 3) == 0
    assert call(a, 'seek', FILE, len(data)) == 0
    call(a, 'reload_service', FS, FILE)
    assert a.get(HASH_READY) == 1
    return a, disk


def poll(a, elapsed):
    a.put(SAMPLES, elapsed)
    a.uc.reg_write(UC_ARM_REG_SP, MAIN_SP)
    a.uc.reg_write(UC_ARM_REG_R6, 1)
    a.uc.reg_write(UC_ARM_REG_R7, FLAGS)
    # Success/no check rejoins mounted dispatch. Failure deregisters the
    # filesystem and rejoins the non-mounted branch of the native main loop.
    a.run('idle', [0x0802321e, 0x08022fe8, 0x08022f96], count=500000)
    return a.uc.reg_read(UC_ARM_REG_PC)


@unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'), 'requires official mg204')
class EmptyReelCard(unittest.TestCase):
    def test_pull_arm_reinsert_and_write_after_erasing_all_audio(self):
        for fat32 in (False, True):
            with self.subTest(fat32=fat32):
                a, disk = mounted_reel(fat32)
                reads = len(disk.reads)
                poll(a, PERIOD - 1)
                self.assertEqual(len(disk.reads), reads)
                tick(a, 6000, present=True)
                self.assertEqual(a.get(PHASE), 0)
                poll(a, PERIOD + 1)
                self.assertEqual(a.get(CARD), 1)
                self.assertEqual(disk.reads[reads:], [(0, 1)])
                self.assertEqual(a.get(FILE+8), len(HEADER))
                self.assertEqual(disk.writes, [])
                disk.inserted = False
                poll(a, 2*(PERIOD+1))
                self.assertEqual(a.get(CARD), 0, 'absent medium still reported as mounted')
                self.assertEqual(a.uc.mem_read(FS, 1), bytes(1))
                self.assertEqual(a.get(HASH_READY), 1)
                a.put(SHIFT, 2)
                for samples in (400000, 448000):
                    a.put(SAMPLES, samples)
                    call(a, 'reload_tick', 4, 0, 0)
                self.assertEqual(a.get(PHASE), 2)
                disk.inserted = True
                self.assertEqual(call(a, 'mount', FS, PATH, 1), 0)
                self.assertEqual(call(a, 'reload_mounted', 0), 1)
                self.assertEqual(call(a, 'reload_service', FS, FILE), 1)
                call(a, 'reload_commit')
                self.assertEqual(a.get(RESULT), 1)
                self.assertEqual(a.get(CARD), 1)
                self.assertEqual(a.uc.mem_read(0x2002a610, 1), b'\1')
                self.assertEqual(a.get(FILE+8), 44)
                self.assertEqual(disk.writes, [])
                # The reconnected header-only reel accepts its first audio.
                a.uc.mem_write(PATH+64, bytes(range(32)))
                self.assertEqual(call(a, 'write', FILE, PATH+64, 32, PATH+100), 0)
                self.assertEqual(a.get(PATH+100), 32)
                self.assertEqual(call(a, 'sync', FILE), 0)
                self.assertEqual(disk.sectors[disk.sector(disk.reel_cluster)][:76],
                                 HEADER + bytes(range(32)))

    def test_long_reel_uses_existing_seek_check(self):
        a, disk = mounted_reel(data=bytes(1536))
        disk.reads.clear()
        poll(a, PERIOD + 1)
        self.assertEqual(a.get(CARD), 1)
        self.assertNotIn((0, 1), disk.reads)
        self.assertEqual(a.get(FILE+8), 1536)

    def test_reinsert_without_shift_returns_to_normal_mount(self):
        a, disk = mounted_reel()
        disk.inserted = False
        poll(a, PERIOD + 1)
        self.assertEqual(a.get(CARD), 0)
        tick(a, 30000, shift=False)
        disk.inserted = True
        self.assertEqual(call(a, 'mount', FS, PATH, 1), 0)
        self.assertEqual(call(a, 'reload_mounted', 0), 0)
        self.assertEqual(a.get(PHASE), 0)
