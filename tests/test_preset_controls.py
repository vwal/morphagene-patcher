"""Dev7 Morph/Gene Size/Slide recall, pickup, gesture and real-audio checks."""
import os
import unittest
from pathlib import Path
from tests.arm import *
from tests.audio import Audio
from tests.fixtures import reference
from tests.test_settings_reload import call
from tests.test_firmware_integration import images

PRESET, MAGIC, MOD = 0x2002a660, 0x54535250, 0x2002a000
ADC = (0x20021c6c, 0x20021c7c, 0x20021c78)
FN = ('preset_morph', 'preset_gene_size', 'preset_slide')
FLAG, HOLD, REF = (94, 212, 213), (96, 216, 218), (92, 208, 210)


def publish(a, values):
    if a.get(PRESET) != MAGIC:
        a.uc.mem_write(PRESET, bytes(160))
    for index, value in values.items():
        a.put(PRESET+16+4*index, value)
    mask = sum(1 << index for index in values)
    a.put(PRESET+8, mask)
    a.put(PRESET+12, mask)
    a.put(PRESET+4, a.get(PRESET+4)+1)
    a.put(PRESET, MAGIC)


def lane(index): return PRESET+32+24*index
def target(percent): return (percent*4095+50)//100


def control_arm(index):
    a = Arm('tape_sos', 'p7_sos_block') if index == 0 else Arm('gene_shape', 'g2_size')
    a.put(MOD, 0x53484654)
    a.put(0x2002a0f0, 0x5354504f)
    a.uc.mem_write(0x2002a0f4, bytes([1, 1, 1, 0, 0, 3, 0, 50, 8]))
    return a


def read_control(a, index, physical, effective=None):
    a.put(ADC[index], physical)
    return call(a, FN[index], physical if effective is None else effective)


class PresetControls(unittest.TestCase):
    def test_missing_keys_leave_legacy_values_and_other_memory_unchanged(self):
        for index in range(3):
            a = control_arm(index)
            for physical in (0, 1000, 2048, 4095):
                self.assertEqual(read_control(a, index, physical, 731), 731)
            publish(a, {(index+1) % 3: 50})
            self.assertEqual(read_control(a, index, 1000, 731), 731)
            self.assertEqual(a.get(lane(index)+20), 0)

    def test_all_percentages_recall_exact_virtual_knob_positions(self):
        for index in range(3):
            a = control_arm(index)
            for percent in range(101):
                publish(a, {index: percent})
                self.assertEqual(read_control(a, index, 500), target(percent))
                self.assertEqual(a.get(lane(index)+16), 1)

    def test_near_and_crossing_pickup_and_endpoint_tolerance(self):
        for index in range(3):
            for initial, next_value in ((1000, 2100), (3000, 1990), (1000, 2000), (3000, 2096)):
                a = control_arm(index)
                publish(a, {index: 50})
                self.assertEqual(read_control(a, index, initial), 2048)
                self.assertEqual(read_control(a, index, next_value), next_value)
                self.assertEqual(a.get(lane(index)+16), 0)
            for percent, physical, want_hold in ((0, 56, False), (0, 129, True),
                                                  (100, 4000, False), (100, 3966, True)):
                a = control_arm(index)
                publish(a, {index: percent})
                read_control(a, index, physical)
                self.assertEqual(read_control(a, index, physical),
                                 target(percent) if want_hold else physical)
                self.assertEqual(a.get(lane(index)+16), int(want_hold))

    def test_explicit_reload_reapplies_but_missing_key_preserves_current_value(self):
        for index in range(3):
            a = control_arm(index)
            publish(a, {index: 50})
            read_control(a, index, 1000)
            self.assertEqual(read_control(a, index, 2300), 2300)
            publish(a, {})
            self.assertEqual(read_control(a, index, 2700), 2700)
            publish(a, {index: 50})
            self.assertEqual(read_control(a, index, 2700), 2048)
            publish(a, {})
            self.assertEqual(read_control(a, index, 3000), 2048)
            self.assertEqual(a.get(PRESET+12), 0)

    def test_shift_preserves_effective_primary_and_suspends_preset_pickup(self):
        for index in range(3):
            a = control_arm(index)
            publish(a, {index: 75})
            read_control(a, index, 1000)
            a.uc.mem_write(MOD+4, bytes([1, 1, index+3]))
            a.uc.mem_write(MOD+FLAG[index], b'\1')
            a.uc.mem_write(MOD+HOLD[index], struct.pack('<H', 1000))
            self.assertEqual(read_control(a, index, 3200, 1000), target(75))
            self.assertEqual(struct.unpack('<H', a.uc.mem_read(MOD+HOLD[index], 2))[0], target(75))
            self.assertEqual(a.get(lane(index)+16), 1)
            # A crossing while editing belongs to the secondary parameter.
            self.assertEqual(read_control(a, index, 2800, target(75)), target(75))
            a.uc.mem_write(MOD+4, bytes(3))
            self.assertEqual(read_control(a, index, 2800, target(75)), target(75))
            self.assertEqual(read_control(a, index, 3200, target(75)), 3200)
            self.assertEqual(a.uc.mem_read(MOD+FLAG[index], 1), b'\0')

    def test_after_pickup_stock_shift_session_snapshot_is_preserved(self):
        for index in range(3):
            a = control_arm(index)
            publish(a, {index: 25})
            read_control(a, index, 500)
            read_control(a, index, 1100)
            a.uc.mem_write(MOD+4, bytes([1, 1, index+3]))
            a.uc.mem_write(MOD+FLAG[index], b'\1')
            a.uc.mem_write(MOD+HOLD[index], struct.pack('<H', 1100))
            self.assertEqual(read_control(a, index, 1800, 1100), 1100)

    def test_reload_supersedes_legacy_and_active_gesture_holds(self):
        for index in range(3):
            for editing in (False, True):
                a = control_arm(index)
                publish(a, {index: 25})
                read_control(a, index, 500)
                a.uc.mem_write(MOD+4, bytes([1, 1, index+3]) if editing else bytes(3))
                a.uc.mem_write(MOD+FLAG[index], b'\1')
                a.uc.mem_write(MOD+HOLD[index], struct.pack('<H', 1024))
                publish(a, {index: 75})
                self.assertEqual(read_control(a, index, 500, 1024), target(75))

    def test_actual_hooks_keep_secondary_effects_physical_and_c_calls_aligned(self):
        for index in range(3):
            pair = [control_arm(index), control_arm(index)]
            for a in pair:
                a.put(ADC[index], 3500)
                a.uc.mem_write(MOD+REF[index], struct.pack('<H', 3500))
                a.uc.mem_write(MOD+4, bytes([1, 1, index+3]))
                a.uc.mem_write(0x2002a607, b'\1')
            publish(pair[1], {index: 25})
            read_control(pair[1], index, 3500)
            # Force legacy initialization, exactly as the first claimed edit.
            pair[1].uc.mem_write(MOD+FLAG[index], b'\0')
            pair[1].put(lane(index)+20, 1)
            aligned = []
            for a in pair:
                a.uc.reg_write(UC_ARM_REG_SP, SP-4)
                def inspect(uc, address, size, data):
                    if address == a.syms[FN[index]]:
                        aligned.append(uc.reg_read(UC_ARM_REG_SP) % 8)
                h = a.uc.hook_add(UC_HOOK_CODE, inspect)
                if index == 0:
                    a.uc.reg_write(UC_ARM_REG_R7, 3500)
                    a.run('p10_morph_cap', [0x0802798c])
                    effective = round(value(a.uc.reg_read(UC_ARM_REG_S31))*4096)
                elif index == 1:
                    a.uc.reg_write(UC_ARM_REG_R0, 3500)
                    a.run('size_hold')
                    effective = a.uc.reg_read(UC_ARM_REG_R0)
                else:
                    a.uc.reg_write(UC_ARM_REG_R6, 0x20021c68)
                    a.run('gs_slide', [0x08027978])
                    effective = a.uc.reg_read(UC_ARM_REG_R2)
                a.uc.hook_del(h)
                self.assertEqual(a.uc.reg_read(UC_ARM_REG_SP), SP-4)
                self.assertEqual(effective, target(25) if a is pair[1] else 3500)
            effect = (MOD+100, 0x2002a808, MOD+224)[index]
            self.assertEqual(pair[0].get(effect), pair[1].get(effect), index)
            self.assertTrue(aligned)
            self.assertEqual(set(aligned), {0})

    def test_scatter_reads_use_cached_size_without_second_pickup_or_register_damage(self):
        for symbol, return_address in (('preset_size_a', 0x08027ec8), ('preset_size_b', 0x08029680)):
            for values in ({}, {0: 75}, {1: 75}):
                a = control_arm(1)
                if values:
                    publish(a, values)
                    read_control(a, 1, 1000)
                a.put(ADC[1], 4000)  # would cross the preset if evaluated again
                for n in range(13):
                    a.uc.reg_write(UC_ARM_REG_R0+n, 0x12340000+n)
                a.uc.reg_write(UC_ARM_REG_R6, 0x20021c68)
                registers = [a.uc.reg_read(UC_ARM_REG_R0+n) for n in range(13)]
                a.uc.reg_write(UC_ARM_REG_APSR, 0xa8000000)
                before = bytes(a.uc.mem_read(lane(1), 24))
                a.run(symbol, [return_address])
                expected = target(75) if 1 in values else 4000
                self.assertEqual(a.uc.reg_read(UC_ARM_REG_R7), expected)
                self.assertEqual(a.get(SP), expected)
                self.assertEqual(a.uc.reg_read(UC_ARM_REG_SP), SP)
                for n in range(13):
                    if n != 7:
                        self.assertEqual(a.uc.reg_read(UC_ARM_REG_R0+n), registers[n])
                self.assertEqual(a.uc.reg_read(UC_ARM_REG_APSR) & 0xf8000000, 0xa8000000)
                self.assertEqual(bytes(a.uc.mem_read(lane(1), 24)), before)


@unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'), 'set MGMOD_FIRMWARE for real audio')
class PresetControlAudio(unittest.TestCase):
    def test_virtual_positions_match_the_same_physical_knob_settings(self):
        for values in ({0: 0, 1: 0, 2: 0}, {0: 35, 1: 50, 2: 75}, {0: 80, 1: 100, 2: 10}):
            reference, recalled = Audio(images()[1]), Audio(images()[1])
            for index, percent in values.items():
                reference.a.put(ADC[index], target(percent))
                recalled.a.put(ADC[index], 4095 if percent == 0 else 0)
            publish(recalled.a, values)
            self.assertEqual(recalled.blocks(500), reference.blocks(500), values)
            for index, percent in values.items():
                self.assertEqual(recalled.a.get(lane(index)+12), target(percent))
            for address in (0x200012a0, 0x2002208c, 0x2002215c, 0x20022160):
                self.assertEqual(recalled.a.get(address), reference.a.get(address))

    def test_no_presets_match_development6_audio(self):
        previous = reference('rollback-dev6-r3/mg204-full.bin')
        for gene, morph, slide in ((0, 0, 0), (0, 3200, 2100), (2000, 1000, 3000), (4095, 4095, 4095)):
            old, new = Audio(previous.read_bytes()), Audio(images()[1])
            for audio in (old, new):
                for address, value_ in zip(ADC, (morph, gene, slide)):
                    audio.a.put(address, value_)
            self.assertEqual(new.blocks(160), old.blocks(160), (gene, morph, slide))


if __name__ == '__main__':
    unittest.main()
