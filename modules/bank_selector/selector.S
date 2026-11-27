    .syntax unified
    .cpu cortex-m4
    .thumb
    .text
    .equ PHASE,       0x20028f58
    .equ GENERATION,  0x20024278
    .equ MODE,        0x20021338
    .equ HOLD_START,  0x20001024
    .equ BANK_OPTION, 0x2002a61f
    .equ CARD,        0x20001290

    .global menu_dispatch, menu_hold, menu_foreground, menu_organize, menu_led, menu_mount
    .global menu_short_release, menu_short_confirm
    .type TIM_DISPATCH, %function
    .type TIM_DONE, %function
    .type TIM_ENTER_REEL, %function
    .type D18_HOLD_END, %function
    .type D15_MAIN_END, %function
    .type D18_ORGANIZE, %function
    .type SKIP_ORGANIZE, %function
    .type D15_LED_START, %function
    .type D15_LED_END, %function
    .type NATIVE_MOUNT, %function
    .type TIM_SHORT_RELEASE_END, %function
    .type TIM_SHORT_CONFIRM, %function
    .type TIM_CONFIRM_DELAY, %function
@ The normal idle case retains the native TIM2 dispatcher. When the two keys
@ first debounce on the same tick, prefer the reel chord on a mounted, bank-
@ enabled module. A preceding REC-only tick remains a recording gesture.
    .thumb_func
menu_dispatch:
    ldr r1,=PHASE
    ldrb r1,[r1]
    cbnz r1,.Lbuttons
    ldr r1,[r9]
    cmp r1,#16                  @ short entry released before the 250ms hold check
    beq .Learly_release
    cmp r1,#8                   @ SPLICE already down
    beq .Lchord
    cmp r1,#1                   @ ordinary playback idle
    bne .Lnative
.Lchord:
    cbz r2,.Lnative
    cbz r3,.Lnative
    cmp ip,#0
    bne .Lnative
    ldr r1,=BANK_OPTION
    ldrb r1,[r1]
    cbnz r1,.Lmounted
    ldr r1,[r9]                 @ in bank 0, simultaneous edges keep stock precedence
    cmp r1,#8                   @ an explicit SPLICE-first chord enters immediately
    bne .Lnative
.Lmounted:
    ldr r1,=CARD
    ldr r1,[r1]
    cmp r1,#1
    bne .Lnative
    ldr r1,=0x20022108          @ leave an ongoing recording's controls alone
    ldr r1,[r1]
    cbnz r1,.Lnative
    ldr r1,=0x20021320
    ldr r1,[r1]
    cbnz r1,.Lnative
    ldr r1,[r9]
    cmp r1,#1
    bne .Lenter
    ldr r1,=HOLD_START
    str lr,[r1]                 @ simultaneous edge has no preceding SPLICE tick
.Lenter:
    b.w TIM_ENTER_REEL          @ mode=2, state=16, even for a short overlap
.Learly_release:
    ldr r1,[sp,#4]              @ wait for complete release after the first chord
    cbnz r1,.Lnative
    ldr r1,[r6]                 @ native foreground has acknowledged reel mode
    cmp r1,#1
    beq menu_short_release
.Lnative:
    ldr r1,[r9]
    b.w TIM_DISPATCH
.Lbuttons:
    push {r0-r3,ip,lr}
    mov r0,r3                   @ current debounced SPLICE, REC and SHIFT
    mov r1,r2
    mov r2,ip
    bl panel_buttons
    pop {r0-r3,ip,lr}
    b.w TIM_DONE                @ consume all edit, record and delete gestures

@ The initiating chord is fully released in ordinary reel mode. Synchronize
@ the stock New Reel cursor once without loading anything. The long hold
@ enters panel_begin instead and never takes this path.
    .thumb_func
menu_short_release:
    push {r0-r3,ip,lr}
    bl panel_short_cursor
    pop {r0-r3,ip,lr}
    ldr r1,=HOLD_START
    movs r3,#18
    b.w TIM_SHORT_RELEASE_END

@ The original state 18 dispatcher arrived here only after debouncing both
@ SPLICE and REC, with SHIFT unpressed. A second 6000-tick delay could then
@ discard a legitimate short confirmation. Use the ordinary confirmation
@ including its pending-load protection and release lock.
    .thumb_func
menu_short_confirm:
    ldr r1,=CARD
    ldr r1,[r1]
    cmp r1,#1
    bne .Loriginal_delay
    push {r0-r3,ip,lr}
    bl panel_short_cursor
    pop {r0-r3,ip,lr}
    b.w TIM_SHORT_CONFIRM
.Loriginal_delay:
    ldr sl,=HOLD_START
    b.w TIM_CONFIRM_DELAY

@ D15 has checked the mounted card and bank settings and saved r0,r1,r4,lr.
@ The long press arms once. Its release never enters the native preview path.
    .thumb_func
menu_hold:
    cmp ip,#0
    bne .Lhold_end
    cbz r2,.Lhold_end
    cbz r3,.Lhold_end
    ldr r0,=HOLD_START
    ldr r0,[r0]
    sub r0,lr,r0
    ldr r1,=288000
    cmp r0,r1
    blo .Lhold_end
    bl panel_begin
    pop {r0,r1,r4,lr}
    b.w TIM_DONE
.Lhold_end:
    b.w D18_HOLD_END

@ Reuse the D15 main-loop frame and its stock card/flags dispatch tail.
    .thumb_func
menu_foreground:
    ldr r0,=PHASE
    ldrb r1,[r0]
    cbz r1,.Lfg_done
    bl panel_service
.Lfg_done:
    b.w D15_MAIN_END

@ Do not allow the acoustic knob task to preview a reel or write its cursor
@ while the performer is selecting a bank/reel/splice. Native epilogues on
@ each path still initialize their audio-block locals.
    .thumb_func
menu_organize:
    push {r1}
    ldr r1,=PHASE
    ldrb r1,[r1]
    cmp r1,#0
    pop {r1}
    beq.w D18_ORGANIZE
    b.w SKIP_ORGANIZE

    .thumb_func
menu_led:
    push {r1,r3}
    ldr r2,=PHASE
    ldrb r7,[r2]
    cbnz r7,.Llights
    @ Stock enters reel mode before the long hold qualifies. Keep REEL
    @ steady during that initiating press so its first blink means BANK.
    ldr r2,=BANK_OPTION
    ldrb r7,[r2]
    cbz r7,.Lstock_lights
    ldr r2,=0x20001020
    ldr r7,[r2]
    subs r7,#16
    cmp r7,#1
    bhi .Lstock_lights
    ldr r2,=0x20028ff1          @ currently open reel slot, even when empty
    ldrb r7,[r2]
    and r7,r7,#7
    ldr r2,=0x20001038
    str r7,[r2]
    b.w D15_LED_END
.Lstock_lights:
    pop {r1,r3}
    b.w D15_LED_START
.Llights:
    push {r0-r3,ip,lr}
    bl panel_lights
    pop {r0-r3,ip,lr}
    b.w D15_LED_END

@ Stock's mount entry invalidates all prior picker state before read_options.
    .thumb_func
menu_mount:
    movs r1,#0
    str r1,[r0,#12]             @ displaced D15 rb_defer stores
    str r1,[r0,#8]
    ldr r0,=PHASE
    strb r1,[r0]
    ldr r0,=0x20028f80
    str r1,[r0]                 @ invalidate any staged load from earlier media
    b.w NATIVE_MOUNT
    .ltorg

.include "storage_hooks.S"
