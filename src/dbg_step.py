#!/usr/bin/env python3
"""Fine-grained step-by-step trace of fadd 3.5+1.25."""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from asm6502 import asm6502
from sim6502 import sim6502

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "ieee754.asm")) as f:
    lib = f.read().splitlines()

a = asm6502(debug=0)
a.assemble(lib)
for addr in range(0xfffa, 0x10000):
    a.object_code[addr] = -1

BUF_A, BUF_B = 0x0200, 0x0208
TEST_ORG, DONE = 0x0300, 0x03ff

def fbytes(f): return struct.pack('<d', f)

stub = [
    f'        org ${TEST_ORG:04x}',
    f'        lda #${BUF_A & 0xff:02x}', '        sta $96',
    f'        lda #${(BUF_A >> 8) & 0xff:02x}', '        sta $97',
    f'        lda #${BUF_B & 0xff:02x}', '        sta $98',
    f'        lda #${(BUF_B >> 8) & 0xff:02x}', '        sta $99',
    '        jsr unpack1', '        jsr unpack2', '        jsr fadd',
    f'        org ${DONE:04x}', '        brk',
]
a.assemble(stub, clear_lst=True, clear_sym=False, clear_obj=False)
obj = a.object_code[:]
obj[0xfffc] = TEST_ORG & 0xff
obj[0xfffd] = (TEST_ORG >> 8) & 0xff
s = sim6502(obj, symbols=a.symbols)
for i,b in enumerate(fbytes(3.5)): s.memory_map.Write(BUF_A+i, b)
for i,b in enumerate(fbytes(1.25)): s.memory_map.Write(BUF_B+i, b)
s.reset(); s.pc = TEST_ORG

fadd_f2_smaller = a.symbols["fadd_f2_smaller"]
# Run to fadd_f2_smaller
while s.pc != fadd_f2_smaller:
    s.execute()
# Now single-step, printing state
tmp0 = a.symbols["tmp0"]
tmp1 = a.symbols["tmp1"]
print(f"AT fadd_f2_smaller: tmp0=${s.memory_map.Read(tmp0):02x} tmp1=${s.memory_map.Read(tmp1):02x}")
print(f"fac1_e=${s.memory_map.Read(a.symbols['fac1_e1']):02x}{s.memory_map.Read(a.symbols['fac1_e0']):02x}")
print(f"fac2_e=${s.memory_map.Read(a.symbols['fac2_e1']):02x}{s.memory_map.Read(a.symbols['fac2_e0']):02x}")

for i in range(20):
    pc = s.pc
    op = s.memory_map.Read(pc)
    op1 = s.memory_map.Read((pc+1)%0x10000)
    op2 = s.memory_map.Read((pc+2)%0x10000)
    print(f"  pc=${pc:04x}  {op:02x} {op1:02x} {op2:02x}  A=${s.a:02x} X=${s.x:02x} Y=${s.y:02x} CC=${s.cc:02x}")
    s.execute()
    if pc == a.symbols.get("fadd_f2_tiny", -1):
        print("  >>> AT fadd_f2_tiny (wrong)")
        break
    if pc == a.symbols.get("fadd_do_addsub", -1):
        print("  >>> AT fadd_do_addsub (correct path)")
        break
