# This shows how to simply feed in straight text
# by passing it through splitlines()

from asm6502 import asm6502

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
a.assemble(lines)

