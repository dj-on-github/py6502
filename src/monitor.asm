; ---------------------------------------------------------------
; Simple monitor for the 6502 simulator.
; Keyboard: Apple II style at $C000 (data+strobe) / $C010 (clear strobe).
; Screen:   ATASCII 40x32 text screen at $0800.
;
; At the "monitor:" prompt (numbers are hexadecimal):
;   g <addr>             jump to <addr> and run (returns here on RTS)
;   c <addr> <byte..>    change memory: write the given hex bytes from <addr>
;   r <addr> <size>      read: dump <size> bytes starting at <addr>
;   d <addr> <count>     disassemble <count> instructions from <addr>
;   h                    help: list the commands
; The input line may be edited with backspace / delete.
; ---------------------------------------------------------------

; ---- zero page variables ----
curlo:   EQU $00
curhi:   EQU $01
ptrlo:   EQU $02
ptrhi:   EQU $03
vallo:   EQU $04
valhi:   EQU $05
col:     EQU $06
ktemp:   EQU $07
cntlo:   EQU $09
cnthi:   EQU $0a
srclo:   EQU $0b
srchi:   EQU $0c
dstlo:   EQU $0d
dsthi:   EQU $0e
govlo:   EQU $10
govhi:   EQU $11
tmp:     EQU $12
scntlo:  EQU $16
scnthi:  EQU $17
pidx:    EQU $18
opcode:  EQU $19
mode:    EQU $1a
op1:     EQU $1b
op2:     EQU $1c
ilen:    EQU $1d
mc0:     EQU $1e
mc1:     EQU $1f
mc2:     EQU $20

; ---- constants ----
kbd:     EQU $c000
kbdstrb: EQU $c010
linbuf:  EQU $0300

         ORG $1000

start:   jsr clrscr
mainloop:
         jsr prompt
         jsr readline
         jsr parseline
         jmp mainloop

; ---------- parse and dispatch a command line ----------
parseline:
         lda #$00
         sta pidx
         jsr skipspaces
         ldy pidx
         lda linbuf,y
         beq pldone
         and #$df              ; force upper case
         cmp #$47              ; 'G'
         beq plg
         cmp #$43              ; 'C'
         beq plc
         cmp #$52              ; 'R'
         beq plr
         cmp #$44              ; 'D'
         beq pld
         cmp #$48              ; 'H'
         beq plh
         jsr printerr
pldone:  rts

plh:     jsr printhelp
         rts

pld:     inc pidx
         jsr skipspaces
         jsr parsehex
         lda vallo
         sta ptrlo
         lda valhi
         sta ptrhi
         jsr skipspaces
         jsr parsehex
         lda vallo
         sta cntlo
         lda valhi
         sta cnthi
         jsr disasmblk
         rts

plg:     inc pidx
         jsr skipspaces
         jsr parsehex
         lda vallo
         sta govlo
         lda valhi
         sta govhi
         jsr govector
         rts

plc:     inc pidx
         jsr skipspaces
         jsr parsehex
         lda vallo
         sta ptrlo
         lda valhi
         sta ptrhi
cbytes:  jsr skipspaces
         ldy pidx
         lda linbuf,y
         beq cdone
         jsr hexval
         bcc cdone
         jsr parsehex
         ldy #$00
         lda vallo
         sta (ptrlo),y
         inc ptrlo
         bne cbytes
         inc ptrhi
         jmp cbytes
cdone:   rts

plr:     inc pidx
         jsr skipspaces
         jsr parsehex
         lda vallo
         sta ptrlo
         lda valhi
         sta ptrhi
         jsr skipspaces
         jsr parsehex
         lda vallo
         sta cntlo
         lda valhi
         sta cnthi
         jsr dumpmem
         rts

govector:
         jmp (govlo)

; ---------- dump memory: r command ----------
dumpmem:
dmline:  lda cntlo
         ora cnthi
         beq dmdone
         jsr printaddr
         ldx #$08
dmbyte:  lda cntlo
         ora cnthi
         beq dmeol
         ldy #$00
         lda (ptrlo),y
         jsr printhex
         lda #$20
         jsr putchar
         inc ptrlo
         bne dmb2
         inc ptrhi
dmb2:    jsr deccnt
         dex
         bne dmbyte
dmeol:   lda #$0d
         jsr putchar
         jmp dmline
dmdone:  rts

; ---------- disassemble: d command ----------
disasmblk:
dnext:   lda cntlo
         ora cnthi
         beq ddone
         jsr disone
         jsr deccnt
         jmp dnext
ddone:   rts

disone:  jsr printaddr           ; "PPPP: "
         ldy #$00
         lda (ptrlo),y
         sta opcode
         ldy #$01
         lda (ptrlo),y
         sta op1
         ldy #$02
         lda (ptrlo),y
         sta op2
         ; print 3-char mnemonic
         ldx opcode
         lda opmnetab,x
         sta tmp
         asl a
         clc
         adc tmp                 ; A = index * 3
         tay
         lda mnemtab,y
         sta mc0
         iny
         lda mnemtab,y
         sta mc1
         iny
         lda mnemtab,y
         sta mc2
         lda mc0
         jsr putchar
         lda mc1
         jsr putchar
         lda mc2
         jsr putchar
         lda #$20
         jsr putchar
         ; operand
         ldx opcode
         lda opmodetab,x
         sta mode
         jsr proper
         lda #$0d
         jsr putchar
         ; advance ptr by ilen
         clc
         lda ilen
         adc ptrlo
         sta ptrlo
         lda ptrhi
         adc #$00
         sta ptrhi
         rts

; ---- print the operand for the current opcode/mode ----
proper:  ldx mode
         lda lentab,x
         sta ilen
         lda mode
         cmp #$01
         bne pn1
         jmp po_acc
pn1:     cmp #$02
         bne pn2
         jmp po_imm
pn2:     cmp #$03
         bne pn3
         jmp po_zp
pn3:     cmp #$04
         bne pn4
         jmp po_zpx
pn4:     cmp #$05
         bne pn5
         jmp po_zpy
pn5:     cmp #$06
         bne pn6
         jmp po_abs
pn6:     cmp #$07
         bne pn7
         jmp po_absx
pn7:     cmp #$08
         bne pn8
         jmp po_absy
pn8:     cmp #$09
         bne pn9
         jmp po_ind
pn9:     cmp #$0a
         bne pn10
         jmp po_indx
pn10:    cmp #$0b
         bne pn11
         jmp po_indy
pn11:    cmp #$0c
         bne pn12
         jmp po_rel
pn12:    cmp #$0d
         bne po_imp
         jmp po_ill
po_imp:  rts                     ; mode 0 = implied: no operand

po_acc:  lda #$41                ; 'A'
         jsr putchar
         rts
po_imm:  lda #$23                ; '#'
         jsr putchar
         jsr podol
         lda op1
         jsr printhex
         rts
po_zp:   jsr podol
         lda op1
         jsr printhex
         rts
po_zpx:  jsr podol
         lda op1
         jsr printhex
         jsr pocx
         rts
po_zpy:  jsr podol
         lda op1
         jsr printhex
         jsr pocy
         rts
po_abs:  jsr poword
         rts
po_absx: jsr poword
         jsr pocx
         rts
po_absy: jsr poword
         jsr pocy
         rts
po_ind:  lda #$28                ; '('
         jsr putchar
         jsr poword
         lda #$29                ; ')'
         jsr putchar
         rts
po_indx: lda #$28
         jsr putchar
         jsr podol
         lda op1
         jsr printhex
         jsr pocx
         lda #$29
         jsr putchar
         rts
po_indy: lda #$28
         jsr putchar
         jsr podol
         lda op1
         jsr printhex
         lda #$29
         jsr putchar
         jsr pocy
         rts
po_rel:  clc                     ; target = ptr + 2 + signed(op1)
         lda ptrlo
         adc #$02
         sta vallo
         lda ptrhi
         adc #$00
         sta valhi
         ldx #$00
         lda op1
         cmp #$80
         bcc porp
         ldx #$ff
porp:    stx tmp
         clc
         lda vallo
         adc op1
         sta vallo
         lda valhi
         adc tmp
         sta valhi
         jsr podol
         lda valhi
         jsr printhex
         lda vallo
         jsr printhex
         rts
po_ill:  jsr podol
         lda opcode
         jsr printhex
         rts

poword:  jsr podol
         lda op2
         jsr printhex
         lda op1
         jsr printhex
         rts
podol:   lda #$24                ; '$'
         jsr putchar
         rts
pocx:    lda #$2c                ; ','
         jsr putchar
         lda #$58                ; 'X'
         jsr putchar
         rts
pocy:    lda #$2c
         jsr putchar
         lda #$59                ; 'Y'
         jsr putchar
         rts

; ---------- 16-bit decrement of the byte count ----------
deccnt:  lda cntlo
         sec
         sbc #$01
         sta cntlo
         lda cnthi
         sbc #$00
         sta cnthi
         rts

printaddr:
         lda ptrhi
         jsr printhex
         lda ptrlo
         jsr printhex
         lda #$3a                ; ':'
         jsr putchar
         lda #$20
         jsr putchar
         rts

; ---------- read one line into linbuf (echoed, editable) ----------
readline:
         ldx #$00
rlloop:  jsr getkey
         cmp #$0d
         beq rlcr
         cmp #$08                ; backspace
         beq rlbs
         cmp #$7f                ; delete
         beq rlbs
         cmp #$20                ; ignore other control codes
         bcc rlloop
         sta linbuf,x
         jsr putchar
         inx
         cpx #$3e
         bcc rlloop
         jmp rlcr
rlbs:    cpx #$00
         beq rlloop              ; empty line
         lda col
         beq rlloop              ; at line start: don't wrap back
         dex
         jsr backspace
         jmp rlloop
rlcr:    lda #$00
         sta linbuf,x
         lda #$0d
         jsr putchar
         rts

; erase the character to the left of the cursor
backspace:
         lda curlo
         bne bs1
         dec curhi
bs1:     dec curlo
         dec col
         ldy #$00
         lda #$20
         sta (curlo),y
         rts

; ---------- print the prompt ----------
prompt:  ldx #$00
prl:     lda promptmsg,x
         beq prdone
         jsr putchar
         inx
         jmp prl
prdone:  rts

; ---------- print the help text ----------
printhelp:
         ldx #$00
hlp:     lda helptext,x
         beq hlpdone
         jsr putchar
         inx
         jmp hlp
hlpdone: rts

printerr:
         lda #$3f                ; '?'
         jsr putchar
         lda #$0d
         jsr putchar
         rts

; ---------- keyboard ----------
getkey:  lda kbd
         bpl getkey
         sta ktemp
         lda kbdstrb
         lda ktemp
         and #$7f
         rts

; ---------- skip spaces in linbuf ----------
skipspaces:
         ldy pidx
         lda linbuf,y
         cmp #$20
         bne ssdone
         inc pidx
         jmp skipspaces
ssdone:  rts

; ---------- parse hex number from linbuf into vallo/valhi ----------
parsehex:
         lda #$00
         sta vallo
         sta valhi
phloop:  ldy pidx
         lda linbuf,y
         jsr hexval
         bcc phdone
         sta tmp
         asl vallo
         rol valhi
         asl vallo
         rol valhi
         asl vallo
         rol valhi
         asl vallo
         rol valhi
         lda vallo
         ora tmp
         sta vallo
         inc pidx
         jmp phloop
phdone:  rts

hexval:  cmp #$30
         bcc hvbad
         cmp #$3a
         bcc hvdig
         cmp #$41
         bcc hvbad
         cmp #$47
         bcc hvup
         cmp #$61
         bcc hvbad
         cmp #$67
         bcc hvlo
hvbad:   clc
         rts
hvdig:   sec
         sbc #$30
         sec
         rts
hvup:    sec
         sbc #$37
         sec
         rts
hvlo:    sec
         sbc #$57
         sec
         rts

; ---------- print A as two hex digits ----------
printhex:
         pha
         lsr a
         lsr a
         lsr a
         lsr a
         jsr printnib
         pla
         and #$0f
         jsr printnib
         rts
printnib:
         cmp #$0a
         bcc pndig
         clc
         adc #$37
         jmp pnout
pndig:   clc
         adc #$30
pnout:   jsr putchar
         rts

; ---------- output one char to the screen ----------
putchar: cmp #$0d
         bne pcprint
         jsr newline
         rts
pcprint: ldy #$00
         sta (curlo),y
         inc curlo
         bne pcnz
         inc curhi
pcnz:    inc col
         lda col
         cmp #$28
         bcc pcret
         jsr newline
pcret:   rts

newline: lda #$28
         sec
         sbc col
         clc
         adc curlo
         sta curlo
         lda curhi
         adc #$00
         sta curhi
         lda #$00
         sta col
         lda curhi
         cmp #$0d
         bcc nlret
         jsr scroll
nlret:   rts

scroll:  lda #$28
         sta srclo
         lda #$08
         sta srchi
         lda #$00
         sta dstlo
         lda #$08
         sta dsthi
         lda #$d8
         sta scntlo
         lda #$04
         sta scnthi
scloop:  ldy #$00
         lda (srclo),y
         sta (dstlo),y
         inc srclo
         bne scs2
         inc srchi
scs2:    inc dstlo
         bne scs3
         inc dsthi
scs3:    lda scntlo
         sec
         sbc #$01
         sta scntlo
         lda scnthi
         sbc #$00
         sta scnthi
         lda scntlo
         ora scnthi
         bne scloop
         lda #$d8
         sta dstlo
         lda #$0c
         sta dsthi
         ldy #$00
         lda #$20
scclr:   sta (dstlo),y
         iny
         cpy #$28
         bne scclr
         lda #$d8
         sta curlo
         lda #$0c
         sta curhi
         lda #$00
         sta col
         rts

clrscr:  lda #$00
         sta ptrlo
         lda #$08
         sta ptrhi
         ldx #$05
         lda #$20
csp:     ldy #$00
csb:     sta (ptrlo),y
         iny
         bne csb
         inc ptrhi
         dex
         bne csp
         lda #$00
         sta curlo
         sta col
         lda #$08
         sta curhi
         rts

promptmsg:
         DB "monitor:", $00

helptext:
         DB "commands:", $0d
         DB "g addr          run at addr", $0d
         DB "c addr bb bb    change memory", $0d
         DB "r addr size     read memory", $0d
         DB "d addr count    disassemble", $0d
         DB "h               this help", $0d
         DB $00

mnemtab:
         DB "ADCANDASLBCCBCSBEQBITBMIBNEBPLBRKBVCBVSCLCCLDCLICLVCMPCPXCPYDECDEXDEYEORINCINXINYJMPJSRLDALDXLDYLSRNOPORAPHAPHPPLAPLPROLRORRTIRTSSBCSECSEDSEISTASTXSTYTAXTAYTSXTXATXSTYA???"
opmnetab:
         DB $0A, $22, $38, $38, $38, $22, $02, $38, $24, $22, $02, $38, $38, $22, $02, $38
         DB $09, $22, $38, $38, $38, $22, $02, $38, $0D, $22, $38, $38, $38, $22, $02, $38
         DB $1C, $01, $38, $38, $06, $01, $27, $38, $26, $01, $27, $38, $06, $01, $27, $38
         DB $07, $01, $38, $38, $38, $01, $27, $38, $2C, $01, $38, $38, $38, $01, $27, $38
         DB $29, $17, $38, $38, $38, $17, $20, $38, $23, $17, $20, $38, $1B, $17, $20, $38
         DB $0B, $17, $38, $38, $38, $17, $20, $38, $0F, $17, $38, $38, $38, $17, $20, $38
         DB $2A, $00, $38, $38, $38, $00, $28, $38, $25, $00, $28, $38, $1B, $00, $28, $38
         DB $0C, $00, $38, $38, $38, $00, $28, $38, $2E, $00, $38, $38, $38, $00, $28, $38
         DB $38, $2F, $38, $38, $31, $2F, $30, $38, $16, $38, $35, $38, $31, $2F, $30, $38
         DB $03, $2F, $38, $38, $31, $2F, $30, $38, $37, $2F, $36, $38, $38, $2F, $38, $38
         DB $1F, $1D, $1E, $38, $1F, $1D, $1E, $38, $33, $1D, $32, $38, $1F, $1D, $1E, $38
         DB $04, $1D, $38, $38, $1F, $1D, $1E, $38, $10, $1D, $34, $38, $1F, $1D, $1E, $38
         DB $13, $11, $38, $38, $13, $11, $14, $38, $1A, $11, $15, $38, $13, $11, $14, $38
         DB $08, $11, $38, $38, $38, $11, $14, $38, $0E, $11, $38, $38, $38, $11, $14, $38
         DB $12, $2B, $38, $38, $12, $2B, $18, $38, $19, $2B, $21, $38, $12, $2B, $18, $38
         DB $05, $2B, $38, $38, $38, $2B, $18, $38, $2D, $2B, $38, $38, $38, $2B, $18, $38
opmodetab:
         DB $00, $0A, $0D, $0D, $0D, $03, $03, $0D, $00, $02, $01, $0D, $0D, $06, $06, $0D
         DB $0C, $0B, $0D, $0D, $0D, $04, $04, $0D, $00, $08, $0D, $0D, $0D, $07, $07, $0D
         DB $06, $0A, $0D, $0D, $03, $03, $03, $0D, $00, $02, $01, $0D, $06, $06, $06, $0D
         DB $0C, $0B, $0D, $0D, $0D, $04, $04, $0D, $00, $08, $0D, $0D, $0D, $07, $07, $0D
         DB $00, $0A, $0D, $0D, $0D, $03, $03, $0D, $00, $02, $01, $0D, $06, $06, $06, $0D
         DB $0C, $0B, $0D, $0D, $0D, $04, $04, $0D, $00, $08, $0D, $0D, $0D, $07, $07, $0D
         DB $00, $0A, $0D, $0D, $0D, $03, $03, $0D, $00, $02, $01, $0D, $09, $06, $06, $0D
         DB $0C, $0B, $0D, $0D, $0D, $04, $04, $0D, $00, $08, $0D, $0D, $0D, $07, $07, $0D
         DB $0D, $0A, $0D, $0D, $03, $03, $03, $0D, $00, $0D, $00, $0D, $06, $06, $06, $0D
         DB $0C, $0B, $0D, $0D, $04, $04, $05, $0D, $00, $08, $00, $0D, $0D, $07, $0D, $0D
         DB $02, $0A, $02, $0D, $03, $03, $03, $0D, $00, $02, $00, $0D, $06, $06, $06, $0D
         DB $0C, $0B, $0D, $0D, $04, $04, $05, $0D, $00, $08, $00, $0D, $07, $07, $08, $0D
         DB $02, $0A, $0D, $0D, $03, $03, $03, $0D, $00, $02, $00, $0D, $06, $06, $06, $0D
         DB $0C, $0B, $0D, $0D, $0D, $04, $04, $0D, $00, $08, $0D, $0D, $0D, $07, $07, $0D
         DB $02, $0A, $0D, $0D, $03, $03, $03, $0D, $00, $02, $00, $0D, $06, $06, $06, $0D
         DB $0C, $0B, $0D, $0D, $0D, $04, $04, $0D, $00, $08, $0D, $0D, $0D, $07, $07, $0D
lentab:
         DB 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 2, 2, 2, 1

