#!/usr/bin/env python3
"""Assemble ieee754.asm and report any errors/warnings."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from asm6502 import asm6502

HERE = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(HERE, "ieee754.asm")

with open(src_path) as f:
    lines = f.read().splitlines()

a = asm6502(debug=0)
(lst, sym) = a.assemble(lines)

# Print first few listing lines + any lines flagged with ??
out = "\n".join(lst)
print(out)
print()
print("Symbol count:", len(sym))
# Check for '??' which asm6502 emits when something didn't resolve
bad = [l for l in lst if "??" in l]
if bad:
    print(f"*** {len(bad)} unresolved lines ***")
    for l in bad[:30]:
        print(" ", l)
