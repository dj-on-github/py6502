#!/usr/bin/env python

import asm6502
import dis6502
import sim6502


def main(debug=0):
    assembly_src = """
            org $0000
            JMP overthere 
bhaddr:     dw &brkhandler,$0102,&another,&labels ; insert address for brkhandler
l8addr:     dw &land8
overthere:	      
            LDA bhaddr 
            LDX 1 
            STA $FFFE 
            LDA bhaddr,x 
            STA $FFFF 
            LDA #$10 
            ADC #$55	    
            ADC $20	        
            ADC $20,X	    
            ADC $0002	        
            ADC $0010,X	    
            ADC $0008,Y	    
            ADC ($20,X)	    
            ADC ($20),Y	    
another:    ADC ($20)	    
            AND #$55	    
            AND $20	        
            AND $20,X	    
            AND $0004	        
labels:	        
            AND $0010,X	    
            AND $0012,Y	    
            AND ($20,X)	    
            AND ($20),Y	    
            AND ($20)	    
            ASL A	        
            ASL $20	        
            ASL $20,X	    
            ASL $2233	        
            ASL $2233,X	    	    
            CLC 
            BCC land1	    
            CLC 
land1:	        
            SEC 
            BCS land2	    
land2:	        
            BEQ land3	    
land3: 
            BIT #$55	    
            BIT $20	    
            BIT $20,X	    
            BIT $2233	    
            BIT $2233,X	    
            BMI land4	    
land4: 
            BNE land5	    
land5: 
            BPL land6	    
land6: 
            BRA land7	    
land7: 
            LDA l8addr
            STA $fffe
            LDX #$01
            LDA l8addr,x
            STA $ffff
            BRK	            
            BVC land8	    
land8: 
            BVS land9	    
land9: 
            CLC	            
            CLD	            
            CLI	            
            CLV	            
            CMP #$55	    
            CMP $20	        
            CMP $20	        
            CMP $2233	        
            CMP $2233,X	    
            CMP $2233,Y	    
            CMP ($20,X)	    
            CMP ($20),Y	    
            CMP ($20)	    
            CPX #$55	    
            CPX $20	        
            CPX $2233	        
            CPY #$55	    
            CPY $20	        
            CPY $2233	        
            DEA	            
            DEC A	            
            DEC $20	        
            DEC $20,X	    
            DEC $2233	        
            DEC $2233,X	    
            DEX	            
            DEY	            
            EOR #$55	    
            EOR $20	        
            EOR $20,X	    
            EOR $2233	        
            EOR $2233,X	    
            EOR $2233,Y	    
            EOR ($20,X)	    
            EOR ($20),Y	    
            EOR ($20)	    
            INA
            INC A	            
            INC $20	        
            INC $20,X	    
            INC $2233	        
            INC $2233,X	    
            INX	            
            INY	            
            JMP jmp1	        
jmpa:       dw &jmp2 
            dw &jmp3 
jmp1:
            JMP (jmpa)	    
jmp2:
            ldx #$02 
            JMP (jmpa,X)	    
jmp3:
            JSR jsrhandler    
            LDA #$55	    
            LDA $20	        
            LDA $20,X	    
            LDA $2233	        
            LDA $2233,X	    
            LDA $2233,Y	    
            LDA ($20,X)	    
            LDA ($20),Y	    
            LDA ($20)	    
            LDX #$55	    
            LDX $20	        
            LDX $20,Y	    
            LDX $2233	        
            LDX $2233,Y	    
            LDY #$55	    
            LDY $20	        
            LDY $20,X	    
            LDY $2233	        
            LDY $2233,X	    
            LSR A	            
            LSR $20	        
            LSR $20,X	        
            LSR $2233	        
            LSR $2233,X	    
            NOP	            
            ORA #$55	        
            ORA $20	        
            ORA $20,X	        
            ORA $2233	        
            ORA $2233,X	    
            ORA $2233,Y	    
            ORA ($20,X)	    
            ORA ($20),Y	    
            ORA ($20)	        
            PHA	            
            PHP               
            PLP               
            PLX	            
            PLY	            
            ROL A	            
            ROL $20	        
            ROL $20,X	        
            ROL $2233	        
            ROL $2233,X	    
            ROR A	            
            ROR $20	        
            ROR $20,X	        
            ROR $2233	        
            ROR $2233,X	    
            SBC #$55	        
            SBC $20 	        
            SBC $20,X	        
            SBC $2233	        
            SBC $2233,X	    
            SBC $2233,Y	    
            SBC ($20,X)	    
            SBC ($20),Y	    
            SBC ($20)	        
            SEC	            
            SED	            
            SEI	            
            STA $20	        
            STA $20,X	    
            STA $2233	        
            STA $2233,X	    
            STA $2233,Y	    
            STA ($20,X)	    
            STA ($20),Y	    
            STA ($20)	    
            STX $20	        
            STX $20,Y	    
            STX $2233	        
            STY $20	        
            STY $20,X	    
            STY $2233	        
            STZ $20	        
            STZ $20,X	    
            STZ $2233	        
            STZ $2233,X	    
            TAX	            
            TAY	            
            TRB $20	        
            TRB $2233	        
            TSB $20	        
            TSB $2233	        
            TSX	            
            TXA	            
            TXS	            
            TYA
; A remark
            JMP $1000 
jsrhandler:
            nop
            nop
            rts
brkhandler: 
            NOP 
            NOP 
            RTI 

    ORG $1000
start: lda #$50
       sta $5000 ; blah
       sta $25
       clc
       ROR A
       adc #%10011010
       sta %0101101000111100
       sta %00111100
       lda ($20)
       adc $10,x
middle:ldx $20,y
       adc $3000,x
       adc $3000,y
       adc ($40,x) 
       adc ($40),y
       jmp $2000
       nop
       nop
label:
       nop
       org $2000
vals:  db @10,$aa,8,$cc,$dd
       be
       dw $1020,$3040
       le
       dw $1020,$3040
       ddw $1020,$3040
       dqw $1020,$3040
       adc start
       adc ($40)
end:   bpl vals
       db $aa,$bb,$cc,$dd
       nop
       org $fffc
       db $00,$00,$00,$00
"""
    lines = assembly_src.splitlines()

    # Instantiate the assembler, assemble the code, grab the object_code
    a = asm6502.asm6502(debug=debug)
    (listing, symbols) = a.assemble(lines)

    for line in listing:
        print line
    print
    for line in symbols:
        print line
    print

    object_code = a.object_code[:]

    print
    # Output IntelHex
    print "IntelHex"
    a.print_intelhex()

    # Output Srecords
    print
    print "SRECORDS"
    a.print_srecords(01, 01, "ModuleName", "Comment")
    print

    # Instantiate the simulator
    s = sim6502.sim6502(object_code, symbols=a.symbols)

    # Instantiate the disassembler
    d = dis6502.dis6502(object_code, symbols=a.symbols)

    # How much space to accomodate the disassembly
    status_indent = 39

    # Reset the state of the simulator
    s.reset()

    print
    print "SIMULATION START"
    print
    # Print a header for the simulator/disassembler output
    print ("LABEL      " + "ADDR HEX      INSTR").ljust(status_indent) + " PC   A  X  Y  SP   Status"

    # Print the initial state
    print " ".ljust(status_indent) + " %04x %02x %02x %02x %04x %02x" % (s.pc, s.a, s.x, s.y, s.sp, s.cc)

    # Execute 200 instructions
    for i in xrange(200):
        # Disassemble the current instruction
        distxt, _ = d.disassemble_line(s.pc)

        # Execute that instruction
        s.execute()

        # Print out the disassembled instruction followed by the simulator state
        print distxt.ljust(status_indent) + " %04x %02x %02x %02x %04x %02x" % (s.pc, s.a, s.x, s.y, s.sp, s.cc)

    print s.memory_map.Dump()

if __name__ == "__main__":
    main()