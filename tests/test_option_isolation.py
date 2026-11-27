"""Check which configuration bytes each valid option writes on ordinary and live reads."""
import os
import unittest
from itertools import chain

from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R3, UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_SP

from mgmod import stock
from tests.arm import Arm, value as float_from_word
from tests import test_preset_chunks as normal
from tests import test_preset_options as preset
from tests import test_settings_reload as live


# Independent expectations for the configured value addresses, write widths,
# and legal inputs. Order is the bit order of the settings-only reader's masks.
CHORD_RATIOS = ('0.06250', '-0.06250', '1', '16.00000000', '+16', '-16',
                '1.23456789', '-1.23456789', '0.99999999', '0.10000000',
                '15.99999999', '+0.06250000')
SWITCH = range(2)
OPTIONS = (
    ('vsop', 0x200012a8, 4, range(3)), ('pmod', 0x200012b0, 4, range(3)),
    ('omod', 0x200012b4, 4, SWITCH), ('cvop', 0x200012bc, 4, SWITCH),
    ('ckop', 0x200012c0, 4, range(3)), ('rsop', 0x200012c4, 4, SWITCH),
    ('pmin', 0x200012c8, 4, SWITCH), ('inop', 0x200012cc, 4, SWITCH),
    ('gnsm', 0x200012d0, 4, SWITCH),
    ('mcr1', 0x200012d4, 4, CHORD_RATIOS), ('mcr2', 0x200012d8, 4, CHORD_RATIOS),
    ('mcr3', 0x200012dc, 4, CHORD_RATIOS),
    ('tape', 0x2002a0f4, 1, SWITCH), ('octl', 0x2002a0f5, 1, range(5)),
    ('fxsl', 0x2002a0f6, 1, range(3)), ('mono', 0x2002a0f7, 1, range(3)),
    ('cpul', 0x2002a0f8, 1, SWITCH), ('mcap', 0x2002a0f9, 1, range(10)),
    ('sldm', 0x2002a0fa, 1, SWITCH), ('root', 0x2002a0fb, 1, range(101)),
    ('tlen', 0x2002a0fc, 1, range(1, 17)), ('ingn', 0x2002a0fd, 1, range(4)),
    ('scal', 0x2002a604, 2, range(0, 4096, 2)), ('vrng', 0x2002a606, 1, SWITCH),
    ('dens', 0x2002a607, 1, SWITCH), ('vqnt', 0x2002a610, 1, SWITCH),
    ('mlop', 0x2002a611, 1, SWITCH), ('dstr', 0x2002a614, 4, range(1281)),
    ('vuni', 0x2002a618, 1, SWITCH), ('vctr', 0x2002a619, 1, SWITCH),
    ('dryk', 0x2002a61a, 1, range(4)), ('dlen', 0x2002a61b, 1, SWITCH),
)
PRESETS = tuple((key, preset.value_addr(i), 4,
                 {'splc': range(1, 301), 'trst': preset.STEPS}.get(key, range(101)))
                for i, key in enumerate(preset.KEYS))
MODES = (('ntch', 0x2002a61d, 1, range(4)), ('thru', 0x2002a61e, 1, range(3)))
ALL_OPTIONS = OPTIONS + MODES + PRESETS
BANK = ('bank', 0x2002a61f, 1, range(9))  # ordinary mounts only


def input_cases():
    # Explicit zero chooses the lowest forward ratio or the first count. For
    # unaligned card slots and near-identical keys, check original destinations,
    # widths and neighboring values through both ordinary and live readers.
    for key, address, width, _ in ALL_OPTIONS:
        if key.startswith('mcr'):
            for token in ('0', '+0', '-0', '0.00000', '-000.00000000'):
                yield key, (address, width), f'{key} {token}', 0.0625
        if key in ('tlen', 'splc', 'trst'):
            for token in ('0', '00', '000'):
                yield key, (address, width), f'{key} {token}', 1
    for key, address, width, domain in ALL_OPTIONS:
        for expected in domain:
            if key == 'scal':
                text = ','.join(str(n) for n in range(1, 12) if expected & (1 << n)) or '0'
            elif key == 'dstr':
                text = f'{expected // 10}.{expected % 10}'
            else:
                text = str(expected)
            stored = expected + 1 if key == 'ntch' else expected
            yield key, (address, width), f'{key} {text}', stored


def record_writes(a):
    writes = set()

    def on_write(uc, access, address, size, value, data):
        writes.add((address, size))

    # Exclude the temporary call stack from the trace.
    a.uc.hook_add(UC_HOOK_MEM_WRITE, on_write, begin=0x20000000, end=0x2002dfff)
    return writes


def storage_bytes(slots):
    # Include the entire stock option block, including the two four-byte
    # positions between documented controls. A stray write there also fails.
    return set(range(0x200012a8, 0x200012e0)) | {
        byte for address, size in slots for byte in range(address, address + size)
    }


def touching(writes, watched_bytes):
    return {(address, size) for address, size in writes
            if not watched_bytes.isdisjoint(range(address, address+size))}


def live_slots():
    slots = {}
    # These settings were added after the original 26-word array.
    offsets = {'mlop': 232, 'dstr': 236, 'vuni': 244, 'vctr': 248, 'dryk': 252, 'dlen': 216}
    for i, (key, *_) in enumerate(OPTIONS):
        slot = live.STATE + offsets[key] if key in offsets else live.VALUES + 4*i
        slots[key] = (slot, live.SEEN, 1 << i)
    for i, key in enumerate(preset.KEYS):
        slots[key] = (preset.LIVE + 4 + 4*i, preset.LIVE, 1 << i)
    slots['ntch'] = (live.STATE+192, None, None)
    slots['thru'] = (live.STATE+196, None, None)
    return slots


class OptionWriteIsolation(unittest.TestCase):
    def check_value(self, raw, key, expected, line):
        if key.startswith('mcr'):
            # Both implementations store a single-precision chord ratio.
            self.assertAlmostEqual(float_from_word(raw), float(expected), delta=1e-6, msg=line)
        else:
            self.assertEqual(raw, expected, line)

    def test_live_stage_and_commit_write_only_selected_values(self):
        a = live.arm()
        writes = record_writes(a)
        staged = live_slots()
        active_bytes = storage_bytes((address, width) for _, address, width, _ in ALL_OPTIONS)
        for key, target, line, expected in input_cases():
            address, width = target
            slot, mask, bit = staged[key]
            a.put(live.SEEN, 0)
            a.put(preset.LIVE, 0)
            for mode, *_ in MODES:
                a.put(staged[mode][0], 0)
            a.put(live.PENDING, 1)
            # Force a real write even when two cases round to the same value.
            a.uc.mem_write(address, b'\xaa' * width)
            writes.clear()
            self.assertEqual(live.line(a, line), 1, line)
            expected_writes = {(slot, 4)}
            if mask is not None:
                expected_writes.add((mask, 4))
                self.assertEqual(a.get(mask), bit, line)
            self.assertEqual(writes, expected_writes, line)
            parsed = a.get(slot)
            if key == 'thru':
                parsed -= 1  # zero token means absent for either new option
            self.check_value(parsed, key, expected, line)
            writes.clear()
            live.call(a, 'reload_commit')
            # Chord mirrors, pickup state and density scheduling are deliberate
            # side effects. The set of configured control values is independent.
            self.assertEqual(touching(writes, active_bytes), {target}, line)
            self.assertEqual(int.from_bytes(a.uc.mem_read(address, width), 'little'), parsed, line)

    @unittest.skipUnless(os.getenv('MGMOD_FIRMWARE'), 'set MGMOD_FIRMWARE for stock dispatch')
    def test_normal_reader_writes_only_selected_values(self):
        a = Arm('options_keys', 'opt_parse')
        a.uc.mem_write(0x08020000, stock.load(os.environ['MGMOD_FIRMWARE']))
        # Constants normally loaded by the surrounding mg204 card-read loop.
        for register, key in ((UC_ARM_REG_R4, b'vsop'), (UC_ARM_REG_R5, b'step'), (UC_ARM_REG_R6, b'rmod')):
            a.uc.reg_write(register, int.from_bytes(key, 'big'))
        # Stock's chord handler addresses the same fgets buffer via sp + 0xe4.
        a.uc.reg_write(UC_ARM_REG_SP, normal.BUFFER - 0xe4)
        # feed() runs the three hooks directly. Between the second and third,
        # real mg204 loads FIL.err into r3 and dispatches only on a zero result.
        def successful_read(uc, address, size, data):
            uc.reg_write(UC_ARM_REG_R3, 0)
        parser = a.syms['opt_parse'] & ~1
        a.uc.hook_add(UC_HOOK_CODE, successful_read, begin=parser, end=parser)
        normal.begin(a)
        normal.feed(a, '6 46345 0\n', run_stock=True)
        preset_slots = {key: (normal.NORMAL + 4 + 4*i, 4) for i, key in enumerate(preset.KEYS)}
        slots = [(address, width) for _, address, width, _ in ALL_OPTIONS + (BANK,)]
        watched = storage_bytes(slots + list(preset_slots.values()))
        writes = record_writes(a)
        # These older stock keys are absent from the editor and live reader.
        # Normal dispatch accepts digit tokens; step aliases vsop's word.
        legacy = ((key, (address, 4), f'{key} {n}', n)
                  for key, address in [('step', 0x200012a8), ('rmod', 0x200012b8)]
                  for n in range(10))
        bank_cases = (('bank', (BANK[1], BANK[2]), f'bank {n}', n) for n in BANK[3])
        for key, target, line, expected in chain(input_cases(), bank_cases, legacy):
            expected_target = preset_slots.get(key, target)
            writes.clear()
            normal.feed(a, line+'\n', run_stock=True)
            self.assertEqual(touching(writes, watched), {expected_target}, line)
            address, width = expected_target
            raw = int.from_bytes(a.uc.mem_read(address, width), 'little')
            self.check_value(raw, key, expected, line)
