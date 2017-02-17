#!/usr/bin/python
from asm6502 import asm6502
a = asm6502(debug=0)
lines = [' ORG $1000', ' NOP', ' LDA #$20', 'here: NOP', '  DB 10,11,12,13', '  RTS']
(listingtext,symboltext)=a.assemble(lines)
lines[0] = ' ORG $2000'
(listingtext2,symboltext2) = a.assemble(lines)

for line in listingtext:
    print line
print

for line in symboltext:
    print line

print
print "Second assemble at $2000"
for line in listingtext2:
    print line
print

for line in symboltext2:
    print line

a.print_object_code()

#results = a.assemble(lines)
#if results != None:
#    (listing_report,object_code_report,symbol_table_report) = results
