@ Use the audio block's already-prepared virtual ADC, without advancing pickup.
@ Physical ADC memory remains untouched for gestures and the next block.
@ Output must be a high register (r4-r12); all other registers/flags survive.
.macro preset_vs_cached output
    push {r0-r2}
    mrs r2, APSR
    ldr r0, =0x2002a660
    ldr r1, [r0]
    ldr r0, =0x54535250
    cmp r1, r0
    bne 99f
    ldr r0, =0x2002ae90
    ldr r1, [r0, #284]              @ aux[15]: virtual ADC active this block
    cbz r1, 99f
    ldr \output, [r0, #280]         @ aux[14]: equivalent calibrated ADC
99: msr APSR_nzcvq, r2
    pop {r0-r2}
.endm
