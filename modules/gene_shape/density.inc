@ dens 1: SHIFT+Gene Size selects stock timing at CCW, then 0.1..128 Hz.
@ 0x2002a800: initialized, enabled-for-block, interval, countdown (u32 each).
@ An initialized interval of zero selects the stock elapsed/interval comparison.
@ Four stock voices; defer a due birth while the next voice is still sounding.
    .equ DENSITY, 0x2002A800
    .equ DENS_OPT, 0x2002A607
    .equ STOCK_ENTER, 96                @ 12-bit ADC, hysteresis about 0.8% of travel
    .equ STOCK_EXIT, 128
    .equ RATE_START, 192                @ 0.1 Hz plateau immediately above the detent
    .type DENS_A_NEXT, %function
    .type DENS_B_NEXT, %function
    .global density_a, density_b, density_adjust, density_prepare

@ r1 = selected; preserves r0,r2-r12 and all floats.
density_mode:
    ldr r1, =DENS_OPT
    ldrb r1, [r1]
    cmp r1, #1
    ite eq
    moveq r1, #1
    movne r1, #0
    bx lr

@ Called once per audio block, before Gene Size processing. Preserve everything.
    .thumb_func
density_prepare:
    push {r0-r3, lr}
    ldr r3, =DENSITY
    ldr r0, =DENS_OPT
    ldrb r0, [r0]
    cmp r0, #1
    bne 2f
    ldr r1, [r3]
    cbnz r1, 1f
    movs r1, #1
    str r1, [r3]
    ldr r1, =0x2002A614             @ dstr in tenths of a Gene/sec
    ldr r1, [r1]
    cmp r1, #1
    blo 4f
    cmp r1, #1280
    bls 5f
4:  movs r1, #80                    @ defensive fallback: 8 Genes/sec
5:  ldr r2, =480000
    add r2, r2, r1, lsr #1
    udiv r2, r2, r1                 @ nearest sample interval, calculated once
    str r2, [r3, #8]
    str r2, [r3, #12]            @ allow the initial stock Gene to play first
1:  ldr r1, [r3, #8]
    cbz r1, 2f                       @ stock timing, with the existing Gene Size
    ldr r1, =0x20021cb0             @ stock external clock active flag
    ldr r1, [r1]
    cmp r1, #1
    beq 2f
    ldr r1, =0x200220e0
    ldr r1, [r1]
    lsls r1, #1                     @ zero speed: pause new births
    beq 2f
    str r0, [r3, #4]
    movs r2, #4
    ldr r1, =0x20022108
    ldr r1, [r1]
    cbz r1, 3f
    ldr r1, =MOD
    ldrb r0, [r1, #234]            @ tape_sos: dryk 2 forces the tape write head
    cmp r0, #3                     @ resampling uses the full Gene playback
    beq 3f
    cmp r0, #2
    beq 6f
    ldrb r1, [r1, #16]
    cmp r1, #1
    bne 3f
    ldr r1, =SETTINGS
    ldrb r0, [r1, #4]
    cmp r0, #1
    bne 3f
6:  ldr r1, =SETTINGS
    ldrb r0, [r1, #9]
    cbz r0, 3f
    movs r2, #2                    @ honor the tape Morph cap with a voice limit
3:  str r2, [r3, #16]
    pop {r0-r3, pc}
2:  movs r0, #0
    str r0, [r3, #4]
    str r0, [r3, #12]
    pop {r0-r3, pc}

@ r0=live ADC. Gene Size itself remains at the pre-gesture value (size_hold).
    .thumb_func
density_adjust:
    push {r0-r3}
    ldr r3, =DENSITY
    ldr r2, [r3, #8]                 @ previous selected interval
    movs r1, #1
    str r1, [r3]                     @ an explicit gesture also counts as initialization
    cmp r0, #STOCK_ENTER
    bls 3f
    cmp r0, #STOCK_EXIT
    bhs 1f
    cbz r2, 3f                       @ between thresholds keep the current timing mode
1:  cmp r0, #2048
    bhs 2f
    subs r0, #RATE_START
    it mi
    movmi r0, #0
    lsls r0, #7
    movw r1, #(2048 - RATE_START)
    udiv r0, r0, r1                  @ lower half: 0.1 Hz through 8 Hz at noon
    b 4f
2:  subs r0, #64                     @ original upper-half scale, 8..128 Hz
    movw r1, #3968
    cmp r0, r1
    it hi
    movhi r0, r1
    lsls r0, #8
    udiv r0, r0, r1
4:  ldr r1, =density_table
    ldr r0, [r1, r0, lsl #2]
    str r0, [r3, #8]
    cbz r2, 5f                       @ leave stock timing with a fresh interval
    ldr r1, [r3, #12]
    cmp r1, r0
    it hi
    strhi r0, [r3, #12]              @ retain phase unless a faster rate is due sooner
    b 6f
3:  movs r0, #0
    str r0, [r3, #8]                 @ stock timing, leave the running voices untouched
5:  str r0, [r3, #12]
6:  pop {r0-r3}
    bx lr

@ Each hook replaces only the elapsed/interval FPU comparison. The stock
@ play/clock checks and birth initializer still execute. FPSCR is the output.
    .macro DENS_TICK name, elapsed, interval, ret
    .thumb_func
\name:
    push {r0-r3}
    ldr r0, =DENSITY
    ldr r1, [r0, #4]
    cbz r1, 8f
    vpush {s0-s1}
    ldr r1, [r0, #12]
    cbz r1, 2f
    subs r1, #1
    str r1, [r0, #12]
    cbnz r1, 6f
2:  ldr r1, [r0, #16]
    cmp r1, #2
    bne 3f
    ldr r2, =0x20021e64
    movs r3, #4
4:  vldr s0, [r2]
    vcmpe.f32 s0, #0.0
    vmrs APSR_nzcv, fpscr
    it gt
    subgt r1, #1
    cbz r1, 6f
    adds r2, #4
    subs r3, #1
    bne 4b
3:  ldr r1, =0x20021cb8            @ last voice selected by stock scheduler
    ldr r1, [r1]
    adds r1, #1
    and r1, r1, #3
    ldr r2, =0x20021e64            @ envelope <=0 means the voice is silent
    add r2, r2, r1, lsl #2
    vldr s0, [r2]
    vcmpe.f32 s0, #0.0
    vmrs APSR_nzcv, fpscr
    bgt 6f
    ldr r1, [r0, #8]
    str r1, [r0, #12]
    vmov.f32 s0, #1.0
    b 7f
6:  vmov.f32 s0, #-1.0
7:  vcmpe.f32 s0, #0.0
    vpop {s0-s1}
    pop {r0-r3}
    b.w \ret
8:  pop {r0-r3}
    vcmpe.f32 \elapsed, \interval
    b.w \ret
    .endm
DENS_TICK density_a, s21, s12, DENS_A_NEXT
DENS_TICK density_b, s20, s11, DENS_B_NEXT
    .ltorg
    .align 2
density_table:
    .include "density_table.inc"
