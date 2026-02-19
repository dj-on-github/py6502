A python based 6502 assembler, disassembler and simulator
David Johnston

The Philosophy
--------------

I enjoy old-school electronics and programming. I've learned over time that there is a benefit to combining old-school methods with modern tools.

For example:
1) My day job is a chip designer, focusing on cryptgraphic circuits. For a particular project I either needed a big state machine or a small CPU. An old school 8 bit processor took me 4 hours to implement in synthesizable RTL and on a modern silicon process it runs blindingly fast in a tiny bit of silicon area. It came with lots of tools already since the instruction was standard.

2) I wrote a Point-of-Sale system for a family store, since the off-the-shelf solutions were expensive and none of them matched the needs of the store. Instead of going for some windows interface or touch driven app on a tablet, I wrote the user interface using the old-school curses library for a text based interface that was designed to minimize keystrokes at the checkout. The staff loved it since the key strokes took a couple of minutes to learn and I wrote it in Python, bringing the simplicity and power of modern programming tools.

In both cases, the benefits of the efficiencies of old school methods with the power of modern methods yielded something better than either.

This project is a proof-of-concept for this idea. I use it for hacking my Apple //e.  It's a 6502 assembler, disassembler and simulator written in Python. Many old 6502 assemblers exist, but they suffer from inconsistent formats, directives and macro processors. In particular the macro processors tended to be horrible.

The thing that makes it a little different is that instead of offering a 'better assembler language' or 'better macro language' I've stripped down the programs to the very basic functions but written them such that they are intended to be called from a python program that feeds it assembler and gets object code back. This then makes python the macro language. So you get the ability to write assembly code normally, or you can write python to automate the code generation or generate parameterized code, or unroll loops or any number of other things, but using a nice language that makes it easy rather than a set of confusing macro directive written in 1978.

If you want to instrument and test of a bit of code, it's easy to assemble it and then write a program in python to iterate over your chosen input states and check the outputs and simulate the code repeatedly, calling the simulation of each instruction directly from python, coding in whatever analysis meets your needs.

The simulator and disassembler works directly with the object code and symbol table from the assembler.

An Simple Example: Sending Assembly to the Assembler From Python
----------------------------------------------------------------
This python (see src/small_example.py) assembles a few instructions

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
        (lst,sym)= a.assemble(lines)
        # inspect output..
        for line in lst:
            print(line)
        print()
        for symbol in sym:
            print(symbol)
        print()
        a.print_object_code()

The output looks like this:
        LISTING
        1    0000 :                                
        2    0100 :                  ORG $100      
        3    0100 : start:                         
        4    0100 :         A9 10    LDA #$10      
        5    0102 :         A2 00    LDX #$00      
        6    0104 : loop:                          
        7    0104 :         9D 00 10 STA $1000,x   
        8    0107 :         E8       INX           
        9    0108 :         E9 01    SBC #$01      
        10   010A :         10 FA    BPL loop      
        11   010C :         60       RTS
        
        SYMBOL TABLE
        start      = $0100
        loop       = $0104
        
        OBJECT CODE
        *
        0100: A9 10 A2 00 9D 00 10 E8 E9 01 10 FA 60
        *

The Listing
-----------

If after running that, you typed this:
    >>> a.listing

you would see the assembly output as an array:

['1    0000 :                                ', '2    0100 :                  org $100      ', '3    0100 : start:                         ', '4    0100 :         A9 10    lda #$10      ', '5    0102 :         A2 00    ldx #$00      ', '6    0104 : loop:                          ', '7    0104 :         9D 00 10 sta $1000,x   ', '8    0107 :         E8       inx           ', '9    0108 :         E9 01    sbc #$01      ', '10   010A :         10 F8    bpl loop      ', '11   010C :         60       rts           ']

The Symbol Table
----------------

You can also see the symbol table as a dictionary after assembling:
    >>> a.symbols
    {'start': 256, 'loop': 260}

The Object Code Map
-------------------

Finally, you can see the list of object code values, but in decimal, since that's how python displays by default:
        >>> a.object_code[256:268]
        [169, 16, 162, 0, 157, 0, 16, 232, 233, 1, 16, 250, 96]
        >>>

The assembler keeps a complete map of the 64K memory space of the 6502 and populates the code and values into that map. The 'object_code' class variable is a list containing the map. Each untouched location is set to -1. Other values indicate the 8 bit value at that location.

After assembling the code into the map, it is possible to add in other things to the map by assigning to the object_code list. E.G.

        a.object_code[0xfffd] = 0x00
        a.object_code[0xfffc] = 0x10
Which would set the reset vector to 0x1000.

Pseudo-ops and Directives
-------------------------

; Comment
ORG address - Set the current assembly location
DB - Generate 8-bit values
DW - Generate 16-bit values
DDW - Generate 32-bit values
DQW - Generate 64-bit values
LE - For multi word data (DW, DDW and DQW) set the encoding to little endian
BE - For multi word data (DW, DDW and DQW) set the encoding to big endian
The assembler defaults to little endian.

DB, DW, DDW and DQW all work in the same way:

* The argument is one or more comma-separated *items*
* Each *item* is one of
  * Decimal number
  * Hex number (indicated by $ prefix)
  * Octal number (indicated by @ prefix)
  * Binary number (indicated by % prefix)
  * Label (indicated by & prefix)
  * String (delimited "thus")
* Each string *item* is transformed into one 8-bit *value* per character (the ASCII code of the character)
* Every other item represents a single *value*
* Every *value* is zero-padded or truncated to generate one or more *bytes* in the object code (1 byte-per-value for DB, 2 for DW etc.)
* The assembler generates a warning when a *value* is truncated

Examples:

DB $0d, "the rain in spain", $0
DB &entry, &loop                 ; both truncated to low byte
DW &entry, "fish"                ; each character padded to 16-bits

Prefixes
--------

The prefixes $, @, % can also be used with numeric arguments to instructions

Labels
------

A word followed by a colon makes a label. It can be on its own line, or in front of an instruction or directive.

alabel:                 ; A label on its own
anotherlabel: STA #$10  ; A label with an instruction

Any address or 16 bit data field can be replaced with a declared label and the label address will be inserted there.
In a DW declaration you need to prefix a label with & to tell the assembler it's a label. Examples:

        dw  $1000, @2000, 123  ; Implicit numbers have a base prefix.
ttable: dw  &l1, &l2, &l3      ; labels in a DW prefixed with &
        org $1000
l1:     lda #$20
        jmp skip
l2:     lda #$30
        jmp skip
l3:     lda #$40
skip:   sta $10

Assembling Into the Same Map
----------------------------

You can call the assembler() class method multiple times; by default, the object_code map is retained between calls. This allows you to assemble multiple pieces of code into different locations and they will be added to the map.
The print_object_code() class method displays the current object code map.
E.G. The following code assembles a sequence, then modifies its origin, then reassembles it:
        from asm6502 import asm6502
        a = asm6502()
        lines = [' ORG $1000', ' NOP', ' LDA #$20', 'here: NOP', ' DB 10,11,12,13', ' RTS']
        a.assemble(lines)
        lines[0] = ' ORG $2000'
        a.assemble(lines)
        a.print_object_code()

This yields this memory map with the same code in two places.
        >>> a.print_object_code()
        OBJECT CODE
        *
        1000: EA A9 20 EA 0A 0B 0C 0D 60
        *
        2000: EA A9 20 EA 0A 0B 0C 0D 60
        *

The default behaviour of the assemble() class method is set by variables that have default values:

        a.assemble(lines, clear_lst=True, clear_sym=True, clear_obj=False)

Setting clear_sym=False retains the symbol table from the previous call, and setting clear_lst=False allows multiple pieces of source code to be grouped together.

Setting clear_sym=True also allows you to establish symbols prior to running the assembler, then reference them in the code:

        from asm6502 import asm6502
        a = asm6502()
        lines = [' ORG $1000', ' NOP', ' LDA #$20', ' JMP syblue', 'here: NOP', ' RTS']
        a.symbols['skyblue'] = 0x4500
        a.assemble(lines, clear_sym=FALSE)

Getting hex dump format data in and out
---------------------------------------
After assembling you can output the object code as a hex dump with * marking the unpopulated spaces

        >>> a.print_object_code()
        >>> a.print_object_code(canonical=True)

The second version used unix hexdump format, which includes an ASCII decode of printable characters.

An optional offset can be used to affect the address field in the output. For example, to generate data for a PROM programmer that expects the addresses to be relative to the first location in the ROM, choose an offset that causes the start address to wrap back to 0 like this:

        >>> a.print_object_code(canonical=True, offset=-0xb400)

You can also load the object code map from a file in hexdump format, also with an optional offset:

        >>> a.load_object_code("some_file.txt", offset=0x400)


Getting IntelHex format data out
--------------------------------
After assembling you can output the object code in intelhex format.
calling the intelhex() method returns lines of intelhex as a list.

        >>> a.intelhex()
        [':10010000A000B90000990020B90001990021B900', ':1001100002990022B90003990023B90004990024', ':10012000B90005990025B90006B90026B9000799', ':0E0130000027B90008990028C8D0D04C59FF', ':10100000A000B90000990020C8D0D0A900850085', ':1010100002A9018501A9218503B2009202E602E6', ':1010200000D0F8E603E601A501C909D0EE4C59FF', ':00000001FF']
        
Calling the print_intelhex() method outputs intelhex format object code to stdout.        
        >>> a.print_intelhex()
        :10010000A000B90000990020B90001990021B900
        :1001100002990022B90003990023B90004990024
        :10012000B90005990025B90006B90026B9000799
        :0E0130000027B90008990028C8D0D04C59FF
        :10100000A000B90000990020C8D0D0A900850085
        :1010100002A9018501A9218503B2009202E602E6
        :1010200000D0F8E603E601A501C909D0EE4C59FF
        :00000001FF
        >>> 

Getting SRecord format data out
--------------------------------
After assembling you can output the object code in S19 Srecord format.
calling the srecord() method returns lines of S19 S Record as a list.

The parameters are (int:version, int:revision, str:module name, str:comment)

>>> a.srecords(10,20,"Module Name,","Comment")
['S02e00000a144d6f64756c65204e616d652c436f6d6d656e74ad', 'S12e1000600D0C0B0AEA20A9EA96', 'S12e2000600D0C0B0AEA20A9EA86', 'S5030003f9', 'S9032008d4']

Calling the print_srecords() method outputs S19 format object code to stdout.        
>>> a.print_srecords(10,20,"Module Name,","Comment")
S02e00000a144d6f64756c65204e616d652c436f6d6d656e74ad
S12e1000600D0C0B0AEA20A9EA96
S12e2000600D0C0B0AEA20A9EA86
S5030003f9
S9032008d4

The Simulator and Disassembler
------------------------------

#The simulator is in sim6502.py, the disassembler is in dis6502.py
#So start with all three..
import asm6502
import sim6502
import dis6502

# The assembler code
src = """
<assembly goes here>
"""
lines = src.splitlines()

#The simulator must be given an object code map. You can get it from the assembler:

# Assemble the code in a list called lines.
a = asm6502.asm6502(debug=0)
a.assemble(lines)
object_code = a.object_code[:]

# Then instantiate the simulator.
# Also pass it the symbol table so it can know addresses
s = sim6502.sim6502(object_code, symbols=a.symbols)

# And instantiate the disassembler:
d = dis6502.dis6502(object_code, symbols=a.symbols)

# Now
# s.reset() will reset the simulation
# s.execute() will execute the current instruction
# The 6502 state will be in
#   s.pc  Program Counter
#   s.a   Accumulator
#   s.x   X registers
#   s.y   Y register
#   s.sp  stack pointer
#   s.cc  Flags
# d.disassemble(address) will disassemble the instruction as the address and
#                        will return a text string of the disassembly
#
# E.G.

s.reset()

print
print "SIMULATION START"
print
# Print a header for the simulator/disassembler output
print ("LABEL      " + "ADDR HEX      INSTR").ljust(status_indent)+" PC   A  X  Y  SP   Status"

# Print the initial state
print " ".ljust(status_indent) + " %04x %02x %02x %02x %04x %02x" % (s.pc,s.a,s.x,s.y,s.sp,s.cc)

# Execute 200 instructions
for i in xrange(200):
    # Disassemble the current instruction
    distxt = d.disassemble_line(s.pc)

    # Execute that instruction
    s.execute()

    # Print out the disassembled instruction followed by the simulator state
    print distxt.ljust(status_indent) + " %04x %02x %02x %02x %04x %02x" % (s.pc,s.a,s.x,s.y,s.sp,s.cc)

# Each output line will then show the address, the hex, the instruction executed and the state of the 6502 after the execution.


The Disassembler for code exploration
-------------------------------------

You can also use the disassembler for code exploration: iteratively disassembling code and then annotating labels. For example consider a file tiny.hexdump with this content:

00000100  a9 10 a2 00 9d 00 10 e8  e9 01 10 f8 60           |............`|

Now try this (see small_dis_example.py):

..
from asm6502 import asm6502
from dis6502 import dis6502

a = asm6502() # only so we can use the loader..
a.load_object_code("tiny.hexdump")

d = dis6502(a.object_code, a.symbols) # a.symbols is empty

z = d.disassemble_region(0x100, 13)
for line in list(z):
    print (line)

The call to disassemble_region() returns a generator, list() consumes its output and the 'for' loop prints it. The result looks like this:

           0100 a9 10    lda  #$10
           0102 a2 00    ldx  #$00
           0104 9d 00 10 sta  $1000,x
           0107 e8       inx  
           0108 e9 01    sbc  #$01
           010a 10 f8    bpl  $f8 ; $0104
           010c 60       rts  

Observe that there is a loop that branches to $f8 which is backwards; the helpful comment shows that the destination address is $104. Add entries to the symbol table for the entry point of the code and another for the loop destination. Whenever you manipulate the symbol table you need to call build_symbols_xref() to rebuild an internal data structure:

d.symbols['start'] = 0x100
d.symbols['loop'] = 0x104
d.build_symbols_xref()

Call disassemble_region() again as before and you will see the labels annotated into the output:

start:     0100 a9 10    lda  #$10
           0102 a2 00    ldx  #$00
loop:      0104 9d 00 10 sta  $1000,x
           0107 e8       inx  
           0108 e9 01    sbc  #$01
           010a 10 f8    bpl  loop ; $0104
           010c 60       rts  

The final trick is that the disassembler will create labels for you. You must call it twice, setting the gen_symbols argument to True. On the first call it populates the symbol table. On the second call, it annotates the symbols onto the output. Like this:

z = d.disassemble_region(0x100, 13, gen_symbols=True)
list(z)
# Build data structure
d.build_symbols_xref()
# Pass 2: and output..
z = d.disassemble_region(0x100, 13)
for line in list(z):
    print (line)

The first "list(z)" might need some explanation: because disassemble_region is a generator, it does not actually perform the calls until it is enumerated (which is done here using 'list'). The output looks like this:

           0100 a9 10    lda  #$10
           0102 a2 00    ldx  #$00
L0104:     0104 9d 00 10 sta  L1000,x
           0107 e8       inx  
           0108 e9 01    sbc  #$01
           010a 10 f8    bpl  L0104 ; $0104
           010c 60       rts  

A symbol is generated for any referenced address, provided one doesn't currently exist. This includes references outside the region being disassembled (L1000 in this example). You can mix this technique with manual manipulation of the symbol table. For example, as an iterative process of exploring a piece of unknown code.

--------------------------------------------
Comments to dj@deadhat.com

--------------------------------------------
TBD 1: Write a 65C02 simulator that runs from the object_code state generated by the assembler
  DONE!

TBD 2: Write an output generator for more of the flash/prom/eeprom programming formats
  Added Srecords. Should also add ascii hex and binary.

TBD 3: Give it decent error handling

TBD 4: Set up a unit test bench to fuzz it with code and do directed tests.

