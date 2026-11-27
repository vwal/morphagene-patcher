"""Exercise the bank-only open modes and WAV error exits in linked mg204."""
import os
import unittest

from tests.arm import UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R2
from tests.test_bank_mount import COUNT, FILE, FS, HEADER, Mount, REEL, SCRATCH_FILE
from tests.test_settings_reload import CARD, STAT, call

UNMOUNTED = 0x08022f96
OPENED_SELECT = 0x080230a2
LOADED = 0x20028ff0


@unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'), 'requires official mg204')
class BankFileSafety(unittest.TestCase):
    def mount(self, payload=HEADER):
        m = Mount(b'1 45875 0\nbank 2\n')
        m.directory('bank2')
        m.write('bank2/mg1.wav', payload)
        return m

    def remount(self, m):
        self.assertEqual(m.arm.get(CARD), 0)
        self.assertEqual(m.arm.uc.mem_read(LOADED, 2), bytes(2))
        self.assertEqual(call(m.arm, 'mount', FS, m.path(''), 1), 0)

    def test_bank_mount_rejects_nonempty_unreadable_or_invalid_wav_intact(self):
        for fault in ('bad file', 'read failure'):
            with self.subTest(fault=fault):
                payload = b'do not overwrite'*8 if fault=='bad file' else HEADER
                m = self.mount(payload)
                a = m.arm
                self.assertEqual(call(a,'open',SCRATCH_FILE,m.path('bank2/mg1.wav'),1),0)
                sector = m.disk.sector(a.get(SCRATCH_FILE+16))
                self.assertEqual(call(a,'close',SCRATCH_FILE),0)
                if fault=='read failure':
                    def faulty_read(a):
                        if a.uc.reg_read(UC_ARM_REG_R2)==sector:
                            m.disk.result(1)
                        else:
                            m.disk.read(a)
                    a.calls[0x0802f8fc] = faulty_read
                m.disk.writes.clear()
                m.run_mount(UNMOUNTED)
                self.assertNotIn(sector, m.disk.writes)
                a.calls[0x0802f8fc] = m.disk.read
                self.remount(m)
                self.assertEqual(m.contents('bank2/mg1.wav'), payload)

    def test_auto_created_and_existing_empty_reels_receive_native_header(self):
        for missing in (False, True):
            with self.subTest(missing=missing):
                m = Mount(b'1 45875 0\nbank 2\n') if missing else self.mount(b'')
                m.run_mount(0x080237dc)
                self.assertEqual(m.arm.get(CARD), 1)
                self.assertEqual(m.arm.get(FILE+12), 44)
                self.assertEqual(m.arm.uc.mem_read(LOADED,2), bytes([2,1]))
                self.assertEqual(call(m.arm,'close',FILE), 0)
                wav = m.contents('bank2/mg1.wav')
                self.assertEqual((wav[:4],wav[8:12],wav[36:40]), (b'RIFF',b'WAVE',b'data'))

    def test_occupied_new_slot_and_missing_existing_selection_fail_closed(self):
        for request in ('create', 'select'):
            with self.subTest(request=request):
                m = self.mount()
                a = m.arm
                m.boot()
                if request=='create':
                    # Simulated card change after counting. The first free slot
                    # now contains another reel, although COUNT is still one.
                    m.write('bank2/mg2.wav', b'never replace this recording')
                    a.syms['request'] = 0x08023076
                    args = (1,)
                else:
                    # The catalog offered a second reel which no longer exists.
                    a.put(COUNT,2)
                    a.put(REEL,2)
                    a.syms['request'] = 0x08023250
                    args = (2,2)
                a.put(CARD,1)
                call(a,'request',*args,stops=[UNMOUNTED,OPENED_SELECT])
                self.assertEqual(a.uc.reg_read(UC_ARM_REG_PC),UNMOUNTED)
                self.remount(m)
                self.assertEqual(m.contents('bank2/mg1.wav'),HEADER)
                if request=='create':
                    self.assertEqual(m.contents('bank2/mg2.wav'),b'never replace this recording')
                else:
                    self.assertEqual(call(a,'stat',m.path('bank2/mg2.wav'),0),4)

    def test_manual_new_slot_and_existing_selection_have_correct_modes(self):
        for new in (False, True):
            with self.subTest(new=new):
                m=self.mount()
                a=m.arm
                if not new:
                    m.write('bank2/mg2.wav',HEADER)
                m.boot()
                a.put(CARD,1)
                if new:
                    a.syms['request']=0x08023076
                    args=(1,)
                else:
                    a.put(REEL,2)
                    a.syms['request']=0x08023250
                    args=(2,2)
                call(a,'request',*args,stops=[UNMOUNTED,OPENED_SELECT])
                self.assertEqual(a.uc.reg_read(UC_ARM_REG_PC),OPENED_SELECT)
                self.assertEqual(a.get(FILE+12),0 if new else len(HEADER))
                self.assertEqual(a.uc.mem_read(LOADED,2),bytes([2,2]))

    def test_first_free_scan_fails_closed_on_io_error_or_stale_count(self):
        for status in (1,0):  # FR_DISK_ERR, or every slot is now occupied
            with self.subTest(stat=status):
                m=self.mount()
                a=m.arm
                m.run_mount(0x080236de)  # options/catalog ready, primary FIL not yet opened
                a.syms['first_free']=0x08023152
                a.calls[STAT]=lambda a: a.uc.reg_write(UC_ARM_REG_R0,status)
                m.disk.writes.clear()
                call(a,'first_free',stops=[UNMOUNTED,0x080231fc])
                self.assertEqual(a.uc.reg_read(UC_ARM_REG_PC),UNMOUNTED)
                self.assertEqual(m.disk.writes,[])
                del a.calls[STAT]
                self.remount(m)
                self.assertEqual(m.contents('bank2/mg1.wav'),HEADER)
