#!/usr/bin/env python3
"""Step through atof_is_digit -> itof32, printing each instruction."""
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

BUF_A, BUF_R = 0x0200, 0x0210
TEST_ORG, DONE = 0x0300, 0x03ff
PTR1 = a.symbols["ptr1"]
stub = [
    f'        org ${TEST_ORG:04x}',
    f'        lda #${BUF_A & 0xff:02x}', f'        sta ${PTR1:02x}',
    f'        lda #${(BUF_A >> 8) & 0xff:02x}', f'        sta ${PTR1 + 1:02x}',
    '        jsr atof',
    f'        org ${DONE:04x}', '        brk',
]
a.assemble(stub, clear_lst=True, clear_sym=False, clear_obj=False)
obj = a.object_code[:]
obj[0xfffc] = TEST_ORG & 0xff
obj[0xfffd] = (TEST_ORG >> 8) & 0xff

s = sim6502(obj, symbols=a.symbols)
s.memory_map.Write(BUF_A, ord('0'))
s.memory_map.Write(BUF_A+1, 0)
s.reset(); s.pc = TEST_ORG

# Run to atof_is_digit
atof_is_digit = a.symbols["atof_is_digit"]
itof32_addr = a.symbols["itof32"]
while s.pc != atof_is_digit:
    s.execute()
# Run past jsr fmul_by_ten (watch pc: it's the 'jsr' at is_digit+2)
# sty tmp0 (2 bytes), jsr fmul_by_ten (3 bytes). So fmul call returns at is_digit+5.
after_fmul = atof_is_digit + 5
while s.pc != after_fmul:
    s.execute()

print(f"After jsr fmul_by_ten (pc=${s.pc:04x})")
print(f"  bigm0=${s.memory_map.Read(0xa1):02x}, A=${s.a:02x}")
print(f"  FAC1_M0=${s.memory_map.Read(0x80):02x}")

# Now trace each instruction up to jsr itof32
# The sequence is: ldy tmp0; lda (ptr1),y; and #$0f; sta bigm0; stz bigm1; stz bigm2; stz bigm3;
# pha x 11; lda bigm0; sta fac1_m0; stz x 7; jsr itof32
for n in range(60):
    pc = s.pc
    op = s.memory_map.Read(pc)
    op1 = s.memory_map.Read((pc+1)&0xffff)
    op2 = s.memory_map.Read((pc+2)&0xffff)
    print(f"  pc=${pc:04x} {op:02x} {op1:02x} {op2:02x}  A=${s.a:02x} X=${s.x:02x} Y=${s.y:02x} CC=${s.cc:02x}  bigm0=${s.memory_map.Read(0xa1):02x} fac1_m0=${s.memory_map.Read(0x80):02x}")
    s.execute()
    if s.pc == itof32_addr:
        pc = s.pc
        print(f"  pc=${pc:04x} ENTER itof32  fac1_m0=${s.memory_map.Read(0x80):02x}  bigm0=${s.memory_map.Read(0xa1):02x}")
        break
