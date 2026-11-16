"""Turing-rate-only gestures must keep every audio Gene Size read held."""
import os
import struct
import unittest
from tests.arm import *
from tests.audio import Audio
from tests.test_firmware_integration import images
from tests.test_preset_gene_effects import arm, hook, publish, RATE, EVOLUTION, JITTER, lane, MOD
from tests.test_preset_primary import publish as publish_controls

SIZE = 0x20021c7c


class RatePresetReads(unittest.TestCase):
    def test_turing_scatter_cached_read_keeps_seed_register_and_flags(self):
        for history,expected in (({},17),({1:50},2048),({RATE:8},2048)):
            a=arm()
            if history:
                publish_controls(a,history);hook(a,RATE,2048)
            a.uc.mem_write(MOD+212,b'\1')
            a.uc.mem_write(MOD+216,struct.pack('<H',2048))
            for n in range(13):a.uc.reg_write(UC_ARM_REG_R0+n,0x23450000+n)
            a.uc.reg_write(UC_ARM_REG_R1,17)
            registers=[a.uc.reg_read(UC_ARM_REG_R0+n) for n in range(13)]
            a.uc.reg_write(UC_ARM_REG_APSR,0xa8000000)
            a.run('preset_size_cached')
            self.assertEqual(a.uc.reg_read(UC_ARM_REG_R1),expected)
            for n in range(13):
                if n!=1:self.assertEqual(a.uc.reg_read(UC_ARM_REG_R0+n),registers[n])
            self.assertEqual(a.uc.reg_read(UC_ARM_REG_APSR)&0xf8000000,0xa8000000)
            self.assertEqual(a.uc.reg_read(UC_ARM_REG_SP),SP)

    def test_scatter_uses_legacy_hold_only_with_initialized_rate_history(self):
        for symbol, destination in (('preset_size_a',0x08027ec8),
                                    ('preset_size_b',0x08029680)):
            for history, held, expected in ((False,True,0),(True,True,2048),(True,False,0)):
                a=arm()
                if history:
                    publish(a,{RATE:8});hook(a,RATE,2048)
                a.put(SIZE,0)
                a.uc.mem_write(MOD+212,bytes([held]))
                a.uc.mem_write(MOD+216,struct.pack('<H',2048))
                for n in range(13):a.uc.reg_write(UC_ARM_REG_R0+n,0x12340000+n)
                a.uc.reg_write(UC_ARM_REG_R6,0x20021c68)
                registers=[a.uc.reg_read(UC_ARM_REG_R0+n) for n in range(13)]
                a.uc.reg_write(UC_ARM_REG_APSR,0xa8000000)
                before=bytes(a.uc.mem_read(lane(RATE),24))
                a.run(symbol,[destination])
                self.assertEqual(a.uc.reg_read(UC_ARM_REG_R7),expected,(symbol,history,held))
                self.assertEqual(a.get(SP),expected)
                self.assertEqual(a.uc.reg_read(UC_ARM_REG_SP),SP)
                for n in range(13):
                    if n!=7:self.assertEqual(a.uc.reg_read(UC_ARM_REG_R0+n),registers[n])
                self.assertEqual(a.uc.reg_read(UC_ARM_REG_APSR)&0xf8000000,0xa8000000)
                self.assertEqual(bytes(a.uc.mem_read(lane(RATE),24)),before)


@unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'),'requires official firmware')
class RatePresetReadAudio(unittest.TestCase):
    def test_primary_gene_presets_match_manual_positions_with_turing_scatter(self):
        manual=arm()
        hook(manual,JITTER,1843,True)
        hook(manual,EVOLUTION,2048,True)
        hook(manual,RATE,2816,True)
        reference,recalled=Audio(images()[1]),Audio(images()[1])
        for audio in (reference,recalled):
            audio.uc.mem_write(0x2002a0fa,b'\1')
            audio.a.put(MOD+224,manual.get(MOD+224))
            audio.uc.mem_write(0x2002a740,bytes(manual.uc.mem_read(0x2002a740,192)))
        for address,physical in ((0x20021c6c,1433),(SIZE,2048),(0x20021c78,3071)):
            reference.a.put(address,physical);recalled.a.put(address,500)
        publish_controls(recalled.a,{0:35,1:50,2:75})
        self.assertEqual(reference.blocks(800),recalled.blocks(800))
        self.assertEqual(reference.births,recalled.births)

    def test_turing_rate_only_shift_and_release_keep_primary_audio_unchanged(self):
        reference,recalled=Audio(images()[1]),Audio(images()[1])
        for audio in (reference,recalled):
            audio.uc.mem_write(0x2002a0fa,b'\1')
            audio.a.put(0x20021c6c,1433);audio.a.put(0x20021c78,3071)
            audio.a.put(SIZE,2048)
            publish(audio.a,{RATE:8})
        self.assertEqual(reference.blocks(400),recalled.blocks(400))
        for audio in (reference,recalled):
            audio.uc.mem_write(MOD+208,struct.pack('<H',2048))
            audio.uc.mem_write(MOD+4,bytes([1,1,4]))
        for physical in (1500,900,0):
            recalled.a.put(SIZE,physical)
            self.assertEqual(reference.blocks(220),recalled.blocks(220),('SHIFT',physical))
            self.assertEqual(recalled.uc.mem_read(MOD+212,1),b'\1')
            self.assertEqual(recalled.uc.mem_read(MOD+216,2),struct.pack('<H',2048))
            self.assertEqual(recalled.a.get(lane(RATE)+16),1,'rate not picked up')
        for audio in (reference,recalled):audio.uc.mem_write(MOD+4,bytes(3))
        self.assertEqual(reference.blocks(400),recalled.blocks(400),'released SHIFT, primary still held')
        self.assertEqual(reference.births,recalled.births)
        recalled.a.put(SIZE,2048)
        self.assertEqual(reference.blocks(220),recalled.blocks(220),'primary pickup')
        self.assertEqual(recalled.uc.mem_read(MOD+212,1),b'\0')


if __name__=='__main__':unittest.main()
