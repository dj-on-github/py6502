        ORG  $100
start:
        LDA #$aa
        STA $10
        ADC #$54 ; comment
        ADC #$01
        ADC #$01 ;comment
        LDA #$55
        STA $11
        LDA #$40
        STA $12
        LDX #$00

loop:
        STA $10,x
        INX
        SBC #$01
        ;CMP #$00
        BNE loop
        NOP
        NOP
        BRA start
        ORG $fffa
        DW  $0100,$0100,$0100 ; Reset Vector
