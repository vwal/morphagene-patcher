@ Forward-only scales: stock stop..4x or extended stop..8x.
@ P5 enters with r0-r10/lr and s0-s1 saved, r3=MOD, r8=vrng.
p5_forward:
    cmp r8, #1
    bne p5_done
    ldrb r1, [r3, #6]
    cmp r1, #2
    bne forward_release
    ldrb r1, [r3, #4]
    cmp r1, #0
    beq forward_release
    ldrb r1, [r3, #5]
    cmp r1, #0
    beq forward_release
forward_quantize:
    @ vqnt 1 can enter directly, including the stock forward-only range.
    vldr s0, f6016
    movw r9, #340
    cmp r8, #1
    beq 0f
    vldr s0, f5248
    movw r9, #292
0:
    vmul.f32 s0, s18, s0
    vcvt.s32.f32 s0, s0
    vmov r0, s0
    sub r0, r0, #256
    movs r6, #1
    movs r7, #128
    ldr r1, =SETTINGS
    ldr r2, [r1]
    ldr r4, =SETTINGS_MAGIC
    cmp r2, r4
    bne 1f
    ldrb r2, [r1, #5]
    cmp r2, #2
    it eq
    moveq r6, #0x81
    cmp r2, #3
    blo 1f
    movs r7, #48
    movw r6, #0xfff
    beq 1f
    ldr r1, =SCALE
    ldrh r6, [r1]
    orr r6, r6, #1
1:  movs r5, #0                     @ stop candidate, center i+0.5
    sub r1, r0, #8
    cmp r1, #0
    it mi
    rsbmi r1, r1, #0                @ best distance
    movs r4, #4
    movs r8, #0                     @ pitch class
2:  lsr r2, r6, r8
    tst r2, #1
    beq 3f
    lsls r2, r4, #4
    adds r2, #8
    subs r2, r0, r2
    it mi
    rsbmi r2, r2, #0
    cmp r2, r1
    itt lt
    movlt r1, r2
    movlt r5, r4
3:  adds r4, #4
    add r8, r8, #1
    cmp r8, #12
    it eq
    moveq r8, #0
    cmp r4, r9
    ble 2b
    ldrb r2, [r3, #7]
    cbz r2, 5f
    ldrh r4, [r3, #12]
    cmp r4, r9
    bhi 5f
    tst r4, #3
    bne 5f
    cbz r4, 4f
    sub r2, r4, #4
    lsrs r2, #2
6:  cmp r2, #12
    itt hs
    subhs r2, #12
    bhs 6b
    lsr r2, r6, r2
    tst r2, #1
    beq 5f
4:  lsls r2, r4, #4
    adds r2, #8
    subs r2, r0, r2
    it mi
    rsbmi r2, r2, #0
    adds r1, r1, r7
    cmp r2, r1
    it le
    movle r5, r4
5:  strh r5, [r3, #12]
    movs r0, #1
    strb r0, [r3, #7]
    movw r0, #0xffff
    strh r0, [r3, #14]
    b forward_apply
forward_release:
    ldrb r1, [r3, #7]
    cbz r1, forward_done
    ldr r0, =VS_ADC
    ldr r0, [r0]
    ldrh r1, [r3, #14]
    movw r2, #0xffff
    cmp r1, r2
    itt eq
    strheq r0, [r3, #14]
    moveq r1, r0
    subs r1, r0, r1
    it mi
    rsbmi r1, r1, #0
    movw r2, #261
    cmp r1, r2                    @ half octave, 24/376 of 4095
    ble forward_apply
    movs r0, #0
    strb r0, [r3, #7]
    b forward_done
forward_apply:
    ldrh r0, [r3, #12]
    adds r0, #16
    vmov s0, r0
    vcvt.f32.s32 s0, s0
    vmov.f32 s1, #0.5
    vadd.f32 s0, s0, s1
    vldr s1, f_inv376
    ldr r1, =RANGE
    ldrb r1, [r1]
    cmp r1, #1
    it ne
    vldrne s1, f_inv328
    vmul.f32 s18, s0, s1
forward_done:
    b p5_done
    .align 2
f6016: .float 6016.0
f5248: .float 5248.0
f_inv376: .float 0.0026595744680851063
f_inv328: .float 0.003048780487804878
    .ltorg

    .global forward_lookup
    .type FORWARD_STOCK, %function
    .type FORWARD_DONE, %function
    .thumb_func
forward_lookup:
    push {r0-r2}
    ldr r0, =RANGE
    ldrb r0, [r0]
    cmp r0, #1
    beq 1f
    pop {r0-r2}
    vldr s23, f328                  @ replaced stock literal
    b.w FORWARD_STOCK
1:  vpush {s0-s1}
    vldr s0, f376
    vmul.f32 s0, s18, s0
    vcvt.s32.f32 s0, s0
    vmov r0, s0
    subs r0, #16
    it mi
    movmi r0, #0
    movw r1, #343
    cmp r0, r1
    it gt
    movgt r0, r1
    ldr r1, =forward_table
    ldr r6, [r1, r0, lsl #2]
    ldr r5, =0x200220e8
    str r6, [r5]
    @ Preserve the stock secondary position calculation for LEDs/control state.
    vmov.f32 s26, #1.0
    vadd.f32 s27, s18, s26
    vcvt.s32.f32 s27, s27, #6
    ldr r1, =0x200220dc
    vstr s27, [r1]
    vpop {s0-s1}
    pop {r0-r2}
    b.w FORWARD_DONE
    .align 2
f328: .float 328.0
f376: .float 376.0
    .ltorg

@ Stock has a second lookup when Gene Size <= 199 (full-splice/reel mode).
@ It must use the same extended table as the ordinary Gene path above.
@ Its return continues the full-splice path, preserving that engine state.
    .global forward_lookup_full
    .type FORWARD_FULL_STOCK, %function
    .type FORWARD_FULL_DONE, %function
    .thumb_func
forward_lookup_full:
    push {r0-r2}
    ldr r0, =RANGE
    ldrb r0, [r0]
    cmp r0, #1
    beq 1f
    pop {r0-r2}
    vldr s16, f328                  @ replaced stock literal
    b.w FORWARD_FULL_STOCK
1:  vpush {s0-s1}
    vldr s0, f376
    vmul.f32 s0, s18, s0
    vcvt.s32.f32 s0, s0
    vmov r0, s0
    subs r0, #16
    it mi
    movmi r0, #0
    movw r1, #343
    cmp r0, r1
    it gt
    movgt r0, r1
    ldr r1, =forward_table
    ldr r0, [r1, r0, lsl #2]
    ldr r1, =0x200220e8
    str r0, [r1]
    vmov.f32 s0, #1.0
    vadd.f32 s0, s18, s0
    vcvt.s32.f32 s0, s0, #6
    ldr r1, =0x200220dc
    vstr s0, [r1]
    vpop {s0-s1}
    pop {r0-r2}
    b.w FORWARD_FULL_DONE
    .ltorg
forward_table:
    .include "forward_table.inc"
