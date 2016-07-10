#!/usr/bin/env python

#
# The 65C02 Simulator
#

import math

class dis6502:
    def __init__(self, object_code, symbols=None):

       self.object_code = object_code[:]
       for i in xrange(len(self.object_code)):
            if self.object_code[i] < 0:
                self.object_code[i] = 0x00
 
       if symbols==None:
            self.have_symbols = False
       else:
            self.have_symbols = True
            
            self.symbols = symbols
            self.labels = dict()
            for label in self.symbols:
                offset = self.symbols[label]
                self.labels[offset]=label
       self.build_opcode_table()

    def build_opcode_table(self):
        self.hexcodes=dict()
        self.hexcodes[0x00] = ("brk","implicit")
        self.hexcodes[0x10] = ("bpl","relative")
        self.hexcodes[0x20] = ("jsr","absolute")
        self.hexcodes[0x30] = ("bmi","relative")
        self.hexcodes[0x40] = ("rti","implicit")
        self.hexcodes[0x50] = ("bvc","relative")
        self.hexcodes[0x60] = ("rts","implicit")
        self.hexcodes[0x70] = ("bvs","relative")
        self.hexcodes[0x80] = ("bra","relative")
        self.hexcodes[0x90] = ("bcc","relative")
        self.hexcodes[0xA0] = ("ldy","immediate")
        self.hexcodes[0xB0] = ("bcs","relative")
        self.hexcodes[0xC0] = ("cpy","immediate")
        self.hexcodes[0xD0] = ("bne","relative")
        self.hexcodes[0xE0] = ("cpx","immediate")
        self.hexcodes[0xF0] = ("beq","relative")
        
        self.hexcodes[0x01] = ("ora","zeropageindexedindirectx")
        self.hexcodes[0x11] = ("ora","zeropageindexedindirecty")
        self.hexcodes[0x21] = ("and","zeropageindexedindirectx")
        self.hexcodes[0x31] = ("and","zeropageindexedindirecty")
        self.hexcodes[0x41] = ("eor","zeropageindexedindirectx")
        self.hexcodes[0x51] = ("eor","zeropageindexedindirecty")
        self.hexcodes[0x61] = ("adc","zeropageindexedindirectx")
        self.hexcodes[0x71] = ("adc","zeropageindexedindirecty")
        self.hexcodes[0x81] = ("sta","zeropageindexedindirectx")
        self.hexcodes[0x91] = ("sta","zeropageindexedindirecty")
        self.hexcodes[0xA1] = ("lda","zeropageindexedindirectx")
        self.hexcodes[0xB1] = ("lda","zeropageindexedindirecty")
        self.hexcodes[0xC1] = ("cmp","zeropageindexedindirectx")
        self.hexcodes[0xD1] = ("cmp","zeropageindexedindirecty")
        self.hexcodes[0xE1] = ("sbc","zeropageindexedindirectx")
        self.hexcodes[0xF1] = ("sbc","zeropageindexedindirecty")
        
        self.hexcodes[0x02] = ("","")
        self.hexcodes[0x12] = ("ora","zeropageindirect")
        self.hexcodes[0x22] = ("","")
        self.hexcodes[0x32] = ("and","zeropageindirect")
        self.hexcodes[0x42] = ("","")
        self.hexcodes[0x52] = ("eor","zeropageindirect")
        self.hexcodes[0x62] = ("","")
        self.hexcodes[0x72] = ("adc","zeropageindirect")
        self.hexcodes[0x82] = ("","")
        self.hexcodes[0x92] = ("sta","zeropageindirect")
        self.hexcodes[0xA2] = ("ldx","immediate")
        self.hexcodes[0xB2] = ("lda","zeropageindirect")
        self.hexcodes[0xC2] = ("","")
        self.hexcodes[0xD2] = ("cmp","zeropageindirect")
        self.hexcodes[0xE2] = ("","")
        self.hexcodes[0xF2] = ("sbc","zeropageindirect")
        
        self.hexcodes[0x03] = ("","")
        self.hexcodes[0x13] = ("","")
        self.hexcodes[0x23] = ("","")
        self.hexcodes[0x33] = ("","")
        self.hexcodes[0x43] = ("","")
        self.hexcodes[0x53] = ("","")
        self.hexcodes[0x63] = ("","")
        self.hexcodes[0x73] = ("","")
        self.hexcodes[0x83] = ("","")
        self.hexcodes[0x93] = ("","")
        self.hexcodes[0xA3] = ("","")
        self.hexcodes[0xB3] = ("","")
        self.hexcodes[0xC3] = ("","")
        self.hexcodes[0xD3] = ("","")
        self.hexcodes[0xE3] = ("","")
        self.hexcodes[0xF3] = ("","")
        
        self.hexcodes[0x04] = ("tsb","zeropage")
        self.hexcodes[0x14] = ("trb","zeropage")
        self.hexcodes[0x24] = ("bit","zeropage")
        self.hexcodes[0x34] = ("bit","zeropagex")
        self.hexcodes[0x44] = ("","")
        self.hexcodes[0x54] = ("","")
        self.hexcodes[0x64] = ("stz","zeropage")
        self.hexcodes[0x74] = ("stz","zeropagex")
        self.hexcodes[0x84] = ("sty","zeropage")
        self.hexcodes[0x94] = ("sty","zeropagex")
        self.hexcodes[0xA4] = ("ldy","zeropage")
        self.hexcodes[0xB4] = ("ldy","zeropagex")
        self.hexcodes[0xC4] = ("cpy","zeropage")
        self.hexcodes[0xD4] = ("","")
        self.hexcodes[0xE4] = ("cpx","zeropage")
        self.hexcodes[0xF4] = ("","")
        
        self.hexcodes[0x05] = ("ora","zeropage")
        self.hexcodes[0x15] = ("ora","zeropagex")
        self.hexcodes[0x25] = ("and","zeropage")
        self.hexcodes[0x35] = ("and","zeropagex")
        self.hexcodes[0x45] = ("eor","zeropage")
        self.hexcodes[0x55] = ("eor","zeropagex")
        self.hexcodes[0x65] = ("adc","zeropage")
        self.hexcodes[0x75] = ("adc","zeropagex")
        self.hexcodes[0x85] = ("sta","zeropage")
        self.hexcodes[0x95] = ("sta","zeropagex")
        self.hexcodes[0xA5] = ("lda","zeropage")
        self.hexcodes[0xB5] = ("lda","zeropagex")
        self.hexcodes[0xC5] = ("cmp","zeropage")
        self.hexcodes[0xD5] = ("cmp","zeropagex")
        self.hexcodes[0xE5] = ("sbc","zeropage")
        self.hexcodes[0xF5] = ("sbc","zeropagex")
        
        self.hexcodes[0x06] = ("asl","zeropage")
        self.hexcodes[0x16] = ("asl","zeropagex")
        self.hexcodes[0x26] = ("rol","zeropage")
        self.hexcodes[0x36] = ("rol","zeropagex")
        self.hexcodes[0x46] = ("lsr","zeropage")
        self.hexcodes[0x56] = ("lsr","zeropagex")
        self.hexcodes[0x66] = ("ror","zeropage")
        self.hexcodes[0x76] = ("ror","zeropagex")
        self.hexcodes[0x86] = ("stx","zeropage")
        self.hexcodes[0x96] = ("stx","zeropagey")
        self.hexcodes[0xA6] = ("ldx","zeropage")
        self.hexcodes[0xB6] = ("ldx","zeropagey")
        self.hexcodes[0xC6] = ("dec","zeropage")
        self.hexcodes[0xD6] = ("dec","zeropagex")
        self.hexcodes[0xE6] = ("inc","zeropage")
        self.hexcodes[0xF6] = ("inc","zeropagex")
        
        self.hexcodes[0x07] = ("","")
        self.hexcodes[0x17] = ("","")
        self.hexcodes[0x27] = ("","")
        self.hexcodes[0x37] = ("","")
        self.hexcodes[0x47] = ("","")
        self.hexcodes[0x57] = ("","")
        self.hexcodes[0x67] = ("","")
        self.hexcodes[0x77] = ("","")
        self.hexcodes[0x87] = ("","")
        self.hexcodes[0x97] = ("","")
        self.hexcodes[0xA7] = ("","")
        self.hexcodes[0xB7] = ("","")
        self.hexcodes[0xC7] = ("","")
        self.hexcodes[0xD7] = ("","")
        self.hexcodes[0xE7] = ("","")
        self.hexcodes[0xF7] = ("","")
        
        self.hexcodes[0x08] = ("php","implicit")
        self.hexcodes[0x18] = ("clc","implicit")
        self.hexcodes[0x28] = ("plp","implicit")
        self.hexcodes[0x38] = ("sec","implicit")
        self.hexcodes[0x48] = ("pha","implicit")
        self.hexcodes[0x58] = ("cli","implicit")
        self.hexcodes[0x68] = ("pla","implicit")
        self.hexcodes[0x78] = ("sei","implicit")
        self.hexcodes[0x88] = ("dey","implicit")
        self.hexcodes[0x98] = ("tya","implicit")
        self.hexcodes[0xA8] = ("tay","implicit")
        self.hexcodes[0xB8] = ("clv","implicit")
        self.hexcodes[0xC8] = ("iny","implicit")
        self.hexcodes[0xD8] = ("cld","implicit")
        self.hexcodes[0xE8] = ("inx","implicit")
        self.hexcodes[0xF8] = ("sed","implicit")
        
        self.hexcodes[0x09] = ("ora","immediate")
        self.hexcodes[0x19] = ("ora","absolutey")
        self.hexcodes[0x29] = ("and","immediate")
        self.hexcodes[0x39] = ("and","absolutey")
        self.hexcodes[0x49] = ("eor","immediate")
        self.hexcodes[0x59] = ("eor","absolutey")
        self.hexcodes[0x69] = ("adc","immediate")
        self.hexcodes[0x79] = ("adc","absolutey")
        self.hexcodes[0x89] = ("bit","immediate")
        self.hexcodes[0x99] = ("sta","absolutey")
        self.hexcodes[0xA9] = ("lda","immediate")
        self.hexcodes[0xB9] = ("lda","absolutey")
        self.hexcodes[0xC9] = ("cmp","immediate")
        self.hexcodes[0xD9] = ("cmp","absolutey")
        self.hexcodes[0xE9] = ("sbc","immediate")
        self.hexcodes[0xF9] = ("sbc","absolutey")
        
        self.hexcodes[0x0A] = ("asl","accumulator")
        self.hexcodes[0x1A] = ("ina","accumulator")
        self.hexcodes[0x2A] = ("rol","accumulator")
        self.hexcodes[0x3A] = ("dea","accumulator")
        self.hexcodes[0x4A] = ("lsr","accumulator")
        self.hexcodes[0x5A] = ("phy","implicit")
        self.hexcodes[0x6A] = ("ror","accumulator")
        self.hexcodes[0x7A] = ("ply","implicit")
        self.hexcodes[0x8A] = ("txa","implicit")
        self.hexcodes[0x9A] = ("txs","implicit")
        self.hexcodes[0xAA] = ("tax","implicit")
        self.hexcodes[0xBA] = ("tsx","implicit")
        self.hexcodes[0xCA] = ("dex","implicit")
        self.hexcodes[0xDA] = ("phx","implicit")
        self.hexcodes[0xEA] = ("nop","implicit")
        self.hexcodes[0xFA] = ("plx","implicit")
        
        self.hexcodes[0x0B] = ("","")
        self.hexcodes[0x1B] = ("","")
        self.hexcodes[0x2B] = ("","")
        self.hexcodes[0x3B] = ("","")
        self.hexcodes[0x4B] = ("","")
        self.hexcodes[0x5B] = ("","")
        self.hexcodes[0x6B] = ("","")
        self.hexcodes[0x7B] = ("","")
        self.hexcodes[0x8B] = ("","")
        self.hexcodes[0x9B] = ("","")
        self.hexcodes[0xAB] = ("","")
        self.hexcodes[0xBB] = ("","")
        self.hexcodes[0xCB] = ("","")
        self.hexcodes[0xDB] = ("","")
        self.hexcodes[0xEB] = ("","")
        self.hexcodes[0xFB] = ("","")

        self.hexcodes[0x0C] = ("tsb","absolute")
        self.hexcodes[0x1C] = ("trb","absolute")
        self.hexcodes[0x2C] = ("bit","absolute")
        self.hexcodes[0x3C] = ("bit","absolutex")
        self.hexcodes[0x4C] = ("jmp","absolute")
        self.hexcodes[0x5C] = ("","")
        self.hexcodes[0x6C] = ("jmp","absoluteindirect")
        self.hexcodes[0x7C] = ("jmp","absoluteindexedindirect")
        self.hexcodes[0x8C] = ("sty","absolute")
        self.hexcodes[0x9C] = ("stz","absolute")
        self.hexcodes[0xAC] = ("ldy","absolute")
        self.hexcodes[0xBC] = ("ldy","absolutex")
        self.hexcodes[0xCC] = ("cpy","absolute")
        self.hexcodes[0xDC] = ("","")
        self.hexcodes[0xEC] = ("cpx","absolute")
        self.hexcodes[0xFC] = ("","")
        
        self.hexcodes[0x0D] = ("ora","absolute")
        self.hexcodes[0x1D] = ("ora","absolutex")
        self.hexcodes[0x2D] = ("and","absolute")
        self.hexcodes[0x3D] = ("and","absolutex")
        self.hexcodes[0x4D] = ("eor","absolute")
        self.hexcodes[0x5D] = ("eor","absolutex")
        self.hexcodes[0x6D] = ("adc","absolute")
        self.hexcodes[0x7D] = ("adc","absolutex")
        self.hexcodes[0x8D] = ("sta","absolute")
        self.hexcodes[0x9D] = ("sta","absolutex")
        self.hexcodes[0xAD] = ("lda","absolute")
        self.hexcodes[0xBD] = ("lda","absolutex")
        self.hexcodes[0xCD] = ("cmp","absolute")
        self.hexcodes[0xDD] = ("cmp","absolutex")
        self.hexcodes[0xED] = ("sbc","absolute")
        self.hexcodes[0xFD] = ("sbc","absolutex")
        
        self.hexcodes[0x0E] = ("asl","absolute")
        self.hexcodes[0x1E] = ("asl","absolutex")
        self.hexcodes[0x2E] = ("rol","absolute")
        self.hexcodes[0x3E] = ("rol","absolutex")
        self.hexcodes[0x4E] = ("lsr","absolute")
        self.hexcodes[0x5E] = ("lsr","absolutex")
        self.hexcodes[0x6E] = ("ror","absolute")
        self.hexcodes[0x7E] = ("ror","absolutex")
        self.hexcodes[0x8E] = ("stx","absolute")
        self.hexcodes[0x9E] = ("stz","absolutex")
        self.hexcodes[0xAE] = ("ldx","absolute")
        self.hexcodes[0xBE] = ("ldx","absolutey")
        self.hexcodes[0xCE] = ("dec","absolute")
        self.hexcodes[0xDE] = ("dec","absolutex")
        self.hexcodes[0xEE] = ("inc","absolute")
        self.hexcodes[0xFE] = ("inc","absolutex")
        
        self.hexcodes[0x0F] = ("","")
        self.hexcodes[0x1F] = ("","")
        self.hexcodes[0x2F] = ("","")
        self.hexcodes[0x3F] = ("","")
        self.hexcodes[0x4F] = ("","")
        self.hexcodes[0x5F] = ("","")
        self.hexcodes[0x6F] = ("","")
        self.hexcodes[0x7F] = ("","")
        self.hexcodes[0x8F] = ("","")
        self.hexcodes[0x9F] = ("","")
        self.hexcodes[0xAF] = ("","")
        self.hexcodes[0xBF] = ("","")
        self.hexcodes[0xCF] = ("","")
        self.hexcodes[0xDF] = ("","")
        self.hexcodes[0xEF] = ("","")
        self.hexcodes[0xFF] = ("","")

    def disassemble_line(self,address):
        #print "DISASSEMBLER ADDR: %04x" % address
        opcode_hex = self.object_code[address]
        operandl = self.object_code[(address+1)%65536]
        operandh = self.object_code[(address+2)%65536]

        operand8 = operandl
        operand16 = operandl + (operandh << 8)

        #print "OPCODE_HEX = %x" % opcode_hex
        opcode,addrmode = self.hexcodes[opcode_hex]
        #print "DISASSEMBLER OPCD: %02x" % opcode_hex
        #print "DISASSMBLER OPCD TXT:"+str(opcode)+" "+str(addrmode)
        if opcode in self.labels:
            label = self.labels[opcode].ljust(15) + " :"
        else:
            label = " "*17

        the_text =  label+" "
        the_text += (opcode.ljust(5))

        # Format the operand based on the addressmode
        
        if addrmode == "zeropageindexedindirectx":
            operandtext = "($%02x,x)" % operand8
        elif addrmode == "zeropageindexedindirecty":
            operandtext = "($%02x,y)" % operand8
        elif addrmode == "zeropageindirect":
            operandtext = "($%02x)" % operand8
        elif addrmode == "zeropage":
            operandtext = "$%02x" % operand8
        elif addrmode == "zeropagex":
            operandtext = "$%02x,x" % operand8
        elif addrmode == "zeropagey":
            operandtext = "$%02x,y" % operand8
        elif addrmode == "immediate":
            operandtext = "#$%02x" % operand8
        elif addrmode == "absolutey":
            operandtext = "$%04x,y" % operand16
        elif addrmode == "absolute":
            operandtext = "$%04x" % operand16
        elif addrmode == "absoluteindirect":
            operandtext = "($%04x)" % operand16
        elif addrmode == "absoluteindexedindirect":
            operandtext = "($%04x,x)" % operand16
        elif addrmode == "absolutex":
            operandtext = "$%04x,x" % operand16
        elif addrmode == "indirect":
            operandtext = "($%04x)" % operand16
        elif addrmode == "relative":
            if operand8 < 128:
                operandtext = "+$%02x" % operand8
            else:
                offset = (operand7 & 0xff) -128
                offset = math.abs(offset)
                operandtext = "-$%02x" %offset
        elif addrmode == "accumulator":
            operandtext = "A" 
        elif addrmode == "implicit":
            operandtext = ""
        elif addrmode == "":
            operandtext = ""
        elif addrmode == None:
            operandtext = ""
        else:
            print "ERROR: Disassembler: Address mode %s not found" % addrmode
            exit()
        the_text += " "+operandtext
        return (the_text)

