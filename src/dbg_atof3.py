#!/usr/bin/env python3
"""Very detailed trace of atof on '0'."""
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
    f'        lda #${BUF_R & 0xff:02x}', f'        sta ${PTR1:02x}',
    f'        lda #${(BUF_R >> 8) & 0xff:02x}', f'        sta ${PTR1 + 1:02x}',
    '        jsr pack1',
    f'        org ${DONE:04x}', '        brk',
]
a.assemble(stub, clear_lst=True, clear_sym=False, clear_obj=False)
obj = a.object_code[:]
obj[0xfffc] = TEST_ORG & 0xff
obj[0xfffd] = (TEST_ORG >> 8) & 0xff

def fac1(s):
    m = [s.memory_map.Read(a.symbols["fac1_m0"] + i) for i in range(8)]
    e0 = s.memory_map.Read(a.symbols["fac1_e0"])
    e1 = s.memory_map.Read(a.symbols["fac1_e1"])
    sg = s.memory_map.Read(a.symbols["fac1_s"])
    return f"S={sg:02x} E=${e1:02x}{e0:02x} M=" + " ".join(f"{b:02x}" for b in m)

def fac2(s):
    m = [s.memory_map.Read(a.symbols["fac2_m0"] + i) for i in range(8)]
    e0 = s.memory_map.Read(a.symbols["fac2_e0"])
    e1 = s.memory_map.Read(a.symbols["fac2_e1"])
    sg = s.memory_map.Read(a.symbols["fac2_s"])
    return f"S={sg:02x} E=${e1:02x}{e0:02x} M=" + " ".join(f"{b:02x}" for b in m)

s = sim6502(obj, symbols=a.symbols)
s.memory_map.Write(BUF_A, ord('0'))
s.memory_map.Write(BUF_A+1, 0)
for i in range(9): s.memory_map.Write(BUF_R+i, 0)
s.reset(); s.pc = TEST_ORG

# Stop at key labels and dump state
checkpoints = [
    ("atof_is_digit", "first atof_is_digit entry"),
    ("fmul_by_ten", "entering fmul_by_ten"),
    ("itof32", "entering itof32"),
    ("cpy_f1_f2", "entering cpy_f1_f2"),
    ("fadd", "entering fadd"),
    ("atof_no_dec_frac", "after fadd"),
]
seen = set()
step = 0
max_steps = 5000
while s.pc != DONE and step < max_steps:
    lbl = None
    for name, desc in checkpoints:
        addr = a.symbols.get(name)
        if addr is not None and s.pc == addr and (name, step) not in seen:
            # only take each the first time
            if name not in seen:
                seen.add(name)
                lbl = (name, desc)
                break
    if lbl:
        print(f"[step {step}] {lbl[0]} ({lbl[1]}) pc=${s.pc:04x}")
        print(f"    FAC1 {fac1(s)}")
        print(f"    FAC2 {fac2(s)}")
    s.execute(); step += 1

# final state
print(f"[step {step}] DONE")
print(f"    FAC1 {fac1(s)}")
print(f"    FAC2 {fac2(s)}")
r = bytes(s.memory_map.Read(BUF_R+i) for i in range(8))
print(f"    packed = {' '.join(f'{b:02x}' for b in r)}  = {struct.unpack('<d', r)[0]}")
