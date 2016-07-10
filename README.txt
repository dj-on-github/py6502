A python based 6502 assembler
David Johnston

The Philosophy
--------------

I enjoy old-school electronics and programming. I've learned over time that there is a benefit to combining old-school methods with modern tools.

For example:
1) My day job is a chip designer, focusing on cryptgraphic circuits. For a particular project I either needed a big state machine or a small CPU. An old school 8 bit processor took me 4 hours to implement in synthesizable RTL and on a modern silicon process it runs blindingly fast in a tiny bit of silicon area. It came with lots of tools already since the instruction was standard.

2) I wrote a Point-of-Sale system for a family store, since the off-the-shelf solutions were expensive and none of them matched the needs of the store. Instead of going for some windows interface or touch driven app on a tablet, I wrote the user interface using the old-school curses library for a text based interface that was designed to minimize keystrokes at the checkout. The staff loved it since the key strokes took a couple of minutes to learn and I wrote it in Python, bringing the simplicity and power of modern programming tools.

In both cases, the benefits of the efficiencies of old school methods with the power of modern methods yielded something better than either.

This project is a proof-of-concept for this. It's a 6502 assembler written in Python. Many old 6502 assemblers exist, but they suffer from inconsistent formats, directives and macro processors. In particular the macro processors tended to be horrible.

The thing that makes it a little different is that instead of offering a 'better assembler language' or 'better macro language' I've stripped down the assembler to the very basic functions but written it such that it is intended to be called from a python program that feeds it assembler and gets object code back. This then makes python the macro language. So you get the ability to write assembly code normally, or you can write python to automate the code generation or generate parameterized code, or unroll loops or any number of other things, but using a nice language that makes it easy rather than a set of confusing macro directive written in 1978.

An Simple Example: Sending Assembly to the Assembler From Python
----------------------------------------------------------------
This python assembles a few instructions

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

The output looks like this:

        65C02 Assembler
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

a.object_code[256:268]

The Object Code Map
-------------------

If after running that, you typed this:
        >>> a.object_code[256:268]

You would see the list of object code values, but in decimal, since that's how python displays by default:

        [169, 16, 162, 0, 157, 0, 16, 232, 233, 1, 16, 250, 96]
        >>> 

What's going on is the assembler keeps a complete map of the 64K memory space of the 6502 and populates the code and values into that map. The 'object_code' class variable is a list containing the map. Each untouched location is set to -1. Other values indicate the 8 bit value at that location.

So after assembling the code into the map, it is possible to add in other things to the map by assigning to the object_code list. E.G.

        a.object_code[0xfffd] = 0x00
        a.object_code[0xfffc] = 0x10
Which would set the reset vector to 0x1000.

The Symbol Table
----------------

You can also see the symbol table as a dictionary after assembling:
    >>> a.symbols
    {'start': 256, 'loop': 260}


Directives
----------

There are a small number of directives:

; Comment
ORG address ; Sets the current aseembly location
STR some_text ; Include text as ascii bytes 
DB comma_separated_list_of_bytes ; $ prefix for hex
DW comma_separated_list_of_16_bit_numbers ; $ prefix for hex
DDW comma_separated_list_of_32_bit_numbers ; $ prefix for hex
DQW comma_separated_list_of_64_bit_numbers ; $ prefix for hex
LE ; For multi word data (DW, DDW and DQW) sets the encoding to little endian
BE ; For multi word data (DW, DDW and DQW) sets the encoding to big endian
The assembler defaults to little endian.

Prefixes
--------

$ for hex. $10 = 16
@ for octal. @10 = 8
& for a label pointer. &labelname = the 16 bit address of the label, only works with DW.

Labels
------

A word followed by a colon makes a label. It can be on it's own line, or in front of an instruction or directive.

alabel: ; A label on it's own
anotherlabel: STA #$10 ; A label with an instruction
Any address or 16 bit data field can be replaced with a declared label and the label address will be inserted there.

Assembling Into the Same Map
----------------------------

The assembler instance clears it's state before assembling, except for the object_code map. This enables you to assemble multiple pieces of code into different locations and they will be added to the map.
The print_object_code() class method displays the current object code map
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

--------------------------------------------
Comments to dj@deadhat.com

--------------------------------------------
TBD 1: Write a 65C02 simulator that runs from the object_code state generated by the assembler

TBD 2: Write an output generator for more of the flash/prom/eeprom programming formats

TBD 3: Give it decent error handling

TBD 4: Set up a unit test bench to fuzz it with code and do directed tests. 
