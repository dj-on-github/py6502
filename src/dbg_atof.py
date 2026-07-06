#!/usr/bin/env python3
"""Trace atof on a simple input."""
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
    f'        lda #${BUF_A & 0xff:02x}',
    f'        sta ${PTR1:02x}',
    f'        lda #${(BUF_A >> 8) & 0xff:02x}',
    f'        sta ${PTR1 + 1:02x}',
    '        jsr atof',
    f'        lda #${BUF_R & 0xff:02x}',
    f'        sta ${PTR1:02x}',
    f'        lda #${(BUF_R >> 8) & 0xff:02x}',
    f'        sta ${PTR1 + 1:02x}',
    '        jsr pack1',
    f'        org ${DONE:04x}',
    '        brk',
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

def run(input_str, stop_label=None):
    s = sim6502(obj, symbols=a.symbols)
    src = input_str.encode('ascii') + b'\0'
    for i,b in enumerate(src): s.memory_map.Write(BUF_A+i, b)
    for i in range(9): s.memory_map.Write(BUF_R+i, 0)
    s.reset(); s.pc = TEST_ORG
    hit_labels = []
    label_addrs = {v:k for k,v in a.symbols.items() if k.startswith("atof")}
    steps = 0
    while s.pc != DONE and steps < 50000:
        if s.pc in label_addrs:
            hit_labels.append(label_addrs[s.pc])
        s.execute()
        steps += 1
    print(f"Input {input_str!r}: {steps} steps")
    # Unique label sequence compressed
    compressed = []
    for lbl in hit_labels:
        if not compressed or compressed[-1][0] != lbl:
            compressed.append([lbl, 1])
        else:
            compressed[-1][1] += 1
    for lbl, cnt in compressed:
        print(f"  {lbl} x{cnt}")
    r = bytes(s.memory_map.Read(BUF_R+i) for i in range(8))
    got = struct.unpack('<d', r)[0]
    print(f"  Result: {got}")
    print(f"  FAC1 (packed): {' '.join(f'{b:02x}' for b in r)}")

run("0")
print()
run("1")
print()
run("5")
