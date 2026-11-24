@ Stock Morph scatter reads Gene Size again after its main block processing.
@ Use that block's cached effective value; do not advance pickup a second time.
@ r7 is the replaced load's output. Preserve every other register and flags.
.macro effective_gene_size output, scratch
    ldr r0, =0x2002a660
    ldr \scratch, [r0]
    ldr r0, =0x54535250
    cmp \scratch, r0
    bne 2f
    ldr r0, =0x2002a660
    ldr \scratch, [r0, #76]            @ Gene Size preset lane initialized
    tst \scratch, #1
    beq 1f
    ldr \output, [r0, #68]             @ preset and pickup already resolved for this block
    b 9f
1:  ldr r0, =0x2002ae90
    ldr \scratch, [r0, #172]           @ Turing rate lane initialized
    tst \scratch, #1
    bne 3f
2:  ldr r0, =DENS_OPT
    ldrb \scratch, [r0]
    cmp \scratch, #1
    bne 9f
3:  ldr r0, =MOD
    ldr \scratch, [r0]
    ldr r0, =MAGIC
    cmp \scratch, r0
    bne 9f
    ldr r0, =MOD
    ldrb \scratch, [r0, #212]          @ SHIFT or its pending primary pickup
    cbz \scratch, 9f
    ldrh \output, [r0, #216]           @ actual Gene Size before the shifted edit
9:
.endm

.macro preset_size_read name, destination
    .global \name
    .thumb_func
\name:
    ldr r7, [r6, #20]
    push {r0-r2}
    mrs r2, APSR
    effective_gene_size r7, r1
    msr APSR_nzcvq, r2
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
    effective_gene_size r1, r2
    msr APSR_nzcvq, r3
    pop {r0,r2,r3,pc}
    .ltorg
