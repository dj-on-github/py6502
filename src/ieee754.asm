; ============================================================================
; ieee754.asm  --  IEEE 754 binary64 (double precision) library for 6502/65C02
; ----------------------------------------------------------------------------
; Target assembler : asm6502.py (py6502)
; CPU              : 65C02 (uses bra, stz, phx, plx, (zp), ina, dea)
;
; This is the "minimal, truncation, no special values" variant:
;   * Rounding     : truncation toward zero
;   * Denormals    : flushed to zero on unpack
;   * NaN / +-Inf  : not produced or detected; treated as ordinary numbers
;   * Exponent overflow / underflow: silently wraps
;
; Supported entry points:
;
;   unpack1, unpack2   (ptr1|ptr2) -> FAC1|FAC2
;   pack1              FAC1 -> (ptr1)
;   cpy_f2_f1          FAC2 -> FAC1
;   cpy_f1_f2          FAC1 -> FAC2
;   neg_f1             negate FAC1
;   fadd               FAC1 <- FAC1 + FAC2
;   fsub               FAC1 <- FAC1 - FAC2
;   fmul               FAC1 <- FAC1 * FAC2
;   fdiv               FAC1 <- FAC1 / FAC2
;   fcmp               A = 0 (=), 1 (FAC1>FAC2), $ff (FAC1<FAC2)
;   itof32             FAC1 <- signed int32 in fac1_m0..fac1_m3
;   ftoi32             fac1_m0..fac1_m3 <- signed int32(FAC1)
;   ftoa               write decimal string (ptr1) from FAC1
;   atof               read decimal string (ptr1) into FAC1
;
; Calling convention:
;   * All routines are plain jsr/rts.
;   * They do not preserve A,X,Y; they do preserve the stack.
;   * FAC1, FAC2 and scratch live in zero page (see layout below).
;   * ptr1, ptr2 are zero-page 16-bit pointers used by the caller to tell
;     unpack / pack / ftoa / atof where to read/write bytes.
;
; Internal unpacked representation:
;
;   FAC*_S       sign byte         $00 = +, $80 = -
;   FAC*_E       2-byte signed unbiased exponent, little-endian
;   FAC*_M0..M7  8-byte mantissa, little-endian. When normalized, the
;                implicit leading 1 sits at bit 52 (M6 bit 4). Bits 0..51
;                hold the fraction. Bits 53..63 are scratch/overflow space.
;
;   A value of zero is represented by *any* exponent and a mantissa that
;   is all zero.  Arithmetic routines always produce zero this way.
;
; Packed storage (as written by pack1 / read by unpack1):
;   Standard IEEE 754 binary64, little-endian, 8 bytes:
;     byte 0..5                       : fraction bits 0..47
;     byte 6 low  nibble              : fraction bits 48..51
;     byte 6 high nibble              : biased-exponent bits 0..3
;     byte 7 bits 0..6                : biased-exponent bits 4..10
;     byte 7 bit  7                   : sign
;   Bias = 1023 ($3ff).
;
; David Johnston / Claude, 2026.
; ============================================================================


; ----------------------------------------------------------------------------
; Zero-page layout.  Every byte has its own symbol because asm6502.py does not
; accept arithmetic in operand fields -- there is no "FAC1_M + 3".
; ----------------------------------------------------------------------------

; --- first floating-point accumulator (FAC1) ---
fac1_m0:  equ $80    ; mantissa byte 0 (LSB)
fac1_m1:  equ $81
fac1_m2:  equ $82
fac1_m3:  equ $83
fac1_m4:  equ $84
fac1_m5:  equ $85
fac1_m6:  equ $86    ; mantissa byte 6 (MSB of 53-bit significand)
fac1_m7:  equ $87    ; overflow byte -- used by fadd during carry-out
fac1_e0:  equ $88    ; exponent low  byte (signed 16-bit, unbiased)
fac1_e1:  equ $89    ; exponent high byte
fac1_s:   equ $8a    ; sign byte ($00 or $80)

; --- second floating-point accumulator (FAC2) ---
fac2_m0:  equ $8b
fac2_m1:  equ $8c
fac2_m2:  equ $8d
fac2_m3:  equ $8e
fac2_m4:  equ $8f
fac2_m5:  equ $90
fac2_m6:  equ $91
fac2_m7:  equ $92
fac2_e0:  equ $93
fac2_e1:  equ $94
fac2_s:   equ $95

; --- caller-supplied 16-bit pointers ---
ptr1:     equ $96
ptr1h:    equ $97
ptr2:     equ $98
ptr2h:    equ $99

; --- general scratch ---
tmp0:     equ $9a
tmp1:     equ $9b
tmp2:     equ $9c
tmp3:     equ $9d
count:    equ $9e
decexp0:  equ $9f    ; decimal exponent used by ftoa/atof (signed 16-bit)
decexp1:  equ $a0

; --- extra scratch (used as tmp4..tmp7 for the fdiv trial subtract) ---
tmp4:     equ $b1
tmp5:     equ $b2
tmp6:     equ $b3
tmp7:     equ $b4

; --- 128-bit product / dividend / scratch mantissa ---
bigm0:    equ $a1
bigm1:    equ $a2
bigm2:    equ $a3
bigm3:    equ $a4
bigm4:    equ $a5
bigm5:    equ $a6
bigm6:    equ $a7
bigm7:    equ $a8
bigm8:    equ $a9
bigm9:    equ $aa
bigma:    equ $ab
bigmb:    equ $ac
bigmc:    equ $ad
bigmd:    equ $ae
bigme:    equ $af
bigmf:    equ $b0

; ============================================================================
; Entry points are below.  Layout is plain code -- place an ORG before
; including this file, or assemble it at some fixed address with asm6502.
; ============================================================================

; ----------------------------------------------------------------------------
; Fixed-address constants (placed here so their high/low byte pointers are
; known at assemble time as plain literals).  If you relocate these, update
; the #$ff immediates in fmul_by_ten / fdiv_by_ten / ftoa / atof_exp_loop.
; ----------------------------------------------------------------------------
                org  $0280
ten_double:
        db   $00,$00,$00,$00,$00,$00,$24,$40    ; 10.0

                org  $0288
tenth_double:
        db   $9a,$99,$99,$99,$99,$99,$b9,$3f    ; 0.1 (nearest double)

                org  $0290
one_double:
        db   $00,$00,$00,$00,$00,$00,$f0,$3f    ; 1.0

                org  $1000

; ----------------------------------------------------------------------------
; unpack1 : decode the 8-byte IEEE 754 value at (ptr1) into FAC1.
; unpack2 : ditto for (ptr2) -> FAC2.
; Destroys A, Y.  ptr1/ptr2 unchanged.
; ----------------------------------------------------------------------------
unpack1:
        ldy  #0
        lda  (ptr1),y
        sta  fac1_m0
        iny
        lda  (ptr1),y
        sta  fac1_m1
        iny
        lda  (ptr1),y
        sta  fac1_m2
        iny
        lda  (ptr1),y
        sta  fac1_m3
        iny
        lda  (ptr1),y
        sta  fac1_m4
        iny
        lda  (ptr1),y
        sta  fac1_m5
        iny
        lda  (ptr1),y
        sta  fac1_m6           ; low nibble = fraction[51:48], high = expo[3:0]
        iny
        lda  (ptr1),y
        sta  fac1_m7           ; bit7=sign, bits0..6=expo[10:4]
        jmp  unpack_common_f1

unpack2:
        ldy  #0
        lda  (ptr2),y
        sta  fac2_m0
        iny
        lda  (ptr2),y
        sta  fac2_m1
        iny
        lda  (ptr2),y
        sta  fac2_m2
        iny
        lda  (ptr2),y
        sta  fac2_m3
        iny
        lda  (ptr2),y
        sta  fac2_m4
        iny
        lda  (ptr2),y
        sta  fac2_m5
        iny
        lda  (ptr2),y
        sta  fac2_m6
        iny
        lda  (ptr2),y
        sta  fac2_m7
        jmp  unpack_common_f2

; --- shared unpack tail for FAC1 ---
unpack_common_f1:
        ; sign
        lda  fac1_m7
        and  #$80
        sta  fac1_s
        ; biased exponent low 4 bits = M6 high nibble
        lda  fac1_m6
        and  #$f0
        lsr  a
        lsr  a
        lsr  a
        lsr  a
        sta  fac1_e0
        ; biased exponent high 7 bits = M7 bits 0..6 -- put into bits 4..10
        lda  fac1_m7
        and  #$7f
        sta  tmp0
        ; tmp0 low 4 bits -> fac1_e0 high nibble
        asl  a
        asl  a
        asl  a
        asl  a
        ora  fac1_e0
        sta  fac1_e0
        ; tmp0 high 3 bits -> fac1_e1 low 3 bits
        lda  tmp0
        lsr  a
        lsr  a
        lsr  a
        lsr  a
        sta  fac1_e1
        ; --- zero / denormal detection ---
        lda  fac1_e0
        ora  fac1_e1
        bne  unpack_f1_normal
        ; biased exp == 0: flush to zero
        stz  fac1_m0
        stz  fac1_m1
        stz  fac1_m2
        stz  fac1_m3
        stz  fac1_m4
        stz  fac1_m5
        stz  fac1_m6
        stz  fac1_m7
        stz  fac1_s
        stz  fac1_e0
        stz  fac1_e1
        rts
unpack_f1_normal:
        ; unbias: subtract 1023
        sec
        lda  fac1_e0
        sbc  #$ff
        sta  fac1_e0
        lda  fac1_e1
        sbc  #$03
        sta  fac1_e1
        ; clean up mantissa: mask out exp bits in M6, zero M7, set implicit 1
        lda  fac1_m6
        and  #$0f
        ora  #$10              ; implicit 1 at bit 52 (M6 bit 4)
        sta  fac1_m6
        stz  fac1_m7
        rts

; --- shared unpack tail for FAC2 (same logic, different accumulator) ---
unpack_common_f2:
        lda  fac2_m7
        and  #$80
        sta  fac2_s
        lda  fac2_m6
        and  #$f0
        lsr  a
        lsr  a
        lsr  a
        lsr  a
        sta  fac2_e0
        lda  fac2_m7
        and  #$7f
        sta  tmp0
        asl  a
        asl  a
        asl  a
        asl  a
        ora  fac2_e0
        sta  fac2_e0
        lda  tmp0
        lsr  a
        lsr  a
        lsr  a
        lsr  a
        sta  fac2_e1
        lda  fac2_e0
        ora  fac2_e1
        bne  unpack_f2_normal
        stz  fac2_m0
        stz  fac2_m1
        stz  fac2_m2
        stz  fac2_m3
        stz  fac2_m4
        stz  fac2_m5
        stz  fac2_m6
        stz  fac2_m7
        stz  fac2_s
        stz  fac2_e0
        stz  fac2_e1
        rts
unpack_f2_normal:
        sec
        lda  fac2_e0
        sbc  #$ff
        sta  fac2_e0
        lda  fac2_e1
        sbc  #$03
        sta  fac2_e1
        lda  fac2_m6
        and  #$0f
        ora  #$10
        sta  fac2_m6
        stz  fac2_m7
        rts

; ----------------------------------------------------------------------------
; pack1 : encode FAC1 into 8 bytes at (ptr1).
; Destroys A, Y.
; ----------------------------------------------------------------------------
pack1:
        ; Zero check -- mantissa all zero means value is zero.
        jsr  iszero_f1
        bne  pack1_nz
        ldy  #0
        lda  #0
pack1_zl:
        sta  (ptr1),y
        iny
        cpy  #8
        bne  pack1_zl
        rts
pack1_nz:
        ; biased exponent = unbiased + 1023
        clc
        lda  fac1_e0
        adc  #$ff
        sta  tmp0              ; biased exp low
        lda  fac1_e1
        adc  #$03
        sta  tmp1              ; biased exp high (only low 3 bits valid)
        ; write bytes 0..5 straight through
        ldy  #0
        lda  fac1_m0
        sta  (ptr1),y
        iny
        lda  fac1_m1
        sta  (ptr1),y
        iny
        lda  fac1_m2
        sta  (ptr1),y
        iny
        lda  fac1_m3
        sta  (ptr1),y
        iny
        lda  fac1_m4
        sta  (ptr1),y
        iny
        lda  fac1_m5
        sta  (ptr1),y
        iny
        ; byte 6: low nibble = fraction bits 48..51 (M6 low nibble),
        ;         high nibble = biased-exp bits 0..3
        lda  fac1_m6
        and  #$0f
        sta  tmp2
        lda  tmp0
        asl  a
        asl  a
        asl  a
        asl  a
        ora  tmp2
        sta  (ptr1),y          ; Y = 6
        iny
        ; byte 7: bit7 = sign, bits0..6 = biased-exp bits 4..10
        lda  tmp0
        lsr  a
        lsr  a
        lsr  a
        lsr  a
        sta  tmp2              ; exp bits 4..7 now in bits 0..3 of tmp2
        lda  tmp1
        and  #$07
        asl  a
        asl  a
        asl  a
        asl  a
        ora  tmp2              ; merge exp bits 8..10 into bits 4..6
        ora  fac1_s            ; OR sign into bit 7
        sta  (ptr1),y          ; Y = 7
        rts

; ----------------------------------------------------------------------------
; iszero_f1 / iszero_f2 : Z flag set (and A=0) iff mantissa is all zero.
; ----------------------------------------------------------------------------
iszero_f1:
        lda  fac1_m0
        ora  fac1_m1
        ora  fac1_m2
        ora  fac1_m3
        ora  fac1_m4
        ora  fac1_m5
        ora  fac1_m6
        ora  fac1_m7
        rts

iszero_f2:
        lda  fac2_m0
        ora  fac2_m1
        ora  fac2_m2
        ora  fac2_m3
        ora  fac2_m4
        ora  fac2_m5
        ora  fac2_m6
        ora  fac2_m7
        rts

; ----------------------------------------------------------------------------
; cpy_f2_f1 : copy FAC2 -> FAC1
; cpy_f1_f2 : copy FAC1 -> FAC2
; ----------------------------------------------------------------------------
cpy_f2_f1:
        lda  fac2_m0
        sta  fac1_m0
        lda  fac2_m1
        sta  fac1_m1
        lda  fac2_m2
        sta  fac1_m2
        lda  fac2_m3
        sta  fac1_m3
        lda  fac2_m4
        sta  fac1_m4
        lda  fac2_m5
        sta  fac1_m5
        lda  fac2_m6
        sta  fac1_m6
        lda  fac2_m7
        sta  fac1_m7
        lda  fac2_e0
        sta  fac1_e0
        lda  fac2_e1
        sta  fac1_e1
        lda  fac2_s
        sta  fac1_s
        rts

cpy_f1_f2:
        lda  fac1_m0
        sta  fac2_m0
        lda  fac1_m1
        sta  fac2_m1
        lda  fac1_m2
        sta  fac2_m2
        lda  fac1_m3
        sta  fac2_m3
        lda  fac1_m4
        sta  fac2_m4
        lda  fac1_m5
        sta  fac2_m5
        lda  fac1_m6
        sta  fac2_m6
        lda  fac1_m7
        sta  fac2_m7
        lda  fac1_e0
        sta  fac2_e0
        lda  fac1_e1
        sta  fac2_e1
        lda  fac1_s
        sta  fac2_s
        rts

; ----------------------------------------------------------------------------
; neg_f1 : flip the sign byte of FAC1.  No effect on zero.
; ----------------------------------------------------------------------------
neg_f1:
        lda  fac1_s
        eor  #$80
        sta  fac1_s
        rts

; ============================================================================
; Mantissa helpers
; ============================================================================

; mshr1_f1 : logical shift FAC1 mantissa right by 1 bit (M7..M0)
mshr1_f1:
        lsr  fac1_m7
        ror  fac1_m6
        ror  fac1_m5
        ror  fac1_m4
        ror  fac1_m3
        ror  fac1_m2
        ror  fac1_m1
        ror  fac1_m0
        rts

; mshl1_f1 : logical shift FAC1 mantissa left by 1 bit (M0..M7)
mshl1_f1:
        asl  fac1_m0
        rol  fac1_m1
        rol  fac1_m2
        rol  fac1_m3
        rol  fac1_m4
        rol  fac1_m5
        rol  fac1_m6
        rol  fac1_m7
        rts

; mshr_f1 : shift FAC1 mantissa right by N bits, N in X.
;           X==0 is a no-op.  X>64 just zeros the mantissa.
mshr_f1:
        cpx  #0
        bne  mshr_f1_loop
        rts
mshr_f1_loop:
        jsr  mshr1_f1
        dex
        bne  mshr_f1_loop
        rts

; normalize_f1 : shift FAC1 mantissa left until bit 52 (M6 bit 4) is set,
;                decrementing exponent for each shift.  If the mantissa is
;                already larger than that (overflow after add), first shift
;                right and bump exponent up until bit 52 is the leading bit.
;                If mantissa is all zero, returns with everything cleared.
normalize_f1:
        jsr  iszero_f1
        bne  norm_f1_nz
        ; true zero -- canonicalize
        stz  fac1_s
        stz  fac1_e0
        stz  fac1_e1
        rts
norm_f1_nz:
        ; Check for too-big mantissa: anything set above bit 52?
        ;   Bits 53..55 live in M6 bits 5..7; bits 56..63 in M7.
        lda  fac1_m7
        bne  norm_f1_shr
        lda  fac1_m6
        and  #$e0              ; bits 5..7 of M6
        bne  norm_f1_shr
        ; Check for leading-bit not yet at position 52
        lda  fac1_m6
        and  #$10              ; bit 4 of M6 == bit 52
        bne  norm_f1_done
        ; Shift left; decrement exponent
        jsr  mshl1_f1
        ; dec exp16
        sec
        lda  fac1_e0
        sbc  #1
        sta  fac1_e0
        lda  fac1_e1
        sbc  #0
        sta  fac1_e1
        bra  norm_f1_nz
norm_f1_shr:
        jsr  mshr1_f1
        ; inc exp16
        clc
        lda  fac1_e0
        adc  #1
        sta  fac1_e0
        lda  fac1_e1
        adc  #0
        sta  fac1_e1
        bra  norm_f1_nz
norm_f1_done:
        rts

; ============================================================================
; fadd / fsub
;   fadd : FAC1 <- FAC1 + FAC2
;   fsub : FAC1 <- FAC1 - FAC2
; Sign rules:
;   same sign     : magnitudes add,    result keeps that sign
;   opposite sign : magnitudes subtract, result takes sign of the bigger
; ============================================================================
fsub:
        lda  fac2_s
        eor  #$80
        sta  fac2_s
        ; fall through into fadd

fadd:
        ; zero short-cuts
        jsr  iszero_f2
        beq  fadd_ret          ; FAC2 == 0 -> FAC1 unchanged
        jsr  iszero_f1
        bne  fadd_align
        ; FAC1 == 0 -> result is FAC2
        jmp  cpy_f2_f1

fadd_ret:
        rts

fadd_align:
        ; Align exponents so FAC1_E == FAC2_E.  Shift the smaller mantissa.
        ; Compute signed (FAC1_E - FAC2_E).  Positive -> FAC2 is smaller.
        sec
        lda  fac1_e0
        sbc  fac2_e0
        sta  tmp0
        lda  fac1_e1
        sbc  fac2_e1
        sta  tmp1              ; tmp1:tmp0 = e1 - e2 (signed 16)
        bpl  fadd_f2_smaller
        ; FAC1 exponent smaller -> shift FAC1 right by -(diff)
        ; negate tmp1:tmp0
        sec
        lda  #0
        sbc  tmp0
        sta  tmp0
        lda  #0
        sbc  tmp1
        sta  tmp1
        ; clamp to 64
        lda  tmp1
        bne  fadd_f1_is_neg    ; >= 256 -> huge, FAC1 goes to 0
        lda  tmp0
        cmp  #64
        bcc  fadd_shift_f1
fadd_f1_is_neg:
        ; FAC1 becomes negligible; replace with FAC2
        jmp  cpy_f2_f1
fadd_shift_f1:
        tax
        jsr  mshr_f1
        ; FAC1 exponent now == FAC2 exponent
        lda  fac2_e0
        sta  fac1_e0
        lda  fac2_e1
        sta  fac1_e1
        bra  fadd_do_addsub

fadd_f2_smaller:
        ; shift FAC2 right by tmp1:tmp0
        lda  tmp1
        bne  fadd_f2_tiny
        lda  tmp0
        cmp  #64
        bcs  fadd_f2_tiny
        tax
        jsr  mshr_f2
        bra  fadd_do_addsub
fadd_f2_tiny:
        ; FAC2 is negligible -- FAC1 unchanged
        rts

; --- FAC2 mantissa shift helper (only used by fadd) ---
mshr1_f2:
        lsr  fac2_m7
        ror  fac2_m6
        ror  fac2_m5
        ror  fac2_m4
        ror  fac2_m3
        ror  fac2_m2
        ror  fac2_m1
        ror  fac2_m0
        rts
mshr_f2:
        cpx  #0
        beq  mshr_f2_done
mshr_f2_loop:
        jsr  mshr1_f2
        dex
        bne  mshr_f2_loop
mshr_f2_done:
        rts

fadd_do_addsub:
        ; Now both mantissas share the same exponent in FAC1_E.
        ; Same sign -> add; different sign -> subtract smaller from larger.
        lda  fac1_s
        eor  fac2_s
        bne  fadd_do_sub

        ; ----- same-sign add -----
        clc
        lda  fac1_m0
        adc  fac2_m0
        sta  fac1_m0
        lda  fac1_m1
        adc  fac2_m1
        sta  fac1_m1
        lda  fac1_m2
        adc  fac2_m2
        sta  fac1_m2
        lda  fac1_m3
        adc  fac2_m3
        sta  fac1_m3
        lda  fac1_m4
        adc  fac2_m4
        sta  fac1_m4
        lda  fac1_m5
        adc  fac2_m5
        sta  fac1_m5
        lda  fac1_m6
        adc  fac2_m6
        sta  fac1_m6
        lda  fac1_m7
        adc  fac2_m7
        sta  fac1_m7
        ; sign already correct in fac1_s
        jmp  normalize_f1

fadd_do_sub:
        ; Compute |FAC1_M| - |FAC2_M|.  If result is negative, flip operands.
        ; Compare magnitudes (big-endian order M7..M0).
        lda  fac1_m7
        cmp  fac2_m7
        bne  fadd_cmp_done
        lda  fac1_m6
        cmp  fac2_m6
        bne  fadd_cmp_done
        lda  fac1_m5
        cmp  fac2_m5
        bne  fadd_cmp_done
        lda  fac1_m4
        cmp  fac2_m4
        bne  fadd_cmp_done
        lda  fac1_m3
        cmp  fac2_m3
        bne  fadd_cmp_done
        lda  fac1_m2
        cmp  fac2_m2
        bne  fadd_cmp_done
        lda  fac1_m1
        cmp  fac2_m1
        bne  fadd_cmp_done
        lda  fac1_m0
        cmp  fac2_m0
fadd_cmp_done:
        bcs  fadd_sub_f2_from_f1
        ; |FAC2| > |FAC1| : compute FAC2 - FAC1, take FAC2's sign
        sec
        lda  fac2_m0
        sbc  fac1_m0
        sta  fac1_m0
        lda  fac2_m1
        sbc  fac1_m1
        sta  fac1_m1
        lda  fac2_m2
        sbc  fac1_m2
        sta  fac1_m2
        lda  fac2_m3
        sbc  fac1_m3
        sta  fac1_m3
        lda  fac2_m4
        sbc  fac1_m4
        sta  fac1_m4
        lda  fac2_m5
        sbc  fac1_m5
        sta  fac1_m5
        lda  fac2_m6
        sbc  fac1_m6
        sta  fac1_m6
        lda  fac2_m7
        sbc  fac1_m7
        sta  fac1_m7
        lda  fac2_s
        sta  fac1_s
        jmp  normalize_f1

fadd_sub_f2_from_f1:
        ; |FAC1| >= |FAC2| : compute FAC1 - FAC2, keep FAC1's sign
        sec
        lda  fac1_m0
        sbc  fac2_m0
        sta  fac1_m0
        lda  fac1_m1
        sbc  fac2_m1
        sta  fac1_m1
        lda  fac1_m2
        sbc  fac2_m2
        sta  fac1_m2
        lda  fac1_m3
        sbc  fac2_m3
        sta  fac1_m3
        lda  fac1_m4
        sbc  fac2_m4
        sta  fac1_m4
        lda  fac1_m5
        sbc  fac2_m5
        sta  fac1_m5
        lda  fac1_m6
        sbc  fac2_m6
        sta  fac1_m6
        lda  fac1_m7
        sbc  fac2_m7
        sta  fac1_m7
        jmp  normalize_f1

; ============================================================================
; fmul : FAC1 <- FAC1 * FAC2
;
; Plan:
;   - sign = fac1_s xor fac2_s
;   - if either operand is zero, result is zero
;   - new exponent = FAC1_E + FAC2_E
;   - multiply the two 53-bit mantissas (in 8-byte containers) with a
;     shift-and-add loop producing a 128-bit product in bigm0..bigmf
;   - the product's leading bit is at position 104 or 105; extract 53 bits
;     starting at position 52, normalize, and store back in FAC1_M.
; ============================================================================
fmul:
        ; sign
        lda  fac1_s
        eor  fac2_s
        sta  fac1_s
        ; zero short-cuts
        jsr  iszero_f1
        bne  fmul_f1nz
        rts
fmul_f1nz:
        jsr  iszero_f2
        bne  fmul_go
        ; FAC2 == 0 -> zero out FAC1
        stz  fac1_m0
        stz  fac1_m1
        stz  fac1_m2
        stz  fac1_m3
        stz  fac1_m4
        stz  fac1_m5
        stz  fac1_m6
        stz  fac1_m7
        stz  fac1_s
        stz  fac1_e0
        stz  fac1_e1
        rts
fmul_go:
        ; exponent = e1 + e2
        clc
        lda  fac1_e0
        adc  fac2_e0
        sta  fac1_e0
        lda  fac1_e1
        adc  fac2_e1
        sta  fac1_e1

        ; ---- 64x64 -> 128 bit multiply ----
        ; Initialize bigm0..bigm7 = FAC2_M (multiplier); bigm8..bigmf = 0.
        lda  fac2_m0
        sta  bigm0
        lda  fac2_m1
        sta  bigm1
        lda  fac2_m2
        sta  bigm2
        lda  fac2_m3
        sta  bigm3
        lda  fac2_m4
        sta  bigm4
        lda  fac2_m5
        sta  bigm5
        lda  fac2_m6
        sta  bigm6
        lda  fac2_m7
        sta  bigm7
        stz  bigm8
        stz  bigm9
        stz  bigma
        stz  bigmb
        stz  bigmc
        stz  bigmd
        stz  bigme
        stz  bigmf

        ldx  #64               ; 64 iterations
fmul_loop:
        ; If low bit of bigm0 is 1, add FAC1_M (8 bytes) into bigm8..bigmf.
        lda  bigm0
        and  #$01
        beq  fmul_shift
        clc
        lda  bigm8
        adc  fac1_m0
        sta  bigm8
        lda  bigm9
        adc  fac1_m1
        sta  bigm9
        lda  bigma
        adc  fac1_m2
        sta  bigma
        lda  bigmb
        adc  fac1_m3
        sta  bigmb
        lda  bigmc
        adc  fac1_m4
        sta  bigmc
        lda  bigmd
        adc  fac1_m5
        sta  bigmd
        lda  bigme
        adc  fac1_m6
        sta  bigme
        lda  bigmf
        adc  fac1_m7
        sta  bigmf
fmul_shift:
        ; shift BIGM right by 1 (16 bytes).  Carry from add above doesn't
        ; matter because max value of bigm8..bigmf stays < 2^63.
        lsr  bigmf
        ror  bigme
        ror  bigmd
        ror  bigmc
        ror  bigmb
        ror  bigma
        ror  bigm9
        ror  bigm8
        ror  bigm7
        ror  bigm6
        ror  bigm5
        ror  bigm4
        ror  bigm3
        ror  bigm2
        ror  bigm1
        ror  bigm0
        dex
        bne  fmul_loop

        ; BIGM now holds the 128-bit product (occupying bits 0..105).
        ; We want FAC1_M = product >> 52.  That is: take bigm6..bigmd,
        ; then shift right by 4 more bits.
        lda  bigm6
        sta  fac1_m0
        lda  bigm7
        sta  fac1_m1
        lda  bigm8
        sta  fac1_m2
        lda  bigm9
        sta  fac1_m3
        lda  bigma
        sta  fac1_m4
        lda  bigmb
        sta  fac1_m5
        lda  bigmc
        sta  fac1_m6
        lda  bigmd
        sta  fac1_m7

        ldx  #4
fmul_sh4:
        lsr  fac1_m7
        ror  fac1_m6
        ror  fac1_m5
        ror  fac1_m4
        ror  fac1_m3
        ror  fac1_m2
        ror  fac1_m1
        ror  fac1_m0
        dex
        bne  fmul_sh4

        ; Normalize: if bit 53 (M6 bit 5) set, shift right, bump exponent.
        jmp  normalize_f1

; ============================================================================
; fdiv : FAC1 <- FAC1 / FAC2
;
; Restoring binary division:
;   dividend bigm8..bigmf starts as FAC1_M; bigm0..bigm7 = 0.
;   divisor  is FAC2_M (8 bytes).
;   quotient accumulates into FAC1_M (8 bytes) -- we overwrite as we go.
;   We run 54 iterations to produce 54 quotient bits, then normalize.
;
; If FAC2 == 0 we return whatever-is-in-FAC1 (garbage) -- the spec says this
; should be Inf/NaN, but per the "minimal" contract we do not generate them.
; If FAC1 == 0 we simply return zero.
; ============================================================================
fdiv:
        lda  fac1_s
        eor  fac2_s
        sta  fac1_s
        jsr  iszero_f1
        bne  fdiv_f1nz
        ; 0 / x = 0 ; don't touch sign beyond what was already xor'd
        rts
fdiv_f1nz:
        jsr  iszero_f2
        bne  fdiv_go
        ; Division by zero: per minimal contract, leave FAC1 alone but zero it.
        stz  fac1_m0
        stz  fac1_m1
        stz  fac1_m2
        stz  fac1_m3
        stz  fac1_m4
        stz  fac1_m5
        stz  fac1_m6
        stz  fac1_m7
        stz  fac1_e0
        stz  fac1_e1
        stz  fac1_s
        rts
fdiv_go:
        ; Exponent = e1 - e2 - 1.
        ; We will pre-shift the dividend right by 1 bit to ensure the loop
        ; invariant dividend_hi < divisor holds on entry to the first
        ; iteration.  That pre-shift halves the effective dividend, so we
        ; compensate by adding 1 to the exponent later (equivalently,
        ; subtracting only 1 here instead of 2).  After the 54-iteration
        ; loop the quotient's leading bit lives at position 52 (when
        ; A_mant < B_mant) or 53 (when A_mant >= B_mant); normalize_f1
        ; adjusts the exponent accordingly.
        sec
        lda  fac1_e0
        sbc  fac2_e0
        sta  fac1_e0
        lda  fac1_e1
        sbc  fac2_e1
        sta  fac1_e1
        sec
        lda  fac1_e0
        sbc  #1
        sta  fac1_e0
        lda  fac1_e1
        sbc  #0
        sta  fac1_e1

        ; Set up BIGM: bigm8..bigmf = FAC1_M (dividend high); bigm0..bigm7 = 0
        lda  fac1_m0
        sta  bigm8
        lda  fac1_m1
        sta  bigm9
        lda  fac1_m2
        sta  bigma
        lda  fac1_m3
        sta  bigmb
        lda  fac1_m4
        sta  bigmc
        lda  fac1_m5
        sta  bigmd
        lda  fac1_m6
        sta  bigme
        lda  fac1_m7
        sta  bigmf
        stz  bigm0
        stz  bigm1
        stz  bigm2
        stz  bigm3
        stz  bigm4
        stz  bigm5
        stz  bigm6
        stz  bigm7

        ; Pre-shift the entire 128-bit dividend right by 1 bit so that
        ; dividend_hi (bigm8..bigmf) is now A_mant >> 1, which is
        ; guaranteed to be strictly less than B_mant (since A_mant < 2^53
        ; and B_mant >= 2^52).  The lost low bit drops into bigm7 bit 7,
        ; where it will be shifted back up during the 54-iteration loop.
        lsr  bigmf
        ror  bigme
        ror  bigmd
        ror  bigmc
        ror  bigmb
        ror  bigma
        ror  bigm9
        ror  bigm8
        ror  bigm7

        ; Quotient accumulator -- reuse FAC1_M; clear it.
        stz  fac1_m0
        stz  fac1_m1
        stz  fac1_m2
        stz  fac1_m3
        stz  fac1_m4
        stz  fac1_m5
        stz  fac1_m6
        stz  fac1_m7

        ldx  #54               ; 54 quotient bits (53 + one for normalize)
fdiv_loop:
        ; 1) shift BIGM left by 1 (16 bytes)
        asl  bigm0
        rol  bigm1
        rol  bigm2
        rol  bigm3
        rol  bigm4
        rol  bigm5
        rol  bigm6
        rol  bigm7
        rol  bigm8
        rol  bigm9
        rol  bigma
        rol  bigmb
        rol  bigmc
        rol  bigmd
        rol  bigme
        rol  bigmf
        ; 2) shift quotient (FAC1_M) left by 1
        asl  fac1_m0
        rol  fac1_m1
        rol  fac1_m2
        rol  fac1_m3
        rol  fac1_m4
        rol  fac1_m5
        rol  fac1_m6
        rol  fac1_m7
        ; 3) trial-subtract divisor from dividend high half (bigm8..bigmf)
        ;    into tmp0..tmp7, leaving bigm8..bigmf untouched.
        sec
        lda  bigm8
        sbc  fac2_m0
        sta  tmp0
        lda  bigm9
        sbc  fac2_m1
        sta  tmp1
        lda  bigma
        sbc  fac2_m2
        sta  tmp2
        lda  bigmb
        sbc  fac2_m3
        sta  tmp3
        lda  bigmc
        sbc  fac2_m4
        sta  tmp4
        lda  bigmd
        sbc  fac2_m5
        sta  tmp5
        lda  bigme
        sbc  fac2_m6
        sta  tmp6
        lda  bigmf
        sbc  fac2_m7
        sta  tmp7
        bcc  fdiv_no_fit       ; borrow out -> divisor > dividend, skip
        ; fits: commit the subtraction and set quotient LSB
        lda  tmp0
        sta  bigm8
        lda  tmp1
        sta  bigm9
        lda  tmp2
        sta  bigma
        lda  tmp3
        sta  bigmb
        lda  tmp4
        sta  bigmc
        lda  tmp5
        sta  bigmd
        lda  tmp6
        sta  bigme
        lda  tmp7
        sta  bigmf
        lda  fac1_m0
        ora  #$01
        sta  fac1_m0
fdiv_no_fit:
        dex
        beq  fdiv_done
        jmp  fdiv_loop
fdiv_done:
        ; Quotient is in FAC1_M.  normalize_f1 handles both "leading bit at
        ; position 53" (overshoot) and "at position 52" (just right) cases.
        jmp  normalize_f1

; ============================================================================
; fcmp : compare FAC1 vs FAC2
;   A = $00 if FAC1 == FAC2
;   A = $01 if FAC1 >  FAC2
;   A = $ff if FAC1 <  FAC2
; ============================================================================
fcmp:
        ; Zero handling
        jsr  iszero_f1
        bne  fcmp_f1nz
        ; FAC1 == 0
        jsr  iszero_f2
        bne  fcmp_0_vs_f2
        lda  #0
        rts
fcmp_0_vs_f2:
        ; 0 vs (signed FAC2): if FAC2 positive, FAC1 < FAC2, return $ff
        lda  fac2_s
        bne  fcmp_0vs_f2_neg   ; FAC2 negative -> return $01
        lda  #$ff
        rts
fcmp_0vs_f2_neg:
        lda  #$01
        rts
fcmp_f1nz:
        jsr  iszero_f2
        bne  fcmp_both_nz
        ; FAC2 == 0, FAC1 != 0 : sign of FAC1 determines
        lda  fac1_s
        bne  fcmp_f1_neg       ; FAC1 negative -> return $ff
        lda  #$01
        rts
fcmp_f1_neg:
        lda  #$ff
        rts
fcmp_both_nz:
        ; Signs differ?
        lda  fac1_s
        eor  fac2_s
        beq  fcmp_same_sign
        ; signs differ: positive > negative
        lda  fac1_s
        bne  fcmp_signs_f1_neg
        ; FAC1 >= 0, FAC2 < 0 -> FAC1 > FAC2
        lda  #$01
        rts
fcmp_signs_f1_neg:
        lda  #$ff
        rts

fcmp_same_sign:
        ; Compare exponent (signed 16-bit), then mantissa big-endian.
        lda  fac1_e1
        cmp  fac2_e1
        beq  fcmp_elo
        bpl  fcmp_exp_f1_bigger_or_sign
        ; fac1_e1 < fac2_e1 (unsigned)... but if both exps are signed 16-bit,
        ; signed comparison is what we want.  On 6502, compare signed using:
        ; subtract and look at N^V.  Simpler: restructure the compare.
        ;
        ; Instead of the branch above, redo signed compare properly:
        bra  fcmp_signed_exp   ; (reach fall-through path)
fcmp_exp_f1_bigger_or_sign:
        bra  fcmp_signed_exp
fcmp_signed_exp:
        ; do signed 16-bit compare of FAC1_E vs FAC2_E
        sec
        lda  fac1_e0
        sbc  fac2_e0
        sta  tmp0
        lda  fac1_e1
        sbc  fac2_e1
        ; N^V flag from this subtract tells us sign of difference.
        ; Use BVS / BMI combo; simpler to manually compute.
        sta  tmp1
        ; If tmp1 == 0 and tmp0 == 0 -> equal exp, fall to mantissa compare
        ora  tmp0
        beq  fcmp_mant
        ; diff is non-zero. Sign of signed diff = (tmp1 bit 7) XOR overflow.
        ; Overflow happens if operands differed in sign but result didn't.
        ; For simplicity, examine: is FAC1_E > FAC2_E ?
        ;   if (fac1_e1 bit7 == fac2_e1 bit7) compare normally (higher is bigger)
        ;   else the one with bit7 == 0 is larger (less negative).
        lda  fac1_e1
        eor  fac2_e1
        bmi  fcmp_exp_opposite_sign
        ; same sign high bytes: unsigned compare is correct
        lda  fac1_e1
        cmp  fac2_e1
        bcc  fcmp_exp_f1_less
        bne  fcmp_exp_f1_more
        lda  fac1_e0
        cmp  fac2_e0
        bcc  fcmp_exp_f1_less
        bra  fcmp_exp_f1_more
fcmp_exp_opposite_sign:
        ; high bytes differ in sign -- fac1_e1 bit7 set => FAC1_E negative,
        ; therefore FAC1_E < FAC2_E.
        lda  fac1_e1
        bmi  fcmp_exp_f1_less
        ; else FAC1 > FAC2
fcmp_exp_f1_more:
        ; |FAC1| > |FAC2|; if sign is -, FAC1 < FAC2; else FAC1 > FAC2
        lda  fac1_s
        bne  fcmp_ret_lt
        bra  fcmp_ret_gt
fcmp_exp_f1_less:
        lda  fac1_s
        bne  fcmp_ret_gt
        bra  fcmp_ret_lt

fcmp_elo:
        ; high bytes equal -- fall through to signed/lower compare
        bra  fcmp_signed_exp

fcmp_mant:
        ; Exponents equal; compare mantissas big-endian (M7..M0).
        lda  fac1_m7
        cmp  fac2_m7
        bne  fcmp_mant_done
        lda  fac1_m6
        cmp  fac2_m6
        bne  fcmp_mant_done
        lda  fac1_m5
        cmp  fac2_m5
        bne  fcmp_mant_done
        lda  fac1_m4
        cmp  fac2_m4
        bne  fcmp_mant_done
        lda  fac1_m3
        cmp  fac2_m3
        bne  fcmp_mant_done
        lda  fac1_m2
        cmp  fac2_m2
        bne  fcmp_mant_done
        lda  fac1_m1
        cmp  fac2_m1
        bne  fcmp_mant_done
        lda  fac1_m0
        cmp  fac2_m0
fcmp_mant_done:
        beq  fcmp_ret_eq
        bcs  fcmp_mant_f1_bigger
        ; |FAC1| < |FAC2|
        lda  fac1_s
        bne  fcmp_ret_gt
        bra  fcmp_ret_lt
fcmp_mant_f1_bigger:
        lda  fac1_s
        bne  fcmp_ret_lt
        bra  fcmp_ret_gt

fcmp_ret_eq:
        lda  #0
        rts
fcmp_ret_gt:
        lda  #$01
        rts
fcmp_ret_lt:
        lda  #$ff
        rts

; ============================================================================
; itof32 : convert signed 32-bit integer in fac1_m0..fac1_m3 to FAC1.
;          Upper 4 bytes of the mantissa area are ignored and overwritten.
; ============================================================================
itof32:
        ; Sign from bit 7 of M3
        lda  fac1_m3
        and  #$80
        sta  fac1_s
        beq  itof32_abs
        ; Negative: two's-complement negate the 32-bit value
        sec
        lda  #0
        sbc  fac1_m0
        sta  fac1_m0
        lda  #0
        sbc  fac1_m1
        sta  fac1_m1
        lda  #0
        sbc  fac1_m2
        sta  fac1_m2
        lda  #0
        sbc  fac1_m3
        sta  fac1_m3
itof32_abs:
        ; If value is zero -> zero
        lda  fac1_m0
        ora  fac1_m1
        ora  fac1_m2
        ora  fac1_m3
        bne  itof32_nz
        ; zero out everything and return
        stz  fac1_m0
        stz  fac1_m1
        stz  fac1_m2
        stz  fac1_m3
        stz  fac1_m4
        stz  fac1_m5
        stz  fac1_m6
        stz  fac1_m7
        stz  fac1_s
        stz  fac1_e0
        stz  fac1_e1
        rts
itof32_nz:
        ; Place the 32-bit magnitude into M3..M6 (shift up by 24 bits) so
        ; that the value occupies bits 24..55.  Initial exponent = 31
        ; (accounts for position of the integer's bit 0).
        lda  fac1_m3
        sta  fac1_m6
        lda  fac1_m2
        sta  fac1_m5
        lda  fac1_m1
        sta  fac1_m4
        lda  fac1_m0
        sta  fac1_m3
        stz  fac1_m0
        stz  fac1_m1
        stz  fac1_m2
        stz  fac1_m7
        ; The integer's bit 0 now sits at bit 24 of the mantissa; the value is
        ; N * 2^24, so initial (pre-normalize) exponent = 52 - 24 = 28.
        lda  #28
        sta  fac1_e0
        stz  fac1_e1
        jmp  normalize_f1

; ============================================================================
; ftoi32 : convert FAC1 to signed 32-bit integer, result in fac1_m0..M3.
;          Out-of-range values wrap (no saturation).
;          Rounding: truncation toward zero.
; ============================================================================
ftoi32:
        jsr  iszero_f1
        bne  ftoi32_nz
        stz  fac1_m0
        stz  fac1_m1
        stz  fac1_m2
        stz  fac1_m3
        rts
ftoi32_nz:
        ; If exponent < 0 -> |x| < 1, result is 0
        lda  fac1_e1
        bmi  ftoi32_zero
        ; If exponent > 30 -> overflow into sign bit; we still wrap mod 2^32
        ; Target: shift mantissa so its bit 52 moves to bit <exp>.
        ; Desired shift amount = 52 - exp.  If exp > 52 we shift LEFT; else
        ; shift RIGHT.  In practice exp will usually be in [0..30] for int32.
        sec
        lda  #52
        sbc  fac1_e0
        sta  tmp0              ; shift count; tmp0>=0 means shift right
        ; Handle high byte of exponent: if non-zero and positive, exp is huge,
        ; shift count is negative and large -> overflow, wrap to 0
        lda  fac1_e1
        beq  ftoi32_shift
        ; Positive high byte means exp >= 256; result wraps to zero.
ftoi32_zero:
        stz  fac1_m0
        stz  fac1_m1
        stz  fac1_m2
        stz  fac1_m3
        rts
ftoi32_shift:
        ldx  tmp0
        bpl  ftoi32_shr
        ; negative count -- shift left by (-count)
        sec
        lda  #0
        sbc  tmp0
        tax
ftoi32_shl_loop:
        cpx  #0
        beq  ftoi32_shl_done
        jsr  mshl1_f1
        dex
        bra  ftoi32_shl_loop
ftoi32_shl_done:
        bra  ftoi32_apply_sign
ftoi32_shr:
        jsr  mshr_f1
        ; fall through
ftoi32_apply_sign:
        ; If sign was negative, two's-complement negate the low 32 bits
        lda  fac1_s
        beq  ftoi32_done
        sec
        lda  #0
        sbc  fac1_m0
        sta  fac1_m0
        lda  #0
        sbc  fac1_m1
        sta  fac1_m1
        lda  #0
        sbc  fac1_m2
        sta  fac1_m2
        lda  #0
        sbc  fac1_m3
        sta  fac1_m3
ftoi32_done:
        rts

; (constants have been moved to the top of the file so we do not need
; low/high-byte address operators -- see "ten_double" near the top.)

; ============================================================================
; fmul_by_ten  (internal) : FAC1 <- FAC1 * 10
; fdiv_by_ten  (internal) : FAC1 <- FAC1 / 10
;
; These load the constant into FAC2 (via unpack2) using an inline pointer
; setup, then call the main fmul/fdiv.  They preserve FAC1's role as the
; working accumulator.
; ============================================================================
fmul_by_ten:
        lda  #$80
        sta  ptr2
        lda  #$02
        sta  ptr2h
        jsr  unpack2
        jmp  fmul

fdiv_by_ten:
        lda  #$88
        sta  ptr2
        lda  #$02
        sta  ptr2h
        jsr  unpack2
        jmp  fmul              ; multiplying by 0.1 is preferable to dividing
                               ; by 10 because there's no worse roundoff here
                               ; than in any other truncated multiply.

; ============================================================================
; ftoa : convert FAC1 to a decimal string at (ptr1), null-terminated.
;        Format: [-]D.DDDDDDDDDDDDDDDDe[+-]NNN      (17 significant digits)
;
; Algorithm:
;   1. Handle sign and the zero case.
;   2. Scale value to [1.0, 10.0) by repeatedly multiplying by 10 (if < 1)
;      or multiplying by 0.1 (if >= 10), tracking the decimal exponent.
;   3. Emit 17 digits: extract integer part (0..9), subtract it, multiply
;      by 10.  Insert the decimal point after the first digit.
;   4. Emit 'e', sign, three digits of decimal exponent.
;
; Precision: since intermediate scaling is itself truncated, the last couple
; of digits are unreliable.  That's consistent with the "minimal" contract.
; ============================================================================
ftoa:
        ldy  #0
        ; sign
        lda  fac1_s
        beq  ftoa_notneg
        lda  #$2d
        sta  (ptr1),y
        iny
        stz  fac1_s            ; work with magnitude
ftoa_notneg:
        jsr  iszero_f1
        bne  ftoa_nz
        lda  #$30
        sta  (ptr1),y
        iny
        lda  #0
        sta  (ptr1),y
        rts
ftoa_nz:
        ; decimal exponent -> 0 initially
        stz  decexp0
        stz  decexp1

        ; --- Scale FAC1 into [1, 10) --------------------------------------
        ; Y (the string index) is stashed on the CPU stack across every
        ; call because fmul/fdiv/fcmp clobber tmp0..tmp3.
ftoa_scale_up:
        ; while FAC1 < 1.0, multiply by 10 and dec DECEXP
        phy
        lda  #$90              ; &one_double
        sta  ptr2
        lda  #$02
        sta  ptr2h
        jsr  unpack2
        jsr  fcmp
        cmp  #$ff
        bne  ftoa_su_exit      ; FAC1 >= 1 -> done scaling up
        jsr  fmul_by_ten
        sec
        lda  decexp0
        sbc  #1
        sta  decexp0
        lda  decexp1
        sbc  #0
        sta  decexp1
        ply
        bra  ftoa_scale_up
ftoa_su_exit:
        ply

ftoa_scale_down:
        ; while FAC1 >= 10.0, multiply by 0.1 and inc DECEXP
        phy
        lda  #$80              ; &ten_double
        sta  ptr2
        lda  #$02
        sta  ptr2h
        jsr  unpack2
        jsr  fcmp
        cmp  #$01              ; FAC1 > 10 ?
        bne  ftoa_sd_exit      ; no -> done
        jsr  fdiv_by_ten
        clc
        lda  decexp0
        adc  #1
        sta  decexp0
        lda  decexp1
        adc  #0
        sta  decexp1
        ply
        bra  ftoa_scale_down
ftoa_sd_exit:
        ply

ftoa_emit:
        ldx  #0                ; digit counter (0..16)
ftoa_digit_loop:
        ; Push digit counter once; we'll pop at loop tail.  Subroutines in
        ; this loop clobber both X and Y, so both must live on the stack.
        phx
        ; Save current FAC1 (in [1, 10)) to BIGM so we can reconstruct it
        ; after ftoi32 rewrites FAC1 as an integer.
        lda  fac1_m0
        sta  bigm0
        lda  fac1_m1
        sta  bigm1
        lda  fac1_m2
        sta  bigm2
        lda  fac1_m3
        sta  bigm3
        lda  fac1_m4
        sta  bigm4
        lda  fac1_m5
        sta  bigm5
        lda  fac1_m6
        sta  bigm6
        lda  fac1_m7
        sta  bigm7
        lda  fac1_e0
        sta  bigm8
        lda  fac1_e1
        sta  bigm9
        lda  fac1_s
        sta  bigma

        ; Extract the integer digit via ftoi32 (clobbers X and Y).
        phy
        jsr  ftoi32            ; low 4 bytes of FAC1 = int part (0..9 usually)
        ply
        ; Due to rounding at the end of scale-down, FAC1 can land on 10.0
        ; exactly.  Clamp the digit to 9 in that case (propagates as 9.999...
        ; which decodes back to the correct value).
        lda  fac1_m0
        cmp  #10
        bcc  ftoa_digit_ok
        lda  #9
        sta  fac1_m0
ftoa_digit_ok:
        lda  fac1_m0
        and  #$0f              ; digit is 0..9
        ora  #$30              ; ASCII
        sta  (ptr1),y
        iny
        ; emit decimal point after first digit (X is still on the stack;
        ; peek via tsx/lda $0101,x is overkill -- just check iteration via
        ; a second stashed copy).
        pla                    ; X -> A
        pha                    ; keep on stack
        cmp  #0
        bne  ftoa_no_dot
        lda  #$2e              ; '.'
        sta  (ptr1),y
        iny
ftoa_no_dot:
        ; Build float(digit) in FAC1 via itof32 (fac1_m0..m3 already holds
        ; the int digit; zero the rest so itof32 sees a clean 32-bit int).
        stz  fac1_m4
        stz  fac1_m5
        stz  fac1_m6
        stz  fac1_m7
        stz  fac1_e0
        stz  fac1_e1
        stz  fac1_s
        phy
        jsr  itof32            ; FAC1 = float(digit)
        jsr  cpy_f1_f2         ; FAC2 = float(digit)
        ply

        ; Restore the scaled-original FAC1 from BIGM.
        lda  bigm0
        sta  fac1_m0
        lda  bigm1
        sta  fac1_m1
        lda  bigm2
        sta  fac1_m2
        lda  bigm3
        sta  fac1_m3
        lda  bigm4
        sta  fac1_m4
        lda  bigm5
        sta  fac1_m5
        lda  bigm6
        sta  fac1_m6
        lda  bigm7
        sta  fac1_m7
        lda  bigm8
        sta  fac1_e0
        lda  bigm9
        sta  fac1_e1
        lda  bigma
        sta  fac1_s

        phy
        jsr  fsub              ; FAC1 -= float(digit) -> fractional part
        jsr  fmul_by_ten       ; FAC1 *= 10 -> next digit in int position
        ply

        plx                    ; restore digit counter
        inx
        cpx  #17
        beq  ftoa_digits_done
        jmp  ftoa_digit_loop
ftoa_digits_done:

        ; Emit 'e'
        lda  #$65
        sta  (ptr1),y
        iny
        ; Emit sign of DECEXP
        lda  decexp1
        bpl  ftoa_exp_pos
        lda  #$2d
        sta  (ptr1),y
        iny
        ; negate DECEXP for printing
        sec
        lda  #0
        sbc  decexp0
        sta  decexp0
        lda  #0
        sbc  decexp1
        sta  decexp1
        bra  ftoa_exp_print
ftoa_exp_pos:
        lda  #$2b
        sta  (ptr1),y
        iny
ftoa_exp_print:
        ; DECEXP fits easily in 3 decimal digits; this covers +-308 for
        ; normal doubles.  Extract hundreds, tens, ones from decexp0 (low
        ; byte is sufficient for |exp| < 256; for larger we'd need a 16-bit
        ; divide, but that's beyond the minimal scope).
        lda  decexp0
        sta  tmp0              ; pending exponent magnitude
        ldx  #0                ; hundreds
ftoa_h_loop:
        lda  tmp0
        cmp  #100
        bcc  ftoa_h_done
        sec
        sbc  #100
        sta  tmp0
        inx
        bra  ftoa_h_loop
ftoa_h_done:
        txa
        ora  #$30
        sta  (ptr1),y
        iny
        ldx  #0                ; tens
ftoa_t_loop:
        lda  tmp0
        cmp  #10
        bcc  ftoa_t_done
        sec
        sbc  #10
        sta  tmp0
        inx
        bra  ftoa_t_loop
ftoa_t_done:
        txa
        ora  #$30
        sta  (ptr1),y
        iny
        lda  tmp0
        ora  #$30
        sta  (ptr1),y
        iny
        ; terminator
        lda  #0
        sta  (ptr1),y
        rts

; ============================================================================
; atof : parse decimal number at (ptr1) into FAC1.  Accepts:
;          [+-]?digits(.digits)?([eE][+-]?digits)?
;        Returns on first non-numeric character (e.g. 0 byte or space).
; ============================================================================
atof:
        ; FAC1 = 0
        stz  fac1_m0
        stz  fac1_m1
        stz  fac1_m2
        stz  fac1_m3
        stz  fac1_m4
        stz  fac1_m5
        stz  fac1_m6
        stz  fac1_m7
        stz  fac1_e0
        stz  fac1_e1
        stz  fac1_s
        stz  decexp0
        stz  decexp1
        stz  tmp2              ; "have a sign" flag for final result
        stz  tmp3              ; "in fractional digits" flag

        ldy  #0
        lda  (ptr1),y
        cmp  #$2d
        bne  atof_chk_plus
        lda  #$80
        sta  tmp2              ; stash sign to apply later
        iny
        bra  atof_intloop
atof_chk_plus:
        cmp  #$2b
        bne  atof_intloop
        iny

atof_intloop:
        lda  (ptr1),y
        cmp  #$2e
        bne  atof_not_dot
        jmp  atof_enter_frac
atof_not_dot:
        cmp  #$65
        bne  atof_not_e
        jmp  atof_expo
atof_not_e:
        cmp  #$45
        bne  atof_not_E
        jmp  atof_expo
atof_not_E:
        cmp  #$30
        bcs  atof_gt_zero
        jmp  atof_finish
atof_gt_zero:
        cmp  #$3a              ; one past '9'
        bcc  atof_is_digit
        jmp  atof_finish
atof_is_digit:
        ; digit 0..9 -- FAC1 = FAC1*10 + digit
        ; Y holds the string index; fmul/fadd clobber tmp0/tmp1, so we stash
        ; Y on the CPU stack (phy/ply) across all subroutine calls.
        phy
        jsr  fmul_by_ten
        ply
        lda  (ptr1),y
        and  #$0f
        sta  bigm0
        stz  bigm1
        stz  bigm2
        stz  bigm3
        ; Convert bigm0..3 to a float in FAC2 via swap/itof32/swap
        ; Save FAC1
        lda  fac1_m0
        pha
        lda  fac1_m1
        pha
        lda  fac1_m2
        pha
        lda  fac1_m3
        pha
        lda  fac1_m4
        pha
        lda  fac1_m5
        pha
        lda  fac1_m6
        pha
        lda  fac1_m7
        pha
        lda  fac1_e0
        pha
        lda  fac1_e1
        pha
        lda  fac1_s
        pha
        ; Load digit as int into FAC1
        lda  bigm0
        sta  fac1_m0
        stz  fac1_m1
        stz  fac1_m2
        stz  fac1_m3
        stz  fac1_m4
        stz  fac1_m5
        stz  fac1_m6
        stz  fac1_m7
        stz  fac1_e0
        stz  fac1_e1
        stz  fac1_s
        jsr  itof32            ; FAC1 = digit.0
        ; Move to FAC2
        jsr  cpy_f1_f2
        ; Restore FAC1
        pla
        sta  fac1_s
        pla
        sta  fac1_e1
        pla
        sta  fac1_e0
        pla
        sta  fac1_m7
        pla
        sta  fac1_m6
        pla
        sta  fac1_m5
        pla
        sta  fac1_m4
        pla
        sta  fac1_m3
        pla
        sta  fac1_m2
        pla
        sta  fac1_m1
        pla
        sta  fac1_m0
        ; Save Y across fadd too (fadd clobbers tmp0/tmp1).
        phy
        jsr  fadd              ; FAC1 += digit
        ply
        ; If we're in the fractional part, pre-decrement DECEXP
        lda  tmp3
        beq  atof_no_dec_frac
        sec
        lda  decexp0
        sbc  #1
        sta  decexp0
        lda  decexp1
        sbc  #0
        sta  decexp1
atof_no_dec_frac:
        iny
        jmp  atof_intloop

atof_enter_frac:
        lda  #1
        sta  tmp3
        iny
        jmp  atof_intloop

atof_expo:
        iny
        ; parse signed exponent into tmp0 (low) / tmp1 (high)
        stz  tmp0
        stz  tmp1
        lda  #0
        sta  bigm0             ; exponent sign flag
        lda  (ptr1),y
        cmp  #$2d
        bne  atof_exp_chkplus
        lda  #$80
        sta  bigm0
        iny
        bra  atof_exp_digits
atof_exp_chkplus:
        cmp  #$2b
        bne  atof_exp_digits
        iny
atof_exp_digits:
        lda  (ptr1),y
        cmp  #$30
        bcc  atof_exp_apply
        cmp  #$3a
        bcs  atof_exp_apply
        ; tmp1:tmp0 = tmp1:tmp0 * 10 + digit
        ; multiply by 10 = (*8) + (*2)
        asl  tmp0
        rol  tmp1              ; x2
        lda  tmp0
        sta  bigm1
        lda  tmp1
        sta  bigm2
        asl  tmp0
        rol  tmp1
        asl  tmp0
        rol  tmp1              ; x8 of the original
        clc
        lda  tmp0
        adc  bigm1
        sta  tmp0
        lda  tmp1
        adc  bigm2
        sta  tmp1              ; now = original * 10
        lda  (ptr1),y
        and  #$0f
        clc
        adc  tmp0
        sta  tmp0
        lda  tmp1
        adc  #0
        sta  tmp1
        iny
        bra  atof_exp_digits
atof_exp_apply:
        ; apply sign and fold into DECEXP
        lda  bigm0
        beq  atof_exp_add
        ; negate tmp1:tmp0
        sec
        lda  #0
        sbc  tmp0
        sta  tmp0
        lda  #0
        sbc  tmp1
        sta  tmp1
atof_exp_add:
        clc
        lda  decexp0
        adc  tmp0
        sta  decexp0
        lda  decexp1
        adc  tmp1
        sta  decexp1
        ; fall through

atof_finish:
        ; Apply accumulated DECEXP by repeated multiply by 10 or 0.1.
        ; DECEXP can be in about +-308 for doubles; for the minimal scope
        ; we do a naive loop.
atof_exp_loop:
        lda  decexp0
        ora  decexp1
        beq  atof_apply_sign
        lda  decexp1
        bmi  atof_exp_neg
        ; positive: multiply by 10, dec DECEXP
        jsr  fmul_by_ten
        sec
        lda  decexp0
        sbc  #1
        sta  decexp0
        lda  decexp1
        sbc  #0
        sta  decexp1
        bra  atof_exp_loop
atof_exp_neg:
        jsr  fdiv_by_ten       ; (*0.1)
        clc
        lda  decexp0
        adc  #1
        sta  decexp0
        lda  decexp1
        adc  #0
        sta  decexp1
        bra  atof_exp_loop

atof_apply_sign:
        lda  tmp2
        sta  fac1_s
        rts

; ============================================================================
; End of library.  The reset vector below lets this be dropped straight into
; a ROM image for a simulator; customize or remove as needed.
; ============================================================================

                org  $fffa
                dw   &unpack1, &unpack1, &unpack1   ; NMI, RESET, IRQ
