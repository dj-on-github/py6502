import memory_map

class Flags(object):
    # processor flags
    NEGATIVE = 128
    OVERFLOW = 64
    UNUSED = 32
    BREAK = 16
    DECIMAL = 8
    INTERRUPT = 4
    ZERO = 2
    CARRY = 1

# TODO: check for other cases of % on negative numbers leading to negative underflow

#
# The 65C02 Simulator
#
class sim6502(object):
    def __init__(self, object_code=None, address=0x0, symbols=None):
        self.pc = 0x0000
        self.a = 0x00
        self.x = 0x00
        self.y = 0x00
        self.sp = 0xff
        self.cc = 0x00

        self.memory_map = memory_map.MemoryMap(self)
        if object_code:
            self.memory_map.InitializeMemory(address, object_code)

        self.build_opcode_table()

        if symbols == None:
            self.have_symbols = False
        else:
            self.have_symbols = True

            self.symbols = symbols
            self.labels = dict()
            for label in self.symbols:
                offset = self.symbols[label]
                self.labels[offset] = label

    # TODO: factor out to common code
    def build_opcode_table(self):
        self.hexcodes = dict()
        self.hexcodes[0x00] = ("brk", "implicit")
        self.hexcodes[0x10] = ("bpl", "relative")
        self.hexcodes[0x20] = ("jsr", "absolute")
        self.hexcodes[0x30] = ("bmi", "relative")
        self.hexcodes[0x40] = ("rti", "implicit")
        self.hexcodes[0x50] = ("bvc", "relative")
        self.hexcodes[0x60] = ("rts", "implicit")
        self.hexcodes[0x70] = ("bvs", "relative")
        self.hexcodes[0x80] = ("bra", "relative")
        self.hexcodes[0x90] = ("bcc", "relative")
        self.hexcodes[0xA0] = ("ldy", "immediate")
        self.hexcodes[0xB0] = ("bcs", "relative")
        self.hexcodes[0xC0] = ("cpy", "immediate")
        self.hexcodes[0xD0] = ("bne", "relative")
        self.hexcodes[0xE0] = ("cpx", "immediate")
        self.hexcodes[0xF0] = ("beq", "relative")

        self.hexcodes[0x01] = ("ora", "zeropageindexedindirectx")
        self.hexcodes[0x11] = ("ora", "zeropageindexedindirecty")
        self.hexcodes[0x21] = ("and", "zeropageindexedindirectx")
        self.hexcodes[0x31] = ("and", "zeropageindexedindirecty")
        self.hexcodes[0x41] = ("eor", "zeropageindexedindirectx")
        self.hexcodes[0x51] = ("eor", "zeropageindexedindirecty")
        self.hexcodes[0x61] = ("adc", "zeropageindexedindirectx")
        self.hexcodes[0x71] = ("adc", "zeropageindexedindirecty")
        self.hexcodes[0x81] = ("sta", "zeropageindexedindirectx")
        self.hexcodes[0x91] = ("sta", "zeropageindexedindirecty")
        self.hexcodes[0xA1] = ("lda", "zeropageindexedindirectx")
        self.hexcodes[0xB1] = ("lda", "zeropageindexedindirecty")
        self.hexcodes[0xC1] = ("cmp", "zeropageindexedindirectx")
        self.hexcodes[0xD1] = ("cmp", "zeropageindexedindirecty")
        self.hexcodes[0xE1] = ("sbc", "zeropageindexedindirectx")
        self.hexcodes[0xF1] = ("sbc", "zeropageindexedindirecty")

        self.hexcodes[0x02] = ("", "")
        self.hexcodes[0x12] = ("ora", "zeropageindirect")
        self.hexcodes[0x22] = ("", "")
        self.hexcodes[0x32] = ("and", "zeropageindirect")
        self.hexcodes[0x42] = ("", "")
        self.hexcodes[0x52] = ("eor", "zeropageindirect")
        self.hexcodes[0x62] = ("", "")
        self.hexcodes[0x72] = ("adc", "zeropageindirect")
        self.hexcodes[0x82] = ("", "")
        self.hexcodes[0x92] = ("sta", "zeropageindirect")
        self.hexcodes[0xA2] = ("ldx", "immediate")
        self.hexcodes[0xB2] = ("lda", "zeropageindirect")
        self.hexcodes[0xC2] = ("", "")
        self.hexcodes[0xD2] = ("cmp", "zeropageindirect")
        self.hexcodes[0xE2] = ("", "")
        self.hexcodes[0xF2] = ("sbc", "zeropageindirect")

        self.hexcodes[0x03] = ("", "")
        self.hexcodes[0x13] = ("", "")
        self.hexcodes[0x23] = ("", "")
        self.hexcodes[0x33] = ("", "")
        self.hexcodes[0x43] = ("", "")
        self.hexcodes[0x53] = ("", "")
        self.hexcodes[0x63] = ("", "")
        self.hexcodes[0x73] = ("", "")
        self.hexcodes[0x83] = ("", "")
        self.hexcodes[0x93] = ("", "")
        self.hexcodes[0xA3] = ("", "")
        self.hexcodes[0xB3] = ("", "")
        self.hexcodes[0xC3] = ("", "")
        self.hexcodes[0xD3] = ("", "")
        self.hexcodes[0xE3] = ("", "")
        self.hexcodes[0xF3] = ("", "")

        self.hexcodes[0x04] = ("tsb", "zeropage")
        self.hexcodes[0x14] = ("trb", "zeropage")
        self.hexcodes[0x24] = ("bit", "zeropage")
        self.hexcodes[0x34] = ("bit", "zeropagex")
        self.hexcodes[0x44] = ("", "")
        self.hexcodes[0x54] = ("", "")
        self.hexcodes[0x64] = ("stz", "zeropage")
        self.hexcodes[0x74] = ("stz", "zeropagex")
        self.hexcodes[0x84] = ("sty", "zeropage")
        self.hexcodes[0x94] = ("sty", "zeropagex")
        self.hexcodes[0xA4] = ("ldy", "zeropage")
        self.hexcodes[0xB4] = ("ldy", "zeropagex")
        self.hexcodes[0xC4] = ("cpy", "zeropage")
        self.hexcodes[0xD4] = ("", "")
        self.hexcodes[0xE4] = ("cpx", "zeropage")
        self.hexcodes[0xF4] = ("", "")

        self.hexcodes[0x05] = ("ora", "zeropage")
        self.hexcodes[0x15] = ("ora", "zeropagex")
        self.hexcodes[0x25] = ("and", "zeropage")
        self.hexcodes[0x35] = ("and", "zeropagex")
        self.hexcodes[0x45] = ("eor", "zeropage")
        self.hexcodes[0x55] = ("eor", "zeropagex")
        self.hexcodes[0x65] = ("adc", "zeropage")
        self.hexcodes[0x75] = ("adc", "zeropagex")
        self.hexcodes[0x85] = ("sta", "zeropage")
        self.hexcodes[0x95] = ("sta", "zeropagex")
        self.hexcodes[0xA5] = ("lda", "zeropage")
        self.hexcodes[0xB5] = ("lda", "zeropagex")
        self.hexcodes[0xC5] = ("cmp", "zeropage")
        self.hexcodes[0xD5] = ("cmp", "zeropagex")
        self.hexcodes[0xE5] = ("sbc", "zeropage")
        self.hexcodes[0xF5] = ("sbc", "zeropagex")

        self.hexcodes[0x06] = ("asl", "zeropage")
        self.hexcodes[0x16] = ("asl", "zeropagex")
        self.hexcodes[0x26] = ("rol", "zeropage")
        self.hexcodes[0x36] = ("rol", "zeropagex")
        self.hexcodes[0x46] = ("lsr", "zeropage")
        self.hexcodes[0x56] = ("lsr", "zeropagex")
        self.hexcodes[0x66] = ("ror", "zeropage")
        self.hexcodes[0x76] = ("ror", "zeropagex")
        self.hexcodes[0x86] = ("stx", "zeropage")
        self.hexcodes[0x96] = ("stx", "zeropagey")
        self.hexcodes[0xA6] = ("ldx", "zeropage")
        self.hexcodes[0xB6] = ("ldx", "zeropagey")
        self.hexcodes[0xC6] = ("dec", "zeropage")
        self.hexcodes[0xD6] = ("dec", "zeropagex")
        self.hexcodes[0xE6] = ("inc", "zeropage")
        self.hexcodes[0xF6] = ("inc", "zeropagex")

        self.hexcodes[0x07] = ("", "")
        self.hexcodes[0x17] = ("", "")
        self.hexcodes[0x27] = ("", "")
        self.hexcodes[0x37] = ("", "")
        self.hexcodes[0x47] = ("", "")
        self.hexcodes[0x57] = ("", "")
        self.hexcodes[0x67] = ("", "")
        self.hexcodes[0x77] = ("", "")
        self.hexcodes[0x87] = ("", "")
        self.hexcodes[0x97] = ("", "")
        self.hexcodes[0xA7] = ("", "")
        self.hexcodes[0xB7] = ("", "")
        self.hexcodes[0xC7] = ("", "")
        self.hexcodes[0xD7] = ("", "")
        self.hexcodes[0xE7] = ("", "")
        self.hexcodes[0xF7] = ("", "")

        self.hexcodes[0x08] = ("php", "implicit")
        self.hexcodes[0x18] = ("clc", "implicit")
        self.hexcodes[0x28] = ("plp", "implicit")
        self.hexcodes[0x38] = ("sec", "implicit")
        self.hexcodes[0x48] = ("pha", "implicit")
        self.hexcodes[0x58] = ("cli", "implicit")
        self.hexcodes[0x68] = ("pla", "implicit")
        self.hexcodes[0x78] = ("sei", "implicit")
        self.hexcodes[0x88] = ("dey", "implicit")
        self.hexcodes[0x98] = ("tya", "implicit")
        self.hexcodes[0xA8] = ("tay", "implicit")
        self.hexcodes[0xB8] = ("clv", "implicit")
        self.hexcodes[0xC8] = ("iny", "implicit")
        self.hexcodes[0xD8] = ("cld", "implicit")
        self.hexcodes[0xE8] = ("inx", "implicit")
        self.hexcodes[0xF8] = ("sed", "implicit")

        self.hexcodes[0x09] = ("ora", "immediate")
        self.hexcodes[0x19] = ("ora", "absolutey")
        self.hexcodes[0x29] = ("and", "immediate")
        self.hexcodes[0x39] = ("and", "absolutey")
        self.hexcodes[0x49] = ("eor", "immediate")
        self.hexcodes[0x59] = ("eor", "absolutey")
        self.hexcodes[0x69] = ("adc", "immediate")
        self.hexcodes[0x79] = ("adc", "absolutey")
        self.hexcodes[0x89] = ("bit", "immediate")
        self.hexcodes[0x99] = ("sta", "absolutey")
        self.hexcodes[0xA9] = ("lda", "immediate")
        self.hexcodes[0xB9] = ("lda", "absolutey")
        self.hexcodes[0xC9] = ("cmp", "immediate")
        self.hexcodes[0xD9] = ("cmp", "absolutey")
        self.hexcodes[0xE9] = ("sbc", "immediate")
        self.hexcodes[0xF9] = ("sbc", "absolutey")

        self.hexcodes[0x0A] = ("asl", "accumulator")
        self.hexcodes[0x1A] = ("ina", "accumulator")
        self.hexcodes[0x2A] = ("rol", "accumulator")
        self.hexcodes[0x3A] = ("dea", "accumulator")
        self.hexcodes[0x4A] = ("lsr", "accumulator")
        self.hexcodes[0x5A] = ("phy", "implicit")
        self.hexcodes[0x6A] = ("ror", "accumulator")
        self.hexcodes[0x7A] = ("ply", "implicit")
        self.hexcodes[0x8A] = ("txa", "implicit")
        self.hexcodes[0x9A] = ("txs", "implicit")
        self.hexcodes[0xAA] = ("tax", "implicit")
        self.hexcodes[0xBA] = ("tsx", "implicit")
        self.hexcodes[0xCA] = ("dex", "implicit")
        self.hexcodes[0xDA] = ("phx", "implicit")
        self.hexcodes[0xEA] = ("nop", "implicit")
        self.hexcodes[0xFA] = ("plx", "implicit")

        self.hexcodes[0x0B] = ("", "")
        self.hexcodes[0x1B] = ("", "")
        self.hexcodes[0x2B] = ("", "")
        self.hexcodes[0x3B] = ("", "")
        self.hexcodes[0x4B] = ("", "")
        self.hexcodes[0x5B] = ("", "")
        self.hexcodes[0x6B] = ("", "")
        self.hexcodes[0x7B] = ("", "")
        self.hexcodes[0x8B] = ("", "")
        self.hexcodes[0x9B] = ("", "")
        self.hexcodes[0xAB] = ("", "")
        self.hexcodes[0xBB] = ("", "")
        self.hexcodes[0xCB] = ("", "")
        self.hexcodes[0xDB] = ("", "")
        self.hexcodes[0xEB] = ("", "")
        self.hexcodes[0xFB] = ("", "")

        self.hexcodes[0x0C] = ("tsb", "absolute")
        self.hexcodes[0x1C] = ("trb", "absolute")
        self.hexcodes[0x2C] = ("bit", "absolute")
        self.hexcodes[0x3C] = ("bit", "absolutex")
        self.hexcodes[0x4C] = ("jmp", "absolute")
        self.hexcodes[0x5C] = ("", "")
        self.hexcodes[0x6C] = ("jmp", "absoluteindirect")
        self.hexcodes[0x7C] = ("jmp", "absoluteindexedindirect")
        self.hexcodes[0x8C] = ("sty", "absolute")
        self.hexcodes[0x9C] = ("stz", "absolute")
        self.hexcodes[0xAC] = ("ldy", "absolute")
        self.hexcodes[0xBC] = ("ldy", "absolutex")
        self.hexcodes[0xCC] = ("cpy", "absolute")
        self.hexcodes[0xDC] = ("", "")
        self.hexcodes[0xEC] = ("cpx", "absolute")
        self.hexcodes[0xFC] = ("", "")

        self.hexcodes[0x0D] = ("ora", "absolute")
        self.hexcodes[0x1D] = ("ora", "absolutex")
        self.hexcodes[0x2D] = ("and", "absolute")
        self.hexcodes[0x3D] = ("and", "absolutex")
        self.hexcodes[0x4D] = ("eor", "absolute")
        self.hexcodes[0x5D] = ("eor", "absolutex")
        self.hexcodes[0x6D] = ("adc", "absolute")
        self.hexcodes[0x7D] = ("adc", "absolutex")
        self.hexcodes[0x8D] = ("sta", "absolute")
        self.hexcodes[0x9D] = ("sta", "absolutex")
        self.hexcodes[0xAD] = ("lda", "absolute")
        self.hexcodes[0xBD] = ("lda", "absolutex")
        self.hexcodes[0xCD] = ("cmp", "absolute")
        self.hexcodes[0xDD] = ("cmp", "absolutex")
        self.hexcodes[0xED] = ("sbc", "absolute")
        self.hexcodes[0xFD] = ("sbc", "absolutex")

        self.hexcodes[0x0E] = ("asl", "absolute")
        self.hexcodes[0x1E] = ("asl", "absolutex")
        self.hexcodes[0x2E] = ("rol", "absolute")
        self.hexcodes[0x3E] = ("rol", "absolutex")
        self.hexcodes[0x4E] = ("lsr", "absolute")
        self.hexcodes[0x5E] = ("lsr", "absolutex")
        self.hexcodes[0x6E] = ("ror", "absolute")
        self.hexcodes[0x7E] = ("ror", "absolutex")
        self.hexcodes[0x8E] = ("stx", "absolute")
        self.hexcodes[0x9E] = ("stz", "absolutex")
        self.hexcodes[0xAE] = ("ldx", "absolute")
        self.hexcodes[0xBE] = ("ldx", "absolutey")
        self.hexcodes[0xCE] = ("dec", "absolute")
        self.hexcodes[0xDE] = ("dec", "absolutex")
        self.hexcodes[0xEE] = ("inc", "absolute")
        self.hexcodes[0xFE] = ("inc", "absolutex")

        self.hexcodes[0x0F] = ("", "")
        self.hexcodes[0x1F] = ("", "")
        self.hexcodes[0x2F] = ("", "")
        self.hexcodes[0x3F] = ("", "")
        self.hexcodes[0x4F] = ("", "")
        self.hexcodes[0x5F] = ("", "")
        self.hexcodes[0x6F] = ("", "")
        self.hexcodes[0x7F] = ("", "")
        self.hexcodes[0x8F] = ("", "")
        self.hexcodes[0x9F] = ("", "")
        self.hexcodes[0xAF] = ("", "")
        self.hexcodes[0xBF] = ("", "")
        self.hexcodes[0xCF] = ("", "")
        self.hexcodes[0xDF] = ("", "")
        self.hexcodes[0xEF] = ("", "")
        self.hexcodes[0xFF] = ("", "")

    def reset(self):
        self.a = 0x00
        self.x = 0x00
        self.y = 0x00
        self.sp = 0xff
        self.cc = Flags.BREAK | Flags.UNUSED
        lowaddr = self.memory_map.Read(0xfffc)
        highaddr = self.memory_map.Read(0xfffd)
        if (lowaddr != None) and (lowaddr > -1) and (highaddr != None) and (highaddr > -1):
            address = (lowaddr & 0xff) | ((highaddr << 8) & 0xff00)
            self.pc = address
            return True
        else:
            print("ERROR: Bad reset vector 0x" + str(self.memory_map.Read(0xfffc)) + ",0x" + str(self.memory_map.Read(0xfffd)))
            return False

    def nmi(self):
        # Read the NMI vector
        lowaddr = self.memory_map.Read(0xfffa)
        highaddr = self.memory_map.Read(0xfffb)
        if (lowaddr != None) and (lowaddr > -1) and (highaddr != None) and (highaddr > -1):
            address = (lowaddr & 0xff) | ((highaddr << 8) & 0xff00)
        else:
            return False

        # push PC and status on stack
        self.memory_map.Write(self.sp, (self.pc >> 8) & 0xff)
        self.memory_map.Write(self.sp - 1, self.pc & 0xff)
        # TODO: does this actually set this flag before pushing to the stack?
        self.memory_map.Write(self.sp - 2, self.cc | Flags.UNUSED)
        self.sp -= 3

        # Set PC to the NMI vector
        self.pc = address
        return True

    def irq(self):
        # Read the IRQ vector
        lowaddr = self.memory_map.Read(0xfffa)
        highaddr = self.memory_map.Read(0xfffb)
        if (lowaddr != None) and (lowaddr > -1) and (highaddr != None) and (highaddr > -1):
            address = (lowaddr & 0xff) | ((highaddr << 8) & 0xff00)
        else:
            return False

        # push PC and status on stack
        self.memory_map.Write(self.sp, (self.pc >> 8) & 0xff)
        self.memory_map.Write(self.sp - 1, self.pc & 0xff)
        self.memory_map.Write(self.sp - 2, self.cc)
        self.sp -= 3

        # Set PC to the NMI vector
        self.pc = address
        return True

    def make_flags_nz(self, result):
        self.set_n(result & 0x80)
        self.set_z(result == 0)

    def make_flags_v(self, acc, operand, carryin, result, carryout):
        # V Flag, bit 6
        self.set_v(((acc ^ result) & (operand ^ result) & 0x80) == 0x80)

    def get_operand(self, addrmode, opcode, operand8, operand16):
        # Get the operand based on the address mode
        # print get operand addrmode="+str(addrmode)+" opcode:"+str(opcode)+" op8:"+str(operand8)
        if addrmode == "zeropageindexedindirectx":
            # 6502 bug/feature: indirecting by x wraps within the zero page
            indirectaddr = (operand8 + self.x) & 0xff
            addr = (self.memory_map.Read(indirectaddr + 1) << 8) + self.memory_map.Read(indirectaddr)
            operand = self.memory_map.Read(addr)
            length = 2
        elif addrmode == "zeropageindexedindirecty":
            indirectaddr = operand8
            # 6502 bug when ($FF),y
            addr = (self.memory_map.Read((indirectaddr + 1) & 0xff) << 8) + self.memory_map.Read(indirectaddr)
            addr = addr + self.y
            operand = self.memory_map.Read(addr)
            length = 2
        elif addrmode == "zeropageindirect":
            indirectaddr = operand8
            addr = (self.memory_map.Read(indirectaddr + 1) << 8) + self.memory_map.Read(indirectaddr)
            operand = self.memory_map.Read(addr)
            length = 2
        elif addrmode == "zeropage":
            addr = operand8
            operand = self.memory_map.Read(addr)
            length = 2
        elif addrmode == "zeropagex":
            addr = (operand8 + self.x) & 0xff
            operand = self.memory_map.Read(addr)
            length = 2
        elif addrmode == "zeropagey":
            addr = (operand8 + self.y) & 0xff
            operand = self.memory_map.Read(addr)
            length = 2
        elif addrmode == "immediate":
            addr = None
            operand = operand8
            length = 2
        elif addrmode == "absolutey":
            addr = operand16 + self.y
            operand = self.memory_map.Read(addr)
            length = 3
        elif addrmode == "absolute":
            addr = operand16
            operand = self.memory_map.Read(addr)
            length = 3
        elif addrmode == "absolutex":
            addr = operand16 + self.x
            operand = self.memory_map.Read(addr)
            length = 3
        elif addrmode == "indirect":
            indirectaddr = operand16
            addr = (self.memory_map.Read(indirectaddr + 1) << 8) + self.memory_map.Read(indirectaddr)
            operand = (self.memory_map.Read(addr + 1) << 8) + self.memory_map.Read(addr)
            length = 3
        elif addrmode == "accumulator":
            addr = None
            operand = self.a
            length = 1
        elif addrmode == "implicit":
            addr = None
            operand = operand8
            length = 1
        else:
            print "ERROR: Address mode %s not found" % addrmode
            print "     : PC = 0x%04x" % self.pc
            exit()
        return (operand, addr, length)

    def get_operand16(self, addrmode, opcode, operand8, operand16):
        # Get the operand based on the address mode
        if addrmode == "absolute":
            addr = operand16
            length = 3
        elif addrmode == "indirect":
            indirectaddr = operand16
            addr = (self.memory_map.Read(indirectaddr + 1) << 8) + self.memory_map.Read(indirectaddr)
            length = 3
        elif addrmode == "absoluteindexedindirect":
            indirectaddr = operand16 + self.x
            addr = (self.memory_map.Read(indirectaddr + 1) << 8) + self.memory_map.Read(indirectaddr)
            length = 3
        elif addrmode == "absoluteindirect":
            indirectaddr = operand16
            addr = (self.memory_map.Read(indirectaddr + 1) << 8) + self.memory_map.Read(indirectaddr)
            length = 3
        else:
            print "ERROR: Address mode %s not found for JMP or JSR" % addrmode
            print "     : PC = 0x%04x" % self.pc
            exit()
        operand = self.memory_map.Read(addr)
        return (operand, addr, length)

    # Execute the instruction at the current program counter location.
    # Converts hex opcode to instruction three letter name and address mode
    # turns instruction name into a method - e.g.  instr_lda()
    # Then calls the method and passes in the operands

    def execute(self, address=None):
        if address == None:
            address = self.pc
            # Pre-increment PC on instruction fetch
            self.pc += 1
        opcode = self.memory_map.Execute(address)
        # TODO: we should increment self.pc here by the opcode argument length instead
        # of doing it manually in every opcode handler and potentially introducing bugs
        # TODO: only fetch the number of operand bytes appropriate for the instruction
        # to avoid the extra memory accesses
        operand8 = self.memory_map.Execute((address + 1) % 65536)
        hi = self.memory_map.Execute((address + 2) % 65536)
        operand16 = operand8 + ((hi << 8) & 0xff00)

        if (opcode >= 0) and (opcode < 256):
            instruction, addrmode = self.hexcodes[opcode]
            if (instruction != ""):
                # TODO: construct a method dispatch table once instead of every time
                methodname = "instr_" + instruction
                # print "METHODNAME:"+methodname
                method = getattr(self, methodname, lambda: "nothing")
                thing = method(addrmode, opcode, operand8, operand16)
                if thing == None:
                    return (None, None)
                return thing
            else:
                # TODO: raise exception here
                return ("not_instruction", self.pc)
        else:
            # TODO: raise exception here
            #print "ERROR: Out in the weeds. Opcode = %d" % opcode
            return ("weeds", self.pc)


    def none_or_byte(self, thebyte):
        if thebyte == None:
            thestr = "None"
        else:
            thestr = "0x%02x" % thebyte
        return thestr

    def show_state(self):
        str_pc = self.none_or_byte(self.pc)
        str_a = self.none_or_byte(self.a)
        str_x = self.none_or_byte(self.x)
        str_y = self.none_or_byte(self.y)
        str_sp = self.none_or_byte(self.sp)
        str_cc = self.none_or_byte(self.cc)
        if (self.have_symbols) and (self.pc in self.labels):
            label = self.labels[self.pc]
            label = label.ljust(10)
            print label + " PC:" + str_pc + " A:" + str_a + " X:" + str_x + " Y:" + str_y + " SP:" + str_sp + " STATUS:" + str_cc

        else:
            print "           PC:" + str_pc + " A:" + str_a + " X:" + str_x + " Y:" + str_y + " SP:" + str_sp + " STATUS:" + str_cc

    # Utility routines to change the flags
    # So you don't need to remember the bit positions
    #

    # 7	        6	        5	    4	    3	    2	        1	    0
    # Negative	Overflow	(S)     Break	Decimal	Interrupt	Zero	Carry
    # N	        V	        -	    B	    D	    I	        Z	    C
    # -	        -	        -	    -	    -	    -	        -	    -

    def set_c(self, truth):
        if truth:
            self.cc = self.cc | Flags.CARRY
        else:
            self.cc = self.cc & (0xff ^ Flags.CARRY)

    def set_z(self, truth):
        if truth:
            self.cc = self.cc | Flags.ZERO
        else:
            self.cc = self.cc & (0xff ^ Flags.ZERO)

    def set_i(self, truth):
        if truth:
            self.cc = self.cc | Flags.INTERRUPT
        else:
            self.cc = self.cc & (0xff ^ Flags.INTERRUPT)

    def set_d(self, truth):
        if truth:
            self.cc = self.cc | Flags.DECIMAL
        else:
            self.cc = self.cc & (0xff ^ Flags.DECIMAL)

    def set_b(self, truth):
        if truth:
            self.cc = self.cc | Flags.BREAK
        else:
            self.cc = self.cc & (0xff ^ Flags.BREAK)

    def set_s(self, truth):
        if truth:
            self.cc = self.cc | Flags.UNUSED
        else:
            self.cc = self.cc & (0xff ^ Flags.UNUSED)

    def set_v(self, truth):
        if truth:
            self.cc = self.cc | Flags.OVERFLOW
        else:
            self.cc = self.cc & (0xff ^ Flags.OVERFLOW)

    def set_n(self, truth):
        if truth:
            self.cc = self.cc | Flags.NEGATIVE
        else:
            self.cc = self.cc & (0xff ^ Flags.NEGATIVE)

    def push(self, value):
        self.memory_map.Write(0x100 + self.sp, value)
        self.sp -= 1

    def pushaddr(self, addr):
        low = addr & 0xff
        high = (addr & 0xff00) >> 8
        self.memory_map.Write(0x100 + self.sp, high)
        self.sp -= 1
        self.memory_map.Write(0x100 + self.sp, low)
        self.sp -= 1

    def pull(self):
        self.sp += 1
        value = self.memory_map.Read(0x100 + self.sp)
        return value

    def pulladdr(self):
        self.sp += 1
        low = self.memory_map.Read(0x100 + self.sp)
        self.sp += 1
        high = self.memory_map.Read(0x100 + self.sp)

        addr = low + (high << 8)
        return addr

    def relative_address(self, operand8, addr):
        if operand8 & 0x80:
            offset = ((operand8 & 0xff) ^ 0xff) + 1 # invert and +1 to change neg to pos
            new_addr = addr - offset
        else:
            offset = operand8
            new_addr = addr + offset
        return new_addr

    # Instruction ADC
    # 69 55    adc #$55      
    # 65 20    adc $20       
    # 75 20    adc $20,X     
    # 6D 33 22 adc $2233     
    # 7D 33 22 adc $2233,X   
    # 79 33 22 adc $2233,Y   
    # 61 20    adc ($20,X)   
    # 71 20    adc ($20),Y   
    # 72 20    adc ($20)
    def instr_adc(self, addrmode, opcode, operand8, operand16):
        # TODO: support non-BCD arguments in DECIMAL mode

        carryin = self.cc & Flags.CARRY

        # Get the operand based on the address mode
        operand, addr, length = self.get_operand(addrmode, opcode, operand8, operand16)

        # Do the add
        # Compute the carry
        # Put the result in A
        # Compute the flags

        if self.cc & Flags.DECIMAL:
            a_10s = ((self.a & 0xf0) >> 4) * 10
            a_1s = (self.a & 0xf)
            operand_10s = ((operand & 0xf0) >> 4) * 10
            operand_1s = (operand & 0xf)
            if (a_10s >= 100 or a_1s >= 10 or operand_10s >= 100 or operand_1s >= 10):
                raise ValueError("Invalid BCD argument not supported")
            sum = (a_10s + a_1s + operand_10s + operand_1s + carryin)
            self.set_c(sum > 100)

            sum_1s = sum % 10
            sum_10s = (sum % 100 - sum_1s)/10
            result = sum_10s << 4 + sum_1s
        else:
            result = (self.a + operand + carryin)
            self.set_c(result > 255)
            result = result % 256

        acc = self.a
        self.a = result
        self.make_flags_nz(result)
        # self.make_flags_v(self.a, operand, carryin, result, carryout)
        self.set_v(((acc ^ result) & (operand ^ result) & 0x80) == 0x80)
        self.pc += length - 1
        return None

    # Instruction AND
    # 29 55    and #$55      
    # 25 20    and $20       
    # 35 20    and $20,X     
    # 2D 33 22 and $2233     
    # 3D 33 22 and $2233,X   
    # 39 33 22 and $2233,Y   
    # 21 20    and ($20,X)   
    # 31 20    and ($20),Y   
    # 32 20    and ($20) 

    def instr_and(self, addrmode, opcode, operand8, operand16):
        # Get the operand based on the address mode
        operand, addr, length = self.get_operand(addrmode, opcode, operand8, operand16)

        # Do the an
        # Put the result in A
        # Compute the flags

        result = (self.a & operand)

        self.a = result
        self.make_flags_nz(result)
        self.pc += length - 1

        return None

    # Instruction ASL
    # 0A       asl A         
    # 06 20    asl $20       
    # 16 20    asl $20,X     
    # 0E 33 22 asl $2233     
    # 1E 33 22 asl $2233,X   
    def instr_asl(self, addrmode, opcode, operand8, operand16):
        if addrmode == "accumulator":
            self.set_c(self.a & 0x80)
            result = (self.a & 0x7f) << 1
            self.a = result
            self.make_flags_nz(result)
            return None
        else:
            # Get the operand based on the address mode
            operand, addr, length = self.get_operand(addrmode, opcode, operand8, operand16)
            self.set_c(operand & 0x80)
            result = (operand & 0x7f) << 1

            self.memory_map.Write(addr, result)
            self.pc += length - 1
            self.make_flags_nz(result)
            return ("w", addr)

    # Instruction BCC
    # 90 55    bcc $55        
    def instr_bcc(self, addrmode, opcode, operand8, operand16):
        self.pc += 1
        if not self.cc & Flags.CARRY:
            self.pc = self.relative_address(operand8, self.pc)

        return None

    # Instruction BCS
    # B0 55    bcs $55       
    def instr_bcs(self, addrmode, opcode, operand8, operand16):
        self.pc += 1
        if self.cc & Flags.CARRY:
            self.pc = self.relative_address(operand8, self.pc)

        return None

    # Instruction BEQ
    # F0 55    beq $55     
    def instr_beq(self, addrmode, opcode, operand8, operand16):
        self.pc += 1
        if self.cc & Flags.ZERO:
            self.pc = self.relative_address(operand8, self.pc)

        return None

    # Instruction BIT
    # 89 55    bit #$55      
    # 24 20    bit $20       
    # 34 20    bit $20,X     
    # 2C 33 22 bit $2233     
    # 3C 33 22 bit $2233,X   
    def instr_bit(self, addrmode, opcode, operand8, operand16):
        # Get the operand, immediate or from memory
        if addrmode == "immediate":
            operand = operand8
            length = 2
        else:
            operand, addr, length = self.get_operand(addrmode, opcode, operand8, operand16)

        # Do the test.
        test = self.a & operand
        self.set_z(test == 0x00)

        # N is set to bit 7 of the operand
        self.set_n(operand & 0x80)

        # V is set to bit 6 of the operand
        self.set_v(operand & 0x40)
        self.pc += length - 1

        return None

    # Instruction BMI
    # 30 55    bmi $55
    def instr_bmi(self, addrmode, opcode, operand8, operand16):
        self.pc += 1
        if self.cc & Flags.NEGATIVE:
            self.pc = self.relative_address(operand8, self.pc)

        return None

    # Instruction BNE
    # D0 55    bne $55
    def instr_bne(self, addrmode, opcode, operand8, operand16):
        self.pc += 1
        if not self.cc & Flags.ZERO:
            self.pc = self.relative_address(operand8, self.pc)

        return None

    # Instruction BPL
    # 10 55    bpl $55
    def instr_bpl(self, addrmode, opcode, operand8, operand16):
        self.pc += 1
        if not self.cc & Flags.NEGATIVE:
            self.pc = self.relative_address(operand8, self.pc)
        return None

    # Instruction BRA
    # 80 55    bra $55
    def instr_bra(self, addrmode, opcode, operand8, operand16):
        self.pc += 1
        self.pc = self.relative_address(operand8, self.pc)
        return None

    # Instruction BRK
    # 00       brk  
    def instr_brk(self, addrmode, opcode, operand8, operand16):
        # PC is pre-incremented on instruction fetch
        self.pushaddr(self.pc + 1)
        self.set_s(True)
        self.set_b(True)
        self.push(self.cc)
        low = self.memory_map.Read(0xfffe)
        high = self.memory_map.Read(0xffff)
        self.pc = low + (high << 8)
        self.set_i(True)
        # 65C02
        self.set_d(False)
        return None

    # Instruction BVC
    # 50 55    bvc $55       
    def instr_bvc(self, addrmode, opcode, operand8, operand16):
        self.pc += 1
        if not self.cc & Flags.OVERFLOW:
            self.pc = self.relative_address(operand8, self.pc)
        return None

    # Instruction BVS
    # 70 55    bvs $55 
    def instr_bvs(self, addrmode, opcode, operand8, operand16):
        self.pc += 1
        if self.cc & Flags.OVERFLOW:
            self.pc = self.relative_address(operand8, self.pc)
        return None

    # Instruction CLC
    # 18        clc 
    def instr_clc(self, addrmode, opcode, operand8, operand16):
        self.set_c(False)
        return None

    # Instruction CLD
    # D8        cld 
    def instr_cld(self, addrmode, opcode, operand8, operand16):
        self.set_d(False)
        return None

    # Instruction CLI
    # 58        cli 
    def instr_cli(self, addrmode, opcode, operand8, operand16):
        self.set_i(False)
        return None

    # Instruction CLV
    # 57        clv 
    def instr_clv(self, addrmode, opcode, operand8, operand16):
        self.set_v(False)
        return None

    # Instruction CMP
    # C9 55    cmp #$55      
    # C5 20    cmp $20       
    # CD 33 22 cmp $2233     
    # DD 33 22 cmp $2233,X   
    # D9 33 22 cmp $2233,Y   
    # C1 20    cmp ($20,X)   
    # D1 20    cmp ($20),Y   
    # D2 20    cmp ($20)     
    def instr_cmp(self, addrmode, opcode, operand8, operand16):
        operand, addr, length = self.get_operand(addrmode, opcode, operand8, operand16)
        test = self.a - operand
        # TODO: add test case
        if test < 0:
            test += 256
        self.make_flags_nz(test)
        self.pc += length - 1
        return None

    # Instruction CMP
    # E0 55    cpx #$55      
    # E4 20    cpx $20       
    # EC 33 22 cpx $2233     
    # C0 55    cpy #$55      
    # C4 20    cpy $20       
    # CC 33 22 cpy $2233 
    def instr_cpx(self, addrmode, opcode, operand8, operand16):
        operand, addr, length = self.get_operand(addrmode, opcode, operand8, operand16)
        test = self.a - operand
        # TODO: add test case
        if test < 0:
            test += 256
        self.make_flags_nz(test)
        self.pc += length
        return None

    # Instruction CPY
    # C0 55    cpy #$55      
    # C4 20    cpy $20       
    # CC 33 22 cpy $2233
    def instr_cpy(self, addrmode, opcode, operand8, operand16):
        operand, addr, length = self.get_operand(addrmode, opcode, operand8, operand16)
        test = self.y - operand
        # TODO: add test case
        if test < 0:
            test += 256
        self.make_flags_nz(test)
        self.pc += length - 1
        return None

    # Instruction DEA aka DEC A
    # 3A       dea 
    def instr_dea(self, addrmode, opcode, operand8, operand16):
        operand, addr, length = self.get_operand(addrmode, opcode, operand8, operand16)
        # TODO: add test case
        if self.a:
            self.a -= 1
        else:
            self.a = 0xff
        self.make_flags_nz(self.a)
        self.pc += length - 1
        return None

    # Instruction DEC
    # C6 20    dec $20       
    # D6 20    dec $20,X     
    # CE 33 22 dec $2233     
    # DE 33 22 dec $2233,X 
    def instr_dec(self, addrmode, opcode, operand8, operand16):
        operand, addr, length = self.get_operand(addrmode, opcode, operand8, operand16)
        # TODO: add test case
        if operand:
            result = operand - 1
        else:
            result = 0xff
        self.make_flags_nz(result)
        self.memory_map.Write(addr, result)
        self.pc += length - 1
        return ("w", addr)

    # Instruction DEX
    # CA       dex
    def instr_dex(self, addrmode, opcode, operand8, operand16):
        operand, addr, length = self.get_operand(addrmode, opcode, operand8, operand16)
        # TODO: add test case
        if self.x:
            result = self.x - 1
        else:
            results = 0xff
        self.make_flags_nz(result)
        self.x = result
        self.pc += length - 1
        return None

    # Instruction DEY
    # 88       dey 
    def instr_dey(self, addrmode, opcode, operand8, operand16):
        operand, addr, length = self.get_operand(addrmode, opcode, operand8, operand16)
        # TODO: add test case
        if self.y:
            result = self.y - 1
        else:
            result = 0xff
        self.make_flags_nz(result)
        self.y = result
        self.pc += length - 1
        return None

    # Instruction EOR
    # 49 55    eor #$55      
    # 45 20    eor $20       
    # 55 20    eor $20,X     
    # 4D 33 22 eor $2233     
    # 5D 33 22 eor $2233,X   
    # 59 33 22 eor $2233,Y   
    # 41 20    eor ($20,X)   
    # 51 20    eor ($20),Y   
    # 52 20    eor ($20)   
    def instr_eor(self, addrmode, opcode, operand8, operand16):
        # Get the operand based on the address mode
        operand, addr, length = self.get_operand(addrmode, opcode, operand8, operand16)

        # Do the an
        # Put the result in A
        # Compute the flags

        result = (self.a ^ operand)

        self.a = result
        self.make_flags_nz(result)
        self.pc += length - 1
        return None

    # Instruction INA aka INC A
    # 1A       ina
    def instr_ina(self, addrmode, opcode, operand8, operand16):
        operand, addr, length = self.get_operand(addrmode, opcode, operand8, operand16)
        self.a = (self.a + 1) % 256
        self.make_flags_nz(self.a)
        self.pc += length - 1
        return None

    # Instruction INC
    # E6 20    inc $20       
    # F6 20    inc $20,X     
    # EE 33 22 inc $2233     
    # FE 33 22 inc $2233,X
    def instr_inc(self, addrmode, opcode, operand8, operand16):
        operand, addr, length = self.get_operand(addrmode, opcode, operand8, operand16)
        result = (operand + 1) % 256
        self.make_flags_nz(result)
        self.pc += length - 1
        self.memory_map.Write(addr, result)
        return None

    # Instruction INX
    # E8       inx
    def instr_inx(self, addrmode, opcode, operand8, operand16):
        operand, addr, length = self.get_operand(addrmode, opcode, operand8, operand16)
        result = (self.x + 1) % 256
        self.make_flags_nz(result)
        self.x = result
        self.pc += length - 1

    # Instruction INY
    # C8       iny 
    def instr_iny(self, addrmode, opcode, operand8, operand16):
        operand, addr, length = self.get_operand(addrmode, opcode, operand8, operand16)
        result = (self.y + 1) % 256
        self.make_flags_nz(result)
        self.y = result
        self.pc += length - 1
        return None

    # Instruction JMP
    # 4C 33 22 jmp $2233     
    # 6C 33 22 jmp ($2233)   
    # 7C 33 22 jmp ($2233,X) 
    def instr_jmp(self, addrmode, opcode, operand8, operand16):
        # print "INSTR_JMP CALLED addrmode = %s opcode=%02x operand8=%02x operand16=%04x" % (addrmode,opcode,operand8,operand16)
        operand, addr, length = self.get_operand16(addrmode, opcode, operand8, operand16)
        # print "INSTR_JMP operand   = %04x addr=%04x length=%d" % (operand,addr, length)
        # print "INSTR_JMP operand16 = %04x " % operand16
        self.pc = addr
        return None

        # Instruction JSR

    # 20 33 22 jsr $2233
    def instr_jsr(self, addrmode, opcode, operand8, operand16):
        operand, addr, length = self.get_operand16(addrmode, opcode, operand8, operand16)
        self.pc += length - 1
        # Pushes the address - 1 of the next operation to be executed, so that when RTS is
        # called and the next opcode pre-increments PC, it will be pointed at the right place.
        self.pushaddr(self.pc - 1)
        self.pc = addr
        return ("stack", self.sp)

        # Instruction LDA

    # A9 55    lda #$55
    # A5 20    lda $20       
    # B5 20    lda $20,X     
    # AD 33 22 lda $2233     
    # BD 33 22 lda $2233,X   
    # B9 33 22 lda $2233,Y   
    # A1 20    lda ($20,X)   
    # B1 20    lda ($20),Y   
    # B2 20    lda ($20)    
    def instr_lda(self, addrmode, opcode, operand8, operand16):
        operand, addr, length = self.get_operand(addrmode, opcode, operand8, operand16)
        # print "LDA : addrmode:"+str(addrmode)+" operand:"+str(operand)+" operand8 "+str(operand8)
        self.a = operand
        self.make_flags_nz(operand)
        self.pc += length - 1
        return None

    # Instruction LDX
    # A9 55    lda #$55      
    # A2 55    ldx #$55      
    # A6 20    ldx $20       
    # B6 20    ldx $20,Y     
    # AE 33 22 ldx $2233     
    # BE 33 22 ldx $2233,Y 
    def instr_ldx(self, addrmode, opcode, operand8, operand16):
        operand, addr, length = self.get_operand(addrmode, opcode, operand8, operand16)
        self.x = operand
        self.make_flags_nz(operand)
        self.pc += length - 1
        return None

    # Instruction LDY
    # A0 55    ldy #$55      
    # A4 20    ldy $20       
    # B4 20    ldy $20,X     
    # AC 33 22 ldy $2233     
    # BC 33 22 ldy $2233,X   
    def instr_ldy(self, addrmode, opcode, operand8, operand16):
        operand, addr, length = self.get_operand(addrmode, opcode, operand8, operand16)
        self.y = operand
        self.make_flags_nz(operand)
        self.pc += length - 1
        return None

    # Instruction LSR
    # 4A       lsr A         
    # 46 20    lsr $20       
    # 56 20    lsr $20,X     
    # 4E 33 22 lsr $2233     
    # 5E 33 22 lsr $2233,X
    def instr_lsr(self, addrmode, opcode, operand8, operand16):
        if (addrmode == "accumulator"):
            self.set_c(self.a & 0x01)

            result = self.a >> 1
            self.a = result
            self.make_flags_nz(result)
            return None
        else:
            operand, addr, length = self.get_operand(addrmode, opcode, operand8, operand16)
            self.set_c(operand & 0x01)

            result = (operand >> 1) & 0xff
            self.pc += length - 1
            self.make_flags_nz(result)
            self.memory_map.Write(addr, result)
            return ("w", addr)

    # Instruction NOP
    # EA       nop
    def instr_nop(self, addrmode, opcode, operand8, operand16):
        return None

    # Instruction ORA
    # 09 55    ora #$55      
    # 05 20    ora $20       
    # 15 20    ora $20,X     
    # 0D 33 22 ora $2233     
    # 1D 33 22 ora $2233,X   
    # 19 33 22 ora $2233,Y   
    # 01 20    ora ($20,X)   
    # 11 20    ora ($20),Y   
    # 12 20    ora ($20)
    def instr_ora(self, addrmode, opcode, operand8, operand16):
        operand, addr, length = self.get_operand(addrmode, opcode, operand8, operand16)
        result = (operand | self.a)
        self.a = result
        self.make_flags_nz(result)
        self.pc += length - 1
        return None

    # Instruction PHA and other Pxx stack instructions
    # 08       php
    # 28       plp
    # 48       pha    
    # DA       phx           
    # 5A       phy           
    # 68       pla           
    # FA       plx           
    # 7A       ply
    def instr_php(self, addrmode, opcode, operand8, operand16):
        self.memory_map.Write(0x100 + self.sp, self.cc)
        if self.sp:
            self.sp = self.sp - 1
        else:
            self.sp = 0xff
        return ("stack", self.sp)

    def instr_pha(self, addrmode, opcode, operand8, operand16):
        self.memory_map.Write(0x100 + self.sp,  self.a)
        if self.sp:
            self.sp = self.sp - 1
        else:
            self.sp = 0xff
        return ("stack", self.sp)

    def instr_phx(self, addrmode, opcode, operand8, operand16):
        self.memory_map.Write(0x100 + self.sp, self.x)
        if self.sp:
            self.sp = self.sp - 1
        else:
            self.sp = 0xff
        return ("stack", self.sp)

    def instr_phy(self, addrmode, opcode, operand8, operand16):
        self.memory_map.Write(0x100 + self.sp,  self.y)
        if self.sp:
            self.sp = self.sp - 1
        else:
            self.sp = 0xff
        return ("stack", self.sp)

    def instr_plp(self, addrmode, opcode, operand8, operand16):
        self.sp = (self.sp + 1) % 256
        self.cc = self.memory_map.Read(0x100 + self.sp)
        return ("stack", self.sp)

    def instr_pla(self, addrmode, opcode, operand8, operand16):
        self.sp = (self.sp + 1) % 256
        self.a = self.memory_map.Read(0x100 + self.sp)
        return ("stack", self.sp)

    def instr_plx(self, addrmode, opcode, operand8, operand16):
        self.sp = (self.sp + 1) % 256
        self.x = self.memory_map.Read(0x100 + self.sp)
        return ("stack", self.sp)

    def instr_ply(self, addrmode, opcode, operand8, operand16):
        self.sp = (self.sp + 1) % 256
        self.y = self.memory_map.Read(0x100 + self.sp)
        return ("stack", self.sp)

    # Instruction ROL
    # 2A       rol A         
    # 26 20    rol $20       
    # 36 20    rol $20,X     
    # 2E 33 22 rol $2233     
    # 3E 33 22 rol $2233,X
    def instr_rol(self, addrmode, opcode, operand8, operand16):
        if (addrmode == "accumulator"):
            carryout = self.a & 0x80
            carryin = self.cc & Flags.CARRY

            result = ((self.a << 1) & 0xff) | carryin
            self.a = result
            self.set_c(carryout)
            self.make_flags_nz(result)
            return None
        else:
            operand, addr, length = self.get_operand(addrmode, opcode, operand8, operand16)

            carryout = (operand & 0x80)
            carryin = self.cc & Flags.CARRY

            result = ((operand << 1) & 0xff) | carryin
            self.set_c(carryout)
            self.memory_map.Write(addr, result)
            self.pc += length - 1
            self.make_flags_nz(result)
            return ("w", addr)

    # Instruction ROR
    # 6A       ror A         
    # 66 20    ror $20       
    # 76 20    ror $20,X     
    # 6E 33 22 ror $2233     
    # 7E 33 22 ror $2233,X   
    def instr_ror(self, addrmode, opcode, operand8, operand16):
        if (addrmode == "accumulator"):
            if self.cc & Flags.CARRY:
                carry = 0x80
            else:
                carry = 0
            carryout = self.a & 0x01

            result = (self.a >> 1) | carry
            self.a = result
            self.set_c(carryout)
            self.make_flags_nz(result)
            return None
        else:
            operand, addr, length = self.get_operand(addrmode, opcode, operand8, operand16)
            if self.cc & Flags.CARRY:
                carry = 0x80
            else:
                carry = 0
            carryout = operand & 0x01

            result = ((operand >> 1) % 256) | carry
            self.memory_map.Write(addr, result)
            self.set_c(carryout)
            self.pc += length - 1
            self.make_flags_nz(result)
            return ("w", addr)

            # Instruction RTI

    # 40       rti
    def instr_rti(self, addrmode, opcode, operand8, operand16):
        self.cc = self.pull()
        self.pc = self.pulladdr()
        self.set_b(True)
        self.set_s(True)
        return ("stack", self.sp)

    # Instruction RTS
    # 60       rts
    def instr_rts(self, addrmode, opcode, operand8, operand16):
        self.pc = (self.pulladdr() + 1) % 0x10000
        return ("stack", self.sp)

        # Instruction SBC

    # E9 55    sbc #$55
    # E5 20    sbc $20       
    # F5 20    sbc $20,X     
    # ED 33 22 sbc $2233     
    # FD 33 22 sbc $2233,X   
    # F9 33 22 sbc $2233,Y   
    # E1 20    sbc ($20,X)   
    # F1 20    sbc ($20),Y   
    # F2 20    sbc ($20)
    def instr_sbc(self, addrmode, opcode, operand8, operand16):
        carryin = not (self.cc & Flags.CARRY)

        # Get the operand based on the address mode
        operand, addr, length = self.get_operand(addrmode, opcode, operand8, operand16)

        # Do the subtract
        # Compute the carry
        # Put the result in A
        # Compute the flags

        if self.cc & Flags.DECIMAL:
            a_10s = ((self.a & 0xf0) >> 4) * 10
            a_1s = (self.a & 0xf)
            operand_10s = ((operand & 0xf0) >> 4) * 10
            operand_1s = (operand & 0xf)

            if (a_10s >= 100 or a_1s >= 10 or operand_10s >= 100 or operand_1s >= 10):
                raise ValueError("Invalid BCD argument not supported")
            diff = (a_10s + a_1s - operand_10s - operand_1s - carryin)
            carryout = diff < 0

            diff_1s = diff % 10
            diff_10s = (diff % 100 - diff_1s)/10

            result = diff_10s * 16 + diff_1s
        else:
            result = (self.a - operand - carryin)
            carryout = result < 0
            result = result % 256

        self.set_c(not carryout)

        self.a = result
        self.make_flags_nz(result)
        self.make_flags_v(self.a, operand, carryin, result, carryout)
        self.pc += length - 1
        return None

    # Instruction SEC    
    # 38       sec
    def instr_sec(self, addrmode, opcode, operand8, operand16):
        self.set_c(True)
        return None

    # Instruction SED    
    # F8       sed
    def instr_sed(self, addrmode, opcode, operand8, operand16):
        self.set_d(True)
        return None

    # Instruction SEI
    # 78       sei
    def instr_sei(self, addrmode, opcode, operand8, operand16):
        self.set_i(True)
        return None

    # Instruction STA
    # 85 20    sta $20       
    # 95 20    sta $20,X     
    # 8D 33 22 sta $2233     
    # 9D 33 22 sta $2233,X   
    # 99 33 22 sta $2233,Y   
    # 81 20    sta ($20,X)   
    # 91 20    sta ($20),Y   
    # 92 20    sta ($20)
    def instr_sta(self, addrmode, opcode, operand8, operand16):
        operand, addr, length = self.get_operand(addrmode, opcode, operand8, operand16)
        self.memory_map.Write(addr, self.a)
        self.pc += length - 1
        return ("w", addr)

    # Instruction STX
    # 86 20    stx $20       
    # 96 20    stx $20,Y     
    # 8E 33 22 stx $2233
    def instr_stx(self, addrmode, opcode, operand8, operand16):
        operand, addr, length = self.get_operand(addrmode, opcode, operand8, operand16)
        self.memory_map.Write(addr, self.x)
        self.pc += length - 1
        return ("w", addr)

    # Instruction STY
    # 84 20    sty $20       
    # 94 20    sty $20,X     
    # 8C 33 22 sty $2233 
    def instr_sty(self, addrmode, opcode, operand8, operand16):
        operand, addr, length = self.get_operand(addrmode, opcode, operand8, operand16)
        self.memory_map.Write(addr, self.y)
        self.pc += length - 1
        return ("w", addr)

    # Instruction STZ
    # 64 20    stz $20       
    # 74 20    stz $20,X     
    # 9C 33 22 stz $2233     
    # 9E 33 22 stz $2233,X 
    def instr_stz(self, addrmode, opcode, operand8, operand16):
        operand, addr, length = self.get_operand(addrmode, opcode, operand8, operand16)
        self.memory_map.Write(addr, 0x00)
        self.pc += length - 1
        return ("w", addr)

    # Instruction TAX    
    # AA       tax
    def instr_tax(self, addrmode, opcode, operand8, operand16):
        self.x = self.a
        self.make_flags_nz(self.a)
        return None

    # Instruction TAY
    # A8       tay
    def instr_tay(self, addrmode, opcode, operand8, operand16):
        self.y = self.a
        self.make_flags_nz(self.a)
        return None

    # Instruction TRB
    # 14 20    trb $20       
    # 1C 33 22 trb $2233
    def instr_trb(self, addrmode, opcode, operand8, operand16):
        operand, addr, length = self.get_operand(addrmode, opcode, operand8, operand16)
        result = operand & (self.a ^ 0xff)
        self.memory_map.Write(addr, result)
        self.set_z((operand & self.a) == 0x00)
        self.pc += length - 1
        return ("w", addr)

    # Instruction TSB
    # 04 20    tsb $20
    # 0C 33 22 tsb $2233
    def instr_tsb(self, addrmode, opcode, operand8, operand16):
        operand, addr, length = self.get_operand(addrmode, opcode, operand8, operand16)
        result = operand | self.a
        self.memory_map.Write(addr, result)
        self.set_z((operand & self.a) == 0x00)
        self.pc += length - 1
        return ("w", addr)

    # BA       tsx  
    def instr_tsx(self, addrmode, opcode, operand8, operand16):
        self.x = self.sp
        self.make_flags_nz(self.sp)
        return None

        # 8A       txa

    def instr_txa(self, addrmode, opcode, operand8, operand16):
        self.a = self.x
        self.make_flags_nz(self.x)
        return None

    # 9A       txs      
    def instr_txs(self, addrmode, opcode, operand8, operand16):
        self.sp = self.x
        return None

    # 98       tya
    def instr_tya(self, addrmode, opcode, operand8, operand16):
        self.a = self.y
        self.make_flags_nz(self.y)
        return None
