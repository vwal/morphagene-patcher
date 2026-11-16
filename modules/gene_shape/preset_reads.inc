@ Stock Morph scatter reads Gene Size again after its main block processing.
@ Use that block's cached effective value; do not advance pickup a second time.
@ r7 is the replaced load's output. Preserve every other register and flags.
.macro preset_size_read name, destination
    .global \name
    .thumb_func
\name:
    ldr r7, [r6, #20]
    push {r0-r2}
    mrs r2, APSR
    ldr r0, =0x2002a660
    ldr r1, [r0]
    ldr r0, =0x54535250
    cmp r1, r0
    bne 9f
    ldr r0, =0x2002a660
    ldr r1, [r0, #76]                 @ Gene Size lane initialized
    tst r1, #1
    beq 1f
    ldr r7, [r0, #68]                 @ Gene Size lane effective
    b 9f
1:  @ A trst-only SHIFT edit still holds primary Gene Size in the legacy
    @ slot. Scatter must honor that hold too, including after SHIFT release.
    @ Keep the no-preset/unrelated-preset path exactly as before.
    ldr r0, =0x2002ae90
    ldr r1, [r0, #172]                @ Turing rate lane initialized
    tst r1, #1
    beq 9f
    ldr r0, =MOD
    ldr r1, [r0]
    ldr r0, =MAGIC
    cmp r1, r0
    bne 9f
    ldr r0, =MOD
    ldrb r1, [r0, #212]               @ legacy primary Gene Size hold
    cbz r1, 9f
    ldrh r7, [r0, #216]
9:  msr APSR_nzcvq, r2
    pop {r0-r2}
    str r7, [sp]                     @ replaced store, using stock SP
    b.w \destination
.endm
    .type PRESET_SIZE_A_NEXT, %function
    .type PRESET_SIZE_B_NEXT, %function
preset_size_read preset_size_a, PRESET_SIZE_A_NEXT
preset_size_read preset_size_b, PRESET_SIZE_B_NEXT
    .ltorg

@ Turing's seeded scatter has its own repeated Gene Size read. r1 is input
@ and output; retain the random seed in r3 and every other register/flag.
    .global preset_size_cached
    .thumb_func
preset_size_cached:
    push {r0,r2,r3,lr}
    mrs r3, APSR
    ldr r0, =0x2002a660
    ldr r2, [r0]
    ldr r0, =0x54535250
    cmp r2, r0
    bne 9f
    ldr r0, =0x2002a660
    ldr r2, [r0, #76]
    tst r2, #1
    beq 1f
    ldr r1, [r0, #68]
    b 9f
1:  ldr r0, =0x2002ae90
    ldr r2, [r0, #172]
    tst r2, #1
    beq 9f
    ldr r0, =MOD
    ldr r2, [r0]
    ldr r0, =MAGIC
    cmp r2, r0
    bne 9f
    ldr r0, =MOD
    ldrb r2, [r0, #212]
    cbz r2, 9f
    ldrh r1, [r0, #216]
9:  msr APSR_nzcvq, r3
    pop {r0,r2,r3,pc}
    .ltorg
