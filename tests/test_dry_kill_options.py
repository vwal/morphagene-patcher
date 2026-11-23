"""Exercise the complete normal parser, writer and atomic live reload for dryk and dlen."""
import unittest

from tests.arm import Arm
from tests import test_settings_reload as live
from tests import test_preset_chunks as normal
from tests.test_preset_options import printf_capture


DRYK = 0x2002A61A
DLEN = 0x2002A61B


class DryKillOptions(unittest.TestCase):
    def test_ordinary_read_write_reread(self):
        a = Arm('options_keys', 'opt_parse')
        a.uc.mem_write(DRYK-2, b'\x01\x01\x00\x77')
        calls = printf_capture(a)
        for value in (2, 1, 0):
            normal.begin(a)
            normal.feed(a, f'1 0 0\nvsop 1\n\tdryk\t{value} // fader\r\n')
            self.assertEqual(bytes(a.uc.mem_read(DRYK-2, 4)), bytes((1, 1, value, 0x77)))
            calls.clear()
            a.run('opt_write', [0x08024566])
            lines = [fmt % v for fmt, v in calls if fmt.startswith('dryk ')]
            self.assertEqual(len(lines), 1)
            self.assertLessEqual(len(lines[0].encode('ascii')), 63)
            a.uc.mem_write(DRYK, b'\x7f')
            normal.begin(a)
            normal.feed(a, '1 0 0\n'+lines[0])
            self.assertEqual(a.uc.mem_read(DRYK, 1), bytes([value]))

    def test_normal_rejects_garbage_and_wrapped_comment(self):
        a = Arm('options_keys', 'opt_parse')
        for text in ('dryk 3', 'dryk 0.5', 'dryk 02', 'dryk 2 tail', 'dryk 2/x', 'drykX 2',
                     'dryk', 'dryk -1', 'dryk 2'+' '*80+'tail', 'dryk 2\x00extra',
                     '//'+'x'*61+'dryk 2'):
            normal.begin(a)
            normal.feed(a, 'header\ndryk 1\n'+text+'\n')
            self.assertEqual(a.uc.mem_read(DRYK, 1), b'\x01', text)

    def test_live_omission_failure_and_atomic_commit(self):
        for line, intended, accepted in (('dryk 2', 2, True), ('dryk 0', 0, True),
                                         ('dryk 1', 1, True), ('', 1, True),
                                         ('dryk 2\ndryk 0', 1, False),
                                         ('dryk 02', 1, False), ('dryk 2 tail', 1, False),
                                         ('dryk -1', 1, False), ('dryk 3', 1, False),
                                         ('dryk 2\nmono 9', 1, False)):
            a = live.arm()
            a.uc.mem_write(DRYK-1, b'\x75\x01\x43')
            live.stage(a, ('1 0 0\nvrng 1\n'+line+'\n').encode())
            self.assertEqual(a.uc.mem_read(DRYK, 1), b'\x01', line)
            self.assertEqual(a.get(live.PENDING), int(accepted), line)
            live.call(a, 'reload_commit')
            self.assertEqual(bytes(a.uc.mem_read(DRYK-1, 3)), bytes([0x75, intended, 0x43]), line)
            self.assertEqual(a.uc.mem_read(0x2002A606, 1), bytes([accepted]), line)

    def test_length_option_roundtrip_and_malformed_lines(self):
        a = Arm('options_keys', 'opt_parse')
        calls = printf_capture(a)
        for value in (1, 0):
            normal.begin(a)
            normal.feed(a, f'1 0 0\n  dlen\t{value} // length\r\n')
            self.assertEqual(a.uc.mem_read(DLEN, 1), bytes([value]))
            calls.clear()
            a.run('opt_write', [0x08024566])
            lines = [fmt % v for fmt, v in calls if fmt.startswith('dlen ')]
            self.assertEqual(len(lines), 1)
            self.assertLessEqual(len(lines[0].encode('ascii')), 63)
            a.uc.mem_write(DLEN, b'\x7f')
            normal.begin(a)
            normal.feed(a, '1 0 0\n' + lines[0])
            self.assertEqual(a.uc.mem_read(DLEN, 1), bytes([value]))
        for bad in ('2', '01', '-1', '1 trailing', '1'+' '*65+'x', '1\x00x'):
            normal.begin(a)
            normal.feed(a, f'1 0 0\ndlen 0\n//'+ 'x'*61+'dlen 1\n' + f'dlen {bad}\n')
            self.assertEqual(a.uc.mem_read(DLEN, 1), b'\x00', bad)

    def test_dlen_commits_independently_or_rejects_entire_reload(self):
        for extra, accepted, expected in (
                ('dlen 1', True, 1), ('dlen 0', True, 0), ('', True, 0),
                ('dlen 01', False, 0), ('dlen 2', False, 0), ('dlen 1\ndlen 0', False, 0),
                ('dlen 1\nmono 9', False, 0)):
            a = live.arm()
            a.uc.mem_write(DRYK, b'\x01\x00\x43')
            live.stage(a, f'1 0 0\ndryk 2\n{extra}\n'.encode())
            self.assertEqual(a.get(live.PENDING), int(accepted), extra)
            self.assertEqual(bytes(a.uc.mem_read(DRYK, 3)), b'\x01\x00\x43', extra)
            live.call(a, 'reload_commit')
            self.assertEqual(bytes(a.uc.mem_read(DRYK, 3)), bytes([2 if accepted else 1, expected, 0x43]), extra)
