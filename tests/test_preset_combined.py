"""All twelve recalls together must match equivalent manual performance state."""
import os
import struct
import unittest
from tests.arm import bits
from tests.audio import Audio
from tests.test_firmware_integration import images
from tests.test_preset_gene_effects import arm as gene_arm, hook as gene_edit, JITTER, EVOLUTION, RATE
from tests.test_preset_tape_effects import arm as tape_arm, target, MOD, FX_TARGET, RETENTION
from tests.arm import UC_ARM_REG_R1, UC_ARM_REG_R7

P,EXT = 0x2002a660,0x2002ae90
VALUES = (35,50,75,1,40,45,65,60,50,8,65,50)


def manual_effects(fxsl):
    gene=gene_arm()
    gene_edit(gene,JITTER,target(VALUES[5]),True)
    gene_edit(gene,EVOLUTION,target(VALUES[8]),True)
    gene_edit(gene,RATE,5*512+256,True)  # eight Genes/step, using ordinary zone gesture
    tape=tape_arm(fxsl)
    physical=target(VALUES[6] if fxsl==2 else VALUES[4])
    tape.put(0x20021c6c,physical)
    tape.uc.mem_write(MOD+4,bytes([1,1,3]))
    tape.uc.reg_write(UC_ARM_REG_R7,physical)
    tape.run('p10_morph_cap',[0x0802798c])
    tape.put(0x20021c68,target(VALUES[7]))
    tape.uc.mem_write(MOD+4,bytes([1,1,1]))
    tape.uc.reg_write(UC_ARM_REG_R1,0x20021c68)
    tape.run('p7_sos_block',[0x080276ca])
    return gene,tape


@unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'),'requires official firmware')
class CombinedPresetAudio(unittest.TestCase):
    def test_all_twelve_recalls_match_manual_positions_effects_and_recording(self):
        for fxsl,tape_mode in ((1,0),(2,1)):
            with self.subTest(fxsl=fxsl,tape=tape_mode):
                manual_gene,manual_tape=manual_effects(fxsl)
                reference,recalled=Audio(images()[1]),Audio(images()[1])
                for audio in (reference,recalled):
                    audio.uc.mem_write(0x2002a0f4,bytes([tape_mode,1,fxsl]))
                    audio.uc.mem_write(0x2002a0fa,b'\1')
                    audio.uc.mem_write(0x2002a619,b'\1')  # unity at noon
                    audio.a.put(0x20021410,bits(1/4000))
                    audio.a.put(0x20021c70,0)  # sole splice, no Organize movement
                    audio.a.put(0x20021cbc,1)
                for address,percent in ((0x20021c6c,VALUES[0]),(0x20021c7c,VALUES[1]),
                                        (0x20021c78,VALUES[2]),(0x20021c68,VALUES[10])):
                    reference.a.put(address,target(percent))
                    recalled.a.put(address,500)
                reference.a.put(0x20021c74,2000)
                recalled.a.put(0x20021c74,500)
                # These values came from the existing SHIFT control hooks, not
                # from any preset consumer or a duplicate of its mapping law.
                reference.a.put(MOD+224,manual_gene.get(MOD+224))
                reference.uc.mem_write(0x2002a740,bytes(manual_gene.uc.mem_read(0x2002a740,192)))
                reference.a.put(FX_TARGET,manual_tape.get(FX_TARGET))
                reference.a.put(RETENTION,manual_tape.get(RETENTION))
                reference.uc.mem_write(MOD+16,b'\1')
                for index,value in enumerate(VALUES):
                    recalled.a.put(P+16+4*index if index<4 else EXT+4*(index-4),value)
                recalled.a.put(P+8,0xfff);recalled.a.put(P+12,0xfff)
                recalled.a.put(P+4,1);recalled.a.put(P,0x54535250)
                self.assertEqual(reference.blocks(400),recalled.blocks(400),'playing')
                for audio in (reference,recalled):
                    audio.a.put(0x20021320,1);audio.a.put(0x20022108,1)
                    audio.a.put(0x20022114,1)
                    audio.uc.mem_write(0x20028000,struct.pack('<16h',*([2800,-1900]*8)))
                before=bytes(reference.uc.mem_read(0xd0000000,96000))
                self.assertEqual(reference.blocks(600),recalled.blocks(600),'recording')
                for address in (0xd0000000,0xd1000000):
                    self.assertEqual(reference.uc.mem_read(address,96000),recalled.uc.mem_read(address,96000))
                self.assertNotEqual(before,bytes(reference.uc.mem_read(0xd0000000,96000)))
                self.assertEqual(reference.births,recalled.births)
                for address in (0x20021cbc,0x200220e0,0x200220e8,FX_TARGET,RETENTION,MOD+224):
                    self.assertEqual(reference.a.get(address),recalled.a.get(address),hex(address))
                self.assertEqual(recalled.a.get(P+8),0xfff)
                self.assertEqual(recalled.a.get(P+12),0xfff)


if __name__=='__main__':unittest.main()
