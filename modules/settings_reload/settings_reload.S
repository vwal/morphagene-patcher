@ Development 4. C helpers use the declared scratch arena and main stack;
@ options/CARD_OK are published at the audio boundary. See README.md.
.syntax unified
.cpu cortex-m4
.fpu fpv4-sp-d16
.thumb
.text
.global reload_mount, reload_mount_done, reload_main, reload_buttons, reload_audio, reload_led, reload_write, reload_open
.type MOUNT_CALL, %function
.type MOUNT_SKIP, %function
.type MOUNT_NORMAL, %function
.type MAIN_RETURN, %function
.type MAIN_MOUNTED, %function
.type MAIN_HEAD, %function
.type BUTTON_RETURN, %function
.type TIM2_DONE, %function
.type LED_RETURN, %function
.type AUDIO_RETURN, %function
.type WRITE_RETURN, %function
.type OPEN_RETURN, %function

@ 96 bytes: preserve volatile integer/FP state, APSR and FPSCR, aligned for C.
.macro save_call
    push {r0-r3, r12, lr}
    vpush {s0-s15}
    mrs r0, APSR
    vmrs r1, FPSCR
    push {r0,r1}
.endm
.macro restore_call
    pop {r0,r1}
    msr APSR_nzcvq, r0
    vmsr FPSCR, r1
    vpop {s0-s15}
    pop {r0-r3, r12, lr}
.endm

@ Before stock f_mount. An owned insertion never enters updater/reel paths.
.thumb_func
reload_mount:
    push {r0,r1}
    ldr r0, =0x2002a820
    ldr r1, [r0]
    cmp r1, #2
    pop {r0,r1}
    bhi 1f
    movs r2, #1
    ldr r1, =0x0803e974
    addw r0, sp, #1948
    b.w MOUNT_CALL
1:  b.w MOUNT_SKIP

@ A successful mount is the reliable insertion signal. Intercept it before
@ the normal updater, stop and reel-load sequence can run.
.thumb_func
reload_mount_done:
    save_call
    ldr r0, [sp, #72]
    bl reload_mounted
    cmp r0, #0
    bne 1f
    restore_call
    cmp r0, #0
    beq 2f
    b.w MOUNT_SKIP
1:  restore_call
    b.w MAIN_HEAD
2:  b.w MOUNT_NORMAL

@ Common main-loop head. Snapshot the idle live file, service reload/cleanup,
@ and hold dispatch until the audio-boundary commit publishes CARD_OK.
.thumb_func
reload_main:
    save_call
    addw r0, sp, #(1948+96)
    addw r1, sp, #(844+96)
    bl reload_service
    cmp r0, #0
    bne 2f
    restore_call
    ldr r6, =0x20001290
    ldr r6, [r6]
    cmp r6, #0
    bne 1f
    ldr r2, [sp, #16]
    b.w MAIN_RETURN
1:  b.w MAIN_MOUNTED
2:  restore_call
    b.w MAIN_HEAD

@ Before stock button dispatch and before SHIFT knob gestures. In ordinary
@ mounted operation, skip C entirely. Owned holds are consumed until release.
.thumb_func
reload_buttons:
    push {r0,r1}
    ldr r0, =0x2002a820
    ldr r1, [r0]
    cbnz r1, 1f
    ldr r0, =0x20001290
    ldr r0, [r0]
    cmp r0, #0
    bne 3f
1:  pop {r0,r1}
    save_call
    mov r0, r12
    mov r1, r2
    mov r2, r3
    bl reload_tick
    cmp r0, #0
    bne 2f
    restore_call
    b 4f
2:  restore_call
    ldr r6, =0x20021338             @ live pointers expected by the LED tail
    ldr r9, =0x20001020
    b.w TIM2_DONE
3:  pop {r0,r1}
4:  ldr r6, =0x20021338
    ldr r9, [r6]
    b.w BUTTON_RETURN

@ Modify only SHIFT's serial LED bit, not CARD_OK or the persistent LED word.
.thumb_func
reload_led:
    push {r0,r1}
    ldr r0, =0x2002a820
    ldr r1, [r0]
    cbnz r1, 3f
    ldr r1, [r0, #228]              @ mounted reel fingerprint scan, not arming
    cbz r1, 1f
3:  pop {r0,r1}
    save_call
    mov r0, r3
    bl reload_led_mask
    str r0, [sp, #84]               @ saved r3 in save_call frame
    restore_call
    b 2f
1:  pop {r0,r1}
2:  ldr r0, =0x40021800
    lsr.w r2, r3, r1
    b.w LED_RETURN

@ Commit all validated settings before the next audio block reads any of
@ them. No FatFs or codec calls here. The normal path is a small flag check.
.thumb_func
reload_audio:
    push {r0,r1}
    ldr r0, =0x2002a82c
    ldr r1, [r0]
    cbnz r1, 3f
    ldr r0, =0x2002a611
    ldrb r1, [r0]
    ldrb r0, [r0, #1]
    cmp r0, r1
    beq 1f
3:  pop {r0,r1}
    save_call
    bl reload_commit
    restore_call
    b 2f
1:  pop {r0,r1}
2:  push {r4-r11, lr}              @ displaced audio prologue
    b.w AUDIO_RETURN

@ Common internal FatFs write core: f_write, f_printf, f_puts all reach here.
.thumb_func
reload_write:
    save_call
    ldr r0, [sp, #72]
    bl reload_dirty
    restore_call
    push {r4-r11,lr}
    b.w WRITE_RETURN

@ Creating/truncating an existing file can change it without a later write.
.thumb_func
reload_open:
    tst r2, #0x1e
    beq 1f
    save_call
    ldr r0, [sp, #72]
    bl reload_dirty
    restore_call
1:  push {r4-r9,lr}
    b.w OPEN_RETURN
.ltorg
