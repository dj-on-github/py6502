#!/usr/bin/env python3
"""Investigate why ftoa output is empty."""
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

def run(v):
    stub = [
        f'        org ${TEST_ORG:04x}',
        f'        lda #${BUF_A & 0xff:02x}', f'        sta ${PTR1:02x}',
        f'        lda #${(BUF_A >> 8) & 0xff:02x}', f'        sta ${PTR1 + 1:02x}',
        '        jsr unpack1',
        f'        lda #${BUF_R & 0xff:02x}', f'        sta ${PTR1:02x}',
        f'        lda #${(BUF_R >> 8) & 0xff:02x}', f'        sta ${PTR1 + 1:02x}',
        '        jsr ftoa',
        f'        org ${DONE:04x}', '        brk',
    ]
    a.assemble(stub, clear_lst=True, clear_sym=False, clear_obj=False)
    obj = a.object_code[:]
    obj[0xfffc] = TEST_ORG & 0xff
    obj[0xfffd] = (TEST_ORG >> 8) & 0xff
    s = sim6502(obj, symbols=a.symbols)
    for i, b in enumerate(struct.pack('<d', v)):
        s.memory_map.Write(BUF_A + i, b)
    for i in range(40):
        s.memory_map.Write(BUF_R + i, 0xcc)  # fill with distinctive byte
    s.reset(); s.pc = TEST_ORG
    steps = 0
    while s.pc != DONE and steps < 2_000_000:
        s.execute()
        steps += 1
    # dump BUF_R as bytes and as string
    buf = bytes(s.memory_map.Read(BUF_R+i) for i in range(40))
    print(f"\n{v!r}:")
    print(f"  raw BUF_R: {' '.join(f'{b:02x}' for b in buf)}")
    # extract up to first 0 byte
    idx = buf.find(0)
    if idx >= 0:
        s_str = buf[:idx].decode('ascii', errors='replace')
    else:
        s_str = buf.decode('ascii', errors='replace')
    print(f"  string: {s_str!r}")
    print(f"  [{steps} steps]")

run(0.0)
run(1.0)
run(2.0)
run(3.141592653589793)
