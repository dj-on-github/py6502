#!/usr/bin/env python3
"""Print the listing around specified labels and disassemble object bytes."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from asm6502 import asm6502

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "ieee754.asm")) as f:
    lib = f.read().splitlines()

a = asm6502(debug=0)
(lst, _) = a.assemble(lib)
sym = a.symbols

import re
labels = ["fadd", "fadd_align", "fadd_f2_smaller", "fadd_f2_tiny",
          "fadd_shift_f1", "fadd_do_addsub", "fadd_do_sub",
          "mshr_f2", "mshr_f2_done", "fadd_cmp_done", "fadd_sub_f2_from_f1"]
for lab in labels:
    if lab in sym:
        print(f"{lab} = ${sym[lab]:04x}")
    else:
        print(f"{lab} not found")

print()
# Show raw bytes around interesting region
start = sym["fadd_f2_smaller"]
end = sym["fadd_do_addsub"] + 20
print(f"Disassembly raw bytes ${start:04x}..${end:04x}:")
for a_ in range(start, end):
    v = a.object_code[a_]
    if v < 0:
        v = "--"
    else:
        v = f"{v:02x}"
    labelstr = ""
    for ln,la in sym.items():
        if la == a_:
            labelstr = ln
            break
    print(f"  ${a_:04x}: {v}  {labelstr}")
