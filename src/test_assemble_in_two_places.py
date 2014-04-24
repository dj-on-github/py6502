#!/usr/bin/python
from asm6502 import asm6502
a = asm6502(debug=0)
lines = [' ORG $1000', ' NOP', ' LDA #$20', 'here: NOP', '  DB 10,11,12,13', '  RTS']
a.assemble(lines)
lines[0] = ' ORG $2000'
a.assemble(lines)
