# This shows how to run the disassembler

from asm6502 import asm6502
from dis6502 import dis6502

thecode = """
        ORG  $100
start:
        LDA #$10
        LDX #$00
loop:
        STA $1000,x
        INX
        SBC #$01
        BPL loop
        RTS
"""

lines = thecode.splitlines()

a = asm6502()
(lst,sym) = a.assemble(lines)
# inspect output
for line in lst:
    print(line)
print()
for symbol in sym:
    print(symbol)
print()
a.print_object_code()

# Now work backwards, but make life hard by using an empty symbol table
d = dis6502(a.object_code, {})
# Pass 1 - build symbol table
z = d.disassemble_region(0x100, 13, gen_symbols=True)
# Need this to make the generator run, even though we ignore the output
list(z)
# Build data structure
d.build_symbols_xref()
# Pass 2: and output..
z = d.disassemble_region(0x100, 13)
for line in list(z):
    print (line)

print()
for sym in d.symbols:
    print(f"{sym:10s} = ${d.symbols[sym]:04X}")

