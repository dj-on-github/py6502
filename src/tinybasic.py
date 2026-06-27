# This shows how to simply feed in straight text
# by passing it through splitlines()

from asm6502 import asm6502

f = open("tinybasic.asm","r")

lines = f.readlines()

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
print()
a.print_intelhex()

