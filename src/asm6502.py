import re


class asm6502():
    def __init__(self, debug=0):
        # print "65C02 Assembler"
        self.debuglevel = debug
        self.text_of_lines = list()  # of strings
        self.lines = list()  # parsed lines (symbol, opcode, addrmode, value
        self.symbols = list()  # of (name,line#) tuples

        self.labeldict = dict()
        self.labellist = list()

        self.opcodelist = list()
        self.opcodedict = dict()

        self.addressmodes = dict()
        self.addressmmodelist = list()
        self.object_code = list()  # 64 K entries to cover whole memory map
        for i in xrange(0, 65536):
            self.object_code.append(-1)  # -1 indicate location not populated

        self.littleendian = True  # Use le and be directives to change this

        self.genopcodelist()  # generate the tables
        self.build_opcode_map()
        self.build_encoding_table()

        # some handy lookups
        self.decimal_digits = "0123456789"
        self.hex_digits = "abcdefABCDEF0123456789"
        self.octal_digits = "01234567"
        self.letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"

        self.allstuff = list()
        self.line = 1

    def clear_state(self):
        self.text_of_lines = list()  # of strings
        self.lines = list()  # parsed lines (symbol, opcode, addrmode, value
        self.symbols = list()  # of (name,line#) tuples

        self.labeldict = dict()
        self.labellist = list()

        self.opcodelist = list()
        self.opcodedict = dict()

        self.addressmodes = dict()
        self.addressmmodelist = list()

        self.littleendian = True  # Use le and be directives to change this

        self.allstuff = list()
        self.line = 1

    def info(self, linenumber, text):
        self.debug(1, "INFO: Line %d :%s" % (linenumber, text))

    def warning(self, linenumber, linetext, text):
        print "WARNING: Line %d :%s" % (linenumber, text)
        print "  " + linetext

    def strip_comments(self, thestring):
        self.debug(3, "string passed to strip_comments()=%s" % thestring)
        position = thestring.find(';')
        if (position == -1):
            return (thestring, "")
        else:
            return (thestring[:position].rstrip(), thestring[position:].rstrip())

    def debug(self, level=0, astring="No String Given"):
        if (level > self.debuglevel):
            pass
        else:
            print "   DEBUG(%d):%s" % (level, astring)

    # find a label at the front. Strip it and return the symbol
    def strip_label(self, thestring, linenumber):
        position = thestring.find(':')
        if (position == -1):
            return ("", thestring.strip())
        else:
            labelstr = thestring[:position].strip()
            returnstr = thestring[position + 1:].strip()
            position = labelstr.find(' ')
            if (position == -1):
                self.labeldict[labelstr] = linenumber
                self.labellist.append((linenumber, labelstr))
                self.debug(2, "Line %d Label %s found at line %d" % (linenumber, labelstr, linenumber))
                return (labelstr, returnstr)
            else:
                labelstr = labelstr[:position]
                self.warning(linenumber=linenumber, linetext=thestring,
                             text="More than one thing in the label field. Ignoring everything between the first space and the colon")
                self.labellist.append((linenum, labelstr))
                self.labeldict[labelstr] = linenum
                self.info(linenumber, text="Label %s found at line %d" % (labelstr, linenumber))
                return (labelstr, returnstr)

    # Consider the next thing an opcode
    # strip it and return the opcode with the remainder of the line
    def strip_opcode(self, thestring, linenumber):
        mystring = thestring.strip()
        noopcode = False
        noremainder = False
        if len(mystring) == 0:
            opcodestr = ""
            remainderstr = ""
            noopcode = True
            noremainder = True
        elif ' ' in mystring:
            position = thestring.find(' ')
            opcodestr = thestring[:position].strip()
            remainderstr = thestring[position + 1:].strip()
            noopcode = False
            noremainder = False
        else:
            opcodestr = mystring
            remainderstr = ""
            noopcode = False
            noremainder = True

        if noopcode:
            # print "no opcode or remainder"
            return (("", ""))
        else:
            if noremainder:
                # print "opcode %s but no remainder" % opcodestr
                return ((opcodestr, ""))
            else:
                # print "opcode %s with remainder %s" % (opcodestr,remainderstr)
                return ((opcodestr, remainderstr))

    def check_opcode(self, opcode_in, linenumber):
        opcode = opcode_in.lower()
        if opcode == "":
            self.debug(3, "check_opcode returning null")
            return None
        elif opcode in self.validopcodes:
            self.opcodelist.append((linenumber, opcode))
            self.debug(3, "check_opcode found %s in validopcodes" % opcode)
            return opcode
        elif opcode in self.validdirectives:
            self.opcodelist.append((linenumber, opcode))
            self.debug(3, "check_opcode found %s in validirectives" % opcode)
            return opcode
        else:
            self.debug(3, "check_opcode could not find opcode %s " % opcode)
            self.warning(linenumber=linenumber, linetext="", text="unknown opcode %s" % opcode)
            return None

    def identify_addressmodeformat(self, remainderstr, linenumber):
        # remove all whitespace
        thestring = remainderstr.replace(" ", "")
        if (thestring == ""):
            premode = "nothing"
            value = ""
        elif thestring[0] == "#":
            # It's immediate
            premode = "immediate"
            value = thestring[1:]
        elif (thestring == "a") or (thestring == "A"):
            premode = "accumulator"
            value = ""
        elif re.search("""^\((.*),[xX]\)$""", thestring):
            premode = "bracketedindexedx"
            b = re.search("""^\((.*),[xX]\)$""", thestring)
            value = b.group(1)
        elif re.search("""^\((.*)\),[yY]$""", thestring):
            premode = "bracketedcommay"
            b = re.search("""^\((.*)\),[yY]$""", thestring)
            value = b.group(1)
        elif re.search("""^(.*),[xX]$""", thestring):
            b = re.search("""^(.*),[xX]$""", thestring)
            value = b.group(1)
            premode = "numbercommax"
        elif re.search("""^(.*),[yY]$""", thestring):
            b = re.search("""^(.*),[yY]$""", thestring)
            value = b.group(1)
            premode = "numbercommay"
        elif (thestring[0] == '$') or (thestring[0] == '@') \
                or (thestring[0] == '%') \
                or (thestring[0] == '&') \
                or (thestring[0] in self.decimal_digits):
            premode = "number"
            value = thestring
        elif ((thestring[0] in self.letters) and ((thestring != "A") or (thestring != "a"))):
            premode = "number"
            value = thestring
        elif (thestring[0] == "+") or (thestring[0] == "-"):
            premode = "offset"
            value = thestring
        elif re.search("""^\((.*),[xX]\)$""", thestring):
            premode = "bracketedindexedx"
            b = re.search("""^\((.*),[xX]\)$""", thestring)
            value = b.group(1)
        elif re.search("""^\((.*)\),[yY]$""", thestring):
            premode = "bracketedcommay"
            b = re.search("""^\((.*)\),[yY]$""", thestring)
            value = b.group(1)
        elif re.search("""^\(.*\)$""", thestring):
            premode = "bracketed"
            value = thestring[1:-1]
        elif thestring[0] in self.letters:
            premode = "name"
            value = thestring
        else:
            self.warning(linenumber, linetext=remainderstr, text="Can\'t make sense of address mode %s" % remainderstr)
            premode = "nothing"
            value = ""

        self.debug(2, "premode = %s, value = %s" % (premode, value))
        # We've classified the basic formats in premode
        # some formats mean different things with different instructions
        # E.G. a number is an offset with a branch but absolute with a load
        # So we need to cross check the combinations of instruction with format
        # to derive the actual address mode and whether or not it is allowed.
        return (premode, value)

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
    #
    # names are numbers..
    def identify_addressmode(self, opcode, premode, value, linenumber):
        if (opcode in self.implicitopcodes) and (premode == "nothing"):
            return "implicit"
        if (opcode in self.immediateopcodes) and (premode == "immediate"):
            return "immediate"
        if (opcode in self.accumulatoropcodes) and (premode == "accumulator"):
            return "accumulator"
        if (opcode in self.accumulatoropcodes) and (premode == "nothing"):
            return "accumulator"
        if (opcode == "jmp"):
            if (premode == "bracketed"):
                return "absoluteindirect"
            if (premode == "bracketedindexedx"):
                return "absoluteindexedindirect"
            if (premode == "number"):
                return "absolute"
            return "UNDECIDED"

        if (opcode in self.zeropageopcodes) and (premode == "number") and (self.decode_value(value) != -1):
            if (self.decode_value(value) < 256):
                return "zeropage"
        if (opcode in self.relativeopcodes) and ((premode == "number") or (premode == "offset")):
            return "relative"
        if (opcode in self.absoluteopcodes) and (premode == "number"):
            return "absolute"
        self.debug(3, "IDENTIFY_ADDRESSMODE for zeropagex opcode=%s premode=%s" % (opcode, premode))
        if (opcode in self.zeropagexopcodes):
            self.debug(3, "opcode was in zeropagexopcodes")
        else:
            self.debug(3, "opcode wasnt in zeropagexopcodes")
        if (opcode in self.zeropagexopcodes) and (premode == "numbercommax"):
            self.debug(3, "IDENTIFY_ADDRESSMODE (opcode was in self.zeropagexopcodes) and (premode was== numbercommax)")
            self.debug(3, "IDENTIFY_ADDRESSMODE decoded value = 0x%x" % self.decode_value(value))
            if (self.decode_value(value) < 256):
                return "zeropagex"
        if (opcode in self.zeropageyopcodes) and (premode == "numbercommay"):
            if (self.decode_value(value) < 256):
                return "zeropagey"
        if (opcode in self.absolutexopcodes) and (premode == "numbercommax"):
            return "absolutex"
        if (opcode in self.absoluteyopcodes) and (premode == "numbercommay"):
            return "absolutey"
        if (opcode in self.zeropageyopcodes) and (premode == "numbercommay"):
            return "zeropagey"
        if (opcode in self.zeropageindexedindirectxopcodes) and (premode == "bracketedindexedx"):
            return "zeropageindexedindirectx"
        if (opcode in self.zeropageindexedindirectyopcodes) and (premode == "bracketedcommay"):
            return "zeropageindexedindirecty"
        if (opcode in self.zeropageindirectopcodes) and (premode == "bracketed"):
            if (self.decode_value(value) < 256):
                return "zeropageindirect"

        self.debug(2, "INFO: GOT TO END OF IDENTIFY_ADDRESSMODE: Line %d opcode:%s premode:%s" % (
        linenumber, opcode, premode))
        return "UNDECIDED"

    def decode_extraquadwords(self, linenumber, linetext, s):
        newstring = "["
        for c in s:
            if c == "$":
                newstring = newstring + "0x"
            elif c == "@":
                newstring = newstring + "0"
            else:
                newstring = newstring + c
        newstring = newstring + "]"
        thelist = eval(newstring)
        newlist = list()
        for i in thelist:
            if type(i) == int:
                a = i & 0x00ff
                b = (((i & 0x000000000000ff00) >> 8) & 0x000000ff)
                c = (((i & 0x0000000000ff0000) >> 16) & 0x000000ff)
                d = (((i & 0x00000000ff000000) >> 24) & 0x000000ff)
                e = (((i & 0x000000ff00000000) >> 32) & 0x000000ff)
                f = (((i & 0x0000ff0000000000) >> 40) & 0x000000ff)
                g = (((i & 0x00ff000000000000) >> 48) & 0x000000ff)
                h = (((i & 0xff00000000000000) >> 56) & 0x000000ff)
                if (self.littleendian == True):
                    newlist.append(a)
                    newlist.append(b)
                    newlist.append(c)
                    newlist.append(d)
                    newlist.append(e)
                    newlist.append(f)
                    newlist.append(g)
                    newlist.append(h)
                else:
                    newlist.append(g)
                    newlist.append(g)
                    newlist.append(f)
                    newlist.append(e)
                    newlist.append(d)
                    newlist.append(c)
                    newlist.append(b)
                    newlist.append(a)
            else:
                self.warning(linenumber, linetext, "Can't parse word string %s" % newstring)
                emptylist = list()
                return emptylist
        return newlist

    def decode_extradoublewords(self, linenumber, linetext, s):
        newstring = "["
        for c in s:
            if c == "$":
                newstring = newstring + "0x"
            elif c == "@":
                newstring = newstring + "0"
            else:
                newstring = newstring + c
        newstring = newstring + "]"
        thelist = eval(newstring)
        newlist = list()
        for i in thelist:
            if type(i) == int:
                a = i & 0x00ff
                b = (((i & 0x0000ff00) >> 8) & 0x000000ff)
                c = (((i & 0x00ff0000) >> 16) & 0x000000ff)
                d = (((i & 0xff000000) >> 24) & 0x000000ff)
                if (self.littleendian == True):
                    newlist.append(a)
                    newlist.append(b)
                    newlist.append(c)
                    newlist.append(d)
                else:
                    newlist.append(d)
                    newlist.append(c)
                    newlist.append(b)
                    newlist.append(a)
            else:
                self.warning(linenumber, linetext, "Can't parse word string %s" % newstring)
                emptylist = list()
                return emptylist
        return newlist

    # Just count the number of bytes without working out what they are
    def count_extrabytes(self, opcode, operand):
        count = len(operand.split(','))
        if opcode == "db":
            return count
        elif opcode == "dw":
            return count * 2
        elif opcode == "ddw":
            return count * 4
        elif opcode == "dqw":
            return count * 8
        else:
            return None

    def decode_extrawords(self, linenumber, linetext, s):
        csl = s.split(',')
        newlist = list()
        for theword in csl:
            if theword[0] == '&':
                label = theword[1:]
                value = self.symbols[label]
            elif theword[0] == '$':
                value = eval("0x" + theword[1:])
            elif theword[0] == '@':
                value = eval("0" + theword[1:])
            else:
                value = eval(theword)

            if type(value) == int:
                a = value & 0x00ff
                b = (((value & 0xff00) >> 8) & 0x00ff)
                if (self.littleendian == True):
                    newlist.append(a)
                    newlist.append(b)
                else:
                    newlist.append(b)
                    newlist.append(a)
            else:
                self.warning(linenumber, linetext, "Can't parse word string %s" % newstring)
                emptylist = list()
                return emptylist
        return newlist

    def decode_extrabytes(self, linenumber, linetext, s):
        newstring = "["

        for c in s:
            if c == "$":
                newstring = newstring + "0x"
            elif c == "@":
                newstring = newstring + "0"
            else:
                newstring = newstring + c
        newstring = newstring + "]"

        # Now parse the list
        thelist = eval(newstring)
        newlist = list()
        for i in thelist:
            if type(i) == int:
                newlist.append(i)
            else:
                self.warning(linenumber, linetext, "Can't parse byte string %s" % newstring)
                emptylist = list()
                return emptylist
        return newlist

    def decode_value(self, s):
        if (s[0] == '$'):
            ns = int(s[1:], 16)
            return ns

        if (s[0] == '@'):
            ns = int(s[1:], 8)
            return ns

        if (s[0] == '%'):
            ns = int(s[1:], 2)
            return ns

        if (s[0] in self.decimal_digits):
            ns = int(s)
            return ns

        return (-1)

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
    def genopcodelist(self):

        self.modeswithlowbytevalue = \
            ["immediate", "absolute", "zeropage", "absolutex", "absolutey", \
             "zeropagex", "zeropagey", "zeropageindexedindirectx", "zeropageindexedindirecty" \
                                                                   "absoluteindexedindirect", "zeropageindirect",
             "absoluteindirect"]
        self.modeswithhighbytevalue = \
            ["absolute", "absolutex", "absolutey", \
             "absoluteindexedindirect", "absoluteindirect"]

        self.validdirectives = \
            ["db", "dw", "ddw", "dqw", "str", "org", "le", "be"]

        self.validopcodes = \
            ["adc", "and", "asl", "bcc", "bcs", "beq", "bit", "bmi", "bne", \
             "bpl", "bra", "brk", "bvc", "bvs", "clc", "cld", "cli", "clv", \
             "cmp", "cpx", "cpy", "dea", "dec", "dex", "dey", "eor", "inc", "ina", "inx", \
             "iny", "jmp", "jsr", "lda", "ldx", "ldy", "lsr", "nop", "ora", \
             "pha", "php", "phx", "phy", "pla", "plp", "plx", "ply", "rol", \
             "ror", "rti", "rts", "sbc", "sec", "sed", "sei", "sta", "stx", \
             "sty", "stz", "tax", "tay", "trb", "tsb", "tsx", "txa", "txs", \
             "tya"]

        self.implicitopcodes = \
            ["brk", "clc", "cld", "cli", "clv", "dex", "dey", "inx", "iny", "nop", \
             "pha", "php", "phx", "phy", "pla", "plp", "plx", "ply", "rti", "rts", \
             "sec", "sed", "sei", "tax", "tay", "trb", "tsb", "tsx", "txa", "txs", \
             "tya"]

        self.immediateopcodes = \
            ["adc", "and", "bit", "cmp", "cpx", "cpy", "eor", "lda", "ldx", \
             "ldy", "ora", "sbc"]

        self.accumulatoropcodes = \
            ["asl", "dea", "dec", "ina", "inc", "lsr", "rol", "ror"]

        self.zeropageopcodes = \
            ["adc", "and", "asl", "bit", "cmp", "cpx", "cpy", "dec", "eor", "inc", \
             "lda", "ldx", "ldy", "lsr", "ora", "rol", "ror", "sbc", "sta", "stx", \
             "sty", "stz", "trb", "tsb"]

        self.absoluteopcodes = \
            ["adc", "and", "asl", "bit", "cmp", "cpx", "cpy", "dec", "eor", "inc", \
             "jmp", "jsr", "lda", "ldx", "ldy", "lsr", "ora", "rol", "ror", "sbc", \
             "sta", "stx", "sty", "stz", "trb", "tsb"]

        self.absolutexopcodes = \
            ["adc", "and", "asl", "bit", "cmp", "dec", "eor", "inc", \
             "lda", "lsr", "ora", "rol", "ror", "sbc", \
             "sta", "stz", "ldy"]

        self.absoluteyopcodes = \
            ["adc", "and", "cmp", "eor", \
             "lda", "ldx", "ora", "sbc", "sta"]

        self.zeropagexopcodes = \
            ["adc", "and", "cmp", "eor", "lda", "dec", "bit", "asl", "ldy", \
             "ora", "sbc", "sta", "sty", "ror", "rol", "lsr", "inc", "stz"]

        self.zeropageyopcodes = \
            ["ldx", "stx"]

        self.relativeopcodes = \
            ["bmi", "bne", "bpl", "bra", "bvc", "bvs", "bcc", "bcs", "beq"]

        self.zeropageindexedindirectxopcodes = \
            ["adc", "and", "cmp", "eor", "lda", "ora", "sbc", "sta"]

        self.zeropageindexedindirectyopcodes = \
            ["adc", "and", "cmp", "eor", "lda", "ora", "sbc", "sta"]

        self.zeropageindirectopcodes = \
            ["adc", "and", "cmp", "eor", "lda", "ora", "sbc", "sta"]

    def build_opcode_map(self):
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

    def build_encoding_table(self):
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

        self.otherhexcodes = dict()  # Make another list for synonyms
        for hexval in xrange(256):
            self.otherhexcodes[hexval] = ("", "")
        self.otherhexcodes[0x1A] = ("inc", "accumulator")
        self.otherhexcodes[0x3A] = ("dec", "accumulator")
        self.otherhexcodes[0x90] = ("blt", "relative")
        self.otherhexcodes[0xB0] = ("bge", "relative")

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
        if addrmode == "implicit":
            return 0
        if addrmode == "immediate":
            return 1
        if addrmode == "accumulator":
            return 0
        if addrmode == "absolute":
            return 2
        if addrmode == "zeropage":
            return 1
        if addrmode == "absolutex":
            return 2
        if addrmode == "absolutey":
            return 2
        if addrmode == "zeropagex":
            return 1
        if addrmode == "zeropagey":
            return 1
        if addrmode == "relative":
            return 1
        if addrmode == "zeropageindexedindirectx":
            return 1
        if addrmode == "zeropageindexedindirecty":
            return 1
        if addrmode == "absoluteindexedindirect":
            return 2
        if addrmode == "zeropageindirect":
            return 1
        if addrmode == "absoluteindirect":
            return 2

    def firstpasstext(self, thetuple):
        (offset, linenumber, labelstring, opcode_val, lowbyte, highbyte, opcode, operand, addressmode, value, comment,
         extrabytes, num_extrabytes, linetext) = thetuple
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
         extrabytes, num_extrabytes, linetext) = thetuple
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
        if (opcode == "db" or opcode == "dw" or opcode == "ddw" or opcode == "dqw"):
            num_extrabytes = self.count_extrabytes(opcode, operand)
        else:
            num_extrabytes = None

        # We are moving the extrabytes parsing to pass 3, so we can
        # add label addresses into DWs and have the label defined when we need it.
        #
        # if (opcode=="db") and (operand != None) and (len(operand) > 0):
        #    extrabytes = self.decode_extrabytes(linenumber, thestring, operand)
        # elif (opcode=="dw") and (operand != None) and (len(operand) > 0):
        #    extrabytes = self.decode_extrawords(linenumber, thestring, operand)
        # elif (opcode=="ddw") and (operand != None) and (len(operand) > 0):
        #    extrabytes = self.decode_extradoublewords(linenumber, thestring, operand)
        # elif (opcode=="dqw") and (operand != None) and (len(operand) > 0):
        #    extrabytes = self.decode_extraquadwords(linenumber, thestring, operand)

        linetext = thestring
        thetuple = (
        offset, linenumber, labelstring, opcode_val, lowbyte, highbyte, opcode, operand, addressmode, value, comment,
        extrabytes, num_extrabytes, linetext)
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
             comment, extrabytes, num_extrabytes, linetext) = tuple
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
            # self.address += len(extrabytes)
            if type(num_extrabytes) == int:
                self.address += num_extrabytes

            # If there is a label, we now know its address. So store it in the symbol table
            if (labelstring != None) and (labelstring != ""):
                self.symbols[labelstring] = offset
            tuple = (
            offset, linenumber, labelstring, opcode_val, lowbyte, highbyte, opcode, operand, addressmode, value,
            comment, extrabytes, num_extrabytes, linetext)
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
        self.instruction_map = [None] * 65536  # A map for where the instructions are so the debugger can know
        # where the start byte of real instructions are.
        # The opcode is entered in the location
        # non instruction locations are set to None.

        for i in xrange(len(self.allstuff)):
            tuple = self.allstuff[i]
            (offset, linenumber, labelstring, opcode_val, lowbyte, highbyte, opcode, operand, addressmode, value,
             comment, extrabytes, num_extrabytes, linetext) = tuple

            # Compute the offset for relative branches
            if (lowbyte == -1) and (addressmode == "relative"):
                destination = self.symbols[value]
                start = offset + 2  # Delta is relative to the first byte after the branch instruction
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

            # populate the extrabytes lists                
            if (opcode == "db") and (operand != None) and (len(operand) > 0):
                extrabytes = self.decode_extrabytes(linenumber, linetext, operand)
            elif (opcode == "dw") and (operand != None) and (len(operand) > 0):
                extrabytes = self.decode_extrawords(linenumber, linetext, operand)
            elif (opcode == "ddw") and (operand != None) and (len(operand) > 0):
                extrabytes = self.decode_extradoublewords(linenumber, linetext, operand)
            elif (opcode == "dqw") and (operand != None) and (len(operand) > 0):
                extrabytes = self.decode_extraquadwords(linenumber, linetext, operand)

            tuple = (
            offset, linenumber, labelstring, opcode_val, lowbyte, highbyte, opcode, operand, addressmode, value,
            comment, extrabytes, num_extrabytes, linetext)
            self.allstuff[i] = tuple
            line = self.secondpasstext(tuple)
            self.listing.append(line)

            # Fill in the instruction map
            # This makes it easy for an interactive disassembler to 
            # know what is instruction code and what is data.
            # By signaling which are operand bytes, it's easy to 
            # disassemble backwards from the current position

            #   None                    = Not an instruction or operand
            #   positive numbers < 256  = an opcode
            #   -1                      = first operand byte
            #   -2                      = second operand bytecount
            if opcode_val != None:
                self.instruction_map[offset] = opcode_val
                if self.addrmode_length(addressmode) > 0:
                    self.instruction_map[offset + 1] = -1  # -1 signals the first operand byte
                if self.addrmode_length(addressmode) > 1:
                    self.instruction_map[offset + 2] = -2  # -2 signals the second operand byte

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

        listingtext = list()
        listingtext.append("LISTING")
        listingtext += self.listing

        symboltext = list()
        symboltext.append("SYMBOL TABLE")
        for label in self.symbols:
            offset = self.symbols[label]
            astring = (("%s" % label).ljust(10)) + (" = " + "$%04X" % offset)
            symboltext.append(astring)

        # print "LISTING"
        # for i in self.listing:
        #    print i
        #
        # print
        # print "SYMBOL TABLE"
        # for label in self.symbols:
        #    offset = self.symbols[label]
        #    astring=(("%s" % label).ljust(10)) +(" = "+"$%04X" % offset)
        #    print astring
        #    
        # print
        # self.print_object_code()
        return (listingtext, symboltext)

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

    def srecord_checksum(self, astring):
        checksum = 0
        for i in xrange(len(astring) / 2):
            hexpair = "0x" + astring[(i * 2):(i * 2) + 2]
            bytevalue = eval(hexpair)
            checksum = checksum + bytevalue
        checksum = checksum & 0x0ff
        checksum = checksum ^ 0xff
        return "%02x" % checksum

    def str2asciibytes(self, astring):
        ascii = ""
        for c in astring:
            num = ord(c)
            ascii += "%02x" % num
        return ascii

    def srecords(self, version, revision, module_name, comment):
        # print "S19 FORMAT OUTPUT"
        # print
        i = 0
        astring = ""
        theoutput = list()
        bytelist = list()
        bytecount = 0
        address = 0

        # Make the Header Record
        if len(module_name) > 20:
            modname_trimmed = module_name[:20]
        else:
            modname_trimmed = module_name.ljust(20)

        if (len(comment) > 36):
            comment_trimmed = comment[:36]
        else:
            comment_trimmed = comment

        text = "%02x%02x" % (version, revision)
        text = text + self.str2asciibytes(module_name + comment)
        addr = "0000"
        countedpart = addr + text
        length = "%02x" % (len(addr + text))
        checksum = self.srecord_checksum(length + addr + text)
        header = "S0" + length + addr + text + checksum
        theoutput.append(header)

        last_addr = 0
        while (i < 65536):
            if self.object_code[i] != -1:
                address = i
                values = list()
                values.append(self.object_code[i])
                localrun = 1
                i = i + 1
                if (i < 65536):
                    nextval = self.object_code[i]
                    while (nextval != -1) and (localrun < 16):
                        values.append(nextval)
                        last_addr = i
                        i = i + 1
                        localrun = localrun + 1
                        if (i < 65536):
                            nextval = self.object_code[i]
                        else:
                            nextval = -1

                    # We reached 16 bytes, or hit the end or hit -1 So
                    # Output the data record
                    data = ""
                    for value in values:
                        data = ("%02X" % value) + data

                    addr = "%02x%02x" % (((address >> 8) & 0xff), (address & 0xff))
                    length = "%02x" % (len(addr + text))
                    checksum = self.srecord_checksum(length + addr + data)
                    record = "S1" + length + addr + data + checksum
                    theoutput.append(record)

            else:
                i = i + 1

        # Output the count
        record_count = len(theoutput)
        data = "%02x%02x" % (((record_count >> 8) & 0xff), (record_count & 0xff))
        length = "03"
        checksum = self.srecord_checksum(length + data)
        record = "S5" + length + data + checksum
        theoutput.append(record)

        # Output the terminator
        length = "03"
        addr = "%02x%02x" % (((last_addr >> 8) & 0xff), (last_addr & 0xff))
        checksum = self.srecord_checksum(length + addr)
        record = "S9" + length + addr + checksum
        theoutput.append(record)

        return (theoutput)

    def print_srecords(self, version, revision, module_name, comment):
        lines = self.srecords(version, revision, module_name, comment)
        for line in lines:
            print line

    def intelhex(self):
        # print "INTEL HEX FORMAT OUTPUT"
        # print
        # Insert a star when there are empty spots in the memory map
        i = 0
        astring = ""
        theoutput = list()
        bytelist = list()
        bytecount = 0
        address = 0

        datarecord = "00"
        eofrecord = ":00000001FF"

        while (i < 65536):
            if self.object_code[i] != -1:
                address = i
                values = list()
                values.append(self.object_code[i])
                localrun = 1
                i = i + 1
                if (i < 65536):
                    nextval = self.object_code[i]
                    while (nextval != -1) and (localrun < 16):
                        values.append(nextval)
                        i = i + 1
                        localrun = localrun + 1
                        if (i < 65536):
                            nextval = self.object_code[i]
                        else:
                            nextval = -1
                    length = len(values)
                    astring = ":%02X%04x" % (length, address)
                    astring += datarecord
                    for value in values:
                        astring += "%02X" % value
                    theoutput.append(astring)

                else:
                    length = len(values)
                    astring = "addr=%04x  len=%02x data=" % (address, length)
                    for value in values:
                        astring += "%02X" % value
                    theoutput.append(astring)
            else:
                i = i + 1
        theoutput.append(eofrecord)
        return theoutput

    def print_intelhex(self):
        lines = self.intelhex()
        for line in lines:
            print line

    # returns entire 64K memory as hex in the form of 64 bytes per line.
    def hex(self, noaddress=False):
        # print "HEX FORMAT OUTPUT"
        # print
        theoutput = list()

        for i in xrange(1024):
            addr = 64 * i

            # Prepend with an address field, or not if not desired
            if noaddress:
                line = ""
            else:
                line = "%04x:" % addr

            # add the bytes as hex to the line    
            for j in xrange(64):
                val = self.object_code[(i * 64) + j]

                # Range check the bytes
                if val < 0:
                    val = 0
                if val > 255:
                    val = 255

                line = line + ("%02x" % val)
            theoutput.append(line)
        return theoutput

    def print_hex(self):
        lines = self.hex()
        for line in lines:
            print line
