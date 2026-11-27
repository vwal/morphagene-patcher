    .global picker_transfer_mode, picker_transfer_abort, picker_wait_for_sd

@ The foreground loader normally limits native reel auditions to 32 large
@ reads. If it starts the current reel's pending copy with the bank chord
@ down, continue the full resident-reel transfer at its normal capacity.
    .thumb_func
picker_transfer_mode:
    ldr r6,[r5]
    cmp r6,#1
    bne 1f
    push {r0,lr}
    bl picker_active
    cmp r0,#0
    it ne
    movne r6,#0
    pop {r0,lr}
1:  ldr r1,[sp,#856]
    ldr pc,=0x08023d01

@ Native main polls this abort word between SD chunks. State 16 normally
@ writes it as soon as the chord starts. A possible long hold cannot abort
@ the playing reel. If a short chord finishes while main is still occupied
@ and cannot acknowledge MODE=2, its complete release can post the abort.
    .thumb_func
picker_transfer_abort:
    push {r0,lr}
    bl picker_active
    cbz r0,1f
    ldr r0,[sp,#12]                   @ original TIM2 [sp,#4]: any button held
    cbnz r0,2f
1:  ldr r1,=0x200213cc
    movs r3,#1
    str r3,[r1]
2:  pop {r0,lr}
    ldr pc,=0x0802524d

@ A long transfer can outlast the three-second gesture. Permit only the
@ initial scan to wait for MODE=2 to be acknowledged; its foreground scan
@ still requires MODE=1 and an idle SD dispatcher. SHIFT and card removal
@ have already been checked, so either can cancel the wait.
    .thumb_func
picker_wait_for_sd:
    cmp r3,#1
    beq 1f
    cmp r3,#2
    bne 2f
    ldrb r3,[r4,#88]
    cmp r3,#1
    bne 2f
1:  ldr pc,=0x08054903                @ D22 check bank option, process buttons
2:  ldr pc,=0x08054909                @ D22 cancel
    .ltorg
