        ORG  $100
start:
        LDA #$aa
        STA $10
        ADC #$54 ; comment
        ADC #$01
        ADC #$01 ;comment
        LDA #$55
        STA $11
        LDA #$FF
        STA $12

loop:
        STA $13,x
        INX
        SBC #$01
        CMP #$00
        BNE loop
        NOP
        ORG $fffa
        DW  $0100,$0100,$0100 ; Reset Vector
