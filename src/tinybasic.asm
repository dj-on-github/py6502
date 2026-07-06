; ===============================================================
; Tiny BASIC (+ FOR/NEXT) for the 6502 simulator
; Keyboard: Apple II style $C000 / $C010.  Screen: ATASCII at $0800.
;
; Integer (16-bit signed) variables A-Z. Line-numbered programs.
; Statements: PRINT LET IF/THEN GOTO GOSUB RETURN INPUT FOR/NEXT
;             REM END LIST RUN NEW.  Operators + - * / ( ) and the
;             relations = <> < > <= >= .  Backspace edits the line.
; Loads and runs at $1000.
; ===============================================================

; ---- zero page ----
curl:   EQU $00
curh:   EQU $01
col:    EQU $02
txtl:   EQU $03
txth:   EQU $04
accl:   EQU $05
acch:   EQU $06
auxl:   EQU $07
auxh:   EQU $08
ptrl:   EQU $09
ptrh:   EQU $0a
pendl:  EQU $0b
pendh:  EQU $0c
linl:   EQU $0d
linh:   EQU $0e
tmp1:   EQU $0f
tmp2:   EQU $10
kwlen:  EQU $11
vecl:   EQU $12
vech:   EQU $13
sign:   EQU $14
cntl:   EQU $15
cnth:   EQU $16
srcl:   EQU $17
srch:   EQU $18
dstl:   EQU $19
dsth:   EQU $1a
scl:    EQU $1b
sch:    EQU $1c
ktemp:  EQU $1d
varidx: EQU $1e
relop:  EQU $1f
forsp:  EQU $20
gosp:   EQU $21
digflag:EQU $22
ysav:   EQU $23
resl:   EQU $24
resh:   EQU $25
reml:   EQU $26
remh:   EQU $27
fvix:   EQU $28
bufpl:  EQU $29
bufph:  EQU $2a
tmp3:   EQU $2b
scsl:   EQU $2c
scsh:   EQU $2d
scdl:   EQU $2e
scdh:   EQU $2f
sccl:   EQU $30
scch:   EQU $31
ctrl:   EQU $32
outfile:EQU $33
lslo:   EQU $34             ; LIST range: start line (low)
lshi:   EQU $35             ; LIST range: start line (high)
lelo:   EQU $36             ; LIST range: end line (low)
lehi:   EQU $37             ; LIST range: end line (high)

; ---- constants ----
kbd:    EQU $c000
kbdstrb:EQU $c010
filecmd:EQU $c0f0
filestat:EQU $c0f0
filedata:EQU $c0f1
varlo:  EQU $0200
varhi:  EQU $0201
gostk:  EQU $0400
gostk1: EQU $0401
forvar: EQU $0440
forliml:EQU $0450
forlimh:EQU $0460
forstpl:EQU $0470
forstph:EQU $0480
forptrl:EQU $0490
forptrh:EQU $04a0
linbuf: EQU $0300
inbuf:  EQU $0380

        ORG $1000

cold:   lda #$00
        sta pendl
        lda #$20
        sta pendh           ; PROGEND = PROGBASE ($2000), empty
        lda #$00
        sta forsp
        sta gosp
        jsr clrvars
        jsr clrscr
        ldx #$00
cb1:    lda banner,x
        beq cb2
        jsr putchar
        inx
        jmp cb1
cb2:    jsr prcr
warm:   ldx #$ff
        txs
        lda #$00
        sta bufpl
        lda #$03
        sta bufph           ; read into LINBUF ($0300)
        jsr prcr
        lda #$3e            ; '>'
        jsr putchar
        jsr readline
        lda #$00
        sta txtl
        lda #$03
        sta txth            ; TXTPTR = LINBUF
        jsr skipspaces
        jsr curch
        bne w1
        jmp warm
w1:     cmp #$30
        bcc wdirect
        cmp #$3a
        bcs wdirect
        jmp progline
wdirect:
        lda #$00
        jsr setctrl0
        jsr exec_stmt
        jmp warm

setctrl0:
        rts                 ; (ctrl flag handled in run loop only)

; ---------- enter / replace / delete a program line ----------
progline:
        jsr parsenum        ; ACC = line number
        lda accl
        sta linl
        lda acch
        sta linh
        jsr curch
        cmp #$20
        bne pgl1
        jsr skipspaces
pgl1:   jsr storeline
        jmp warm

; ---------- execute one statement at TXTPTR ----------
exec_stmt:
        jsr skipspaces
        jsr curch
        bne es1
        rts                 ; empty
es1:    jsr matchkw
        bcc esasn
        jmp (vecl)
esasn:  jmp st_let          ; no keyword -> assignment

; ---------- keyword matcher (table indexed by X, < 256 bytes) ----------
matchkw:
        ldx #$00
mkent:  lda kwtab,x
        bne mk1
        clc                 ; end of table -> no match
        rts
mk1:    sta kwlen
        inx                 ; X -> first keyword char
        ldy #$00
mkcmp:  cpy kwlen
        beq mkfound
        lda (txtl),y
        and #$df
        cmp kwtab,x
        bne mkskip
        inx
        iny
        jmp mkcmp
mkskip: sty tmp1
        lda kwlen
        sec
        sbc tmp1            ; remaining chars
        clc
        adc #$02            ; + address bytes
        sta tmp1
        txa
        clc
        adc tmp1
        tax
        jmp mkent
mkfound:
        lda kwtab,x
        sta vecl
        inx
        lda kwtab,x
        sta vech
        tya                 ; advance TXTPTR by keyword length
        clc
        adc txtl
        sta txtl
        lda txth
        adc #$00
        sta txth
        sec
        rts

; ---------- statement handlers ----------
st_rem: rts

st_end: lda #$02
        sta ctrl
        rts

st_new: lda #$00
        sta pendl
        lda #$20
        sta pendh
        jsr clrvars
        lda #$00
        sta forsp
        sta gosp
        rts

st_let: jsr skipspaces
        jsr curch
        and #$df
        cmp #$41
        bcc leterr
        cmp #$5b
        bcs leterr
        sec
        sbc #$41
        asl a
        sta varidx
        jsr advtxt
        jsr skipspaces
        jsr curch
        cmp #$3d
        bne leterr
        jsr advtxt
        jsr expr
        ldx varidx
        lda accl
        sta varlo,x
        lda acch
        sta varhi,x
        rts
leterr: jmp error

st_print:
prloop: jsr skipspaces
        jsr curch
        bne pr1
        jmp prend
pr1:    cmp #$22
        beq prstr
        jsr expr
        jsr prdec
        jmp prsep
prstr:  jsr advtxt
prs1:   jsr curch
        bne prs2
        jmp prend
prs2:   cmp #$22
        beq prs3
        jsr putchar
        jsr advtxt
        jmp prs1
prs3:   jsr advtxt
prsep:  jsr skipspaces
        jsr curch
        cmp #$2c
        beq prcomma
        cmp #$3b
        beq prsemi
        jmp prend
prcomma:
        jsr advtxt
        lda #$20
        jsr putchar
        jmp prloop
prsemi: jsr advtxt
        jsr skipspaces
        jsr curch
        bne prloop
        rts                 ; trailing ';' -> no newline
prend:  jsr prcr
        rts

st_goto:
        jsr expr
        lda accl
        sta linl
        lda acch
        sta linh
        jsr findline
        bcc gotoerr
        lda ptrl
        sta curl
        lda ptrh
        sta curh
        lda #$01
        sta ctrl
        rts
gotoerr:
        jmp error

st_gosub:
        jsr expr
        lda accl
        sta linl
        lda acch
        sta linh
        jsr findline
        bcc gotoerr
        lda gosp
        asl a
        tax
        lda curl
        sta gostk,x
        lda curh
        sta gostk1,x
        inc gosp
        lda ptrl
        sta curl
        lda ptrh
        sta curh
        lda #$01
        sta ctrl
        rts

st_return:
        lda gosp
        bne ret1
        jmp error
ret1:   dec gosp
        lda gosp
        asl a
        tax
        lda gostk,x
        sta curl
        lda gostk1,x
        sta curh
        lda #$00
        sta ctrl
        rts

st_if:  jsr expr
        lda accl
        pha
        lda acch
        pha
        jsr getrelop
        jsr expr
        pla
        sta auxh
        pla
        sta auxl
        jsr cmp16s
        jsr evalrelop
        bcc iffalse
        jsr skipspaces
        jsr skipthen
        jmp exec_stmt
iffalse:
        rts

st_list:
        lda #$00
        sta outfile
        ; default range = whole program (0 .. $FFFF)
        lda #$00
        sta lslo
        sta lshi
        lda #$ff
        sta lelo
        sta lehi
        jsr skipspaces
        jsr curch
        beq listgo          ; "LIST" with no argument -> list all
        jsr expr            ; first line number
        lda accl
        sta lslo
        lda acch
        sta lshi
        lda accl            ; single-line default: end = start
        sta lelo
        lda acch
        sta lehi
        jsr skipspaces
        jsr curch
        cmp #$2c            ; ',' ?
        bne listgo          ; no comma -> single line
        jsr advtxt          ; skip the comma
        jsr skipspaces
        jsr expr            ; second line number (range end)
        lda accl
        sta lelo
        lda acch
        sta lehi
listgo: jsr listprog
        rts

st_save:
        lda #$53
        sta filecmd
        lda #$01
        sta outfile
        lda #$00            ; SAVE lists the whole program
        sta lslo
        sta lshi
        lda #$ff
        sta lelo
        sta lehi
        jsr listprog
        lda #$00
        sta outfile
        lda #$45
        sta filecmd
        rts

st_load:
        lda #$4c
        sta filecmd
ldwait: lda filestat
        and #$80
        bne ldwait
        lda filestat
        and #$02
        bne lderr
        jsr st_new
ldline: lda filestat
        and #$01
        beq lddone
        ldy #$00
ldch:   lda filestat
        and #$01
        beq ldendl
        lda filedata
        cmp #$0d
        beq ldendl
        cmp #$0a
        beq ldendl
        sta linbuf,y
        iny
        cpy #$70
        bcc ldch
ldendl: lda #$00
        sta linbuf,y
        lda #$00
        sta txtl
        lda #$03
        sta txth
        jsr skipspaces
        jsr curch
        beq ldline
        cmp #$30
        bcc ldline
        cmp #$3a
        bcs ldline
        jsr parsenum
        lda accl
        sta linl
        lda acch
        sta linh
        jsr curch
        cmp #$20
        bne ldsl
        jsr skipspaces
ldsl:   jsr storeline
        jmp ldline
lddone: rts
lderr:  jmp error

listprog:
        lda #$00
        sta ptrl
        lda #$20
        sta ptrh
lsloop: lda ptrh
        cmp pendh
        bcc lsin
        bne lsdone
        lda ptrl
        cmp pendl
        bcs lsdone
lsin:   ldy #$00
        lda (ptrl),y
        sta accl
        iny
        lda (ptrl),y
        sta acch
        ; skip this line if its number < start (lslo:lshi)
        lda acch
        cmp lshi
        bcc lsskip
        bne lschke
        lda accl
        cmp lslo
        bcc lsskip
lschke: ; skip this line if its number > end (lelo:lehi)
        lda acch
        cmp lehi
        bcc lsprint
        bne lsskip
        lda accl
        cmp lelo
        beq lsprint
        bcs lsskip
lsprint:
        jsr prdec
        lda #$20
        jsr emit
        clc
        lda ptrl
        adc #$02
        sta srcl
        lda ptrh
        adc #$00
        sta srch
lstext: ldy #$00
        lda (srcl),y
        beq lseol
        jsr emit
        inc srcl
        bne lst2
        inc srch
lst2:   jmp lstext
lseol:  lda #$0d
        jsr emit
lsskip: jsr recnext
        jmp lsloop
lsdone: rts

st_run: lda #$00
        sta forsp
        sta gosp
        lda #$00
        sta curl
        lda #$20
        sta curh
runlp:  jsr chkbreak
        lda curh
        cmp pendh
        bcc rlin
        bne rldone
        lda curl
        cmp pendl
        bcs rldone
rlin:   clc
        lda curl
        adc #$02
        sta txtl
        lda curh
        adc #$00
        sta txth
        lda #$00
        sta ctrl
        jsr exec_stmt
        lda ctrl
        cmp #$02
        beq rldone
        cmp #$01
        beq runlp
        jsr nextlinecur
        jmp runlp
rldone: rts

st_input:
inloop: jsr skipspaces
        jsr curch
        and #$df
        cmp #$41
        bcc inerr
        cmp #$5b
        bcs inerr
        sec
        sbc #$41
        asl a
        sta varidx
        jsr advtxt
        lda #$3f            ; '?'
        jsr putchar
        lda txtl
        pha
        lda txth
        pha
        lda #$80
        sta bufpl
        lda #$03
        sta bufph
        jsr readline
        lda #$80
        sta txtl
        lda #$03
        sta txth
        jsr skipspaces
        jsr curch
        cmp #$2d
        bne inpos
        jsr advtxt
        jsr parsenum
        sec
        lda #$00
        sbc accl
        sta accl
        lda #$00
        sbc acch
        sta acch
        jmp instore
inpos:  jsr parsenum
instore:
        pla
        sta txth
        pla
        sta txtl
        ldx varidx
        lda accl
        sta varlo,x
        lda acch
        sta varhi,x
        jsr skipspaces
        jsr curch
        cmp #$2c
        bne indone
        jsr advtxt
        jmp inloop
indone: rts
inerr:  jmp error

st_cxy: jsr skipspaces
        jsr curch
        cmp #$28
        bne cxy1
        jsr advtxt
cxy1:   jsr expr
        lda accl
        sta tmp3
        jsr skipspaces
        jsr curch
        cmp #$2c
        bne cxyerr
        jsr advtxt
        jsr expr
        lda accl
        sta auxl
        lda acch
        sta auxh
        lda #$28
        sta accl
        lda #$00
        sta acch
        jsr mul16
        clc
        lda accl
        adc tmp3
        sta accl
        lda acch
        adc #$00
        sta acch
        clc
        lda accl
        adc #$00
        sta accl
        lda acch
        adc #$08
        sta acch
        lda accl
        sta scl
        lda acch
        sta sch
        lda tmp3
        sta col
        jsr skipspaces
        jsr curch
        cmp #$29
        bne cxydone
        jsr advtxt
cxydone:
        rts
cxyerr: jmp error

st_poke:
        jsr expr
        lda accl
        pha
        lda acch
        pha
        jsr skipspaces
        jsr curch
        cmp #$2c
        bne pokeerr
        jsr advtxt
        jsr expr
        pla
        sta ptrh
        pla
        sta ptrl
        ldy #$00
        lda accl
        sta (ptrl),y
        rts
pokeerr:
        jmp error

st_for: jsr skipspaces
        jsr curch
        and #$df
        cmp #$41
        bcs forc1
        jmp forerr
forc1:  cmp #$5b
        bcc forc2
        jmp forerr
forc2:  nop
        sec
        sbc #$41
        sta fvix            ; var index 0-25
        asl a
        sta varidx
        jsr advtxt
        jsr skipspaces
        jsr curch
        cmp #$3d
        beq forc3
        jmp forerr
forc3:  jsr advtxt
        jsr expr            ; initial value
        ldx varidx
        lda accl
        sta varlo,x
        lda acch
        sta varhi,x
        jsr skipspaces
        jsr curch
        and #$df
        cmp #$54            ; 'T'
        bne forerr
        jsr advtxt
        jsr curch
        and #$df
        cmp #$4f            ; 'O'
        bne forerr
        jsr advtxt
        jsr expr            ; limit
        lda accl
        pha
        lda acch
        pha
        jsr skipspaces
        jsr curch
        and #$df
        cmp #$53            ; 'S' (STEP)
        bne fornostep
        lda txtl
        clc
        adc #$04
        sta txtl
        lda txth
        adc #$00
        sta txth
        jsr expr            ; step
        jmp forhave
fornostep:
        lda #$01
        sta accl
        lda #$00
        sta acch
forhave:
        ldx forsp
        lda fvix
        sta forvar,x
        lda accl
        sta forstpl,x
        lda acch
        sta forstph,x
        pla
        sta forlimh,x
        pla
        sta forliml,x
        jsr nextlineptr
        lda ptrl
        sta forptrl,x
        lda ptrh
        sta forptrh,x
        inc forsp
        rts
forerr: jmp error

st_next:
        jsr skipspaces
        jsr curch
        and #$df
        cmp #$41
        bcc nxgo
        cmp #$5b
        bcs nxgo
        jsr advtxt
nxgo:   lda forsp
        bne nxhave
        jmp error
nxhave: ldx forsp
        dex
        stx tmp1            ; frame index
        lda forvar,x
        asl a
        tay                 ; Y = var*2
        clc
        lda varlo,y
        adc forstpl,x
        sta varlo,y
        lda varhi,y
        adc forstph,x
        sta varhi,y
        lda varlo,y
        sta auxl
        lda varhi,y
        sta auxh
        lda forliml,x
        sta accl
        lda forlimh,x
        sta acch
        jsr cmp16s
        sta tmp2
        lda forstph,x
        bmi nxneg
        lda tmp2
        cmp #$01
        beq nxdone
        jmp nxcont
nxneg:  lda tmp2
        cmp #$ff
        beq nxdone
nxcont: ldx tmp1
        lda forptrl,x
        sta curl
        lda forptrh,x
        sta curh
        lda #$01
        sta ctrl
        rts
nxdone: dec forsp
        lda #$00
        sta ctrl
        rts

; ---------- relational helpers ----------
getrelop:
        jsr skipspaces
        jsr curch
        cmp #$3d
        beq greq
        cmp #$3c
        beq grlt
        cmp #$3e
        beq grgt
        jmp error
greq:   jsr advtxt
        lda #$00
        sta relop
        rts
grlt:   jsr advtxt
        jsr curch
        cmp #$3d
        beq grle
        cmp #$3e
        beq grne
        lda #$02
        sta relop
        rts
grle:   jsr advtxt
        lda #$04
        sta relop
        rts
grne:   jsr advtxt
        lda #$01
        sta relop
        rts
grgt:   jsr advtxt
        jsr curch
        cmp #$3d
        beq grge
        lda #$03
        sta relop
        rts
grge:   jsr advtxt
        lda #$05
        sta relop
        rts

evalrelop:
        sta tmp1
        lda relop
        cmp #$00
        beq ereq
        cmp #$01
        beq erne
        cmp #$02
        beq erlt
        cmp #$03
        beq ergt
        cmp #$04
        beq erle
        lda tmp1            ; relop 5 = GE
        cmp #$ff
        beq erfalse
        jmp ertrue
ereq:   lda tmp1
        beq ertrue
        jmp erfalse
erne:   lda tmp1
        beq erfalse
        jmp ertrue
erlt:   lda tmp1
        cmp #$ff
        beq ertrue
        jmp erfalse
ergt:   lda tmp1
        cmp #$01
        beq ertrue
        jmp erfalse
erle:   lda tmp1
        cmp #$01
        beq erfalse
        jmp ertrue
ertrue: sec
        rts
erfalse:
        clc
        rts

skipthen:
        jsr skipspaces
        jsr curch
        and #$df
        cmp #$54
        bne sthret
        lda txtl
        clc
        adc #$04
        sta txtl
        lda txth
        adc #$00
        sta txth
sthret: rts

; ---------- expression evaluator ----------
expr:   jsr term
exloop: jsr skipspaces
        jsr curch
        cmp #$2b
        beq exadd
        cmp #$2d
        beq exsub
        rts
exadd:  jsr advtxt
        lda accl
        pha
        lda acch
        pha
        jsr term
        pla
        sta auxh
        pla
        sta auxl
        clc
        lda auxl
        adc accl
        sta accl
        lda auxh
        adc acch
        sta acch
        jmp exloop
exsub:  jsr advtxt
        lda accl
        pha
        lda acch
        pha
        jsr term
        pla
        sta auxh
        pla
        sta auxl
        sec
        lda auxl
        sbc accl
        sta accl
        lda auxh
        sbc acch
        sta acch
        jmp exloop

term:   jsr factor
tmloop: jsr skipspaces
        jsr curch
        cmp #$2a
        beq tmmul
        cmp #$2f
        beq tmdiv
        rts
tmmul:  jsr advtxt
        lda accl
        pha
        lda acch
        pha
        jsr factor
        pla
        sta auxh
        pla
        sta auxl
        jsr mul16
        jmp tmloop
tmdiv:  jsr advtxt
        lda accl
        pha
        lda acch
        pha
        jsr factor
        pla
        sta auxh
        pla
        sta auxl
        jsr div16
        jmp tmloop

factor: jsr skipspaces
        jsr ispeek
        bcs fpeek
        jsr curch
        cmp #$28
        beq fparen
        cmp #$2d
        beq fneg
        cmp #$30
        bcc fvar
        cmp #$3a
        bcc fnum
        jmp fvar
fparen: jsr advtxt
        jsr expr
        jsr skipspaces
        jsr curch
        cmp #$29
        bne ferr
        jsr advtxt
        rts
fneg:   jsr advtxt
        jsr factor
        sec
        lda #$00
        sbc accl
        sta accl
        lda #$00
        sbc acch
        sta acch
        rts
fnum:   jsr parsenum
        rts
fvar:   jsr curch
        and #$df
        cmp #$41
        bcc ferr
        cmp #$5b
        bcs ferr
        sec
        sbc #$41
        asl a
        tax
        lda varlo,x
        sta accl
        lda varhi,x
        sta acch
        jsr advtxt
        rts
ferr:   jmp error

fpeek:  jsr skipspaces
        jsr curch
        cmp #$28
        bne ferr
        jsr advtxt
        jsr expr
        jsr skipspaces
        jsr curch
        cmp #$29
        bne ferr
        jsr advtxt
        lda accl
        sta ptrl
        lda acch
        sta ptrh
        ldy #$00
        lda (ptrl),y
        sta accl
        lda #$00
        sta acch
        rts

ispeek: ldy #$00
        lda (txtl),y
        and #$df
        cmp #$50
        bne ispno
        iny
        lda (txtl),y
        and #$df
        cmp #$45
        bne ispno
        iny
        lda (txtl),y
        and #$df
        cmp #$45
        bne ispno
        iny
        lda (txtl),y
        and #$df
        cmp #$4b
        bne ispno
        lda txtl
        clc
        adc #$04
        sta txtl
        lda txth
        adc #$00
        sta txth
        sec
        rts
ispno:  clc
        rts

parsenum:
        lda #$00
        sta accl
        sta acch
pn1:    jsr curch
        cmp #$30
        bcc pndone
        cmp #$3a
        bcs pndone
        sec
        sbc #$30
        sta tmp2
        jsr mul10
        clc
        lda accl
        adc tmp2
        sta accl
        lda acch
        adc #$00
        sta acch
        jsr advtxt
        jmp pn1
pndone: rts

mul10:  lda accl
        asl a
        sta auxl
        lda acch
        rol a
        sta auxh            ; aux = ACC*2
        lda auxl
        asl a
        sta resl
        lda auxh
        rol a
        sta resh
        asl resl
        rol resh            ; res = ACC*8
        clc
        lda auxl
        adc resl
        sta accl
        lda auxh
        adc resh
        sta acch
        rts

; ---------- 16-bit multiply (low 16 bits) ----------
mul16:  lda #$00
        sta resl
        sta resh
        ldx #$10
ml1:    lda accl
        and #$01
        beq ml2
        clc
        lda resl
        adc auxl
        sta resl
        lda resh
        adc auxh
        sta resh
ml2:    asl auxl
        rol auxh
        lsr acch
        ror accl
        dex
        bne ml1
        lda resl
        sta accl
        lda resh
        sta acch
        rts

; ---------- 16-bit signed divide: ACC = AUX / ACC ----------
div16:  lda accl
        ora acch
        bne dvok
        jmp error           ; divide by zero
dvok:   lda auxh
        eor acch
        and #$80
        sta sign
        lda auxh
        bpl dva1
        sec
        lda #$00
        sbc auxl
        sta auxl
        lda #$00
        sbc auxh
        sta auxh
dva1:   lda acch
        bpl dva2
        sec
        lda #$00
        sbc accl
        sta accl
        lda #$00
        sbc acch
        sta acch
dva2:   jsr udiv16
        lda auxl
        sta accl
        lda auxh
        sta acch
        lda sign
        beq dvdone
        sec
        lda #$00
        sbc accl
        sta accl
        lda #$00
        sbc acch
        sta acch
dvdone: rts

udiv16: lda #$00
        sta reml
        sta remh
        ldx #$10
ud1:    asl auxl
        rol auxh
        rol reml
        rol remh
        lda reml
        sec
        sbc accl
        sta tmp1
        lda remh
        sbc acch
        bcc ud2
        sta remh
        lda tmp1
        sta reml
        inc auxl
ud2:    dex
        bne ud1
        rts

; ---------- signed 16-bit compare: A = 0(eq) 1(aux>acc) $ff(aux<acc) ----------
cmp16s: lda auxh
        cmp acch
        bne c16hi
        lda auxl
        cmp accl
        bne c16lo
        lda #$00
        rts
c16lo:  bcs c16gt
        lda #$ff
        rts
c16gt:  lda #$01
        rts
c16hi:  lda auxh
        sec
        sbc acch
        bvc c16h1
        eor #$80
c16h1:  bmi c16lt
        lda #$01
        rts
c16lt:  lda #$ff
        rts

; ---------- print signed 16-bit ACC in decimal ----------
prdec:  lda acch
        bpl pdpos
        lda #$2d
        jsr emit
        sec
        lda #$00
        sbc accl
        sta accl
        lda #$00
        sbc acch
        sta acch
pdpos:  ldx #$00
        lda #$00
        sta digflag
pdpow:  cpx #$05
        beq pddone
        ldy #$00
pdsub:  lda accl
        sec
        sbc powlo,x
        sta tmp1
        lda acch
        sbc powhi,x
        bcc pdemit
        sta acch
        lda tmp1
        sta accl
        iny
        jmp pdsub
pdemit: cpy #$00
        bne pdprint
        lda digflag
        bne pdprint
        cpx #$04
        beq pdprint
        jmp pdnext
pdprint:
        lda #$01
        sta digflag
        tya
        clc
        adc #$30
        jsr emit
pdnext: inx
        jmp pdpow
pddone: rts

; ---------- program line storage ----------
storeline:
        jsr findline
        bcc slnoexist
        jsr deleteline
slnoexist:
        jsr textlen
        lda cntl
        sta tmp3
        ora cnth
        bne slins
        rts
slins:  jsr findline
        jsr insertroom
        ldy #$00
        lda linl
        sta (ptrl),y
        iny
        lda linh
        sta (ptrl),y
        clc
        lda ptrl
        adc #$02
        sta dstl
        lda ptrh
        adc #$00
        sta dsth
        lda txtl
        sta srcl
        lda txth
        sta srch
        ldx tmp3
        ldy #$00
slcp:   cpx #$00
        beq slcpd
        lda (srcl),y
        sta (dstl),y
        iny
        dex
        jmp slcp
slcpd:  lda #$00
        sta (dstl),y
        rts

textlen:
        ldy #$00
tl1:    lda (txtl),y
        beq tldone
        iny
        bne tl1
tldone: sty cntl
        lda #$00
        sta cnth
        rts

findline:
        lda #$00
        sta ptrl
        lda #$20
        sta ptrh
flloop: lda ptrh
        cmp pendh
        bcc flin
        bne flnf
        lda ptrl
        cmp pendl
        bcs flnf
flin:   ldy #$00
        lda (ptrl),y
        sta auxl
        iny
        lda (ptrl),y
        sta auxh
        lda linl
        sta accl
        lda linh
        sta acch
        jsr cmp16su         ; aux(rec) vs acc(target)
        cmp #$00
        beq flfound
        cmp #$01
        beq flins2          ; rec > target -> insertion point
        jsr recnext
        jmp flloop
flfound:
        sec
        rts
flins2:
flnf:   clc
        rts

; unsigned 16-bit compare: A=0 eq, 1 aux>acc, $ff aux<acc
cmp16su:
        lda auxh
        cmp acch
        bne cu_hi
        lda auxl
        cmp accl
        bne cu_lo
        lda #$00
        rts
cu_lo:  bcs cu_gt
        lda #$ff
        rts
cu_gt:  lda #$01
        rts
cu_hi:  bcs cu_gt
        lda #$ff
        rts

recnext:
        clc
        lda ptrl
        adc #$02
        sta ptrl
        lda ptrh
        adc #$00
        sta ptrh
rn1:    ldy #$00
        lda (ptrl),y
        inc ptrl
        bne rn2
        inc ptrh
rn2:    cmp #$00
        bne rn1
        rts

nextlinecur:
        clc
        lda curl
        adc #$02
        sta curl
        lda curh
        adc #$00
        sta curh
ncl1:   ldy #$00
        lda (curl),y
        inc curl
        bne ncl2
        inc curh
ncl2:   cmp #$00
        bne ncl1
        rts

nextlineptr:
        clc
        lda curl
        adc #$02
        sta ptrl
        lda curh
        adc #$00
        sta ptrh
nlp1:   ldy #$00
        lda (ptrl),y
        inc ptrl
        bne nlp2
        inc ptrh
nlp2:   cmp #$00
        bne nlp1
        rts

insertroom:
        lda cntl
        clc
        adc #$03
        sta tmp1            ; record size
        sec
        lda pendl
        sbc ptrl
        sta cntl
        lda pendh
        sbc ptrh
        sta cnth
        lda pendl
        sta srcl
        lda pendh
        sta srch
        clc
        lda pendl
        adc tmp1
        sta dstl
        lda pendh
        adc #$00
        sta dsth
ir1:    lda cntl
        ora cnth
        beq irdone
        lda srcl
        bne irs1
        dec srch
irs1:   dec srcl
        lda dstl
        bne ird1
        dec dsth
ird1:   dec dstl
        ldy #$00
        lda (srcl),y
        sta (dstl),y
        lda cntl
        bne irc1
        dec cnth
irc1:   dec cntl
        jmp ir1
irdone: clc
        lda pendl
        adc tmp1
        sta pendl
        lda pendh
        adc #$00
        sta pendh
        rts

deleteline:
        lda ptrl
        sta dstl
        lda ptrh
        sta dsth
        jsr recnext
        lda ptrl
        sta srcl
        lda ptrh
        sta srch
        sec
        lda pendl
        sbc srcl
        sta cntl
        lda pendh
        sbc srch
        sta cnth
        sec
        lda srcl
        sbc dstl
        sta tmp1            ; record size
dl1:    lda cntl
        ora cnth
        beq dldone
        ldy #$00
        lda (srcl),y
        sta (dstl),y
        inc srcl
        bne dls1
        inc srch
dls1:   inc dstl
        bne dld1
        inc dsth
dld1:   lda cntl
        bne dlc1
        dec cnth
dlc1:   dec cntl
        jmp dl1
dldone: sec
        lda pendl
        sbc tmp1
        sta pendl
        lda pendh
        sbc #$00
        sta pendh
        rts

; ---------- Ctrl-C break check (called between statements) ----------
chkbreak:
        lda kbd
        bpl cbret
        and #$7f
        cmp #$03
        bne cbret
        lda kbdstrb
        jsr prcr
        ldx #$00
brk1:   lda brkmsg,x
        beq brk2
        jsr putchar
        inx
        jmp brk1
brk2:   jsr prcr
        jmp warm
cbret:  rts

; ---------- misc helpers ----------
clrvars:
        ldx #$00
        lda #$00
cv1:    sta varlo,x
        inx
        cpx #$34
        bne cv1
        rts

skipspaces:
        jsr curch
        cmp #$20
        bne ssret
        jsr advtxt
        jmp skipspaces
ssret:  rts

curch:  ldy #$00
        lda (txtl),y
        rts

advtxt: inc txtl
        bne avret
        inc txth
avret:  rts

error:  jsr prcr
        ldx #$00
erp:    lda errmsg,x
        beq erd
        jsr putchar
        inx
        jmp erp
erd:    jsr prcr
        jmp warm

emit:   pha
        lda outfile
        beq emitscr
        pla
        sta filedata
        rts
emitscr:
        pla
        jmp putchar

prcr:   lda #$0d
        jsr putchar
        rts

; ---------- console I/O ----------
readline:
        ldy #$00
rl1:    jsr getkey
        cmp #$0d
        beq rlcr
        cmp #$08
        beq rlbs
        cmp #$7f
        beq rlbs
        cmp #$20
        bcc rl1
        sta (bufpl),y
        jsr putchar
        iny
        cpy #$70
        bcc rl1
rlcr:   lda #$00
        sta (bufpl),y
        lda #$0d
        jsr putchar
        rts
rlbs:   cpy #$00
        beq rl1
        lda col
        beq rl1
        dey
        jsr bsdel
        jmp rl1

getkey: lda kbd
        bpl getkey
        sta ktemp
        lda kbdstrb
        lda ktemp
        and #$7f
        rts

bsdel:  sty ysav
        lda scl
        bne bd1
        dec sch
bd1:    dec scl
        dec col
        ldy #$00
        lda #$20
        sta (scl),y
        ldy ysav
        rts

putchar:
        sty ysav
        cmp #$0d
        bne pcprint
        jsr newline
        jmp pcret
pcprint:
        ldy #$00
        sta (scl),y
        inc scl
        bne pcnz
        inc sch
pcnz:   inc col
        lda col
        cmp #$28
        bcc pcret
        jsr newline
pcret:  ldy ysav
        rts

newline:
        lda #$28
        sec
        sbc col
        clc
        adc scl
        sta scl
        lda sch
        adc #$00
        sta sch
        lda #$00
        sta col
        lda sch
        cmp #$0d
        bcc nlret
        jsr scroll
nlret:  rts

scroll: lda #$28
        sta scsl
        lda #$08
        sta scsh
        lda #$00
        sta scdl
        lda #$08
        sta scdh
        lda #$d8
        sta sccl
        lda #$04
        sta scch
scl1:   ldy #$00
        lda (scsl),y
        sta (scdl),y
        inc scsl
        bne scs2
        inc scsh
scs2:   inc scdl
        bne scs3
        inc scdh
scs3:   lda sccl
        sec
        sbc #$01
        sta sccl
        lda scch
        sbc #$00
        sta scch
        lda sccl
        ora scch
        bne scl1
        lda #$d8
        sta scdl
        lda #$0c
        sta scdh
        ldy #$00
        lda #$20
scc1:   sta (scdl),y
        iny
        cpy #$28
        bne scc1
        lda #$d8
        sta scl
        lda #$0c
        sta sch
        lda #$00
        sta col
        rts

clrscr: lda #$00
        sta ptrl
        lda #$08
        sta ptrh
        ldx #$05
        lda #$20
cs1:    ldy #$00
cs2:    sta (ptrl),y
        iny
        bne cs2
        inc ptrh
        dex
        bne cs1
        lda #$00
        sta scl
        sta col
        lda #$08
        sta sch
        rts

; ---------- data ----------
banner: DB "TINY BASIC", $00
errmsg: DB "?ERROR", $00
brkmsg: DB "BREAK", $00

powlo:  DB $10, $e8, $64, $0a, $01
powhi:  DB $27, $03, $00, $00, $00

kwtab:
        DB 5
        DB "PRINT"
        DW &st_print
        DB 3
        DB "LET"
        DW &st_let
        DB 2
        DB "IF"
        DW &st_if
        DB 4
        DB "GOTO"
        DW &st_goto
        DB 5
        DB "GOSUB"
        DW &st_gosub
        DB 6
        DB "RETURN"
        DW &st_return
        DB 5
        DB "INPUT"
        DW &st_input
        DB 3
        DB "FOR"
        DW &st_for
        DB 4
        DB "NEXT"
        DW &st_next
        DB 4
        DB "POKE"
        DW &st_poke
        DB 3
        DB "REM"
        DW &st_rem
        DB 3
        DB "END"
        DW &st_end
        DB 4
        DB "LIST"
        DW &st_list
        DB 4
        DB "SAVE"
        DW &st_save
        DB 4
        DB "LOAD"
        DW &st_load
        DB 3
        DB "RUN"
        DW &st_run
        DB 3
        DB "NEW"
        DW &st_new
        DB 3
        DB "CLS"
        DW &clrscr
        DB 3
        DB "CXY"
        DW &st_cxy
        DB 0
