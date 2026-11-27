@ Narrow extension for the pinned Development 15 image. Each hook is reached
@ inside an existing card-out or armed-settings branch in settings_reload.
.syntax unified
.cpu cortex-m4
.thumb
.text
.global rearm_button_state, rearm_mount_state, rearm_parked
.type TICK_ACCEPT, %function
.type TICK_CANCEL, %function
.type TICK_OWNER, %function
.type MOUNT_OWNER, %function
.type MOUNT_ACCEPT, %function
.type MOUNT_NORMAL, %function
.type PARK_PROBE, %function
.type SERVICE_DONE, %function

.equ BUTTON_STATE, 0x20001020
.equ REEL_MODE,    0x20021338
.equ CARD_OK,      0x20001290
.equ SHIFT_MOD,    0x2002a000

@ The timer already checked the physical SHIFT input, both other buttons,
@ recording, the normal-load interlock and CARD_OK. In ordinary state 14,
@ the shifted-knob owner must still be free. State 18 is the reel browser.
.thumb_func
rearm_button_state:
    ldr r3, =BUTTON_STATE
    ldr r3, [r3]
    cmp r3, #14
    beq.w TICK_OWNER
    cmp r3, #18
    bne.w TICK_CANCEL
    ldr r3, =REEL_MODE
    ldr r3, [r3]
    cmp r3, #1
    beq.w TICK_ACCEPT
    b.w TICK_CANCEL

@ Stock FatFs has succeeded and the settings gesture is armed. D15 checks
@ CARD_OK, physical SHIFT and quiet() under the interrupt lock before here.
@ Recheck the same browser state under that lock before taking ownership.
.thumb_func
rearm_mount_state:
    ldr r3, [r5, #32]
    cmp r3, #14
    beq.w MOUNT_OWNER
    cmp r3, #18
    bne.w MOUNT_NORMAL
    ldr r3, =REEL_MODE
    ldr r3, [r3]
    cmp r3, #1
    bne.w MOUNT_NORMAL
    ldr r3, =SHIFT_MOD             @ live pointer used to claim the gesture
    movs r5, #0                   @ original accepted branch clears result
    b.w MOUNT_ACCEPT

@ Only reached when parked, quiet and outside the mounted path. A successful
@ settings reload can stay parked even after D15 detects the next removal.
@ Once the owning press is released and CARD_OK is zero, the next insertion
@ can be handled immediately. A rejected card keeps D15's absence probe.
.thumb_func
rearm_parked:
    ldr r4, [r5, #40]             @ owned; D15 expects r4=0 in PARK_PROBE
    cmp r4, #0
    bne.w SERVICE_DONE
    ldr r3, =CARD_OK
    ldr r3, [r3]
    cmp r3, #0
    bne.w PARK_PROBE
    ldr r3, [r5, #48]             @ result: 1 = settings applied
    cmp r3, #1
    bne.w PARK_PROBE
    str r4, [r5, #48]
    str r4, [r5, #32]             @ publish IDLE after clearing the old result
    b.w SERVICE_DONE
    .ltorg
