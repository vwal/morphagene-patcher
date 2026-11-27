"""Normal card rewrites and atomic live changes of the Development 14 modes."""
import unittest

from tests import test_preset_chunks as normal, test_settings_reload as live
from tests.arm import Arm
from tests.test_preset_options import printf_capture

NTCH = 0x2002a61d
BANK = 0x2002a61f


class NotchThroughOptions(unittest.TestCase):
    def test_bank_normal_loads_older_cards_and_persists_selected_value(self):
        a = Arm('options_keys', 'opt_parse')
        calls = printf_capture(a)
        for n in range(9):
            normal.begin(a)
            normal.feed(a, '1 0 0\nntch 3\nthru 1\nbank\t'+str(n)+' //'+'x'*80+'\n')
            self.assertEqual(bytes(a.uc.mem_read(NTCH, 3)), bytes((4, 1, n)))
            # Use the same byte as a successful panel bank change.
            selected = n % 8 + 1
            a.uc.mem_write(BANK, bytes((selected,)))
            calls.clear()
            a.run('opt_write', [0x08024566])
            bank_lines = [fmt % value for fmt, value in calls if fmt.startswith('bank ')]
            self.assertEqual(len(bank_lines), 1)
            self.assertEqual(bank_lines[0].split()[:2], ['bank', str(selected)])
            self.assertLessEqual(len(bank_lines[0].encode()), 63)
            normal.begin(a)
            normal.feed(a, '1 0 0\n'+bank_lines[0])
            self.assertEqual(a.uc.mem_read(BANK, 1), bytes((selected,)))
            normal.begin(a)
            normal.feed(a, '1 0 0\n// firmware version 204+c6-nt\nntch 3\nthru 1\n')
            self.assertEqual(bytes(a.uc.mem_read(NTCH, 3)), bytes((4, 1, 0)))

    def test_bank_normal_invalid_and_truncated_values_preserve_last_valid(self):
        a = Arm('options_keys', 'opt_parse')
        bad = ['bank 9', 'bank 01', 'bank -1', 'bank 2.0', 'banking 2',
               'bank 3'+' '*57+'4', '//'+' '*61+'bank 4']
        for line in bad:
            normal.begin(a)
            normal.feed(a, 'bank 7\nbank 5\n'+line+'\n')
            self.assertEqual(a.uc.mem_read(BANK, 1), b'\x05', line)

    def test_normal_roundtrip_and_legacy_card_after_explicit_override(self):
        a = Arm('options_keys', 'opt_parse')
        calls = printf_capture(a)
        for notch in (3, 0, None, 1, 2):
            for thru in (2, 1, 0, None):
                with self.subTest(ntch=notch, thru=thru):
                    normal.begin(a)
                    source = '1 0 0\r\nvctr 1\n'
                    if notch is not None:
                        source += f'ntch\t{notch} //' + 'x'*63 + '\r\n'
                    if thru is not None:
                        source += f'thru {thru}'
                    normal.feed(a, source)
                    expect = bytes([notch+1 if notch is not None else 0, thru or 0])
                    self.assertEqual(a.uc.mem_read(NTCH, 2), expect)
                    calls.clear()
                    a.run('opt_write', [0x08024566])
                    lines = [fmt % v for fmt, v in calls if fmt.startswith(('ntch ', 'thru '))]
                    emitted = [line.split()[:2] for line in lines]
                    self.assertEqual(emitted, ([['ntch', str(notch)]] if notch is not None else [])
                                     + [['thru', str(thru or 0)]])
                    self.assertTrue(all(len(line.encode()) <= 63 for line in lines))
                    a.uc.mem_write(NTCH, b'\xff\xff')
                    normal.begin(a)
                    normal.feed(a, '1 0 0\n'+''.join(lines))
                    self.assertEqual(a.uc.mem_read(NTCH, 2), expect)

    def test_invalid_values_and_continuations_do_not_become_options(self):
        a = Arm('options_keys', 'opt_parse')
        for key, bad in (('ntch', ('4', '-1', '01', '3.0', '1!')),
                         ('thru', ('3', '-1', '01', '1.0', '1!'))):
            for value in bad:
                normal.begin(a)
                normal.feed(a, f'1 0 0\n{key} {value}\n' + '//' + ' '*61 + 'ntch 1\n')
                self.assertEqual(a.uc.mem_read(NTCH, 2), bytes(2))
            normal.begin(a)
            normal.feed(a, f'1 0 0\n{key} 1' + ' '*57 + '2\n')
            self.assertEqual(a.uc.mem_read(NTCH, 2), bytes(2))

    def test_live_commit_preserves_omissions_and_explicit_zero(self):
        a = live.arm()
        for text, expected in (
                ('ntch 3', (4, 0)), ('thru 2', (4, 2)), ('vctr 1', (4, 2)), ('thru 1', (4, 1)),
                ('ntch 0', (1, 1)), ('thru 0', (1, 0)), ('thru 1\nntch 2', (3, 1))):
            a.put(live.CARD, 0)
            before = bytes(a.uc.mem_read(NTCH, 2))
            live.stage(a, ('1 0 0\r\n'+text).encode(), chunks=3)
            self.assertEqual(a.get(live.PENDING), 1, text)
            self.assertEqual(a.uc.mem_read(NTCH, 2), before)
            live.call(a, 'reload_commit')
            self.assertEqual(a.uc.mem_read(NTCH, 2), bytes(expected), text)

    def test_bad_or_duplicate_line_rejects_every_staged_change(self):
        for bad in ('ntch 4', 'thru 3', 'ntch 03', 'thru 1.0', 'ntch 1\nntch 1',
                    'thru 0\nthru 1', 'ntch 0\nthru 0\nvsop 7'):
            a = live.arm()
            a.uc.mem_write(NTCH, b'\x04\x01')
            live.stage(a, ('1 0 0\nvctr 1\n'+bad+'\n').encode())
            self.assertEqual(a.get(live.PENDING), 0, bad)
            live.call(a, 'reload_commit')
            self.assertEqual(a.uc.mem_read(NTCH, 2), b'\x04\x01')
            self.assertEqual(a.uc.mem_read(0x2002a619, 1), b'\0')
