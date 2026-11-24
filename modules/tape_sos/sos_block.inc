@ Shared per-block S.O.S. hook (P7) for tape_sos.S.
@ The including file defines the P7_EXTRA macro (runs with r0-r3, s0-s1 free,
@ r3 = MOD, just before the hook returns) and the k_scale/k_top/k_offset
@ constants plus MOD, MAGIC, T_PICKUP and P7_RETURN.

@ Map a primary or secondary S.O.S. ADC value to the standard 0..1 recording gain.
    .macro SOS_RETENTION adc
    vmov    s0, \adc
    vcvt.f32.s32 s0, s0
    vldr    s1, k_scale
    vmul.f32 s0, s0, s1
    vldr    s1, k_top
    vcmpe.f32 s0, s1
    vmrs    APSR_nzcv, fpscr
    ble     81f
    vmov.f32 s0, #1.0
    b       82f
81: vldr    s1, k_offset
    vsub.f32 s0, s0, s1
    vcmpe.f32 s0, #0
    vmrs    APSR_nzcv, fpscr
    it      lt
    vsublt.f32 s0, s0, s0
82:
    .endm

@ P7 (hook at 0x080276c4, once per audio block). r1 = &0x20021c68; r5 is
@ the S.O.S. reading the stock code converts into the listening coefficient.
    .thumb_func
p7_sos_block:
    ldr     r5, [r1]                    @ replaced: S.O.S. reading
    push    {r0-r3, r12, lr}
    vpush   {s0-s1}
    ldr     r3, =MOD
    ldr     r0, [r3]
    ldr     r2, =MAGIC
    cmp     r0, r2
    bne     9f
    ldrb    r0, [r3, #6]                @ editing S.O.S. with SHIFT?
    cmp     r0, #1
    bne     5f
    ldrb    r0, [r3, #5]
    cbz     r0, 5f
    ldrb    r0, [r3, #4]
    cbz     r0, 5f
    SOS_RETENTION r5                    @ SHIFT + S.O.S. feedback bank
    vstr    s0, [r3, #20]
    movs    r0, #1
    strb    r0, [r3, #16]
    ldrb    r0, [r3, #17]
    cbnz    r0, 3f
    ldrh    r0, [r3, #8]                @ pre-edit knob position (session snapshot)
    strh    r0, [r3, #18]
    movs    r0, #1
    strb    r0, [r3, #17]
3:  ldrh    r5, [r3, #18]               @ listening mix stays where it was
    b       9f
5:  ldrb    r0, [r3, #17]               @ pickup pending?
    cbz     r0, 9f
    ldrh    r0, [r3, #18]
    subs    r0, r5, r0
    it      mi
    rsbmi   r0, r0, #0
    cmp     r0, #T_PICKUP
    ble     6f
    ldrh    r5, [r3, #18]
    b       9f
6:  movs    r0, #0                      @ knob is back: follow it again
    strb    r0, [r3, #17]
9:  preset_post preset_feedback_effect, 0, 0
    P7_EXTRA
    mov r0, r5
    preset_post preset_sos, 0, 0
    mov r5, r0
    @ The old block is flushed by P7_EXTRA with its previous tape cache.
    @ Publish these settings before this block picks record and monitor paths.
    ldr     r3, =MOD
    ldr     r1, =DRYK_OPTION            @ boot-cleared even before first SHIFT timer tick
    ldrb    r0, [r1]
    cmp     r0, #3
    it      hi
    movhi   r0, #0
    strb    r0, [r3, #DRYK_BLOCK]
    @ Symmetric endpoint allowance; both analog controls and presets use r5.
    subs    r1, r5, #185
    it      mi
    movmi   r1, #0
    movw    r0, #3726
    cmp     r1, r0
    it      hi
    movhi   r1, r0                      @ existing contribution before mode selection
    subs    r2, r0, r1                  @ incoming contribution
    ldr     r12, =SOSC_OPTION
    ldrb    r12, [r12]
    cmp     r12, #1
    beq     13f
    cmp     r12, #2
    beq     14f
    movw    r0, #1831                   @ both at unity over ADC 2016..2080
    cmp     r1, r0
    it      hi
    movhi   r1, r0
    cmp     r2, r0
    it      hi
    movhi   r2, r0
    b       15f
13: mov     r2, r0                      @ keep incoming at unity
    b       15f
14: mov     r1, r0                      @ keep existing at unity
15: vmov    s1, r0
    vcvt.f32.u32 s1, s1
    vmov    s0, r1
    vcvt.f32.u32 s0, s0
    vdiv.f32 s0, s0, s1
    vstr    s0, [r3, #DRYK_GAIN]
    vmov    s0, r2
    vcvt.f32.u32 s0, s0
    vdiv.f32 s0, s0, s1
    vstr    s0, [r3, #INPUT_GAIN]
    vpop    {s0-s1}
    pop     {r0-r3, r12, lr}
    vldr    s1, k_top                   @ replaced: vldr s1, =1.04884
    b.w     P7_RETURN

