#   Address mode        format                    name applied
# implicit                                       ~ "implicit"
# immediate               #num                   ~ "immediate"
# accumulator             A                      ~ "accumulator"
# absolute                $2000                  ~ "absolute"
# zero page               $20                    ~ "zeropage"
# absolute indexed x      $5000,X                ~ "absolutex"
# absolute indexed y      $5000,y                ~ "absolutey"
# zeropage indexed x      $20,X                  ~ "zeropagex"
# zeropage indexed y      $20,Y                  ~ "zeropagey"
# relative                +10 (or label)         ~ "relative"
# zeropage indexed indirect x ($20,X)            ~ "zeropageindexedindirectx"
# zeropage indexed indirect y ($20),Y            ~ "zeropageindexedindirecty"
# absolute indexed indirect ($5000,X) - only JMP ~ "absoluteindexedindirect"
# zeropage indirect       ($20)                  ~ "zeropageindirect"
# absolute indirect       ($5000) - only JMP     ~ "absoluteindirect"

class py6502_common(object):
    def __init__(self):

        # Build the opcode type tables

        self.modeswithlowbytevalue = {
            "immediate", "absolute", "zeropage", "absolutex", "absolutey",
            "zeropagex", "zeropagey", "zeropageindexedindirectx", "zeropageindexedindirecty",
            "absoluteindexedindirect", "zeropageindirect",
            "absoluteindirect"
        }
        self.modeswithhighbytevalue = {
            "absolute", "absolutex", "absolutey",
            "absoluteindexedindirect", "absoluteindirect"
        }

        self.validdirectives = {
            "db", "dw", "ddw", "dqw", "str", "org", "le", "be"
        }

        # TODO: construct this as the union of all of the others.
        self.validopcodes = {
            "adc", "and", "asl", "bcc", "bcs", "beq", "bit", "bmi", "bne",
            "bpl", "bra", "brk", "bvc", "bvs", "clc", "cld", "cli", "clv",
            "cmp", "cpx", "cpy", "dea", "dec", "dex", "dey", "eor", "inc", "ina", "inx",
            "iny", "jmp", "jsr", "lda", "ldx", "ldy", "lsr", "nop", "ora",
            "pha", "php", "phx", "phy", "pla", "plp", "plx", "ply", "rol",
            "ror", "rti", "rts", "sbc", "sec", "sed", "sei", "sta", "stx",
            "sty", "stz", "tax", "tay", "trb", "tsb", "tsx", "txa", "txs",
            "tya"
        }

        self.implicitopcodes = {
            "brk", "clc", "cld", "cli", "clv", "dex", "dey", "inx", "iny", "nop",
            "pha", "php", "phx", "phy", "pla", "plp", "plx", "ply", "rti", "rts",
            "sec", "sed", "sei", "tax", "tay", "trb", "tsb", "tsx", "txa", "txs",
            "tya"
        }

        self.immediateopcodes = {
            "adc", "and", "bit", "cmp", "cpx", "cpy", "eor", "lda", "ldx",
            "ldy", "ora", "sbc"
        }

        self.accumulatoropcodes = {
            "asl", "dea", "dec", "ina", "inc", "lsr", "rol", "ror"
        }

        self.zeropageopcodes = {
            "adc", "and", "asl", "bit", "cmp", "cpx", "cpy", "dec", "eor", "inc",
            "lda", "ldx", "ldy", "lsr", "ora", "rol", "ror", "sbc", "sta", "stx",
            "sty", "stz", "trb", "tsb"
        }

        self.absoluteopcodes = {
            "adc", "and", "asl", "bit", "cmp", "cpx", "cpy", "dec", "eor", "inc",
            "jmp", "jsr", "lda", "ldx", "ldy", "lsr", "ora", "rol", "ror", "sbc",
            "sta", "stx", "sty", "stz", "trb", "tsb"
        }

        self.absolutexopcodes = {
            "adc", "and", "asl", "bit", "cmp", "dec", "eor", "inc",
            "lda", "lsr", "ora", "rol", "ror", "sbc",
            "sta", "stz", "ldy"
        }

        self.absoluteyopcodes = {
            "adc", "and", "cmp", "eor",
            "lda", "ldx", "ora", "sbc", "sta"
        }

        self.zeropagexopcodes = {
            "adc", "and", "cmp", "eor", "lda", "dec", "bit", "asl", "ldy",
            "ora", "sbc", "sta", "sty", "ror", "rol", "lsr", "inc", "stz"
        }

        self.zeropageyopcodes = {"ldx", "stx"}

        self.relativeopcodes = {"bmi", "bne", "bpl", "bra", "bvc", "bvs", "bcc", "bcs", "beq"}

        self.zeropageindexedindirectxopcodes = {
            "adc", "and", "cmp", "eor", "lda", "ora", "sbc", "sta"
        }

        self.zeropageindexedindirectyopcodes = {
            "adc", "and", "cmp", "eor", "lda", "ora", "sbc", "sta"
        }

        self.zeropageindirectopcodes = {
            "adc", "and", "cmp", "eor", "lda", "ora", "sbc", "sta"
        }

        # Build a map of opcodes to list of modes the opcode supports.
        self.map = dict()

        for opcode in self.validopcodes:
            self.map[opcode] = list()
            if opcode in self.implicitopcodes:
                self.map[opcode].append("implicit")
            if opcode in self.immediateopcodes:
                self.map[opcode].append("immediate")
            if opcode in self.accumulatoropcodes:
                self.map[opcode].append("accumulator")
            if opcode in self.zeropageopcodes:
                self.map[opcode].append("zeropage")
            if opcode in self.absoluteopcodes:
                self.map[opcode].append("absolute")
            if opcode in self.absolutexopcodes:
                self.map[opcode].append("absolutex")
            if opcode in self.absoluteyopcodes:
                self.map[opcode].append("absolutey")
            if opcode in self.zeropagexopcodes:
                self.map[opcode].append("zeropagex")
            if opcode in self.zeropageyopcodes:
                self.map[opcode].append("zeropagey")
            if opcode in self.relativeopcodes:
                self.map[opcode].append("relative")
            if opcode in self.zeropageindexedindirectxopcodes:
                self.map[opcode].append("zeropageindexedindirectx")
            if opcode in self.zeropageindexedindirectyopcodes:
                self.map[opcode].append("zeropageindexedindirecty")
            if opcode in self.zeropageindirectopcodes:
                self.map[opcode].append("zeropageindirect")

        # Build the opcode value to opcode name/address mode dictionary
        # TODO: this implies all of the above
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

        # Make another list for synonyms
        self.otherhexcodes = dict()
        for hexval in xrange(256):
            self.otherhexcodes[hexval] = ("", "")
        self.otherhexcodes[0x1A] = ("inc", "accumulator")
        self.otherhexcodes[0x3A] = ("dec", "accumulator")
        self.otherhexcodes[0x90] = ("blt", "relative")
        self.otherhexcodes[0xB0] = ("bge", "relative")

        # Make a dictionary to map opcode+address mode to the opcode value.
        self.hexmap = dict()
        for hexval in xrange(256):
            op, mode = self.hexcodes[hexval]
            astring = op + mode
            if len(astring) > 1:
                self.hexmap[astring] = hexval

            op, mode = self.otherhexcodes[hexval]
            astring = op + mode
            if len(astring) > 1:
                self.hexmap[astring] = hexval

    # implicit                                       ~ "implicit"
    # immediate               #num                   ~ "immediate"
    # accumulator             A                      ~ "accumulator"
    # absolute                $2000                  ~ "absolute"
    # zero page               $20                    ~ "zeropage"
    # absolute indexed x      $5000,X                ~ "absolutex"
    # absolute indexed y      $5000,y                ~ "absolutey"
    # zeropage indexed x      $20,X                  ~ "zeropagex"
    # zeropage indexed y      $20,Y                  ~ "zeropagey"
    # relative                +10 (or label)         ~ "relative"
    # zeropage indexed indirect x ($20,X)            ~ "zeropageindexedindirectx"
    # zeropage indexed indirect y ($20),Y            ~ "zeropageindexedindirecty"
    # absolute indexed indirect ($5000,X) - only JMP ~ "absoluteindexedindirect"
    # zeropage indirect       ($20)                  ~ "zeropageindirect"
    # absolute indirect       ($5000) - only JMP     ~ "absoluteindirect"
    def addrmode_length(self, addrmode):
        return {
            'implicit': 0,
            'immediate': 1,
            'accumulator': 0,
            'absolute': 2,
            'zeropage': 1,
            'absolutex': 2,
            'absolutey': 2,
            'zeropagex': 1,
            'zeropagey': 1,
            'relative': 1,
            'zeropageindexedindirectx': 1,
            'zeropageindexedindirecty': 1,
            'absoluteindexedindirect': 2,
            'zeropageindirect': 1,
            'absoluteindirect': 2
        }[addrmode]
        
    def firstpasstext(self, thetuple):
        (offset, linenumber, labelstring, opcode_val, lowbyte, highbyte, opcode, operand, addressmode, value, comment,
         extrabytes) = thetuple
        a = ("%d" % linenumber).ljust(4)
        if (labelstring != None):
            b = (": %s" % labelstring).ljust(10)
        else:
            b = "          "

        if (opcode_val == None):
            c = "   "
        else:
            if (opcode_val > -1):
                c = "%02X " % opcode_val
            else:
                c = "?? "

        if (lowbyte == None):
            d = "   "
        else:
            if (lowbyte > -1):
                d = "%02X " % lowbyte
            else:
                d = "?? "

        if (highbyte == None):
            e = "   "
        else:
            if (highbyte > -1):
                e = "%02X " % highbyte
            else:
                e = "?? "

        # Print the opcode in 4 spaces
        if (opcode == None):
            f = "    "
        else:
            f = opcode.ljust(4)

        # Either print the operand in 10 spaces or print 10 spaces
        # when there is no operand
        if (operand == None):
            g = "          "
        else:
            if (len(operand) > 0):
                g = operand.ljust(10)
            else:
                g = "          "

        h = comment
        astring = a + b + c + d + e + f + g + h
        self.debug(1, astring)
        return astring

    def secondpasstext(self, thetuple):
        (offset, linenumber, labelstring, opcode_val, lowbyte, highbyte, opcode, operand, addressmode, value, comment,
         extrabytes) = thetuple
        a = ("%d " % linenumber).ljust(5)
        aa = ("%04X " % offset)

        if (labelstring != None) and (labelstring != ""):
            b = (": %s:" % labelstring).ljust(10)
        else:
            b = ":         "

        if (opcode_val == None):
            c = "   "
        else:
            if (opcode_val > -1):
                c = "%02X " % opcode_val
            else:
                c = "?? "

        if (lowbyte == None):
            d = "   "
        else:
            if (lowbyte > -1):
                d = "%02X " % lowbyte
            else:
                d = "?? "

        if (highbyte == None):
            e = "   "
        else:
            if (highbyte > -1):
                e = "%02X " % highbyte
            else:
                e = "?? "

        # Print the opcode in 4 spaces
        if (opcode == None):
            f = "    "
        else:
            f = opcode.ljust(4)

        if (operand == None):
            g = "          "
        else:
            if (len(operand) > 0):
                g = operand.ljust(10)
            else:
                g = "          "

        h = comment

        astring = a + aa + b + c + d + e + f + g + h
        self.debug(1, astring)
        self.debug(2, thetuple)

        # If there are extra bytes from a db, dw, dq, do or text operator,
        # print the resulting hex bytes on the next line.
        if (extrabytes != None) and (len(extrabytes) > 1):
            hexchars = ""
            index = 0
            for index in range(0, len(extrabytes) - 1):
                hexchars = hexchars + "%02X " % extrabytes[index]

            hexchars = hexchars + "%02X" % extrabytes[len(extrabytes) - 1]
            bytestring = a + aa + ":         " + hexchars
            self.debug(1, bytestring)
            return astring + "\n" + bytestring
        return astring

    # Separate out the label, opcode, operand and comment fields.
    # Identify the address mode as we go along
    # The results end up in self.allstuff in a tuple per entry
    # -1 in fields indicates a value not known yet
    # None in a field indicates that it doesn't exist
    def parse_line(self, thestring):
        linenumber = self.line
        self.line += 1
        thetext = "LINE #" + ("%d" % linenumber).ljust(5) + (": %s" % thestring)
        self.debug(2, thetext)
        mystring, comment = self.strip_comments(thestring)
        labelstring, mystring = self.strip_label(mystring, linenumber)
        opcode_anycase, operand = self.strip_opcode(mystring, linenumber)
        opcode = self.check_opcode(opcode_anycase, linenumber)
        premode, value = self.identify_addressmodeformat(operand, linenumber)
        addressmode = self.identify_addressmode(opcode, premode, value, linenumber)
        self.debug(3, "PARSE LINE: opcode=%s  addressmode=%s" % (str(opcode), addressmode))
        if (opcode != None) and (addressmode != "UNDECIDED"):
            astring = opcode + addressmode
            self.debug(3, "PARSE LINE 2 astring=%s" % astring)
            if astring in self.hexmap:
                self.debug(3, "PARSE LINE 3 astring=%s  self.hexmap[astring]=0x%x" % (astring, self.hexmap[astring]))
                opcode_val = self.hexmap[astring]
            else:
                opcode_val = None
        else:
            opcode_val = None
            astring = ""

        if (self.addrmode_length(addressmode) == 0):
            lowbyte = None
            highbyte = None
        elif (self.addrmode_length(addressmode) == 1) and (self.decode_value(value) != -1):
            lowbyte = self.decode_value(value) & 0x00FF
            highbyte = None
        elif (self.addrmode_length(addressmode) == 2) and (self.decode_value(value) != -1):
            lowbyte = self.decode_value(value) & 0x00FF
            highbyte = ((self.decode_value(value) & 0xFF00) >> 8) & 0x00FF
        elif (self.addrmode_length(addressmode) == 1) and (self.decode_value(value) == -1):
            lowbyte = -1
            highbyte = None
        elif (self.addrmode_length(addressmode) == 2) and (self.decode_value(value) == -1):
            lowbyte = -1
            highbyte = -1
        else:
            lowbyte = None
            highbyte = None
        offset = -1

        # Handle switches between little endian and big endian
        if (opcode == "le"):
            self.littleendian = True
        if (opcode == "be"):
            self.littleendian = False

        # interpret extra bytes from the db, dw, ddw, dqw directives.
        extrabytes = list()
        if (opcode == "db") and (operand != None) and (len(operand) > 0):
            extrabytes = self.decode_extrabytes(linenumber, thestring, operand)
        elif (opcode == "dw") and (operand != None) and (len(operand) > 0):
            extrabytes = self.decode_extrawords(linenumber, thestring, operand)
        elif (opcode == "ddw") and (operand != None) and (len(operand) > 0):
            extrabytes = self.decode_extradoublewords(linenumber, thestring, operand)
        elif (opcode == "dqw") and (operand != None) and (len(operand) > 0):
            extrabytes = self.decode_extraquadwords(linenumber, thestring, operand)

        thetuple = (
            offset, linenumber, labelstring, opcode_val, lowbyte, highbyte, opcode, operand, addressmode, value,
            comment,
            extrabytes)
        self.allstuff.append(thetuple)
        self.firstpasstext(thetuple)

        self.debug(2, "addressmode = %s" % addressmode)
        self.debug(2, str(self.allstuff[linenumber - 1]))
        self.debug(2, "-----------------------")

    # Perform the three passes of the assembly    
    def assemble(self, lines):
        self.clear_state()

        # First pass, parse each line for label, opcode, operand and comments
        self.debug(1, "First Pass")
        for line in lines:
            self.parse_line(line)

        # Second pass, compute the offsets and populate the symbol table
        self.debug(1, "Second Pass")
        self.symbols = dict()

        # Default to 0x0000. ORG directive overrides
        self.address = 0x0000

        # Add the offset to each line by counting the opcodes and operands
        for i in xrange(len(self.allstuff)):
            tuple = self.allstuff[i]
            (offset, linenumber, labelstring, opcode_val, lowbyte, highbyte, opcode, operand, addressmode, value,
             comment, extrabytes) = tuple
            # Handle ORG directive
            if (opcode == "org"):
                newaddr = self.decode_value(value)
                if (newaddr != -1):
                    self.address = newaddr & 0x00ffff
            offset = self.address

            if (opcode_val != None):
                self.address += 1
            if (lowbyte != None):
                self.address += 1
            if (highbyte != None):
                self.address += 1
            self.address += len(extrabytes)

            # If there is a label, we now know its address. So store it in the symbol table
            if (labelstring != None) and (labelstring != ""):
                self.symbols[labelstring] = offset
            tuple = (
                offset, linenumber, labelstring, opcode_val, lowbyte, highbyte, opcode, operand, addressmode, value,
                comment, extrabytes)
            self.allstuff[i] = tuple
            self.secondpasstext(tuple)

        # Print out the symbol table
        self.debug(1, "Symbol Table")
        for label in self.symbols:
            offset = self.symbols[label]
            astring = (("%s" % label).ljust(10)) + (" = " + "$%04X" % offset)
            self.debug(1, astring)

        # Third pass
        # Go through filling in the unknown values from the symbol table
        self.debug(1, "Third Pass")
        self.listing = list()
        for i in xrange(len(self.allstuff)):
            tuple = self.allstuff[i]
            (offset, linenumber, labelstring, opcode_val, lowbyte, highbyte, opcode, operand, addressmode, value,
             comment, extrabytes) = tuple

            if (lowbyte == -1) and (addressmode == "relative"):
                destination = self.symbols[value]
                start = offset
                delta = destination - start
                lowbyte = delta & 0x00ff
                if (delta > 127) or (delta < -128):
                    self.warning(linenumber, "", "branch can't reach destination, delta is %d" % delta)
            elif (lowbyte == -1) and (
                        (addressmode in self.modeswithlowbytevalue) or (addressmode in self.modeswithhighbytevalue)):
                if (value in self.symbols):
                    newvalue = self.symbols[value]
                    lowbyte = newvalue & 0x00ff
                if (highbyte == -1) and (addressmode in self.modeswithhighbytevalue):
                    if (value in self.symbols):
                        newvalue = self.symbols[value]
                        highbyte = ((newvalue & 0xff00) >> 8) & 0x00ff

            tuple = (
                offset, linenumber, labelstring, opcode_val, lowbyte, highbyte, opcode, operand, addressmode, value,
                comment, extrabytes)
            self.allstuff[i] = tuple
            line = self.secondpasstext(tuple)
            self.listing.append(line)

            # write generated bytes to object code map
            addr = offset
            if (opcode_val != None) and (opcode_val != -1):
                self.object_code[addr] = opcode_val
                addr = addr + 1
            if (lowbyte != None):
                self.object_code[addr] = lowbyte
                addr = addr + 1
            if (highbyte != None):
                self.object_code[addr] = highbyte
                addr = addr + 1
            if (extrabytes != None):
                for i in extrabytes:
                    self.object_code[addr] = i
                    addr = addr + 1

        print "LISTING"
        for i in self.listing:
            print i

        print
        print "SYMBOL TABLE"
        for label in self.symbols:
            offset = self.symbols[label]
            astring = (("%s" % label).ljust(10)) + (" = " + "$%04X" % offset)
            print astring

        print
        self.print_object_code()

    def print_object_code(self):
        print "OBJECT CODE"

        # Insert a star when there are empty spots in the memory map
        i = 0
        astring = ""
        printed_a_star = 0
        while (i < 65536):
            if self.object_code[i] != -1:
                printed_a_star = 0
                astring = "%04X: %02X" % (i, self.object_code[i])
                localrun = 1
                i = i + 1
                if (i < 65536):
                    nextval = self.object_code[i]
                    while (nextval != -1) and (localrun < 16):
                        astring = astring + " %02X" % self.object_code[i]
                        i = i + 1
                        localrun = localrun + 1
                        if (i < 65536):
                            nextval = self.object_code[i]
                        else:
                            nextval = -1
                    print astring
                else:
                    print astring
            else:
                if (printed_a_star == 0):
                    print "*"
                    printed_a_star = 1
                i = i + 1


def go(debug=0):
    lines = list()
    lines.append("    ADC #$55	    ")
    lines.append("    ADC $20	        ")
    lines.append("    ADC $20,X	    ")
    lines.append("    ADC $2233	        ")
    lines.append("    ADC $2233,X	    ")
    lines.append("    ADC $2233,Y	    ")
    lines.append("    ADC ($20,X)	    ")
    lines.append("    ADC ($20),Y	    ")
    lines.append("    ADC ($20)	    ")
    lines.append("    AND #$55	    ")
    lines.append("    AND $20	        ")
    lines.append("    AND $20,X	    ")
    lines.append("    AND $2233	        ")
    lines.append("    AND $2233,X	    ")
    lines.append("    AND $2233,Y	    ")
    lines.append("    AND ($20,X)	    ")
    lines.append("    AND ($20),Y	    ")
    lines.append("    AND ($20)	    ")
    lines.append("    ASL A	        ")
    lines.append("    ASL $20	        ")
    lines.append("    ASL $20,X	    ")
    lines.append("    ASL $2233	        ")
    lines.append("    ASL $2233,X	    	    ")
    lines.append("    BCC $55	    ")
    lines.append("    BCS $55	    ")
    lines.append("    BEQ $55	    ")
    lines.append("    BIT #$55	    ")
    lines.append("    BIT $20	    ")
    lines.append("    BIT $20,X	    ")
    lines.append("    BIT $2233	    ")
    lines.append("    BIT $2233,X	    ")
    lines.append("    BMI $55	    ")
    lines.append("    BNE $55	    ")
    lines.append("    BPL $55	    ")
    lines.append("    BRA $55	    ")
    lines.append("    BRK	            ")
    lines.append("    BVC $55	    ")
    lines.append("    BVS $55	    ")
    lines.append("    CLC	            ")
    lines.append("    CLD	            ")
    lines.append("    CLI	            ")
    lines.append("    CLV	            ")
    lines.append("    CMP #$55	    ")
    lines.append("    CMP $20	        ")
    lines.append("    CMP $20	        ")
    lines.append("    CMP $2233	        ")
    lines.append("    CMP $2233,X	    ")
    lines.append("    CMP $2233,Y	    ")
    lines.append("    CMP ($20,X)	    ")
    lines.append("    CMP ($20),Y	    ")
    lines.append("    CMP ($20)	    ")
    lines.append("    CPX #$55	    ")
    lines.append("    CPX $20	        ")
    lines.append("    CPX $2233	        ")
    lines.append("    CPY #$55	    ")
    lines.append("    CPY $20	        ")
    lines.append("    CPY $2233	        ")
    lines.append("    DEA	            ")
    lines.append("    DEC A	            ")
    lines.append("    DEC $20	        ")
    lines.append("    DEC $20,X	    ")
    lines.append("    DEC $2233	        ")
    lines.append("    DEC $2233,X	    ")
    lines.append("    DEX	            ")
    lines.append("    DEY	            ")
    lines.append("    EOR #$55	    ")
    lines.append("    EOR $20	        ")
    lines.append("    EOR $20,X	    ")
    lines.append("    EOR $2233	        ")
    lines.append("    EOR $2233,X	    ")
    lines.append("    EOR $2233,Y	    ")
    lines.append("    EOR ($20,X)	    ")
    lines.append("    EOR ($20),Y	    ")
    lines.append("    EOR ($20)	    ")
    lines.append("    INA")
    lines.append("    INC A	            ")
    lines.append("    INC $20	        ")
    lines.append("    INC $20,X	    ")
    lines.append("    INC $2233	        ")
    lines.append("    INC $2233,X	    ")
    lines.append("    INX	            ")
    lines.append("    INY	            ")
    lines.append("    JMP $2233	        ")
    lines.append("    JMP ($2233)	    ")
    lines.append("    JMP ($2233,X)	    ")
    lines.append("    JSR $2233	        ")
    lines.append("    LDA #$55	    ")
    lines.append("    LDA $20	        ")
    lines.append("    LDA $20,X	    ")
    lines.append("    LDA $2233	        ")
    lines.append("    LDA $2233,X	    ")
    lines.append("    LDA $2233,Y	    ")
    lines.append("    LDA ($20,X)	    ")
    lines.append("    LDA ($20),Y	    ")
    lines.append("    LDA ($20)	    ")
    lines.append("    LDX #$55	    ")
    lines.append("    LDX $20	        ")
    lines.append("    LDX $20,Y	    ")
    lines.append("    LDX $2233	        ")
    lines.append("    LDX $2233,Y	    ")
    lines.append("    LDY #$55	    ")
    lines.append("    LDY $20	        ")
    lines.append("    LDY $20,X	    ")
    lines.append("    LDY $2233	        ")
    lines.append("    LDY $2233,X	    ")
    lines.append("    LSR A	        ")
    lines.append("    LSR $20	        ")
    lines.append("    LSR $20,X	    ")
    lines.append("    LSR $2233	        ")
    lines.append("    LSR $2233,X	    ")
    lines.append("    NOP	            ")
    lines.append("    ORA #$55	    ")
    lines.append("    ORA $20	        ")
    lines.append("    ORA $20,X	    ")
    lines.append("    ORA $2233	        ")
    lines.append("    ORA $2233,X	    ")
    lines.append("    ORA $2233,Y	    ")
    lines.append("    ORA ($20,X)	    ")
    lines.append("    ORA ($20),Y	    ")
    lines.append("    ORA ($20)	    ")
    lines.append("    PHA	            ")
    lines.append("    PHX	            ")
    lines.append("    PHY	            ")
    lines.append("    PLA	            ")
    lines.append("    PLX	            ")
    lines.append("    PLY	            ")
    lines.append("    ROL A	        ")
    lines.append("    ROL $20	        ")
    lines.append("    ROL $20,X	    ")
    lines.append("    ROL $2233	        ")
    lines.append("    ROL $2233,X	    ")
    lines.append("    ROR A	        ")
    lines.append("    ROR $20	        ")
    lines.append("    ROR $20,X	    ")
    lines.append("    ROR $2233	        ")
    lines.append("    ROR $2233,X	    ")
    lines.append("    RTI	            ")
    lines.append("    RTS	            ")
    lines.append("    SBC #$55	    ")
    lines.append("    SBC $20 	    ")
    lines.append("    SBC $20,X	    ")
    lines.append("    SBC $2233	        ")
    lines.append("    SBC $2233,X	    ")
    lines.append("    SBC $2233,Y	    ")
    lines.append("    SBC ($20,X)	    ")
    lines.append("    SBC ($20),Y	    ")
    lines.append("    SBC ($20)	    ")
    lines.append("    SEC	            ")
    lines.append("    SED	            ")
    lines.append("    SEI	            ")
    lines.append("    STA $20	        ")
    lines.append("    STA $20,X	    ")
    lines.append("    STA $2233	        ")
    lines.append("    STA $2233,X	    ")
    lines.append("    STA $2233,Y	    ")
    lines.append("    STA ($20,X)	    ")
    lines.append("    STA ($20),Y	    ")
    lines.append("    STA ($20)	    ")
    lines.append("    STX $20	        ")
    lines.append("    STX $20,Y	    ")
    lines.append("    STX $2233	        ")
    lines.append("    STY $20	        ")
    lines.append("    STY $20,X	    ")
    lines.append("    STY $2233	        ")
    lines.append("    STZ $20	        ")
    lines.append("    STZ $20,X	    ")
    lines.append("    STZ $2233	        ")
    lines.append("    STZ $2233,X	    ")
    lines.append("    TAX	            ")
    lines.append("    TAY	            ")
    lines.append("    TRB $20	        ")
    lines.append("    TRB $2233	        ")
    lines.append("    TSB $20	        ")
    lines.append("    TSB $2233	        ")
    lines.append("    TSX	            ")
    lines.append("    TXA	            ")
    lines.append("    TXS	            ")
    lines.append("    TYA")
    lines.append("; A remark")
    lines.append("       org $1000")
    lines.append("start: lda #$50")
    lines.append("       sta $5000 ; blah")
    lines.append("       sta $25")
    lines.append("       clc")
    lines.append("       ROR A")
    lines.append("       adc #%10011010")
    lines.append("       sta %0101101000111100")
    lines.append("       sta %00111100")
    lines.append("       lda ($20)")
    lines.append("       adc $10,x")
    lines.append("middle:ldx $20,y")
    lines.append("       adc $3000,x")
    lines.append("       adc $3000,y")
    lines.append("       adc ($40,x) ")
    lines.append("       adc ($40),y")
    lines.append("       nop")
    lines.append("       nop")
    lines.append("label:")
    lines.append("       nop")
    lines.append("       org $3000")
    lines.append("vals:  db @10,$aa,8,$cc,$dd")
    lines.append("       be")
    lines.append("       dw $1020,$3040")
    lines.append("       le")
    lines.append("       dw $1020,$3040")
    lines.append("       ddw $1020,$3040")
    lines.append("       dqw $1020,$3040")
    lines.append("       adc start")
    lines.append("       adc ($40)")
    lines.append("end:   bpl vals")
    lines.append("       db $aa,$bb,$cc,$dd")
    lines.append("       nop")

    a = asm6502(debug=debug)
    a.assemble(lines)
