"""Dev8 SRR/warble banks and feedback: virtual controls, pickup and audio."""
import os
import unittest
from pathlib import Path
from tests.arm import *
from tests.audio import Audio
from tests.fixtures import reference
from tests.test_settings_reload import call
from tests.test_firmware_integration import images

P, EXT, MAGIC, MOD = 0x2002a660, 0x2002ae90, 0x54535250, 0x2002a000
SRR, WARBLE, FEEDBACK = 4, 6, 7
FX_TARGET, RETENTION = MOD+100, MOD+20


def lane(index): return P+32+24*index if index < 4 else EXT+32+24*(index-4)
def target(percent): return (percent*4095+50)//100
def fx_amount(adc): return f32(max(0, min(4095, adc)-96)*f32(.000250062516))


def feedback_amount(adc):
    amount = f32(adc*f32(.00026350463))
    return 1. if amount > f32(1.04884) else max(0., f32(amount-f32(.04884)))


def publish(a, values):
    if a.get(P) != MAGIC:
        a.uc.mem_write(P, bytes(160))
        a.uc.mem_write(EXT, bytes(288))
    for index, value_ in values.items():
        a.put(P+16+4*index if index < 4 else EXT+4*(index-4), value_)
    mask = sum(1 << index for index in values)
    a.put(P+8, mask); a.put(P+12, mask)
    a.put(P+4, a.get(P+4)+1); a.put(P, MAGIC)


def arm(fxsl=1):
    a = Arm('tape_sos', 'p7_sos_block')
    a.put(MOD, 0x53484654); a.put(0x2002a0f0, 0x5354504f)
    a.uc.mem_write(0x2002a0f4, bytes([1, 1, fxsl, 0, 0, 3, 0, 50, 8]))
    a.put(0x200220e0, bits(1)); a.put(0x200220e8, bits(1))
    return a


def effect(a, physical, editing=False, feedback=False):
    owner = 1 if feedback else 3
    a.uc.mem_write(MOD+4, bytes([1, 1, owner]) if editing else bytes(3))
    a.put(0x20021c68 if feedback else 0x20021c6c, physical)
    if editing:
        a.put(RETENTION if feedback else FX_TARGET,
              bits(feedback_amount(physical) if feedback else fx_amount(physical)))
    name = 'preset_feedback_effect' if feedback else 'preset_morph_effects'
    assert call(a, name, 0x12345678) == 0x12345678
    return value(a.get(RETENTION if feedback else FX_TARGET))


class TapeEffectPresets(unittest.TestCase):
    def test_fxsl_off_bypasses_presets_and_removes_previous_warble(self):
        for preceding in (0, 1, 2):
            a = arm(preceding)
            publish(a, {SRR: 50, WARBLE: 75})
            a.put(0x20021c6c, 500)
            a.uc.reg_write(UC_ARM_REG_R7, 500)
            a.run('p10_morph_cap', [0x0802798c])
            # Model an already-applied multiplier; Off must remove it, not
            # merely stop calling the warble update and freeze the pitch.
            if preceding == 2:
                for address, value_ in {
                    0x2002a700: 0x4c425257, 0x2002a704: 0x12345678,
                    0x2002a708: bits(140), 0x2002a70c: bits(300),
                    0x2002a710: bits(.001), 0x2002a714: bits(.8),
                    0x2002a718: bits(1.25), 0x2002a71c: bits(1),
                    0x200220e8: bits(1), 0x200220e0: bits(1),
                }.items(): a.put(address, value_)
            a.uc.mem_write(0x2002a0f6, b'\0')
            # A previously claimed gesture can outlive a settings reload;
            # disabling fxsl must not edit stored banks during that release.
            a.uc.mem_write(MOD+4, bytes([1, 1, 3]))
            a.uc.mem_write(MOD+92, struct.pack('<H', 500))
            for _ in range(2):
                a.uc.reg_write(UC_ARM_REG_R7, 500)
                a.run('p10_morph_cap', [0x0802798c])
                self.assertEqual(a.uc.mem_read(MOD+95, 1), b'\0')
                self.assertEqual(a.uc.mem_read(MOD+232, 1), b'\0')
            if preceding == 2:
                self.assertEqual(a.get(0x200220e8), bits(1.25))
                self.assertEqual(a.get(0x200220e0), bits(1.25))
                self.assertEqual(a.get(0x2002a714), bits(1))
                self.assertEqual(a.get(0x2002a708), bits(100))
                self.assertEqual(a.get(0x2002a70c), bits(100))
                self.assertEqual(a.get(0x2002a710), 0)
                self.assertEqual(a.get(0x2002a704), 0x12345678)
            a.uc.mem_write(MOD+4, bytes(3))
            for mode, percent in ((1, 50), (2, 75)):
                a.uc.mem_write(0x2002a0f6, bytes([mode]))
                a.uc.reg_write(UC_ARM_REG_R7, 500)
                a.run('p10_morph_cap', [0x0802798c])
                self.assertEqual(a.get(FX_TARGET), bits(fx_amount(target(percent))))

    def test_every_percentage_matches_existing_hardware_gesture_laws(self):
        for index in (SRR, WARBLE, FEEDBACK):
            for percent in range(101):
                selected = 2 if index == WARBLE else 1
                old, recalled = arm(selected), arm(selected)
                publish(recalled, {index: percent})
                for a, physical, editing in ((old, target(percent), True), (recalled, 500, False)):
                    a.uc.mem_write(MOD+4, bytes([1, 1, 1 if index == FEEDBACK else 3]) if editing else bytes(3))
                    if index == FEEDBACK:
                        a.put(0x20021c68, physical)
                        a.uc.reg_write(UC_ARM_REG_R1, 0x20021c68)
                        a.run('p7_sos_block', [0x080276ca])
                    else:
                        a.put(0x20021c6c, physical)
                        a.uc.reg_write(UC_ARM_REG_R7, physical)
                        a.run('p10_morph_cap', [0x0802798c])
                address = RETENTION if index == FEEDBACK else FX_TARGET
                self.assertEqual(old.get(address), recalled.get(address), (index, percent))
                if index == FEEDBACK:
                    self.assertEqual(recalled.uc.mem_read(MOD+16, 1), b'\1')

    def test_secondary_pickup_requires_shift_and_missing_reload_preserves(self):
        for index in (SRR, WARBLE, FEEDBACK):
            a = arm(2 if index == WARBLE else 1)
            feedback = index == FEEDBACK
            law = feedback_amount if feedback else fx_amount
            publish(a, {index: 50})
            self.assertEqual(effect(a, 0, feedback=feedback), law(2048))
            self.assertEqual(effect(a, 4095, feedback=feedback), law(2048))
            self.assertEqual(a.get(lane(index)+16), 1)
            self.assertEqual(effect(a, 3000, editing=True, feedback=feedback), law(2048))
            self.assertEqual(effect(a, 1000, editing=True, feedback=feedback), law(1000))
            self.assertEqual(a.get(lane(index)+16), 0)
            publish(a, {})
            self.assertEqual(effect(a, 3500, feedback=feedback), law(1000))
            publish(a, {index: 50})
            self.assertEqual(effect(a, 3500, feedback=feedback), law(2048))
            self.assertEqual(a.get(lane(index)+16), 1)

    def test_independent_banks_keep_live_edits_and_consume_inactive_recalls(self):
        a = arm(); a.put(FX_TARGET, bits(.2))
        publish(a, {SRR: 25, WARBLE: 75})
        self.assertEqual(effect(a, 0), fx_amount(target(25)))
        a.uc.mem_write(0x2002a0f6, b'\2')
        self.assertEqual(effect(a, 0), fx_amount(target(75)))
        self.assertEqual(effect(a, 3100, editing=True), fx_amount(3100))
        self.assertEqual(effect(a, 3500, editing=True), fx_amount(3500))
        a.uc.mem_write(0x2002a0f6, b'\1')
        self.assertEqual(effect(a, 0), fx_amount(target(25)))
        a.uc.mem_write(0x2002a0f6, b'\2')
        self.assertEqual(effect(a, 0), fx_amount(3500))
        self.assertEqual(a.get(lane(WARBLE)+16), 1)
        a.uc.mem_write(0x2002a0f6, b'\1')
        publish(a, {WARBLE: 60})
        self.assertEqual(effect(a, 0), fx_amount(target(25)))
        publish(a, {})
        effect(a, 0)
        a.uc.mem_write(0x2002a0f6, b'\2')
        self.assertEqual(effect(a, 0), fx_amount(target(60)))

    def test_unconfigured_bank_keeps_legacy_level_and_direct_editing(self):
        a = arm(2); a.put(FX_TARGET, bits(.4))
        publish(a, {SRR: 15})
        self.assertEqual(effect(a, 0), f32(.4))
        self.assertEqual(effect(a, 2000, editing=True), fx_amount(2000))
        a.uc.mem_write(0x2002a0f6, b'\1')
        self.assertEqual(effect(a, 0), fx_amount(target(15)))
        a.uc.mem_write(0x2002a0f6, b'\2')
        self.assertEqual(effect(a, 0), fx_amount(2000))
        self.assertEqual(a.get(lane(WARBLE)+20), 0)

    def test_unrelated_presets_do_not_change_legacy_shared_amount_or_feedback(self):
        a = arm(); publish(a, {0: 35})
        a.put(FX_TARGET, bits(.4)); a.put(RETENTION, bits(.75))
        for mode in (1, 2, 0, 1):
            a.uc.mem_write(0x2002a0f6, bytes([mode]))
            self.assertEqual(effect(a, 3000), f32(.4))
            self.assertEqual(effect(a, 3000, feedback=True), .75)
            self.assertEqual(a.get(EXT+224), 0)
            self.assertEqual(a.uc.mem_read(MOD+16, 1), b'\0')

    def test_effect_pickup_keeps_existing_primary_gesture_hold(self):
        for index in (SRR, WARBLE, FEEDBACK):
            a = arm(2 if index == WARBLE else 1)
            publish(a, {index: 25})
            effect(a, 3500, feedback=index == FEEDBACK)
            a.uc.mem_write(MOD+4, bytes([1, 1, 1 if index == FEEDBACK else 3]))
            # Existing SHIFT gesture snapshots the primary control separately.
            a.uc.mem_write(MOD+(8 if index == FEEDBACK else 92), struct.pack('<H', 1700))
            if index == FEEDBACK:
                a.put(0x20021c68, 3000)
                a.uc.reg_write(UC_ARM_REG_R1, 0x20021c68)
                a.run('p7_sos_block', [0x080276ca])
                primary = a.uc.reg_read(UC_ARM_REG_R5)
                amount = value(a.get(RETENTION))
            else:
                a.put(0x20021c6c, 3000)
                a.uc.reg_write(UC_ARM_REG_R7, 3000)
                a.run('p10_morph_cap', [0x0802798c])
                primary = round(value(a.uc.reg_read(UC_ARM_REG_S31))*4096)
                amount = value(a.get(FX_TARGET))
            self.assertEqual(primary, 1700)
            self.assertEqual(amount, feedback_amount(target(25)) if index == FEEDBACK else fx_amount(target(25)))
            self.assertEqual(a.get(lane(index)+16), 1)


@unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'), 'requires official firmware')
class TapeEffectAudio(unittest.TestCase):
    def test_fxsl_off_is_clean_audio_even_with_nonzero_effect_presets(self):
        reference, recalled = Audio(images()[1]), Audio(images()[1])
        for audio in (reference, recalled):
            audio.uc.mem_write(0x2002a0f6, b'\0')
        publish(recalled.a, {SRR: 50, WARBLE: 75})
        self.assertEqual(reference.blocks(600), recalled.blocks(600))
        self.assertEqual(recalled.uc.mem_read(MOD+95, 1), b'\0')
        self.assertEqual(recalled.uc.mem_read(MOD+232, 1), b'\0')
        self.assertEqual(reference.a.get(0x200220e0), recalled.a.get(0x200220e0))

    def test_running_warble_stops_without_frozen_pitch_when_switched_off(self):
        audio = Audio(images()[1]); audio.uc.mem_write(0x2002a0f6, b'\2')
        publish(audio.a, {SRR: 50, WARBLE: 75})
        audio.blocks(1000)
        self.assertNotEqual(audio.a.get(0x2002a714), bits(1))
        clean = audio.a.get(0x2002a718)
        audio.uc.mem_write(0x2002a0f6, b'\0')
        audio.blocks(1)
        self.assertEqual(audio.a.get(0x200220e8), clean)
        self.assertEqual(audio.a.get(0x2002a714), bits(1))
        self.assertEqual(audio.a.get(0x2002a708), bits(100))
        self.assertEqual(audio.a.get(0x2002a710), 0)
        self.assertEqual(audio.uc.mem_read(MOD+95, 1), b'\0')
        rng = audio.a.get(0x2002a704)
        audio.blocks(100)
        self.assertEqual(audio.a.get(0x2002a704), rng)
        self.assertEqual(audio.a.get(0x200220e8), clean)

    def test_effect_banks_match_manually_set_amounts_through_fxsl_changes(self):
        reference, recalled = Audio(images()[1]), Audio(images()[1])
        publish(recalled.a, {SRR: 40, WARBLE: 65})
        for mode, amount in ((1, 40), (2, 65), (1, 40), (2, 65)):
            for audio in (reference, recalled):
                audio.uc.mem_write(0x2002a0f6, bytes([mode]))
            reference.a.put(FX_TARGET, bits(fx_amount(target(amount))))
            self.assertEqual(reference.blocks(300), recalled.blocks(300), mode)
            self.assertEqual(reference.a.get(0x200220e0), recalled.a.get(0x200220e0))
            self.assertEqual(reference.a.get(FX_TARGET), recalled.a.get(FX_TARGET))
            self.assertEqual(reference.births, recalled.births)

    def test_feedback_presets_match_overdub_output_and_recorded_buffers(self):
        for tape in (0, 1):
            reference, recalled = Audio(images()[1]), Audio(images()[1])
            reference.uc.mem_write(MOD+16, b'\1')
            reference.a.put(RETENTION, bits(feedback_amount(target(60))))
            publish(recalled.a, {FEEDBACK: 60})
            for audio in (reference, recalled):
                audio.uc.mem_write(0x2002a0f4, bytes([tape]))
                audio.blocks(200)
                audio.a.put(0x20021320, 1)
                audio.a.put(0x20022108, 1)
                audio.a.put(0x20022114, 1)
                audio.uc.mem_write(0x20028000, struct.pack('<16h', *([3000, -2100]*8)))
            before = bytes(reference.uc.mem_read(0xd0000000, 96000))
            self.assertEqual(reference.blocks(600), recalled.blocks(600), tape)
            for address in (0xd0000000, 0xd1000000):
                self.assertEqual(reference.uc.mem_read(address, 96000), recalled.uc.mem_read(address, 96000))
            self.assertNotEqual(before, bytes(reference.uc.mem_read(0xd0000000, 96000)))
            for address in (0x20022108, 0x2002210c, 0x20022114, MOD+32, MOD+36):
                self.assertEqual(reference.a.get(address), recalled.a.get(address))
            self.assertEqual(recalled.a.get(0x20022108), 1)

    def test_no_effect_keys_preserve_development7_audio_with_legacy_warble(self):
        previous = reference('rollback-dev7/mg204-full.bin')
        old, new = Audio(previous.read_bytes()), Audio(images()[1])
        for audio in (old, new):
            publish(audio.a, {0: 35})
            audio.uc.mem_write(0x2002a0f6, b'\2')
            audio.a.put(FX_TARGET, bits(.35))
        self.assertEqual(old.blocks(600), new.blocks(600))


if __name__ == '__main__':
    unittest.main()
