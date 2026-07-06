#!/usr/bin/env python3
"""Single-step trace through an op to find where control flow goes wrong."""
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

# Build reverse label map: addr -> label (for a subset of interesting labels)
labels_of_interest = [
    "fadd", "fadd_ret", "fadd_align", "fadd_f2_smaller", "fadd_f2_tiny",
    "fadd_f1_is_neg", "fadd_shift_f1", "fadd_do_addsub", "fadd_do_sub",
    "fadd_cmp_done", "fadd_sub_f2_from_f1",
    "mshr_f1", "mshr_f1_loop", "mshr1_f1",
    "mshr_f2", "mshr_f2_loop", "mshr_f2_done", "mshr1_f2",
    "normalize_f1", "norm_f1_nz", "norm_f1_shr", "norm_f1_done",
    "iszero_f1", "iszero_f2", "cpy_f2_f1",
    "unpack1", "unpack2", "unpack_common_f1", "unpack_common_f2",
]
addr_to_label = {}
for lab in labels_of_interest:
    if lab in a.symbols:
        addr_to_label[a.symbols[lab]] = lab

def go(op, va, vb, trace=True, max_trace=120):
    print(f"=== {va} {op} {vb} ===")
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
    op_addr = a.symbols[op]
    # Run up to op
    while s.pc != op_addr:
        s.execute()
    # Trace
    count = 0
    visited = []
    while s.pc != DONE:
        if s.pc in addr_to_label:
            visited.append((count, s.pc, addr_to_label[s.pc]))
        s.execute()
        count += 1
        if count > 2000:
            print("  ABORT (too many steps)")
            break
    for (n, pc, lab) in visited[:max_trace]:
        print(f"  step {n:4d}  pc=${pc:04x}  {lab}")
    # Final state
    m = [s.memory_map.Read(a.symbols["fac1_m0"] + i) for i in range(8)]
    e = [s.memory_map.Read(a.symbols["fac1_e0"]), s.memory_map.Read(a.symbols["fac1_e1"])]
    sg = s.memory_map.Read(a.symbols["fac1_s"])
    print(f"  FINAL FAC1 M="+ " ".join(f"{b:02x}" for b in m) + f"  E={e[1]:02x}{e[0]:02x}  S={sg:02x}")

go("fadd", 3.5, 1.25)
go("fadd", 1.0, 2.0)  # known good, for comparison
go("fadd", 1.0, -0.5)
