    .syntax unified
    .cpu cortex-m4
    .fpu fpv4-sp-d16
    .thumb
    .text
    .global picker_active, picker_organize, picker_enter, picker_short, picker_leave, picker_mount

@ Leaf used by DSP and the thru scheduler. Return r0 = 0/1, preserve r1-r12.
@ Check mode before button state: the real foreground commit clears mode at
@ the exact point at which the new bank and slot are published.
    .thumb_func
picker_active:
    ldr r0,=0x20021338              @ native reel mode 2 (request) or 1 (ready)
    ldr r0,[r0]
    cbz r0,3f
    ldr r0,=0x2002a61f              @ bank 0 has only the native reel browser
    ldrb r0,[r0]
    cbz r0,3f
    ldr r0,=0x20001290
    ldr r0,[r0]
    cmp r0,#1
    bne 3f
    ldr r0,=0x20028f58              @ D22 browsing phases, through commit
    ldrb r0,[r0]
    cbz r0,1f
    cmp r0,#7
    bhi 3f
    b 2f
1:  ldr r0,=0x20001020              @ bank-enabled chord awaiting the long hold
    ldr r0,[r0]
    subs r0,#16
    cmp r0,#1
    bhi 3f
2:  movs r0,#1
    bx lr
3:  movs r0,#0
    bx lr

@ Snapshot the real Organize position as soon as D22 accepts the chord.
    .thumb_func
picker_enter:
    ldr r1,=0x20021c70
    ldr r1,[r1]
    ldr r2,=0x20028f8c
    str r1,[r2,#4]
    @ Publish the two native stores together. A higher-priority audio IRQ can
    @ run before this pair or after it, never with MODE=2 but the old state.
    push {r0}
    mrs r0,primask
    cpsid i
    movs r1,#2
    movs r2,#16
    str r1,[r6]
    str r2,[r9]
    msr primask,r0
    pop {r0}
    ldr pc,=0x080248fd

@ Short release hands Organize to the ordinary reel browser. Clear a previous
@ canceled hold even when no audio runs between release and the next chord.
    .thumb_func
picker_short:
    ldr r1,=0x20028f8c
    movs r3,#0
    str r3,[r1]
    @ A genuine short release still lets the native foreground abandon a
    @ large current transfer to begin auditioning reels. Bank 0 already
    @ made this request immediately, in its original state-16 handler.
    ldr r1,=0x2002a61f
    ldrb r3,[r1]
    cbz r3,1f
    ldr r1,=0x20001290
    ldr r3,[r1]
    cmp r3,#1
    bne 1f
    ldr r1,=0x20021388
    ldr r3,[r1]
    cbnz r3,1f
    ldr r1,=0x200213cc
    movs r3,#1
    str r3,[r1]
1:
    ldr r1,=0x20001024               @ D22 displaced hold timestamp pointer
    movs r3,#18
    ldr pc,=0x0805408f

@ D22 panel_leave runs before clearing MODE on cancel, or after the successful
@ commit has already cleared it. Preserve caller registers and the D22 ABI.
    .thumb_func
picker_leave:
    push {r0-r3,ip,lr}
    ldr r0,=0x20028fa0
    movs r1,#0
    str r1,[r0]                     @ invalidate any deferred Gene boundary
    bl picker_end_organize
    pop {r0-r3,ip,lr}
    ldr r3,=0x20028f00
    ldr r2,[r3,#96]
    ldr pc,=0x080542b1

    .thumb_func
picker_mount:
    ldr r0,=0x20028f8c
    str r1,[r0]                     @ r1 = 0 in D22 menu_mount
    str r1,[r0,#20]                 @ no boundary request across mounts
    ldr pc,=0x08023b03

@ D22's normal Organize handler consults both preset and Turing pickup, and
@ rereads the physical ADC. Leave those latches untouched while it is a menu
@ dial. Stock still receives the last accepted playback position and continues
@ to clock, reschedule and play the existing voices.
    .thumb_func
picker_organize:
    push {r0-r3,ip,lr}
    bl picker_active
    cbnz r0,1f
    ldr r1,=0x20028f8c
    ldr r1,[r1]
    cbz r1,2f
    bl picker_hold_after_cancel
    cbz r0,2f
1:  pop {r0-r3,ip,lr}
    ldr r7,=0x200220ac
    ldr r0,[r7]
    cmp r0,#4096                    @ native first-load sentinel is negative
    blo 3f
    ldr r7,=0x20028f8c
    ldr r0,[r7,#4]
3:  ldr r7,=0x20022078              @ calibration max expected by native code
    ldr pc,=0x080276f5
2:  pop {r0-r3,ip,lr}
    ldr pc,=0x0804dfc1              @ D22 o1_organize: normal ADC and both pickups
    .ltorg

    .include "audio.inc.S"
    .include "boundary.inc.S"
    .include "thru.inc.S"
    .include "transfer.inc.S"
    .include "timing.inc.S"
