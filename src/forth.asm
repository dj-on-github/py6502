; ===============================================================
; A small indirect-threaded Forth for the sim_6502 simulator.
; Keyboard: Apple II style $C000 / $C010.  Screen: ATASCII at $0800.
;
; 16-bit cells. Data stack in page 2 (X = stack pointer). Return
; stack in page 3. Input buffer in page 4. User dictionary at $2000.
; Loads and runs at $1000.
;
; Words: DUP DROP SWAP OVER ROT DEPTH  + - * / MOD NEGATE
;        AND OR XOR INVERT  = < > 0=   @ ! C@ C!
;        EMIT KEY . CR SPACE CLS  HERE , ALLOT
;        : ; EXIT  IF ELSE THEN BEGIN UNTIL AGAIN
;        VARIABLE CONSTANT
; ===============================================================

; ---- zero page (Forth VM) : avoids the console-I/O bytes below ----
ip:     EQU $10          ; instruction pointer (2)
w:      EQU $12          ; working / CFA pointer (2)
rp:     EQU $14          ; return-stack pointer (2), into page 3
dp:     EQU $16          ; dictionary pointer / HERE (2)
latest: EQU $18          ; newest dictionary header (2)
state:  EQU $1a          ; 0 = interpret, 1 = compile
toin:   EQU $1e          ; parse offset into the input buffer
ntib:   EQU $1f          ; number of chars in the input buffer
wlen:   EQU $20          ; length of the last parsed word
savex:  EQU $21          ; save X (data-stack ptr) across CLS
dcount: EQU $22          ; digit count for number printing
tmp1:   EQU $24          ; general 16-bit temporaries (2)
tmp2:   EQU $26          ; (2)
tmp3:   EQU $28          ; (2)
num:    EQU $2a          ; number build / dividend (2)
den:    EQU $32          ; divisor (2)
rem:    EQU $34          ; remainder (2)
res:    EQU $36          ; product / result (2)
qsign:  EQU $38          ; quotient sign
rsign:  EQU $39          ; remainder sign
newdef: EQU $3a          ; header of the definition in progress (2)
namep:  EQU $3c          ; pointer to a dictionary name (2)
immflag:EQU $3e          ; nonzero if the found word is immediate
tmpy:   EQU $3f          ; save Y across an inner store
numneg: EQU $40          ; number had a leading '-'
tmpdig: EQU $41          ; current digit
wptr:   EQU $42          ; word-buffer store pointer (2)
loadact:EQU $44          ; nonzero while LOAD is feeding a source file
pbflag: EQU $45          ; a pushed-back input char is waiting
pbchar: EQU $46          ; the pushed-back char
saveptr:EQU $47          ; address cursor for SAVE / image restore (2)

; ---- zero page (console I/O, reused from the Tiny BASIC interpreter) ----
col:    EQU $02
ptrl:   EQU $09
ptrh:   EQU $0a
scl:    EQU $1b
sch:    EQU $1c
ktemp:  EQU $1d
ysav:   EQU $23
scsl:   EQU $2c
scsh:   EQU $2d
scdl:   EQU $2e
scdh:   EQU $2f
sccl:   EQU $30
scch:   EQU $31

; ---- constants ----
kbd:    EQU $c000
kbdstrb:EQU $c010
filecmd: EQU $c0f0        ; host file I/O: command (write) / status (read)
filedata:EQU $c0f1        ; host file I/O: data byte
tib:    EQU $0400         ; input buffer (page 4)
wbuf:   EQU $0480         ; parsed-word buffer
numbuf: EQU $04c0         ; digit reversal buffer
; data stack cells live at $0200,X ; return stack in page 3

        ORG $1000

cold:
        lda #$00
        sta dp
        lda #$20
        sta dp+1             ; HERE = $2000
        lda #<h_last
        sta latest
        lda #>h_last
        sta latest+1
        lda #$00
        sta loadact
        sta pbflag
        jsr clrscr
        lda #<bannermsg
        sta tmp1
        lda #>bannermsg
        sta tmp1+1
        jsr prstr
        lda #$0d
        jsr putchar
        ; fall into QUIT

; ---------------------------------------------------------------
; Outer interpreter
; ---------------------------------------------------------------
quit:
        ldx #$80             ; data-stack pointer base
        lda #$00
        sta rp
        lda #$04
        sta rp+1             ; return stack base = $0400 (grows down)
        lda #$00
        sta state
qline:
        jsr readline
        lda #$00
        sta toin
qw:
        jsr parseword
        bcc qok              ; no more words on the line
        jsr find
        bcc qnum             ; not in the dictionary -> try a number
        lda state
        beq qexec            ; interpret mode -> execute
        lda immflag
        bne qexec            ; immediate word -> execute even while compiling
        jsr comma            ; compile the found word's CFA (in tmp1)
        jmp qw
qnum:
        jsr number
        bcc qerr             ; not a number either -> error
        lda state
        beq qpush
        ; compiling: append  LIT value
        lda tmp1
        sta tmp3
        lda tmp1+1
        sta tmp3+1
        lda #<lit
        sta tmp1
        lda #>lit
        sta tmp1+1
        jsr comma
        lda tmp3
        sta tmp1
        lda tmp3+1
        sta tmp1+1
        jsr comma
        jmp qw
qpush:
        dex
        dex
        lda tmp1
        sta $0200,x
        lda tmp1+1
        sta $0201,x
        jmp qw
qexec:
        lda tmp1
        sta exec_slot
        lda tmp1+1
        sta exec_slot+1
        lda #<exec_thread
        sta ip
        lda #>exec_thread
        sta ip+1
        jmp next
qok:
        lda #<okmsg
        sta tmp1
        lda #>okmsg
        sta tmp1+1
        jsr prstr
        lda #$0d
        jsr putchar
        jmp qline
qerr:
        jsr print_wbuf
        jmp quit

; A one-word thread used to EXECUTE a single word and return here.
pause:
        jmp qw
exec_thread:
exec_slot:
        DW $0000
        DW pause

; ---------------------------------------------------------------
; Inner interpreter
; ---------------------------------------------------------------
next:
        ldy #$00
        lda (ip),y
        sta w
        iny
        lda (ip),y
        sta w+1
        lda ip
        clc
        adc #$02
        sta ip
        bcc nx1
        inc ip+1
nx1:    jmp (w)

; DOCOL (direct-threaded): entered by the "JSR docol" at a colon word's code
; field. The 6502 return address is (code field + 2); the parameter list
; starts one byte later. Save the caller's IP on the Forth return stack.
docol:
        lda rp
        sec
        sbc #$02
        sta rp
        bcs dc1
        dec rp+1
dc1:    ldy #$00
        lda ip
        sta (rp),y
        iny
        lda ip+1
        sta (rp),y
        pla
        sta ip
        pla
        sta ip+1
        inc ip
        bne dc2
        inc ip+1
dc2:    jmp next

; DOVAR / DOCON: entered by "JSR dovar" / "JSR docon" at the code field of a
; VARIABLE / CONSTANT. The parameter cell is at (return address + 1).
dovar:
        pla
        sta tmp1
        pla
        sta tmp1+1
        inc tmp1
        bne dv1
        inc tmp1+1
dv1:    dex
        dex
        lda tmp1
        sta $0200,x
        lda tmp1+1
        sta $0201,x
        jmp next

docon:
        pla
        sta tmp1
        pla
        sta tmp1+1
        inc tmp1
        bne dn1
        inc tmp1+1
dn1:    dex
        dex
        ldy #$00
        lda (tmp1),y
        sta $0200,x
        iny
        lda (tmp1),y
        sta $0201,x
        jmp next

; ---------------------------------------------------------------
; Internal code words used by the compiler (no dictionary headers). Under DTC
; the execution token IS the address of this code.
; ---------------------------------------------------------------
exit:
        ldy #$00
        lda (rp),y
        sta ip
        iny
        lda (rp),y
        sta ip+1
        lda rp
        clc
        adc #$02
        sta rp
        bcc ex1
        inc rp+1
ex1:    jmp next

lit:
        dex
        dex
        ldy #$00
        lda (ip),y
        sta $0200,x
        iny
        lda (ip),y
        sta $0201,x
        lda ip
        clc
        adc #$02
        sta ip
        bcc li1
        inc ip+1
li1:    jmp next

branch:
        ldy #$00
        lda (ip),y
        sta tmp1
        iny
        lda (ip),y
        sta ip+1
        lda tmp1
        sta ip
        jmp next

zbranch:
        lda $0200,x
        ora $0201,x
        inx
        inx
        cmp #$00             ; re-test flag: inx above clobbered Z
        bne zbno
        ldy #$00
        lda (ip),y
        sta tmp1
        iny
        lda (ip),y
        sta ip+1
        lda tmp1
        sta ip
        jmp next
zbno:   lda ip
        clc
        adc #$02
        sta ip
        bcc zb1
        inc ip+1
zb1:    jmp next

; ---------------------------------------------------------------
; Primitive words (dictionary headers + code)
; ---------------------------------------------------------------
h_dup:  DW $0000
        DB 3
        DB "DUP"
dup:
        dex
        dex
        lda $0202,x
        sta $0200,x
        lda $0203,x
        sta $0201,x
        jmp next

h_drop: DW h_dup
        DB 4
        DB "DROP"
drop:
        inx
        inx
        jmp next

h_swap: DW h_drop
        DB 4
        DB "SWAP"
swap:
        lda $0200,x
        pha
        lda $0202,x
        sta $0200,x
        pla
        sta $0202,x
        lda $0201,x
        pha
        lda $0203,x
        sta $0201,x
        pla
        sta $0203,x
        jmp next

h_over: DW h_swap
        DB 4
        DB "OVER"
over:
        dex
        dex
        lda $0204,x
        sta $0200,x
        lda $0205,x
        sta $0201,x
        jmp next

h_rot:  DW h_over
        DB 3
        DB "ROT"
rot:
        lda $0204,x
        sta tmp1
        lda $0205,x
        sta tmp1+1
        lda $0202,x
        sta $0204,x
        lda $0203,x
        sta $0205,x
        lda $0200,x
        sta $0202,x
        lda $0201,x
        sta $0203,x
        lda tmp1
        sta $0200,x
        lda tmp1+1
        sta $0201,x
        jmp next

h_depth: DW h_rot
        DB 5
        DB "DEPTH"
depth:
        stx tmp1
        lda #$80
        sec
        sbc tmp1
        lsr a
        pha
        dex
        dex
        pla
        sta $0200,x
        lda #$00
        sta $0201,x
        jmp next

h_plus: DW h_depth
        DB 1
        DB "+"
plus:
        clc
        lda $0202,x
        adc $0200,x
        sta $0202,x
        lda $0203,x
        adc $0201,x
        sta $0203,x
        inx
        inx
        jmp next

h_minus: DW h_plus
        DB 1
        DB "-"
minus:
        sec
        lda $0202,x
        sbc $0200,x
        sta $0202,x
        lda $0203,x
        sbc $0201,x
        sta $0203,x
        inx
        inx
        jmp next

h_star: DW h_minus
        DB 1
        DB "*"
star:
        lda $0202,x
        sta tmp1
        lda $0203,x
        sta tmp1+1
        lda $0200,x
        sta tmp2
        lda $0201,x
        sta tmp2+1
        lda #$00
        sta res
        sta res+1
        ldy #16
mul1:   lsr tmp2+1
        ror tmp2
        bcc mul2
        clc
        lda res
        adc tmp1
        sta res
        lda res+1
        adc tmp1+1
        sta res+1
mul2:   asl tmp1
        rol tmp1+1
        dey
        bne mul1
        lda res
        sta $0202,x
        lda res+1
        sta $0203,x
        inx
        inx
        jmp next

h_slash: DW h_star
        DB 1
        DB "/"
slash:
        jsr setdiv
        lda qsign
        beq sl_pos
        jsr negnum
sl_pos: lda num
        sta $0202,x
        lda num+1
        sta $0203,x
        inx
        inx
        jmp next

h_mod:  DW h_slash
        DB 3
        DB "MOD"
mod:
        jsr setdiv
        lda rsign
        beq md_pos
        ; negate remainder
        sec
        lda #$00
        sbc rem
        sta rem
        lda #$00
        sbc rem+1
        sta rem+1
md_pos: lda rem
        sta $0202,x
        lda rem+1
        sta $0203,x
        inx
        inx
        jmp next

h_negate: DW h_mod
        DB 6
        DB "NEGATE"
negate:
        sec
        lda #$00
        sbc $0200,x
        sta $0200,x
        lda #$00
        sbc $0201,x
        sta $0201,x
        jmp next

h_and:  DW h_negate
        DB 3
        DB "AND"
w_and:
        lda $0202,x
        and $0200,x
        sta $0202,x
        lda $0203,x
        and $0201,x
        sta $0203,x
        inx
        inx
        jmp next

h_or:   DW h_and
        DB 2
        DB "OR"
w_or:
        lda $0202,x
        ora $0200,x
        sta $0202,x
        lda $0203,x
        ora $0201,x
        sta $0203,x
        inx
        inx
        jmp next

h_xor:  DW h_or
        DB 3
        DB "XOR"
w_xor:
        lda $0202,x
        eor $0200,x
        sta $0202,x
        lda $0203,x
        eor $0201,x
        sta $0203,x
        inx
        inx
        jmp next

h_invert: DW h_xor
        DB 6
        DB "INVERT"
invert:
        lda $0200,x
        eor #$ff
        sta $0200,x
        lda $0201,x
        eor #$ff
        sta $0201,x
        jmp next

h_equal: DW h_invert
        DB 1
        DB "="
equal:
        lda $0200,x
        cmp $0202,x
        bne eqf
        lda $0201,x
        cmp $0203,x
        bne eqf
        lda #$ff
        bne eqs
eqf:    lda #$00
eqs:    sta $0202,x
        sta $0203,x
        inx
        inx
        jmp next

h_less: DW h_equal
        DB 1
        DB "<"
less:
        sec
        lda $0202,x
        sbc $0200,x
        lda $0203,x
        sbc $0201,x
        bvc lt1
        eor #$80
lt1:    bmi lts
        lda #$00
        beq ltst
lts:    lda #$ff
ltst:   sta $0202,x
        sta $0203,x
        inx
        inx
        jmp next

h_greater: DW h_less
        DB 1
        DB ">"
greater:
        sec
        lda $0200,x
        sbc $0202,x
        lda $0201,x
        sbc $0203,x
        bvc gt1
        eor #$80
gt1:    bmi gts
        lda #$00
        beq gtst
gts:    lda #$ff
gtst:   sta $0202,x
        sta $0203,x
        inx
        inx
        jmp next

h_zeq:  DW h_greater
        DB 2
        DB "0="
zeq:
        lda $0200,x
        ora $0201,x
        bne zef
        lda #$ff
        bne zes
zef:    lda #$00
zes:    sta $0200,x
        sta $0201,x
        jmp next

h_fetch: DW h_zeq
        DB 1
        DB "@"
fetch:
        lda $0200,x
        sta tmp1
        lda $0201,x
        sta tmp1+1
        ldy #$00
        lda (tmp1),y
        sta $0200,x
        iny
        lda (tmp1),y
        sta $0201,x
        jmp next

h_store: DW h_fetch
        DB 1
        DB "!"
store:
        lda $0200,x
        sta tmp1
        lda $0201,x
        sta tmp1+1
        ldy #$00
        lda $0202,x
        sta (tmp1),y
        iny
        lda $0203,x
        sta (tmp1),y
        inx
        inx
        inx
        inx
        jmp next

h_cfetch: DW h_store
        DB 2
        DB "C@"
cfetch:
        lda $0200,x
        sta tmp1
        lda $0201,x
        sta tmp1+1
        ldy #$00
        lda (tmp1),y
        sta $0200,x
        lda #$00
        sta $0201,x
        jmp next

h_cstore: DW h_cfetch
        DB 2
        DB "C!"
cstore:
        lda $0200,x
        sta tmp1
        lda $0201,x
        sta tmp1+1
        ldy #$00
        lda $0202,x
        sta (tmp1),y
        inx
        inx
        inx
        inx
        jmp next

h_emit: DW h_cstore
        DB 4
        DB "EMIT"
emit:
        lda $0200,x
        jsr putchar
        inx
        inx
        jmp next

h_key:  DW h_emit
        DB 3
        DB "KEY"
key:
        jsr getkey
        dex
        dex
        sta $0200,x
        lda #$00
        sta $0201,x
        jmp next

h_dot:  DW h_key
        DB 1
        DB "."
dot:
        lda $0200,x
        sta num
        lda $0201,x
        sta num+1
        inx
        inx
        lda num+1
        bpl dot2
        lda #$2d             ; '-'
        jsr putchar
        sec
        lda #$00
        sbc num
        sta num
        lda #$00
        sbc num+1
        sta num+1
dot2:   jsr prunum
        lda #$20
        jsr putchar
        jmp next

h_cr:   DW h_dot
        DB 2
        DB "CR"
cr:
        lda #$0d
        jsr putchar
        jmp next

h_space: DW h_cr
        DB 5
        DB "SPACE"
space:
        lda #$20
        jsr putchar
        jmp next

h_cls:  DW h_space
        DB 3
        DB "CLS"
cls:
        stx savex
        jsr clrscr
        ldx savex
        jmp next

h_here: DW h_cls
        DB 4
        DB "HERE"
here:
        dex
        dex
        lda dp
        sta $0200,x
        lda dp+1
        sta $0201,x
        jmp next

h_comma: DW h_here
        DB 1
        DB ","
w_comma:
        lda $0200,x
        sta tmp1
        lda $0201,x
        sta tmp1+1
        inx
        inx
        jsr comma
        jmp next

h_allot: DW h_comma
        DB 5
        DB "ALLOT"
allot:
        clc
        lda $0200,x
        adc dp
        sta dp
        lda $0201,x
        adc dp+1
        sta dp+1
        inx
        inx
        jmp next

; ---------------------------------------------------------------
; Defining and control words
; ---------------------------------------------------------------
h_colon: DW h_allot
        DB 1
        DB ":"
colon:
        jsr parseword
        bcc colerr
        jsr make_header
        lda #<docol
        sta tmp1
        lda #>docol
        sta tmp1+1
        jsr comma_jsr        ; code field = JSR DOCOL
        lda #$01
        sta state            ; enter compile mode
        jmp next
colerr: jmp quit

h_semi: DW h_colon
        DB $81               ; immediate, length 1
        DB ";"
semi:
        lda #<exit
        sta tmp1
        lda #>exit
        sta tmp1+1
        jsr comma            ; compile EXIT
        lda newdef
        sta latest           ; publish the new definition
        lda newdef+1
        sta latest+1
        lda #$00
        sta state
        jmp next

h_if:   DW h_semi
        DB $82
        DB "IF"
w_if:
        lda #<zbranch
        sta tmp1
        lda #>zbranch
        sta tmp1+1
        jsr comma            ; compile 0BRANCH
        dex
        dex
        lda dp
        sta $0200,x          ; leave the slot address for THEN/ELSE
        lda dp+1
        sta $0201,x
        lda dp
        clc
        adc #$02
        sta dp
        bcc if1
        inc dp+1
if1:    jmp next

h_else: DW h_if
        DB $84
        DB "ELSE"
w_else:
        lda #<branch
        sta tmp1
        lda #>branch
        sta tmp1+1
        jsr comma            ; compile BRANCH
        ; old IF slot is on the stack -> point it just past this branch slot
        lda $0200,x
        sta tmp2
        lda $0201,x
        sta tmp2+1
        lda dp
        clc
        adc #$02
        sta tmp3
        lda dp+1
        adc #$00
        sta tmp3+1
        ldy #$00
        lda tmp3
        sta (tmp2),y
        iny
        lda tmp3+1
        sta (tmp2),y
        ; leave the new (branch) slot for THEN
        lda dp
        sta $0200,x
        lda dp+1
        sta $0201,x
        lda dp
        clc
        adc #$02
        sta dp
        bcc el1
        inc dp+1
el1:    jmp next

h_then: DW h_else
        DB $84
        DB "THEN"
w_then:
        lda $0200,x
        sta tmp1
        lda $0201,x
        sta tmp1+1
        inx
        inx
        ldy #$00
        lda dp
        sta (tmp1),y
        iny
        lda dp+1
        sta (tmp1),y
        jmp next

h_begin: DW h_then
        DB $85
        DB "BEGIN"
w_begin:
        dex
        dex
        lda dp
        sta $0200,x
        lda dp+1
        sta $0201,x
        jmp next

h_until: DW h_begin
        DB $85
        DB "UNTIL"
w_until:
        lda #<zbranch
        sta tmp1
        lda #>zbranch
        sta tmp1+1
        jsr comma
        lda $0200,x
        sta tmp1
        lda $0201,x
        sta tmp1+1
        inx
        inx
        jsr comma
        jmp next

h_again: DW h_until
        DB $85
        DB "AGAIN"
w_again:
        lda #<branch
        sta tmp1
        lda #>branch
        sta tmp1+1
        jsr comma
        lda $0200,x
        sta tmp1
        lda $0201,x
        sta tmp1+1
        inx
        inx
        jsr comma
        jmp next

h_variable: DW h_again
        DB 8
        DB "VARIABLE"
variable:
        jsr parseword
        bcc varerr
        jsr make_header
        lda #<dovar
        sta tmp1
        lda #>dovar
        sta tmp1+1
        jsr comma_jsr        ; code field = JSR DOVAR
        lda #$00
        sta tmp1
        sta tmp1+1
        jsr comma            ; one cell, initialised to 0
        lda newdef
        sta latest
        lda newdef+1
        sta latest+1
        jmp next
varerr: jmp quit

h_constant: DW h_variable
        DB 8
        DB "CONSTANT"
constant:
        lda $0200,x
        sta tmp3
        lda $0201,x
        sta tmp3+1
        inx
        inx
        jsr parseword
        bcc conerr
        jsr make_header
        lda #<docon
        sta tmp1
        lda #>docon
        sta tmp1+1
        jsr comma_jsr        ; code field = JSR DOCON
        lda tmp3
        sta tmp1
        lda tmp3+1
        sta tmp1+1
        jsr comma
        lda newdef
        sta latest
        lda newdef+1
        sta latest+1
        jmp next
conerr: jmp quit

; SAVE  ( -- )   Write the compiled dictionary ($2000..HERE) to a host file as
; an image: a $00 marker, HERE, LATEST, then the bytes. LOAD restores it.
h_save: DW h_constant
        DB 4
        DB "SAVE"
save:
        lda #$53
        sta filecmd          ; 'S' begin save
        lda #$00
        sta filedata         ; image marker
        lda dp
        sta filedata
        lda dp+1
        sta filedata         ; HERE
        lda latest
        sta filedata
        lda latest+1
        sta filedata         ; LATEST
        lda #$00
        sta saveptr
        lda #$20
        sta saveptr+1        ; from $2000
svlp:   lda saveptr+1
        cmp dp+1
        bcc svby
        bne svend
        lda saveptr
        cmp dp
        bcs svend
svby:   ldy #$00
        lda (saveptr),y
        sta filedata
        inc saveptr
        bne svlp
        inc saveptr+1
        jmp svlp
svend:  lda #$45
        sta filecmd          ; 'E' commit
        jmp next

; LOAD  ( -- )   Open a host file. A dictionary image (leading $00) is restored;
; anything else is treated as Forth source and interpreted as if typed.
h_last:
h_load: DW h_save
        DB 4
        DB "LOAD"
load:
        lda #$4c
        sta filecmd          ; 'L' start load
ldwt:   lda filecmd
        and #$80
        bne ldwt             ; wait while busy
        lda filecmd
        and #$02
        bne lderr
        lda filecmd
        and #$01
        beq lddone           ; empty file
        lda filedata         ; first byte
        bne ldtext           ; nonzero -> source text
        ; ---- restore a dictionary image ----
        lda filedata
        sta dp
        lda filedata
        sta dp+1
        lda filedata
        sta latest
        lda filedata
        sta latest+1
        lda #$00
        sta saveptr
        lda #$20
        sta saveptr+1
rslp:   lda saveptr+1
        cmp dp+1
        bcc rsby
        bne lddone
        lda saveptr
        cmp dp
        bcs lddone
rsby:   lda filedata
        ldy #$00
        sta (saveptr),y
        inc saveptr
        bne rslp
        inc saveptr+1
        jmp rslp
ldtext: sta pbchar           ; push the first byte back
        lda #$01
        sta pbflag
        sta loadact          ; feed the rest of the file to getkey
lddone: jmp next
lderr:  lda #$3f             ; '?'
        jsr putchar
        lda #$0d
        jsr putchar
        jmp next

; ---------------------------------------------------------------
; Compiler / interpreter support (assembly subroutines)
; ---------------------------------------------------------------

; Append the 16-bit value in tmp1 to HERE.
comma:
        ldy #$00
        lda tmp1
        sta (dp),y
        iny
        lda tmp1+1
        sta (dp),y
        lda dp
        clc
        adc #$02
        sta dp
        bcc cm1
        inc dp+1
cm1:    rts

; Append a "JSR tmp1" instruction (3 bytes) to HERE. Used to write the code
; field of colon / VARIABLE / CONSTANT definitions under direct threading.
comma_jsr:
        ldy #$00
        lda #$20             ; JSR opcode
        sta (dp),y
        iny
        lda tmp1
        sta (dp),y
        iny
        lda tmp1+1
        sta (dp),y
        lda dp
        clc
        adc #$03
        sta dp
        bcc cj1
        inc dp+1
cj1:    rts

; Build a dictionary header from wbuf/wlen: link, length, name.
; Records the header address in newdef and leaves HERE at the code field.
make_header:
        lda dp
        sta newdef
        lda dp+1
        sta newdef+1
        ldy #$00
        lda latest
        sta (dp),y
        iny
        lda latest+1
        sta (dp),y
        iny
        lda wlen
        sta (dp),y
        lda dp
        clc
        adc #$03
        sta dp
        bcc mh1
        inc dp+1
mh1:    ldy #$00
mh2:    cpy wlen
        beq mh3
        lda wbuf,y
        sta (dp),y
        iny
        jmp mh2
mh3:    tya
        clc
        adc dp
        sta dp
        bcc mh4
        inc dp+1
mh4:    rts

; Parse the next space-delimited word from the input buffer into wbuf.
; Returns carry set and wlen>0 if a word was found, carry clear at end.
parseword:
        ldy toin
pwsk:   cpy ntib
        bcs pwnone
        lda tib,y
        cmp #$20
        bne pwst
        iny
        jmp pwsk
pwst:   lda #<wbuf
        sta wptr
        lda #>wbuf
        sta wptr+1
        lda #$00
        sta wlen
pwcol:  cpy ntib
        bcs pwend
        lda tib,y
        cmp #$20
        beq pwend
        cmp #$61             ; 'a'
        bcc pwsto
        cmp #$7b             ; 'z'+1
        bcs pwsto
        and #$df             ; fold to upper case
pwsto:  sty tmpy
        ldy #$00
        sta (wptr),y
        inc wptr
        bne pws2
        inc wptr+1
pws2:   inc wlen
        ldy tmpy
        iny
        jmp pwcol
pwend:  sty toin
        sec
        rts
pwnone: sty toin
        clc
        rts

; Search the dictionary for wbuf/wlen. Carry set if found, with the CFA in
; tmp1 and immflag = the immediate bit. Carry clear if not found.
find:
        lda latest
        sta tmp2
        lda latest+1
        sta tmp2+1
floop:  lda tmp2
        ora tmp2+1
        bne fhave
        clc
        rts
fhave:  ldy #$02
        lda (tmp2),y
        sta tmp3             ; flags+length
        and #$1f
        cmp wlen
        bne fnext
        lda tmp2
        clc
        adc #$03
        sta namep
        lda tmp2+1
        adc #$00
        sta namep+1
        ldy #$00
fcmp:   cpy wlen
        beq fmatch
        lda (namep),y
        cmp wbuf,y
        bne fnext
        iny
        jmp fcmp
fmatch: lda namep
        clc
        adc wlen
        sta tmp1
        lda namep+1
        adc #$00
        sta tmp1+1
        lda tmp3
        and #$80
        sta immflag
        sec
        rts
fnext:  ldy #$00
        lda (tmp2),y
        pha
        iny
        lda (tmp2),y
        sta tmp2+1
        pla
        sta tmp2
        jmp floop

; Parse wbuf/wlen as a signed decimal number into tmp1.
; Carry set on success, carry clear if it is not a valid number.
number:
        ldy #$00
        lda #$00
        sta tmp1
        sta tmp1+1
        sta numneg
        lda wbuf
        cmp #$2d             ; '-'
        bne numlp
        lda #$01
        sta numneg
        iny
        cpy wlen
        bcc numlp
        clc                  ; a lone '-' is not a number
        rts
numlp:  cpy wlen
        bcs numdone
        lda wbuf,y
        cmp #$30             ; '0'
        bcc numbad
        cmp #$3a             ; '9'+1
        bcs numbad
        sec
        sbc #$30
        sta tmpdig
        sty tmpy
        jsr mul10
        clc
        lda tmp1
        adc tmpdig
        sta tmp1
        lda tmp1+1
        adc #$00
        sta tmp1+1
        ldy tmpy
        iny
        jmp numlp
numdone: lda numneg
        beq numok
        sec
        lda #$00
        sbc tmp1
        sta tmp1
        lda #$00
        sbc tmp1+1
        sta tmp1+1
numok:  sec
        rts
numbad: clc
        rts

; tmp1 = tmp1 * 10
mul10:
        lda tmp1
        asl a
        sta tmp2
        lda tmp1+1
        rol a
        sta tmp2+1           ; tmp2 = tmp1 * 2
        asl tmp2
        rol tmp2+1           ; tmp2 = tmp1 * 4
        asl tmp2
        rol tmp2+1           ; tmp2 = tmp1 * 8
        clc
        lda tmp1
        asl a
        sta tmp3
        lda tmp1+1
        rol a
        sta tmp3+1           ; tmp3 = tmp1 * 2
        clc
        lda tmp2
        adc tmp3
        sta tmp1
        lda tmp2+1
        adc tmp3+1
        sta tmp1+1
        rts

; Prepare a signed division of NOS by TOS (from the data stack).
; Sets num = |dividend|, den = |divisor|, records qsign/rsign, then
; leaves quotient in num and remainder in rem (unsigned) via udiv16.
setdiv:
        lda $0202,x
        sta num
        lda $0203,x
        sta num+1
        lda $0200,x
        sta den
        lda $0201,x
        sta den+1
        ; rsign = sign(dividend)
        lda num+1
        and #$80
        sta rsign
        ; qsign = sign(dividend) xor sign(divisor)
        lda num+1
        eor den+1
        and #$80
        sta qsign
        ; abs(num)
        lda num+1
        bpl sd1
        sec
        lda #$00
        sbc num
        sta num
        lda #$00
        sbc num+1
        sta num+1
sd1:    lda den+1
        bpl sd2
        sec
        lda #$00
        sbc den
        sta den
        lda #$00
        sbc den+1
        sta den+1
sd2:    ; divisor zero -> quotient 0, remainder 0
        lda den
        ora den+1
        bne sd3
        lda #$00
        sta num
        sta num+1
        sta rem
        sta rem+1
        rts
sd3:    jsr udiv16
        rts

; num / den -> quotient in num, remainder in rem (16-bit unsigned).
udiv16:
        lda #$00
        sta rem
        sta rem+1
        ldy #16
ud1:    asl num
        rol num+1
        rol rem
        rol rem+1
        lda rem+1
        cmp den+1
        bcc ud2
        bne ud3
        lda rem
        cmp den
        bcc ud2
ud3:    sec
        lda rem
        sbc den
        sta rem
        lda rem+1
        sbc den+1
        sta rem+1
        inc num
ud2:    dey
        bne ud1
        rts

; negate num (16-bit)
negnum:
        sec
        lda #$00
        sbc num
        sta num
        lda #$00
        sbc num+1
        sta num+1
        rts

; Print the unsigned 16-bit value in num as decimal.
prunum:
        lda #$00
        sta dcount
        lda num
        ora num+1
        bne prlp
        lda #$30
        jsr putchar
        rts
prlp:   lda num
        ora num+1
        beq prem
        lda #10
        sta den
        lda #$00
        sta den+1
        jsr udiv16           ; num = quotient, rem = digit
        ldy dcount
        lda rem
        clc
        adc #$30
        sta numbuf,y
        inc dcount
        jmp prlp
prem:   ldy dcount
prem1:  dey
        lda numbuf,y
        jsr putchar
        cpy #$00
        bne prem1
        rts

; Print the NUL-terminated string pointed to by tmp1.
prstr:
        ldy #$00
prs1:   lda (tmp1),y
        beq prs2
        jsr putchar
        iny
        jmp prs1
prs2:   rts

; Print the parsed word (wbuf/wlen) followed by " ?" and a newline.
print_wbuf:
        ldy #$00
pwb1:   cpy wlen
        beq pwb2
        lda wbuf,y
        jsr putchar
        iny
        jmp pwb1
pwb2:   lda #$20
        jsr putchar
        lda #$3f
        jsr putchar
        lda #$0d
        jsr putchar
        rts

; ---------------------------------------------------------------
; Console I/O (reused from the Tiny BASIC interpreter)
; ---------------------------------------------------------------
readline:
        ldy #$00
rl0:    jsr getkey
        cmp #$0d
        beq rldone
        cmp #$08
        beq rlbs
        cmp #$7f
        beq rlbs
        sta tib,y
        jsr putchar
        iny
        cpy #$7e
        bcc rl0
        jmp rl0
rlbs:   cpy #$00
        beq rl0
        dey
        jsr bsdel
        jmp rl0
rldone: sty ntib
        lda #$0d
        jsr putchar
        rts

; Fetch the next input character. While a LOAD is active the characters come
; from the host file instead of the keyboard, so a source file is interpreted
; exactly as if it were typed.
getkey: lda loadact
        beq getkbd
        lda pbflag
        beq gkfile
        lda #$00             ; return the pushed-back first byte
        sta pbflag
        lda pbchar
        rts
gkfile: lda filecmd          ; status
        and #$01
        beq gkend            ; no more file data
        lda filedata         ; read a byte (advances the host cursor)
        cmp #$0a
        bne gkret
        lda #$0d             ; translate LF -> CR
gkret:  rts
gkend:  lda #$00
        sta loadact          ; end of file -> back to the keyboard
        lda #$0d             ; terminate the final line
        rts
getkbd: lda kbd
        bpl getkbd
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

; ---------------------------------------------------------------
; Data
; ---------------------------------------------------------------
bannermsg: DB "FORTH", $00
okmsg:  DB "ok", $00
