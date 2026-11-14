"""Execute the project's assembled Thumb hooks; no vendor firmware required."""
from functools import lru_cache
from pathlib import Path
import struct
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS, UC_HOOK_CODE
from unicorn.arm_const import *
from mgmod.module import assemble

ROOT = Path(__file__).resolve().parents[1]
CODE = 0x08048400
STOP = 0x08020000
SP = 0x2002F000

def u32(n): return struct.pack('<I', n)
def f32(n): return struct.unpack('<f', struct.pack('<f', n))[0]
def bits(n): return struct.unpack('<I', struct.pack('<f', n))[0]
def value(n): return struct.unpack('<f', u32(n))[0]

@lru_cache(None)
def compiled(name, entry):
    return assemble(ROOT / 'modules' / name / (name + '.S'), entry, CODE)

class Arm:
    def __init__(self, name, entry):
        self.uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
        self.uc.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_M4)
        self.uc.mem_map(0x08020000, 0x40000)
        self.uc.mem_map(0x20000000, 0x30000)
        self.uc.mem_map(0x40020000, 0x10000)
        self.uc.mem_map(0xE0000000, 0x100000)
        self.uc.mem_map(0xD0000000, 0x50000)
        code, self.syms = compiled(name, entry)
        self.uc.mem_write(CODE, code)
        self.uc.reg_write(UC_ARM_REG_C1_C0_2, 0xF00000)
        self.uc.reg_write(UC_ARM_REG_FPEXC, 0x40000000)
        self.uc.reg_write(UC_ARM_REG_SP, SP)
        self.uc.reg_write(UC_ARM_REG_LR, STOP | 1)
        self.stops = {STOP}
        self.calls = {}
        self.code_hook = self.uc.hook_add(UC_HOOK_CODE, self._code)
    def _code(self, uc, addr, size, _):
        if addr in self.stops:
            uc.emu_stop()
        elif addr in self.calls:
            self.calls[addr](self)
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
    def put(self, addr, n): self.uc.mem_write(addr, u32(n))
    def get(self, addr): return struct.unpack('<I', self.uc.mem_read(addr, 4))[0]
    def run(self, name, stops=(), count=20000):
        self.stops = {STOP, *stops}
        self.uc.reg_write(UC_ARM_REG_LR, STOP | 1)
        self.uc.emu_start(self.syms[name] | 1, 0, count=count)
        pc = self.uc.reg_read(UC_ARM_REG_PC)
        if pc not in self.stops: raise AssertionError(f'{name} did not return: {pc:#x}')
