#!/usr/bin/env python3
"""Dump fcmp label addresses to find branch-out-of-range issues."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from asm6502 import asm6502

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "ieee754.asm")) as f:
    lib = f.read().splitlines()
a = asm6502(debug=0)
(lst, _) = a.assemble(lib)
sym = a.symbols

for key in sorted(sym.keys()):
    if key.startswith("fcmp"):
        print(f"{key} = ${sym[key]:04x}")

# Look for ?? in listing (unresolved branches)
print()
print("Unresolved lines:")
for l in lst:
    if "??" in l:
        print(" ", l)
