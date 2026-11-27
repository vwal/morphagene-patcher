@ Module splice_thru: Organize fully clockwise plays the reel through (mg204).
@ Adapted from Carlos de Paula's splice_thru (carlosedp/morphagene-mods,
@ commit 7184795), under LICENSES/Briskcat-MIT.txt.
@ Development 18 appends the Development 16 audio scheduler to the pinned
@ Development 17 image. The normal and live readers publish thru in RAM.
@
@ A full-splice Gene advances in the audio scheduler just before the new
@ voice acquires its marker bounds. Short Genes and external-clock scheduling
@ retain EOSG-driven navigation. Mode 2 follows the main Varispeed direction.

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
    .equ FULL_SPLICE,    0x20021e14     @ native fully-open Gene Size flag
    .equ CLOCK_ACTIVE,   0x20021cb0
    .equ RATE_TARGET,    0x200220e8
    .equ RATE_PLAYING,   0x200220e0
    .equ ACTIVE,         0x20021de4
    .equ VOICE_SPLICES,  0x20021fb8
    .equ MARKERS,        0x2002215c
    .equ LENGTHS,        0x200230fc
    .type BIRTH_A_RETURN, %function
    .type BIRTH_B_RETURN, %function
    .type MAP_RETURN, %function
    .type EOS_RETURN, %function

    .text
    .global o1_map, e1_eos

@ r0 = configured mode (0, 1 or 2). Uses r0, r1.
    .thumb_func
thru_on:
    ldr     r1, =SETTINGS
    ldr     r0, [r1]
    ldr     r1, =SETTINGS_MAGIC
    cmp     r0, r1
    bne     1f
    ldr     r0, =THRU
    ldrb    r0, [r0]
    cmp     r0, #2
    it      ls
    bxls    lr
1:  movs    r0, #0
    bx      lr

@ O1 (audio block, 0x080277b0..0x080277d1): Organize -> selected splice,
@ reached only when the Organize reading moved (or at the first block with
@ splices). Replaces, and recomputes with the same registers:
@   s30 = 0.001; r0 = &SELECTED; s14 = r2 (count); s31 = s21 - 0.001;
@   s15 = count; s0 = s15 * s31; s13 = trunc(s0); r3 = s13 + 1; [r0] = r3
@ With either play-through mode, below the zone s21 is stretched by 1 / 0.95; in the zone a valid
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

@ Return direction in r0 (+1, -1, or 0). Called on an event, never for
@ each sample. ORG_USED is the post-calibration/pickup Organize reading.
@ r1/r2 are scratch. FPSCR is restored for the interrupted native DSP.
    .thumb_func
step_direction:
    push    {r4, lr}
    bl      thru_on
    cmp     r0, #0
    beq     .Linactive
    mov     r4, r0
    ldr     r1, =REEL_MODE
    ldr     r1, [r1]
    cbnz    r1, .Linactive
    ldr     r1, =REC_ACTIVE
    ldr     r1, [r1]
    cbnz    r1, .Linactive
    ldr     r1, =REC_REQUEST
    ldr     r1, [r1]
    cbnz    r1, .Linactive
    ldr     r1, =NAVIGATION
    ldr     r1, [r1]
    cbnz    r1, .Linactive
    ldr     r1, =COUNT
    ldr     r1, [r1]
    cmp     r1, #2
    blt     .Linactive
    cmp     r1, #300
    bgt     .Linactive
    ldr     r1, =ORG_USED
    ldr     r1, [r1]
    ldr     r2, =ORG_MIN
    ldr     r2, [r2]
    subs    r1, r1, r2
    ble     .Linactive
    vmrs    r2, fpscr
    vpush   {s0-s1}
    vmov    s0, r1
    vcvt.f32.s32 s0, s0
    ldr     r1, =ORG_SCALE
    vldr    s1, [r1]
    vmul.f32 s0, s0, s1
    vldr    s1, k_zone
    vcmpe.f32 s0, s1
    vmrs    APSR_nzcv, fpscr
    vpop    {s0-s1}
    vmsr    fpscr, r2
    blt     .Linactive
    ldr     r1, =RATE_TARGET
    ldr     r1, [r1]
    lsls    r1, r1, #1
    beq     .Linactive               @ a stopped target cannot start stepping
    ldr     r1, =RATE_PLAYING
    ldr     r1, [r1]
    lsls    r1, r1, #1
    beq     .Linactive
    bcc     .Lforward
    cmp     r4, #2
    bne     .Lforward
    mov     r0, #-1
    pop     {r4, pc}
.Lforward:
    movs    r0, #1
    pop     {r4, pc}
.Linactive:
    movs    r0, #0
    pop     {r4, pc}

@ Nonzero for self-timed, full-splice playback. These two mutually
@ exclusive routes prevent an EOSG pulse and a birth from both advancing.
    .thumb_func
whole_splice:
    ldr r1, =FULL_SPLICE
    ldr r1, [r1]
    cmp r1, #1
    bne 1f
    ldr r1, =CLOCK_ACTIVE
    ldr r1, [r1]
    cbnz r1, 1f
    movs r1, #1
    bx lr
1:  movs r1, #0
    bx lr

@ TIM2 observes the native start of the EOSG output pulse. Leave the physical
@ gate and its original 4 -> 3 -> 2 countdown to the stock instructions.
    .thumb_func
e1_eos:
    ldr sb, =EOS_TRIG
    ldr r2, [sb]
    cmp r2, #4
    bne 2f
    push {r1-r3, lr}
    bl whole_splice
    cbnz r1, 1f
    bl step_direction
    cbz r0, 1f
    ldr r1, =NAVIGATION
    str r0, [r1]
1:  pop {r1-r3, lr}
2:  b.w EOS_RETURN

@ Entered exactly when the native scheduler allocates its next voice.
@ r0 is the selected splice, r1 the preceding voice index. Return the
@ selection which native slide/length/marker lookup should use right now.
    .thumb_func
whole_birth:
    push {r4-r6, lr}
    mov r4, r0
    mov r5, r1
    bl whole_splice
    cbz r1, 9f
    bl step_direction
    cbz r0, 9f
    cmp r5, #3
    bhi 9f
    ldr r1, =VOICE_SPLICES
    ldr r1, [r1, r5, lsl #2]
    cmp r1, r4
    bne 9f                      @ a fresh manual or preset choice wins
    ldr r2, =COUNT
    ldr r2, [r2]
    cmp r4, #1
    blo 9f
    cmp r4, r2
    bhi 9f
    add r4, r4, r0
    cmp r4, r2
    it hi
    movhi r4, #1
    cmp r4, #0
    it eq
    moveq r4, r2
    ldr r1, =SELECTED
    str r4, [r1]
    ldr r1, =ACTIVE
    str r4, [r1]                 @ avoid re-triggering the same voice via omod 1
    @ The per-splice length is normally refreshed on the next block.
    @ Slide and the first voice in the new splice need it in THIS sample.
    ldr r1, =MARKERS
    add r1, r1, r4, lsl #2
    ldr r0, [r1]
    ldr r2, [r1, #-4]
    subs r0, r0, r2
    ldr r1, =LENGTHS
    vmrs r2, fpscr
    vpush {s0}
    vmov s0, r0
    vcvt.f32.s32 s0, s0
    add r1, r1, r4, lsl #2
    vstr s0, [r1]
    vpop {s0}
    vmsr fpscr, r2
9:  mov r0, r4
    pop {r4-r6, pc}

@ Each path carries the same two values in different registers. Restore
@ every other live register before replaying the displaced native loads.
    .thumb_func
thru_birth_a:
    push {r1-r3, lr}
    mov r1, r7
    bl whole_birth
    pop {r1-r3, lr}
    ldr r2, [sp, #44]
    ldr r4, [sp, #140]
    b.w BIRTH_A_RETURN

    .thumb_func
thru_birth_b:
    push {r0-r3, r4, lr}
    mov r0, r7
    mov r1, r6
    bl whole_birth
    mov r7, r0
    pop {r0-r3, r4, lr}
    ldr r5, [sp, #32]
    ldr r1, [sp, #140]
    b.w BIRTH_B_RETURN
@ Development 15's preset_organize reaches this block after checking the
@ settings magic and loading the mode byte into r2. Both enabled modes use
@ the same 95% Organize travel. r3 is temporary and the native continuation
@ immediately compares r7, so the condition flags are dead.
    .type PICKUP_LAYOUT_RETURN, %function
    .thumb_func
preset_thru_layout:
    subs r2, r2, #1
    cmp r2, #2
    ite lo
    movlo r2, #1
    movhs r2, #0
    b.w PICKUP_LAYOUT_RETURN
    .ltorg

    .align 2
k_milli:    .word 0x3a83126f
k_zone:     .float 0.95
k_stretch:  .float 1.05263158
