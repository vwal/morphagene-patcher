@ Module splice_thru: Organize fully clockwise plays the reel through (mg204).
@ Adapted from Carlos de Paula's splice_thru (carlosedp/morphagene-mods,
@ commit 7184795), under LICENSES/Briskcat-MIT.txt.
@ Linked after the previous module's code (mgmod/module.py).
@ Design: README.md beside this file. Requires options_keys (thru) and
@ sd_updater (its boot default).
@
@ With thru 1, the top ZONE (5%) of Organize no longer selects the last
@ splice. Instead, every end-of-splice event (the one that drives the EOSG
@ output) asks for the next splice, exactly as a SHIFT tap does. It's the
@ same as patching EOSG into the SHIFT input. Below the zone, Organize is
@ stretched so it still reaches every splice, the last one included.
@
@ Stock pieces:
@   0x20021cbc  selected splice, 1..count. Organize sets it only when its
@               reading moves more than 8 counts; a SHIFT tap (navigation
@               request 0x200012e0 = 1) adds 1, wrapping to 1 after count.
@   0x2002208c  splice count. 0x20021338 reel mode. 0x20022108 recording.
@   0x20021de8  end-of-splice trigger: the audio code sets it to 4; TIM2
@               counts it down to 2 while it drives the EOSG gate.
@   0x200220ac  the (effective) Organize reading the selection last used,
@               0x20022080 its calibration minimum, 0x200220a0 the scale, so
@               position = (reading - minimum) * scale, as in the audio code.

    .syntax unified
    .cpu cortex-m4
    .fpu fpv4-sp-d16
    .thumb

    .equ SETTINGS,       0x2002A0F0
    .equ SETTINGS_MAGIC, 0x5354504f
    .equ THRU,           0x2002A61E     @ options.txt thru (options_keys), u8
    .equ SELECTED,       0x20021cbc
    .equ COUNT,          0x2002208c
    .equ REEL_MODE,      0x20021338
    .equ REC_ACTIVE,     0x20022108
    .equ REC_REQUEST,    0x20021320
    .equ NAVIGATION,     0x200012e0
    .equ EOS_TRIG,       0x20021de8
    .equ ORG_USED,       0x200220ac
    .equ ORG_MIN,        0x20022080
    .equ ORG_SCALE,      0x200220a0
    .type MAP_RETURN, %function
    .type EOS_RETURN, %function

    .text
    .global o1_map, e1_eos

@ r0 = 1 only when initialized settings explicitly enable thru. Uses r0, r1.
    .thumb_func
thru_on:
    ldr     r1, =SETTINGS
    ldr     r0, [r1]
    ldr     r1, =SETTINGS_MAGIC
    cmp     r0, r1
    bne     1f
    ldr     r0, =THRU
    ldrb    r0, [r0]
    cmp     r0, #1
    it      eq
    bxeq    lr
1:  movs    r0, #0
    bx      lr

@ O1 (audio block, 0x080277b0..0x080277d1): Organize -> selected splice,
@ reached only when the Organize reading moved (or at the first block with
@ splices). Replaces, and recomputes with the same registers:
@   s30 = 0.001; r0 = &SELECTED; s14 = r2 (count); s31 = s21 - 0.001;
@   s15 = count; s0 = s15 * s31; s13 = trunc(s0); r3 = s13 + 1; [r0] = r3
@ thru 1: below the zone s21 is stretched by 1 / 0.95; in the zone a valid
@ selection (1..count) is kept, so turning into the zone carries on from the
@ splice playing now. With no valid selection yet (a reel just loaded with
@ Organize already in the zone), it starts from splice 1.
    .thumb_func
o1_map:
    push    {r1, r4, lr}
    vldr    s30, k_milli
    vmov    s14, r2
    vmov.f32 s31, s21
    movs    r4, #0                      @ r4 = 1: in the zone
    bl      thru_on
    cbz     r0, 5f
    vldr    s0, k_zone
    vcmpe.f32 s21, s0
    vmrs    APSR_nzcv, fpscr
    bge     4f
    vldr    s0, k_stretch
    vmul.f32 s31, s21, s0
    b       5f
4:  movs    r4, #1
5:  ldr     r0, =SELECTED
    vsub.f32 s31, s31, s30
    vcvt.f32.s32 s15, s14
    vmul.f32 s0, s15, s31
    vcvt.s32.f32 s13, s0
    vmov    r3, s13
    adds    r3, r3, #1
    cbz     r4, 6f
    movs    r3, #1                      @ in the zone: keep a valid selection,
    ldr     r1, [r0]                    @ else start from splice 1 (reel load)
    cmp     r1, #1
    blt     6f
    cmp     r1, r2
    it      le
    movle   r3, r1
6:  str     r3, [r0]
    pop     {r1, r4, lr}
    b.w     MAP_RETURN

@ E1 (TIM2, 0x08024d2a): replaces "ldr.w sb, =EOS_TRIG; ldr.w r2, [sb]".
@ The first tick that sees a fresh trigger (4) asks for the next splice when
@ thru is on, Organize is in the zone, there are 2 or more splices, and the
@ module is neither in reel mode nor recording. r0 is free (overwritten at
@ 0x08024d32); r1 and r3 are live and saved. s0/s1 are saved (TIM2 uses the
@ FPU elsewhere, so lazy stacking already covers this interrupt).
    .thumb_func
e1_eos:
    ldr     sb, =EOS_TRIG
    ldr     r2, [sb]
    cmp     r2, #4
    bne     9f
    push    {r1, r3, lr}
    bl      thru_on
    cbz     r0, 8f
    ldr     r0, =REEL_MODE
    ldr     r0, [r0]
    cbnz    r0, 8f
    ldr     r0, =REC_ACTIVE
    ldr     r0, [r0]
    cbnz    r0, 8f
    ldr     r0, =REC_REQUEST
    ldr     r0, [r0]
    cbnz    r0, 8f
    ldr     r0, =COUNT
    ldr     r0, [r0]
    cmp     r0, #2
    blt     8f
    ldr     r0, =ORG_USED               @ position the selection last used
    ldr     r0, [r0]
    ldr     r1, =ORG_MIN
    ldr     r1, [r1]
    subs    r0, r0, r1
    ble     8f
    vpush   {s0-s1}
    vmov    s0, r0
    vcvt.f32.s32 s0, s0
    ldr     r0, =ORG_SCALE
    vldr    s1, [r0]
    vmul.f32 s0, s0, s1
    vldr    s1, k_zone
    vcmpe.f32 s0, s1
    vmrs    APSR_nzcv, fpscr
    vpop    {s0-s1}
    blt     8f
    ldr     r0, =NAVIGATION             @ as a SHIFT tap: next splice
    ldr     r1, [r0]
    cbnz    r1, 8f                      @ preserve a queued manual navigation
    movs    r1, #1
    str     r1, [r0]
8:  pop     {r1, r3, lr}                @ r2 still holds the trigger; the stock
9:  b.w     EOS_RETURN                  @ cmp at 0x08024d36 sets the flags again
    .ltorg

    .align 2
k_milli:    .word 0x3a83126f            @ 0.001, the stock constant
k_zone:     .float 0.95                 @ the zone: the top 5% of Organize
k_stretch:  .float 1.05263158           @ 1 / 0.95
