    .syntax unified
    .cpu cortex-m4
    .thumb
    .text

    .global bank_reel_candidate
    .type BANK_MAX_32, %function
    .type COMPARE_WITH_CURSOR, %function
    .equ AWAIT_CONFIRM, 0x20028f0e

@ In the native reel picker r0 is the candidate (1..reels+1), r4 the
@ existing reel count, and the last segment normally creates a new reel on
@ confirmation. Only a deliberate bank switch sets AWAIT_CONFIRM. Values
@ above 1 identify the only recorded reel among multiple files. Otherwise
@ preserve every existing reel's bin and fold just the virtual creation
@ slot onto the last reel. The short-entry picker still offers New Reel.
@ The D19 caller already saved r2 and loaded the bank option's address.
    .thumb_func
bank_reel_candidate:
    ldrb    r2, [r2]
    cmp     r2, #0
    beq.w   COMPARE_WITH_CURSOR
    ldr     r2, =AWAIT_CONFIRM
    ldrb    r2, [r2]
    cbz     r2, 1f
    cbz     r4, 1f
    subs    r2, #1
    cmp     r2, r4
    bhi     2f
    cmp     r2, #0
    it      ne
    movne   r0, r2
2:
    cmp     r0, r4
    it      hi
    movhi   r0, r4
1:  b.w     BANK_MAX_32
    .ltorg
