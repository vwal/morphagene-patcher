"""Real mg204 audio engine, with only hardware and buffer-fill setup simulated."""
from tests.arm import *
from mgmod import stock
import os

class Audio:
    def __init__(self,image):
        a=Arm('shift_gestures','p1_session');self.a=a;self.uc=a.uc
        a.uc.hook_del(a.code_hook)
        a.uc.mem_write(0x08020000,image)
        a.uc.mem_write(0x20000000,image[0x27250:0x28400])
        a.uc.mem_map(0xd0050000,0x2000000-0x50000)
        def skip(uc,pc,size,data):
            if pc==0x8026944:uc.reg_write(UC_ARM_REG_PC,0x8026957)
            if pc==0x802695c:uc.reg_write(UC_ARM_REG_PC,0x8026967)
        h=a.uc.hook_add(UC_HOOK_CODE,skip,begin=0x8026944,end=0x802695c)
        self.call(0x8026730)
        a.uc.hook_del(h)
        # Calibration/state for one loaded stereo splice, no clock, Play high.
        for adr,n in {0x2002208c:1,0x2002215c:0,0x20022160:48000,0x20021dec:bits(1.),  # settled full-wet S.O.S. coefficient
            0x20001054:1,0x20021410:bits(1/4095),0x200012e4:1,0x2002205c:0,0x20021cb8:0,0x200220e0:bits(1),
            0x200220e8:bits(1),0x20021c68:4095,0x20021c6c:420,0x20021c74:3500,
            0x20021c78:0,0x20021c7c:2000,0x20022074:0,0x20021fb8+4:bits(48000),
            0x2002A000:0x53484654,0x2002A0F0:0x5354504f}.items():a.put(adr,n)
        a.uc.mem_write(0x2002A0F4,bytes([1,1,1,0,0,3,0,50,8,0,0,0]))
        # full .bss reset is covered separately; initial Arm memory is zero.
        wave=struct.pack('<48000h',*(int(10000*__import__('math').sin(2*__import__('math').pi*i/100)) for i in range(48000)))
        a.uc.mem_write(0xd0000000,wave);a.uc.mem_write(0xd1000000,wave)
        self.block_index=0;self.births=[];self.paths=set();self.sample_index=0
        def tick(uc,pc,size,data):self.sample_index+=1
        a.uc.hook_add(UC_HOOK_CODE,tick,begin=0x80280dc,end=0x80280dc)
        a.uc.hook_add(UC_HOOK_CODE,tick,begin=0x8029940,end=0x8029940)
        def birth(uc,pc,size,data):
            self.paths.add('A' if pc==0x802838a else 'B')
            self.births.append(self.sample_index)
        a.uc.hook_add(UC_HOOK_CODE,birth,begin=0x802838a,end=0x802838a)
        a.uc.hook_add(UC_HOOK_CODE,birth,begin=0x8029bb8,end=0x8029bb8)
    def call(self,address):
        self.uc.reg_write(UC_ARM_REG_LR,STOP|1)
        self.uc.emu_start(address|1,STOP,count=200000)
        assert self.uc.reg_read(UC_ARM_REG_PC)==STOP,hex(self.uc.reg_read(UC_ARM_REG_PC))
    def blocks(self,n):
        out=bytearray()
        for _ in range(n):
            self.uc.reg_write(UC_ARM_REG_R0,0x20028000)
            self.uc.reg_write(UC_ARM_REG_R1,0x20028100)
            self.uc.reg_write(UC_ARM_REG_R2,16)
            self.call(0x8027518)
            out+=self.uc.mem_read(0x20028100,32);self.block_index+=1
        return bytes(out)
