"""Optional tests from the user's own mg204.wav, never a bundled firmware image."""
import math, os, struct, unittest
from functools import lru_cache
from mgmod import registry, stock
from mgmod.__main__ import build
from tests.arm import *

@lru_cache(None)
def images():
    original=stock.load(os.environ['MGMOD_FIRMWARE'])
    return original,build(registry.remix('full'),original)

@unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'),'set MGMOD_FIRMWARE for real stock lookup integration')
class FirmwareIntegration(unittest.TestCase):
    def test_real_rate_path_all_control_positions(self):
        original,modified=images()
        standard=struct.unpack_from('<200f',original,0x080462B0-0x08020000)
        forward=struct.unpack_from('<296f',original,0x08045E10-0x08020000)
        a=Arm('shift_gestures','p1_session');a.uc.mem_write(0x08020000,modified)
        for extended in (0,1):
            a.uc.mem_write(0x2002A606,bytes([extended]))
            for mode in (0,1,2):
                a.syms['lookup']=0x080287E0 if mode==2 else 0x0802AA96
                for adc in range(4096):
                    x=f32(adc/4095)
                    a.uc.reg_write(UC_ARM_REG_R4,mode);a.uc.reg_write(UC_ARM_REG_S18,bits(x))
                    a.run('lookup',[0x080278CC])
                    actual=value(a.get(0x200220E8))
                    if mode==2:
                        i=max(0,min(295,int(f32(x*328))-16));expected=forward[i]
                        if extended:
                            j=max(0,min(343,int(f32(x*376))-16))
                            expected=0. if j<4 else f32(2**((min(j,340)-196)/48))
                    else:
                        m=min(399,int(f32(x*400))) & ~(1 if extended or mode==0 else 3)
                        if m>=200:expected=standard[m-200]
                        elif m<=196:expected=-standard[196-m]
                        else:expected=0.
                        if extended:expected=f32(math.copysign(expected*expected,expected))
                    self.assertEqual(actual,expected,(extended,mode,adc))

    def test_web_patch_bundle_matches_local_builds(self):
        import hashlib,json
        from pathlib import Path
        original=images()[0]
        path=Path(__file__).resolve().parents[1]/'web/remixes.js'
        remixes=json.loads(path.read_text().split(' = ',1)[1].rstrip(';\n'))
        for remix in remixes:
            built=build(registry.remix(remix['name']),original)
            browser=bytearray(original)+bytearray(b'\xff'*(remix['size']-len(original)))
            for offset,hexbytes in remix['runs']:browser[offset:offset+len(hexbytes)//2]=bytes.fromhex(hexbytes)
            self.assertEqual(browser,built)
            self.assertEqual(hashlib.sha256(built).hexdigest(),remix['sha256'])
