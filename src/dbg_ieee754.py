#!/usr/bin/env python3
"""Dump FAC1 state after executing a single float op."""
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

BUF_A, BUF_B, BUF_R = 0x0200, 0x0208, 0x0210
TEST_ORG, DONE = 0x0300, 0x03ff

def fbytes(f): return struct.pack('<d', f)

def dump_fac1(s, label):
    m = [s.memory_map.Read(a.symbols["fac1_m0"] + i) for i in range(8)]
    e = [s.memory_map.Read(a.symbols["fac1_e0"]), s.memory_map.Read(a.symbols["fac1_e1"])]
    sg = s.memory_map.Read(a.symbols["fac1_s"])
    print(f"  [{label}] FAC1 M="+ " ".join(f"{b:02x}" for b in m) + f"  E={e[1]:02x}{e[0]:02x}  S={sg:02x}")

def dump_fac2(s, label):
    m = [s.memory_map.Read(a.symbols["fac2_m0"] + i) for i in range(8)]
    e = [s.memory_map.Read(a.symbols["fac2_e0"]), s.memory_map.Read(a.symbols["fac2_e1"])]
    sg = s.memory_map.Read(a.symbols["fac2_s"])
    print(f"  [{label}] FAC2 M="+ " ".join(f"{b:02x}" for b in m) + f"  E={e[1]:02x}{e[0]:02x}  S={sg:02x}")

def go(op, va, vb):
    print(f"--- {va} {op} {vb} ---")
    stub = [
        f'        org ${TEST_ORG:04x}',
        f'        lda #${BUF_A & 0xff:02x}', f'        sta $96',
        f'        lda #${(BUF_A >> 8) & 0xff:02x}', f'        sta $97',
        f'        lda #${BUF_B & 0xff:02x}', f'        sta $98',
        f'        lda #${(BUF_B >> 8) & 0xff:02x}', f'        sta $99',
        '        jsr unpack1',
        '        jsr unpack2',
        f'        jsr {op}',
        f'        org ${DONE:04x}', '        brk',
    ]
    a.assemble(stub, clear_lst=True, clear_sym=False, clear_obj=False)
    obj = a.object_code[:]
    obj[0xfffc] = TEST_ORG & 0xff
    obj[0xfffd] = (TEST_ORG >> 8) & 0xff
    s = sim6502(obj, symbols=a.symbols)
    for i,b in enumerate(fbytes(va)): s.memory_map.Write(BUF_A+i, b)
    for i,b in enumerate(fbytes(vb)): s.memory_map.Write(BUF_B+i, b)
    s.reset(); s.pc = TEST_ORG
    # Step past unpack1 & unpack2 so we can see the pre-op state
    unpack1_addr = a.symbols["unpack1"]
    fadd_addr = a.symbols[op]
    # Run until we're about to call the op
    while True:
        s.execute()
        if s.pc == fadd_addr:
            dump_fac1(s, "pre-op")
            dump_fac2(s, "pre-op")
            break
    # Step into op, run until rts back
    sp0 = s.sp
    while True:
        s.execute()
        if s.pc == DONE:
            break
    dump_fac1(s, "post-op")

go("fadd", 1.0, -0.5)
go("fadd", 3.5, 1.25)
go("fsub", 3.0, 1.0)
go("fdiv", 6.0, 2.0)
