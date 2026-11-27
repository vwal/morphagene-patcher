    .syntax unified
    .cpu cortex-m4
    .thumb
    .text

    .type D18_SMALL_WAV,%function
    .type MEDIA_OK,%function
    .type MEDIA_LOST,%function
    .type NATIVE_DUE_BRANCH,%function

@ Carry is clear when the check is due. Compare elapsed ticks so that a busy
@ foreground crossing 32-bit counter rollover still reaches the existing check.
@ Restore both original temporary register values without disturbing carry.
    .global presence_elapsed
    .thumb_func
presence_elapsed:
    sub.w   r0, r2, r4
    ldr     lr, =192000
    cmp     lr, r0
    add.w   lr, r4, #191488
    add.w   r0, lr, #512
    b.w     NATIVE_DUE_BRANCH

@ At the native command helper's return, the SDIO registers are already
@ programmed. r4/r5 are scratch here because the original epilogue restores
@ their caller's values. Preserve the condition flags and return value.
    .global presence_activity
    .thumb_func
presence_activity:
    ldr     r4, =0x20028f40
    ldr     r5, =0x20021c88
    ldr     r5, [r5]
    str     r5, [r4, #4]
    ldr     r5, [r4]
    add.w   r5, r5, #1
    str     r5, [r4]
    pop     {r4, r5}
    bx      lr

@ Only reached after the mounted idle check's two successful native seeks.
@ The original <= 512-byte media read and failure paths keep their exact
@ stack frame. On larger files the native path needs r4-r11 on either exit.
    .global presence_idle
    .thumb_func
presence_idle:
    bls.w   D18_SMALL_WAV
    push    {r4, lr}
    bl      presence_missing
    pop     {r4, lr}
    cmp     r0, #0
    bne.w   MEDIA_LOST
    b.w     MEDIA_OK
    .ltorg
