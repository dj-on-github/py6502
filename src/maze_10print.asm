            ORG $0200

            LDA #$A5        ; LFSR seed (must be non-zero)
            STA $12
start:
            LDA #$00        ; screen pointer low  = $00
            STA $10
            LDA #$08        ; screen pointer high = $08  -> $0800
            STA $11

loop:       LDA $12         ; advance the LFSR
            LSR A           ;   C = bit shifted out
            BCC nofb
            EOR #$B8        ;   feedback tap for maximal length
nofb:       STA $12

            LDA #$06        ; assume '/'
            BCC store       ; ...unless the shifted-out bit was 1
            LDA #$07        ; then '\'
store:      LDY #$00
            STA ($10),Y     ; write character to the screen

            INC $10         ; advance pointer
            BNE skiphi
            INC $11
skiphi:     LDA $11
            CMP #$0D        ; reached $0D00 (one past the screen)?
            BNE loop
            
            JMP start
            DB  $02       ; KIL: halt the simulator now the screen is full
