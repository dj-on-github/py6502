# Some code sequences from
# http://www.textfiles.com/100/krckwczt.app

# This shows how to simply feed in straight text
# by passing it through splitlines() or reading from a file with readlines()

from asm6502 import asm6502

f = open("Krakowicz_examples.asm",'r')
lines = f.readlines()

a = asm6502()
a.assemble(lines)

