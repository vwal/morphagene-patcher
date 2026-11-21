"""Execute the normal options hooks with stock's 63-character fgets chunks."""
import os
import unittest

from mgmod import stock
from tests.arm import *

NORMAL = 0x2002AE10
LIVE = 0x2002AE50
BUFFER = 0x20028000
NEXT = 0x080232FC
STOCK = 0x0802332A
AFTER_GETS = 0x0802330C
GETS_CALL = 0x08023304
VSOP = 0x200012A8
VRNG = 0x2002A606
# Emitted by both the module and options editor in mg204+c/c2.
LEGACY_RANGE = ('vrng {} //Varispeed range: 0 stock, 1 extended: '
                'vsop 0/1 +/-4x; vsop 2 forward stop to 8x with scale lock\n')


def call(a, symbol, *args):
    for reg, value in zip((UC_ARM_REG_R0, UC_ARM_REG_R1), args):
        a.uc.reg_write(reg, value)
    a.run(symbol)


def chunks(text):
    # mg204 fgets discards CR, retains LF, and terminates each 63-byte chunk.
    pending = ''
    for c in text:
        if c == '\r':
            continue
        pending += c
        if c == '\n' or len(pending) == 63:
            yield pending
            pending = ''
    if pending:
        yield pending


def feed(a, text, run_stock=False):
    forwarded = []
    for chunk in chunks(text):
        a.uc.reg_write(UC_ARM_REG_R11, BUFFER)
        a.run('opt_prepare_read', [GETS_CALL])
        a.uc.mem_write(BUFFER, chunk.encode() + b'\0')
        a.run('opt_preset_chunk', [AFTER_GETS])
        # Stock routes only its first fgets chunk to the state-line parser.
        if a.uc.reg_read(UC_ARM_REG_R9) != 1:
            a.uc.reg_write(UC_ARM_REG_R10, ord(chunk[0]))  # stock loads sl = fp[0]
            a.run('opt_parse', [NEXT] if run_stock else [NEXT, STOCK])
            if a.uc.reg_read(UC_ARM_REG_PC) == STOCK:
                forwarded.append(chunk)
    a.uc.reg_write(UC_ARM_REG_R0, 0)
    a.run('opt_preset_chunk', [AFTER_GETS])
    return forwarded


def begin(a):
    call(a, 'presets_normal_begin')
    a.uc.reg_write(UC_ARM_REG_R9, 0)


class NormalPresetChunks(unittest.TestCase):
    def setUp(self):
        self.a = Arm('options_keys', 'opt_parse')
        begin(self.a)

    def test_short_lines_and_final_line_without_newline(self):
        feed(self.a, '6 46345 0\r\nmpos 25\r\ngpos 100\nspos 0\nsplc 300')
        self.assertEqual(self.a.get(NORMAL), 15)
        self.assertEqual([self.a.get(NORMAL+4+i*4) for i in range(4)], [25, 100, 0, 300])
        self.assertEqual(self.a.get(NORMAL+60), 0)  # EOF disables stale parsing

    def test_all_twelve_keys_keep_independent_chunks_and_stage_bounds(self):
        keys = ('mpos', 'gpos', 'spos', 'splc', 'srrp', 'jitp', 'wrbp',
                'fbkp', 'evop', 'trst', 'sosp', 'vpos')
        values = (12, 34, 56, 300, 21, 43, 65, 87, 9, 16, 11, 99)
        self.a.uc.mem_write(LIVE, b'\xa5'*64)
        feed(self.a, 'header\n' + ''.join(f'{k} {v} //'+'x'*90+'\n' for k,v in zip(keys, values)))
        self.assertEqual(self.a.get(NORMAL), 0xfff)
        self.assertEqual([self.a.get(NORMAL+4+i*4) for i in range(12)], list(values))
        self.assertEqual(self.a.get(NORMAL+52), 1)
        self.assertEqual(self.a.get(NORMAL+56), 0)
        self.assertEqual(self.a.get(NORMAL+60), 0)
        self.assertEqual(bytes(self.a.uc.mem_read(LIVE, 64)), b'\xa5'*64)
        begin(self.a)
        self.assertEqual(bytes(self.a.uc.mem_read(NORMAL, 52)), bytes(52))
        self.assertEqual(self.a.get(NORMAL+52), 1)
        self.assertEqual(self.a.get(NORMAL+56), 1)

    def test_whole_logical_header_is_ignored(self):
        for header in ('mpos 40\n', 'x'*63 + 'gpos 80\n',
                       'x'*126 + 'splc 12\n', 'x'*62 + '\ngpos 80\n'):
            with self.subTest(header=header):
                begin(self.a)
                feed(self.a, header + 'spos 37\n')
                # The last case contains a genuine second line.
                self.assertEqual(self.a.get(NORMAL), 6 if header.startswith('x'*62+'\n') else 4)
                self.assertEqual(self.a.get(NORMAL+12), 37)

    def test_long_comment_continuations_cannot_become_options(self):
        for comment in ('//'+' '*61+'mpos 50\n',
                        '// '+'x'*60+'gpos 75'+' '*56+'splc 12\n'):
            with self.subTest(comment=comment):
                begin(self.a)
                feed(self.a, 'header\n' + comment + 'spos 27\n')
                self.assertEqual(self.a.get(NORMAL), 4)

    def test_prepare_read_sets_only_stock_buffer_and_preserves_file_pointer(self):
        a = self.a
        a.uc.mem_write(BUFFER-4, b'A'*72)
        a.uc.reg_write(UC_ARM_REG_R11, BUFFER)
        a.uc.reg_write(UC_ARM_REG_R2, 0x20024000)
        a.run('opt_prepare_read', [GETS_CALL])
        self.assertEqual(bytes(a.uc.mem_read(BUFFER-4,72)), b'AAAA' + b'\xff'*64 + b'AAAA')
        self.assertEqual(a.uc.reg_read(UC_ARM_REG_R0), BUFFER)
        self.assertEqual(a.uc.reg_read(UC_ARM_REG_R1), 64)
        self.assertEqual(a.uc.reg_read(UC_ARM_REG_R2), 0x20024000)

    def test_embedded_nul_preserves_next_real_option(self):
        for length in (11, 62, 63, 64, 125, 126, 127):
            with self.subTest(length=length):
                begin(self.a)
                malformed = ('spos 99\0' + 'x'*length)[:length]
                feed(self.a, 'header\nspos 17\n' + malformed + '\r\ngpos 42')
                self.assertEqual(self.a.get(NORMAL), 6)
                self.assertEqual(self.a.get(NORMAL+12), 17)
                self.assertEqual(self.a.get(NORMAL+8), 42)

    def test_embedded_nul_in_wrapped_header_and_comments_keeps_continuations_hidden(self):
        for prefix in ('header\0', '//\0', '//' + 'x'*61 + 'note\0'):
            with self.subTest(prefix=prefix):
                begin(self.a)
                wrapped = prefix.ljust(63 if len(prefix) < 63 else 126, 'x')
                following = feed(self.a, ('header\n' if prefix.startswith('/') else '') +
                                 wrapped + 'vsop 2\nspos 31\nvsop 1')
                self.assertEqual([chunk for chunk in following if chunk.startswith('vsop')], ['vsop 1'])
                self.assertEqual(self.a.get(NORMAL+12), 31)

    def test_legacy_range_comment_does_not_override_real_options(self):
        for mode in (0, 1, 2):
            for extended in (0, 1):
                with self.subTest(mode=mode, extended=extended):
                    begin(self.a)
                    layout = f'vsop {mode}\n'
                    legacy = LEGACY_RANGE.format(extended)
                    self.assertTrue(legacy[63:].startswith('vsop 2'))
                    # Also exercise an ordinary mod key in a header continuation
                    # and in the third chunk of an unrelated comment.
                    self.a.uc.mem_write(VRNG, bytes([1 - extended]))
                    self.a.uc.mem_write(0x2002A0F4, b'\0')
                    header = 'x'*63 + 'tape 1\n'
                    comment = '//' + 'x'*124 + 'tape 1\n'
                    forwarded = feed(self.a, header + layout + legacy + comment + 'omod 0\n')
                    self.assertEqual([line for line in forwarded if not line.startswith('//')],
                                     [layout, 'omod 0\n'])
                    self.assertEqual(self.a.uc.mem_read(VRNG, 1), bytes([extended]))
                    self.assertEqual(self.a.uc.mem_read(0x2002A0F4, 1), b'\0')

    @unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'), 'set MGMOD_FIRMWARE to run stock option dispatch')
    def test_stock_dispatch_reads_selected_layout_from_legacy_files(self):
        a = self.a
        a.uc.mem_write(0x08020000, stock.load(os.environ['MGMOD_FIRMWARE']))
        # Three fixed key constants kept in registers by stock's normal read loop.
        for reg, key in ((UC_ARM_REG_R4, b'vsop'), (UC_ARM_REG_R5, b'step'),
                         (UC_ARM_REG_R6, b'rmod')):
            a.uc.reg_write(reg, int.from_bytes(key, 'big'))
        for mode in (0, 1, 2):
            for extended in (0, 1):
                with self.subTest(mode=mode, extended=extended):
                    begin(a)
                    a.put(VSOP, 99)
                    a.uc.mem_write(VRNG, bytes([1 - extended]))
                    feed(a, f'6 46345 0\nvsop {mode}\n' + LEGACY_RANGE.format(extended),
                         run_stock=True)
                    self.assertEqual(a.get(VSOP), mode)
                    self.assertEqual(a.uc.mem_read(VRNG, 1), bytes([extended]))

    def test_valid_prefix_and_long_comment_is_kept_once(self):
        feed(self.a, 'header\nmpos 44 //'+' '*52+'mpos 99\n' +
             'gpos 55 //'+ 'x'*180+'\nsplc 300 //'+ 'z'*250+'\nspos 12\n')
        self.assertEqual(self.a.get(NORMAL), 15)
        self.assertEqual([self.a.get(NORMAL+4+i*4) for i in range(4)], [44, 55, 12, 300])

    def test_truncated_significant_line_disables_key_and_skips_remainder(self):
        feed(self.a, 'header\nmpos 23\nmpos 50'+' '*56+'gpos 80\nspos 31\n')
        self.assertEqual(self.a.get(NORMAL), 4)
        self.assertEqual(self.a.get(NORMAL+4), 23)  # never accepted truncated 50
        self.assertEqual(self.a.get(NORMAL+12), 31)
        # A 63-byte chunk with no terminator remains ambiguous even at EOF.
        begin(self.a)
        feed(self.a, 'header\nsplc 300'+' '*55)
        self.assertEqual(self.a.get(NORMAL), 0)

    def test_exact_boundary_newline_and_following_key_are_not_continuations(self):
        line = 'mpos 17'+' '*55+'\n'
        self.assertEqual(len(line), 63)
        feed(self.a, 'header\n'+line+'gpos 18\n')
        self.assertEqual(self.a.get(NORMAL), 3)
        self.assertEqual(self.a.get(NORMAL+4), 17)
        self.assertEqual(self.a.get(NORMAL+8), 18)

    def test_fresh_transaction_resets_unfinished_comment_and_header_state(self):
        feed(self.a, 'header\n//'+'x'*61)
        begin(self.a)
        feed(self.a, 'header\nmpos 42\n')
        self.assertEqual(self.a.get(NORMAL), 1)
        self.assertEqual(self.a.get(NORMAL+4), 42)

    def test_direct_parser_and_existing_options_remain_available(self):
        self.a.uc.mem_write(BUFFER, b'mpos 83\0')
        call(self.a, 'presets_normal_parse', BUFFER)
        self.assertEqual(self.a.get(NORMAL), 1)
        self.assertEqual(self.a.get(NORMAL+4), 83)
        # An ordinary first chunk may reach older mod keys without preset parsing.
        self.a.put(NORMAL+60, 0)
        self.a.uc.mem_write(BUFFER, b'tape 0\0')
        self.a.uc.mem_write(0x2002A0F4, b'\1')
        self.a.uc.reg_write(UC_ARM_REG_R11, BUFFER)
        self.a.run('opt_parse', [NEXT, STOCK])
        self.assertEqual(bytes(self.a.uc.mem_read(0x2002A0F4, 1)), b'\0')

    def test_chunk_wrapper_preserves_integer_float_flags_and_stack(self):
        a = self.a
        a.uc.mem_write(BUFFER, b'header\n\0')
        registers = [UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
                     UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
                     UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11,
                     UC_ARM_REG_R12]
        for i, reg in enumerate(registers):
            a.uc.reg_write(reg, 0x12340000+i)
        a.uc.reg_write(UC_ARM_REG_R0, BUFFER)
        a.uc.reg_write(UC_ARM_REG_R11, BUFFER)
        before = {reg: a.uc.reg_read(reg) for reg in registers}
        for i in range(32):
            a.uc.reg_write(UC_ARM_REG_S0+i, 0x3F800000+i)
        # Establish Unicorn's active FP context before the wrapper's VPUSH.
        a.syms['fp_seed'] = 0x0805FF00
        a.uc.mem_write(0x0805FF00, bytes.fromhex('e1ee100a7047'))
        a.uc.reg_write(UC_ARM_REG_R0, 0x01000010)
        a.run('fp_seed')
        a.uc.reg_write(UC_ARM_REG_R0, before[UC_ARM_REG_R0])
        a.uc.reg_write(UC_ARM_REG_APSR, 0xA8000000)
        a.uc.mem_write(LIVE, b'\xa5'*64)
        a.run('opt_preset_chunk', [AFTER_GETS])
        for reg, value in before.items():
            self.assertEqual(a.uc.reg_read(reg), value+(reg == UC_ARM_REG_R9))
        for i in range(32):
            self.assertEqual(a.uc.reg_read(UC_ARM_REG_S0+i), 0x3F800000+i)
        self.assertEqual(a.uc.reg_read(UC_ARM_REG_APSR) & 0xF8000000, 0xA8000000)
        self.assertEqual(a.uc.reg_read(UC_ARM_REG_FPSCR), 0x01000010)
        self.assertEqual(a.uc.reg_read(UC_ARM_REG_SP), SP)
        self.assertEqual(bytes(a.uc.mem_read(LIVE, 64)), b'\xa5'*64)
        # EOF must not inspect whatever pointer remains in fp.
        a.uc.reg_write(UC_ARM_REG_R0, 0)
        a.uc.reg_write(UC_ARM_REG_R11, 0xDEADBEEF)
        a.run('opt_preset_chunk', [AFTER_GETS])
        self.assertEqual(a.get(NORMAL+60), 0)


if __name__ == '__main__':
    unittest.main()
