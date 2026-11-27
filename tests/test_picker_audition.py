"""Use c7's mounted filesystem, buttons, audio callback and real stereo WAV data."""
import os
import struct
import unittest
from unicorn import UC_HOOK_CODE

from tests.arm import (SP, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R6, UC_ARM_REG_R7,
                       UC_ARM_REG_R8, UC_ARM_REG_R11, UC_ARM_REG_S16, UC_ARM_REG_SP, bits)
from tests.test_bank_mount import DATA, HEADER, LIMIT, MAIN_SP, SCRATCH_FILE, TRANSFERRED, Mount
from tests import test_settings_reload
from tests.test_settings_reload import FLAGS, SAMPLES, call

AUDT, PHASE, ORGANIZE = 0x20028fa4, 0x20028f58, 0x20021c70
MAIN, AFTER_PICKER = 0x08022fbc, 0x08022fc2


def stereo_wav(pairs, boundaries=()):
    """Build canonical 48 kHz float stereo audio with optional splice end markers."""
    pcm = b''.join(struct.pack('<ff', l/32768, r/32768) for l, r in pairs)
    wave = bytearray(HEADER + pcm)
    struct.pack_into('<I', wave, 40, len(pcm))
    if boundaries:
        entries = b''.join(struct.pack('<II4sIII', i, end, b'data', 0, 0, end)
                           for i, end in enumerate(boundaries))
        wave.extend(struct.pack('<4sII', b'cue ', len(entries) + 4, len(boundaries)) + entries)
    struct.pack_into('<I', wave, 4, len(wave) - 8)
    return bytes(wave)


class Picker:
    def __init__(self, option):
        self.volume = m = Mount(b'1 45875 0\nbank 1\nomod 1\n' + option)
        m.disk.file(1, b'MG1     WAV', m.disk.reel_cluster,
                    stereo_wav([(600, -400)] * 200, [200]))
        m.directory('bank2')
        m.write('bank2/mg1.wav', stereo_wav([(4096, -1024)] * 9 + [(-2048, 8192)] * 11,
                                           [9, 20]))
        a = self.a = m.arm
        a.uc.mem_map(0x40000000, 0x1000)
        a.uc.mem_map(0xd0050000, 0x2000000 - 0x50000)
        # Simulate hardware-ready flags during stock audio initialization.
        ready_flags = {0x08026944: 0x08026957, 0x0802695c: 0x08026967}
        def ready(uc, pc, size, context):
            if pc in ready_flags:
                uc.reg_write(UC_ARM_REG_PC, ready_flags[pc])
        hook = a.uc.hook_add(UC_HOOK_CODE, ready, begin=0x08026944, end=0x0802695c)
        a.syms.update(init=0x08026730, timer=0x08024718, main=MAIN, audio=0x08027518)
        call(a, 'init')
        a.uc.hook_del(hook)
        for address, val in ((0x20001054, 1), (0x200012e4, 1), (0x20021410, bits(1/4095)),
                             (0x200220fc, 0xd0000000), (0x20022100, 0xd1000000),
                             (0x20021ca4, 48000)):
            a.put(address, val)
        a.uc.reg_write(UC_ARM_REG_S16, bits(1/32768))
        a.calls[0x0802dcd4] = lambda arm: arm.uc.reg_write(UC_ARM_REG_R0, 1)
        m.run_mount(0x080237dc)
        a.put(FLAGS, 4)  # finish the native reel transfer
        self.main(0x08022f7e)
        a.put(0x20001020, 1)
        a.put(0x40020010, 32)
        a.put(0x20022080, 0)
        a.put(0x20022078, 4095)
        a.put(0x200220a0, bits(1/4095))

    def main(self, stop=AFTER_PICKER):
        a = self.a
        for reg, value in ((UC_ARM_REG_SP, MAIN_SP), (UC_ARM_REG_R6, 1),
                           (UC_ARM_REG_R7, FLAGS), (UC_ARM_REG_R8, LIMIT),
                           (UC_ARM_REG_R11, MAIN_SP + 228)):
            a.uc.reg_write(reg, value)
        a.run('main', [stop], count=3000000)
        assert a.uc.reg_read(UC_ARM_REG_PC) == stop
        a.uc.reg_write(UC_ARM_REG_SP, SP)

    def buttons(self, splice=False, rec=False, elapsed=0):
        self.a.put(0x40021010, 4 if splice else 0)
        self.a.put(0x40021810, 4096 if rec else 0)
        self.a.put(SAMPLES, self.a.get(SAMPLES) + elapsed)
        for _ in range(8):
            test_settings_reload.ReloadIntegration().timer_tick(self.a, False)

    def enter(self):
        self.buttons()
        self.buttons(splice=True)
        self.buttons(splice=True, rec=True)
        self.buttons(splice=True, rec=True, elapsed=7000)
        self.main(0x08023274)
        self.buttons(splice=True, rec=True, elapsed=26000)
        self.buttons(splice=True, rec=True, elapsed=320000)
        self.main()
        self.buttons()

    def choose(self, adc):
        self.a.put(ORGANIZE, adc)
        self.buttons()
        self.main()
        self.buttons(splice=True)
        self.buttons(splice=True, rec=True)
        self.buttons()
        self.main()

    def samples(self, adc):
        self.a.put(ORGANIZE, adc)
        self.buttons()
        self.main()
        self.buttons(elapsed=19200)  # 200 ms on the hardware's 96 kHz sample counter
        self.main()
        call(self.a, 'audio', DATA, DATA + 64, 16)
        return list(struct.iter_unpack('<hh', self.a.uc.mem_read(DATA + 64, 32)))


@unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'), 'requires official mg204')
class PickerAudition(unittest.TestCase):
    def test_browse_another_bank_then_cancel(self):
        for option, enabled in ((b'', True), (b'audt 0\n', True), (b'audt 1\n', False)):
            with self.subTest(option=option):
                picker = Picker(option)
                arm = picker.a
                self.assertEqual(arm.uc.mem_read(AUDT, 1), bytes([int(not enabled)]))
                picker.enter()
                self.assertEqual(arm.uc.mem_read(PHASE, 1), b'\x02')
                before = dict(picker.volume.disk.sectors)
                picker.choose(4095)
                self.assertEqual(arm.uc.mem_read(PHASE, 1), b'\x04')
                first = picker.samples(0)
                picker.choose(0)
                self.assertEqual(arm.uc.mem_read(PHASE, 1), b'\x06')
                second = picker.samples(4095)
                self.assertEqual(first == [(4096, -1024)] * 8, enabled)
                self.assertEqual(second == [(-2048, 8192)] * 8, enabled)
                for _ in range(12):
                    test_settings_reload.ReloadIntegration().timer_tick(arm, True)
                picker.buttons()
                picker.main()
                self.assertEqual(arm.uc.mem_read(PHASE, 1), b'\x00')
                self.assertEqual(bytes(arm.uc.mem_read(0x20028ff0, 2)), b'\x01\x01')
                self.assertEqual(picker.volume.disk.sectors, before)

    def test_native_card_writer_identifies_the_release_and_preserves_the_option(self):
        for option, expected in ((b'', 0), (b'audt 0\n', 0), (b'audt 1\n', 1)):
            with self.subTest(option=option):
                picker = Picker(option)
                a, volume = picker.a, picker.volume
                a.put(FLAGS, 0x80)  # ordinary options save request in the mounted dispatcher
                picker.main(0x08022f7e)
                buffer = 0x31000000
                a.uc.mem_map(buffer, 8192)
                self.assertEqual(call(a, 'open', SCRATCH_FILE, volume.path('options.txt'), 1), 0)
                self.assertEqual(call(a, 'read', SCRATCH_FILE, buffer, 8192, TRANSFERRED), 0)
                text = bytes(a.uc.mem_read(buffer, a.get(TRANSFERRED))).decode('ascii')
                self.assertEqual(call(a, 'close', SCRATCH_FILE), 0)
                self.assertEqual(text.splitlines().count('// firmware version 204+c7'), 1)
                self.assertEqual([line.split()[:2] for line in text.splitlines()
                                  if line.startswith('audt ')], [['audt', str(expected)]])
