#!/usr/bin/env python3
"""Check state right before normalize_f1 in fdiv."""
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
    '        jsr unpack1', '        jsr unpack2', '        jsr fdiv',
    f'        org ${DONE:04x}', '        brk',
]
a.assemble(stub, clear_lst=True, clear_sym=False, clear_obj=False)
obj = a.object_code[:]
obj[0xfffc] = TEST_ORG & 0xff
obj[0xfffd] = (TEST_ORG >> 8) & 0xff

def run(A, B):
    s = sim6502(obj, symbols=a.symbols)
    for i,b in enumerate(fbytes(A)): s.memory_map.Write(BUF_A+i, b)
    for i,b in enumerate(fbytes(B)): s.memory_map.Write(BUF_B+i, b)
    s.reset(); s.pc = TEST_ORG
    fdiv_go = a.symbols["fdiv_go"]
    fdiv_loop = a.symbols["fdiv_loop"]
    fdiv_done = a.symbols["fdiv_done"]
    norm = a.symbols["normalize_f1"]
    # Run to fdiv_go
    while s.pc != fdiv_go:
        s.execute()
    # Run to fdiv_loop
    while s.pc != fdiv_loop:
        s.execute()
    # At loop start, check E
    e0 = s.memory_map.Read(a.symbols["fac1_e0"])
    e1 = s.memory_map.Read(a.symbols["fac1_e1"])
    print(f"  at fdiv_loop start: E=${e1:02x}{e0:02x}")
    # Run to normalize_f1
    while s.pc != norm:
        s.execute()
    m = [s.memory_map.Read(a.symbols["fac1_m0"] + i) for i in range(8)]
    e0 = s.memory_map.Read(a.symbols["fac1_e0"])
    e1 = s.memory_map.Read(a.symbols["fac1_e1"])
    print(f"  at normalize_f1:    FAC1 M="+ " ".join(f"{b:02x}" for b in m) + f"  E=${e1:02x}{e0:02x}")
    # Also peek at bigm (should hold the remainder)
    bigm = [s.memory_map.Read(a.symbols["bigm0"] + i) for i in range(16)]
    print(f"  BIGM: "+ " ".join(f"{b:02x}" for b in bigm))
    # Continue to DONE
    while s.pc != DONE:
        s.execute()
    m = [s.memory_map.Read(a.symbols["fac1_m0"] + i) for i in range(8)]
    e0 = s.memory_map.Read(a.symbols["fac1_e0"])
    e1 = s.memory_map.Read(a.symbols["fac1_e1"])
    print(f"  after normalize:    FAC1 M="+ " ".join(f"{b:02x}" for b in m) + f"  E=${e1:02x}{e0:02x}")

print("6.0 / 2.0:")
run(6.0, 2.0)
print("\n1.0 / 0.5:")
run(1.0, 0.5)
print("\n1.0 / 3.0:")
run(1.0, 3.0)
