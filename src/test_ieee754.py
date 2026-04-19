#!/usr/bin/env python3
"""
Exercise ieee754.asm in the py6502 simulator.

Strategy:
  - Assemble ieee754.asm plus a tiny scaffold that sets ptr1/ptr2 to
    known buffers and JSRs into the routine under test.
  - Drive the simulator until PC lands on a sentinel 'brk' at a fixed
    address.
  - Read result bytes back out of the simulator's memory, compare against
    Python's reference float.

We test: unpack/pack roundtrip, fadd, fsub, fmul, fdiv, fcmp, itof32/ftoi32.
"""

import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from asm6502 import asm6502
from sim6502 import sim6502

HERE = os.path.dirname(os.path.abspath(__file__))

BUF_A = 0x0200   # 8-byte operand A
BUF_B = 0x0208   # 8-byte operand B
BUF_R = 0x0210   # 8-byte result buffer
TEST_ORG = 0x0300  # test stub entry point
DONE_ADDR = 0x03ff # sentinel brk

# ---------- assemble once ----------
with open(os.path.join(HERE, "ieee754.asm")) as f:
    lib_src = f.read().splitlines()

a = asm6502(debug=0)
a.assemble(lib_src)
# remove the reset-vector overlay so our test stub can use org 0x300 freely
for addr in range(0xfffa, 0x10000):
    a.object_code[addr] = -1
LIB_SYMS = dict(a.symbols)

def build_stub(op_label, swap_operands=False):
    """A tiny driver: load PTR1/PTR2, run unpack/op/pack, halt at DONE_ADDR."""
    stub = [
        f'        org ${TEST_ORG:04x}',
        f'        lda #${BUF_A & 0xff:02x}',
        f'        sta ${a.symbols["ptr1"]:02x}',
        f'        lda #${(BUF_A >> 8) & 0xff:02x}',
        f'        sta ${a.symbols["ptr1"] + 1:02x}',
        f'        lda #${BUF_B & 0xff:02x}',
        f'        sta ${a.symbols["ptr2"]:02x}',
        f'        lda #${(BUF_B >> 8) & 0xff:02x}',
        f'        sta ${a.symbols["ptr2"] + 1:02x}',
        '        jsr unpack1',
        '        jsr unpack2',
    ]
    if op_label is not None:
        stub.append(f'        jsr {op_label}')
    # store A into a well-known byte so fcmp tests can inspect it
    stub.append(f'        sta ${BUF_R + 8:04x}')
    # pack result (harmless if op_label is None / fcmp)
    stub += [
        f'        lda #${BUF_R & 0xff:02x}',
        f'        sta ${a.symbols["ptr1"]:02x}',
        f'        lda #${(BUF_R >> 8) & 0xff:02x}',
        f'        sta ${a.symbols["ptr1"] + 1:02x}',
        '        jsr pack1',
        f'        org ${DONE_ADDR:04x}',
        '        brk',
    ]
    return stub

def run(stub, bufA, bufB, max_steps=2_000_000):
    # re-assemble with library + stub.  asm6502.assemble by default retains
    # object_code between calls, so we just add the stub on top.
    a.assemble(stub, clear_lst=True, clear_sym=False, clear_obj=False)
    obj = a.object_code[:]
    # Zero the reset-vector region so the simulator resets cleanly
    obj[0xfffc] = TEST_ORG & 0xff
    obj[0xfffd] = (TEST_ORG >> 8) & 0xff
    s = sim6502(obj, symbols=a.symbols)
    # write operand buffers
    for i, b in enumerate(bufA):
        s.memory_map.Write(BUF_A + i, b)
    for i, b in enumerate(bufB):
        s.memory_map.Write(BUF_B + i, b)
    # clear result buffer
    for i in range(9):
        s.memory_map.Write(BUF_R + i, 0)
    s.reset()
    s.pc = TEST_ORG
    steps = 0
    while s.pc != DONE_ADDR and steps < max_steps:
        s.execute()
        steps += 1
    if steps >= max_steps:
        raise RuntimeError(f"Simulation timed out (>{max_steps} steps) at pc=${s.pc:04x}")
    result = bytes(s.memory_map.Read(BUF_R + i) for i in range(8))
    a_reg = s.memory_map.Read(BUF_R + 8)
    return result, a_reg, steps

def f_to_bytes(f):
    return struct.pack('<d', f)

def bytes_to_f(b):
    return struct.unpack('<d', b)[0]

def approx_eq(a, b, rel=1e-12, abs_=1e-300):
    if a == b:
        return True
    if b == 0:
        return abs(a) < abs_
    return abs(a - b) / abs(b) < rel

# ---------- individual tests ----------
def test_unpack_pack():
    for v in [1.0, -1.0, 0.0, 2.0, 0.5, 3.141592653589793, 1e100, -1e-100, 1234567.875]:
        r, _, _ = run(build_stub(None), f_to_bytes(v), b'\0'*8)
        got = bytes_to_f(r)
        ok = (v == 0.0 and got == 0.0) or approx_eq(got, v)
        print(f"  pack(unpack({v!r:>26})) = {got!r:<26} {'OK' if ok else 'FAIL'}")

def test_binop(op_label, fn, cases):
    print(f"{op_label}:")
    for av, bv in cases:
        r, _, steps = run(build_stub(op_label), f_to_bytes(av), f_to_bytes(bv))
        got = bytes_to_f(r)
        expected = fn(av, bv)
        ok = (expected == 0.0 and got == 0.0) or approx_eq(got, expected, rel=1e-12)
        print(f"  {av!r:>16} {op_label} {bv!r:<16} = {got!r:<24} (expected {expected!r:<24}) [{steps} steps] {'OK' if ok else 'FAIL'}")

def test_fcmp():
    print("fcmp:")
    cases = [
        (1.0, 1.0, 0x00),
        (2.0, 1.0, 0x01),
        (1.0, 2.0, 0xff),
        (-1.0, 1.0, 0xff),
        (1.0, -1.0, 0x01),
        (-2.0, -1.0, 0xff),
        (0.0, 0.0, 0x00),
        (0.0, 1.0, 0xff),
        (1.0, 0.0, 0x01),
        (1e100, 1e-100, 0x01),
    ]
    for av, bv, expected_a in cases:
        _, a_reg, _ = run(build_stub("fcmp"), f_to_bytes(av), f_to_bytes(bv))
        ok = a_reg == expected_a
        print(f"  fcmp({av:>8}, {bv:<8}) -> A=${a_reg:02x} (expected ${expected_a:02x}) {'OK' if ok else 'FAIL'}")

def test_itof32():
    print("itof32:")
    # Layout: put a 32-bit signed int at BUF_A, zero FAC2, call a stub that
    # copies BUF_A -> FAC1_M0..M3 then calls itof32 then pack1.
    FAC1_M0 = a.symbols["fac1_m0"]
    PTR1 = a.symbols["ptr1"]
    for v in [0, 1, -1, 42, -42, 1_000_000, -1_000_000, 2_000_000_000, -2_000_000_000]:
        stub = [
            f'        org ${TEST_ORG:04x}',
            # load the 4 bytes of v into FAC1_M0..M3 directly
        ]
        vb = struct.pack('<i', v)
        for i, byte in enumerate(vb):
            stub.append(f'        lda #${byte:02x}')
            stub.append(f'        sta ${FAC1_M0 + i:02x}')
        # clear M4..M7 so itof32 sees a clean slate
        for i in range(4, 8):
            stub.append(f'        stz ${FAC1_M0 + i:02x}')
        stub += [
            '        jsr itof32',
            f'        lda #${BUF_R & 0xff:02x}',
            f'        sta ${PTR1:02x}',
            f'        lda #${(BUF_R >> 8) & 0xff:02x}',
            f'        sta ${PTR1 + 1:02x}',
            '        jsr pack1',
            f'        org ${DONE_ADDR:04x}',
            '        brk',
        ]
        r, _, _ = run(stub, b'\0'*8, b'\0'*8)
        got = bytes_to_f(r)
        ok = got == float(v)
        print(f"  itof32({v!r:>12}) = {got!r:<10} {'OK' if ok else 'FAIL'}")

def test_ftoi32():
    print("ftoi32:")
    FAC1_M0 = a.symbols["fac1_m0"]
    PTR1 = a.symbols["ptr1"]
    for v in [0.0, 1.0, -1.0, 42.0, -42.0, 1234567.875, -1234567.875, 2_000_000_000.0, -2_000_000_000.0]:
        stub = [
            f'        org ${TEST_ORG:04x}',
            f'        lda #${BUF_A & 0xff:02x}',
            f'        sta ${PTR1:02x}',
            f'        lda #${(BUF_A >> 8) & 0xff:02x}',
            f'        sta ${PTR1 + 1:02x}',
            '        jsr unpack1',
            '        jsr ftoi32',
            # copy FAC1_M0..M3 to BUF_R
            f'        lda ${FAC1_M0:02x}',
            f'        sta ${BUF_R:04x}',
            f'        lda ${FAC1_M0 + 1:02x}',
            f'        sta ${BUF_R + 1:04x}',
            f'        lda ${FAC1_M0 + 2:02x}',
            f'        sta ${BUF_R + 2:04x}',
            f'        lda ${FAC1_M0 + 3:02x}',
            f'        sta ${BUF_R + 3:04x}',
            f'        org ${DONE_ADDR:04x}',
            '        brk',
        ]
        r, _, _ = run(stub, f_to_bytes(v), b'\0'*8)
        got = struct.unpack('<i', r[:4])[0]
        expected = int(v)  # Python's int() truncates toward zero
        ok = got == expected
        print(f"  ftoi32({v!r:>16}) = {got!r:<14} (expected {expected:<14}) {'OK' if ok else 'FAIL'}")

def test_ftoa():
    print("ftoa:")
    PTR1 = a.symbols["ptr1"]
    PTR2 = a.symbols["ptr2"]
    # We'll place the input operand at BUF_A, unpack into FAC1, then point
    # ptr1 at BUF_R (which will hold the output ASCII string, up to 24 bytes).
    cases = [0.0, 1.0, -1.0, 2.0, 0.5, 3.141592653589793, 1234567.875,
             -1234567.875, 1e20, 1e-20, 6.283185307179586]
    for v in cases:
        stub = [
            f'        org ${TEST_ORG:04x}',
            # ptr1 = BUF_A (input packed double)
            f'        lda #${BUF_A & 0xff:02x}',
            f'        sta ${PTR1:02x}',
            f'        lda #${(BUF_A >> 8) & 0xff:02x}',
            f'        sta ${PTR1 + 1:02x}',
            '        jsr unpack1',
            # ptr1 = BUF_R (output string)
            f'        lda #${BUF_R & 0xff:02x}',
            f'        sta ${PTR1:02x}',
            f'        lda #${(BUF_R >> 8) & 0xff:02x}',
            f'        sta ${PTR1 + 1:02x}',
            '        jsr ftoa',
            f'        jmp ${DONE_ADDR:04x}',  # avoid falling through to leftover code
            f'        org ${DONE_ADDR:04x}',
            '        brk',
        ]
        a.assemble(stub, clear_lst=True, clear_sym=False, clear_obj=False)
        obj = a.object_code[:]
        obj[0xfffc] = TEST_ORG & 0xff
        obj[0xfffd] = (TEST_ORG >> 8) & 0xff
        s = sim6502(obj, symbols=a.symbols)
        for i, b in enumerate(f_to_bytes(v)):
            s.memory_map.Write(BUF_A + i, b)
        # clear output buffer so null-termination is visible
        for i in range(32):
            s.memory_map.Write(BUF_R + i, 0)
        s.reset()
        s.pc = TEST_ORG
        steps = 0
        while s.pc != DONE_ADDR and steps < 5_000_000:
            s.execute()
            steps += 1
        # read string up to null
        out = bytearray()
        for i in range(32):
            b = s.memory_map.Read(BUF_R + i)
            if b == 0:
                break
            out.append(b)
        s_str = out.decode('ascii', errors='replace')
        # parse back with Python to verify it's close
        try:
            got = float(s_str)
            ok = (v == 0.0 and got == 0.0) or approx_eq(got, v, rel=1e-12)
        except ValueError:
            got = None
            ok = False
        print(f"  ftoa({v!r:>24}) = {s_str!r:<28} parsed={got!r:<24} [{steps} steps] {'OK' if ok else 'FAIL'}")

def test_atof():
    print("atof:")
    PTR1 = a.symbols["ptr1"]
    cases = ["0", "1", "-1", "42", "-42", "3.141592653589793",
             "1234567.875", "-1234567.875", "1e20", "1e-20",
             "0.5", "6.283185307179586", "2.5e10", "-1.5e-5"]
    for s_in in cases:
        # Build stub: ptr1 = BUF_A (source string), atof, pack1 to BUF_R
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
            f'        org ${DONE_ADDR:04x}',
            '        brk',
        ]
        a.assemble(stub, clear_lst=True, clear_sym=False, clear_obj=False)
        obj = a.object_code[:]
        obj[0xfffc] = TEST_ORG & 0xff
        obj[0xfffd] = (TEST_ORG >> 8) & 0xff
        s = sim6502(obj, symbols=a.symbols)
        src = s_in.encode('ascii') + b'\0'
        for i, b in enumerate(src):
            s.memory_map.Write(BUF_A + i, b)
        for i in range(9):
            s.memory_map.Write(BUF_R + i, 0)
        s.reset()
        s.pc = TEST_ORG
        steps = 0
        while s.pc != DONE_ADDR and steps < 5_000_000:
            s.execute()
            steps += 1
        r = bytes(s.memory_map.Read(BUF_R + i) for i in range(8))
        got = bytes_to_f(r)
        expected = float(s_in)
        ok = (expected == 0.0 and got == 0.0) or approx_eq(got, expected, rel=1e-12)
        print(f"  atof({s_in!r:>24}) = {got!r:<24} (expected {expected!r:<24}) [{steps} steps] {'OK' if ok else 'FAIL'}")

if __name__ == "__main__":
    print("unpack/pack roundtrip:")
    test_unpack_pack()
    print()
    test_binop("fadd", lambda x, y: x + y, [
        (1.0, 2.0), (3.5, 1.25), (1.0, -0.5), (-2.0, -3.0),
        (1e20, 1.0), (0.0, 5.0), (5.0, 0.0), (1.0, -1.0),
        (1.1, 2.2),
    ])
    print()
    test_binop("fsub", lambda x, y: x - y, [
        (3.0, 1.0), (1.0, 3.0), (0.5, 0.25), (-1.0, -1.0),
        (1e20, 1.0), (1.0, 1e-20),
    ])
    print()
    test_binop("fmul", lambda x, y: x * y, [
        (2.0, 3.0), (1.5, 2.5), (-2.0, 3.0), (0.5, 0.5),
        (1e10, 1e10), (1e-10, 1e-10), (0.0, 123.0), (3.141592653589793, 2.0),
    ])
    print()
    test_binop("fdiv", lambda x, y: x / y, [
        (6.0, 2.0), (1.0, 3.0), (-10.0, 4.0), (1.0, 0.5),
        (1e20, 1e10), (355.0, 113.0),
    ])
    print()
    test_fcmp()
    print()
    test_itof32()
    print()
    test_ftoi32()
    print()
    test_ftoa()
    print()
    test_atof()
