@ Both stock REC layouts feed this single start path. R5 is its resolved SD
@ start offset in frames. If selected, change it together with the RAM head.
    .global length_start, length_stop
    .thumb_func
length_start:
    push    {r0-r3, ip, lr}
    mov     r0, r5
    bl      dry_length_start
    mov     r5, r0
    pop     {r0-r3, ip, lr}
    movs    r3, #0                     @ displaced
    lsls    r5, r5, #3
    b.w     LENGTH_START_RETURN

@ Publish marker and head before the normal stop signals the mounted WAV
@ writer. A foreground stop may also enter here. Clear recording first, as
@ stock does, so an interrupt cannot write between publication and stop.
    .thumb_func
length_stop:
    str     r3, [r6]                   @ displaced: REC_ACTIVE = 0
    str     r3, [r5]                   @ displaced: record state = 0
    ldr     r3, =LENGTH_TAKE
    ldr     r3, [r3]
    cbz     r3, 1f
    push    {r0-r3, ip, lr}
    bl      dry_length_finish
    pop     {r0-r3, ip, lr}
    cmp     r0, #1
    it      eq
    moveq   r0, #0                     @ a replacement never adds a marker
1:  movs    r3, #0                     @ stock zero remains live
    cmp     r0, #1                     @ restore flags for stock BEQ
    b.w     LENGTH_STOP_RETURN
    .ltorg

@ The two sample callbacks supply different VFP registers. Keep their live
@ registers intact. Write a single calibrated input frame, just like an empty
@ capture, saturating the resulting PCM to the range of its signed storage.
    .macro LINEAR_SAMPLE left, right, done
    ldr     r4, =LENGTH_TAKE
    ldr     r1, [r4]                   @ latched one-based splice
    ldr     r3, =MARKER_COUNT
    ldr     r3, [r3]
    cmp     r1, r3
    bne     72f
    ldr     r3, =REC_INDEX
    ldr     r3, [r3]
    cmp     r1, r3
    bne     72f
    ldr     r5, =MARKERS
    add     r5, r5, r1, lsl #2
    ldr     r3, [r5, #-4]
    ldr     r6, [r4, #4]
    cmp     r3, r6
    bne     72f
    ldr     r3, [r5]
    ldr     r6, [r4, #8]
    cmp     r3, r6
    bne     72f
    ldr     r1, [r4, #12]              @ private cursor advances exactly once per frame
    ldr     r5, [r4, #16]              @ validated against both stereo planes at start
    ldr     r3, =CAPACITY
    ldr     r3, [r3]
    cmp     r3, r5
    bne     72f
    cmp     r1, r5
    bhs     72f
    vpush   {s0-s1}
    vldr    s0, 73f
    ldr     r2, =LEFT_PTR
    ldr     r2, [r2]
    vmul.f32 s1, \left, s0
    vcvt.s32.f32 s1, s1
    vmov    r3, s1
    ssat    r3, #16, r3
    strh    r3, [r2, r1, lsl #1]
    ldr     r2, =RIGHT_PTR
    ldr     r2, [r2]
    vmul.f32 s1, \right, s0
    vcvt.s32.f32 s1, s1
    vmov    r3, s1
    ssat    r3, #16, r3
    strh    r3, [r2, r1, lsl #1]
    vpop    {s0-s1}
    adds    r1, r1, #1
    str     r1, [r4, #12]
    ldr     r2, =HEAD
    str     r1, [r2]
    cmp     r1, r5
    blo     74f
72: push    {r0-r2, ip, lr}            @ align stock call after WRITE_HOOK saved three words
    movs    r0, #0
    bl      STOCK_RECORD_STOP
    pop     {r0-r2, ip, lr}
74: pop     {r1-r3}                    @ from WRITE_HOOK
    b.w     \done
    .align 2
73: .float 32767.0
    .endm
