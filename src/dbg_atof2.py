#!/usr/bin/env python3
"""Check constants memory and trace fmul_by_ten during atof."""
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

print("From library-only object_code:")
print(f"  $0280 (ten):   " + " ".join(f"{a.object_code[0x0280+i]:02x}" for i in range(8)))
print(f"  $0288 (tenth): " + " ".join(f"{a.object_code[0x0288+i]:02x}" for i in range(8)))
print(f"  $0290 (one):   " + " ".join(f"{a.object_code[0x0290+i]:02x}" for i in range(8)))

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

print("\nAfter re-assembling stub:")
print(f"  $0280 (ten):   " + " ".join(f"{obj[0x0280+i] & 0xff:02x}" for i in range(8)))
print(f"  $0288 (tenth): " + " ".join(f"{obj[0x0288+i] & 0xff:02x}" for i in range(8)))
print(f"  $0290 (one):   " + " ".join(f"{obj[0x0290+i] & 0xff:02x}" for i in range(8)))

# Now run atof("0") and inspect after fmul_by_ten
s = sim6502(obj, symbols=a.symbols)
s.memory_map.Write(BUF_A, ord('0'))
s.memory_map.Write(BUF_A+1, 0)
for i in range(9): s.memory_map.Write(BUF_R+i, 0)
s.reset(); s.pc = TEST_ORG

print("\nMemory at $0280 from sim:")
print("  ten:   " + " ".join(f"{s.memory_map.Read(0x0280+i):02x}" for i in range(8)))

# Step to after first fmul_by_ten returns, i.e. to label atof_is_digit + past the jsr
atof_is_digit = a.symbols["atof_is_digit"]
fmul_by_ten = a.symbols["fmul_by_ten"]
steps = 0
while s.pc != atof_is_digit and steps < 10000:
    s.execute(); steps += 1

# Now at atof_is_digit. Step past the save-y (sty tmp0) and into fmul_by_ten.
# Find fmul_by_ten label in symbols
print(f"\nAt atof_is_digit, FAC1: " + " ".join(f"{s.memory_map.Read(a.symbols['fac1_m0']+i):02x}" for i in range(8)))

# Step until pc == fmul_by_ten
while s.pc != fmul_by_ten and steps < 10000:
    s.execute(); steps += 1
print(f"At fmul_by_ten, FAC1: " + " ".join(f"{s.memory_map.Read(a.symbols['fac1_m0']+i):02x}" for i in range(8)))
print(f"  fac1_e=${s.memory_map.Read(a.symbols['fac1_e1']):02x}{s.memory_map.Read(a.symbols['fac1_e0']):02x}  fac1_s=${s.memory_map.Read(a.symbols['fac1_s']):02x}")

# Run past the rts of fmul_by_ten. fmul_by_ten JMPs to fmul so the RTS that lands us back is inside fmul.
fmul_done = a.symbols.get("fmul_done", None)
print(f"  fmul_done = ${fmul_done:04x}" if fmul_done else "")

# Continue until we're back at atof_is_digit's next instruction (after jsr fmul_by_ten)
# Just continue to the very next label in atof which is atof_no_dec_frac or similar.
# Actually the cleanest is to advance until PC is back within atof range (close to atof_is_digit)
atof_range = (a.symbols["atof_is_digit"], a.symbols["atof_no_dec_frac"])
while not (atof_range[0] < s.pc < atof_range[1] + 0x20) and steps < 50000:
    s.execute(); steps += 1

print(f"\nAfter fmul_by_ten return, FAC1 (unpacked): " + " ".join(f"{s.memory_map.Read(a.symbols['fac1_m0']+i):02x}" for i in range(8)))
print(f"  fac1_e=${s.memory_map.Read(a.symbols['fac1_e1']):02x}{s.memory_map.Read(a.symbols['fac1_e0']):02x}  fac1_s=${s.memory_map.Read(a.symbols['fac1_s']):02x}")
print(f"  fac2_m0..7: " + " ".join(f"{s.memory_map.Read(a.symbols['fac2_m0']+i):02x}" for i in range(8)))
print(f"  fac2_e=${s.memory_map.Read(a.symbols['fac2_e1']):02x}{s.memory_map.Read(a.symbols['fac2_e0']):02x}  fac2_s=${s.memory_map.Read(a.symbols['fac2_s']):02x}")
