@ D22 has accepted the final chord and stored its chosen existing splice.
@ The New Reel branch goes directly from the reel step into commit.
    .global picker_final_recorded_chord, picker_timed_commit
    .thumb_func
picker_final_recorded_chord:
    bl picker_confirm_recording     @ r0 = selected one-based splice
    ldr pc,=0x080548d9              @ panel_buttons epilogue

@ Replaces the BL to selector_commit in the native foreground panel_service.
@ A return value of zero keeps the picker open for its next foreground visit.
    .thumb_func
picker_timed_commit:
    bl picker_service_recording     @ r0/r1/r2 = bank, reel, splice
    ldr pc,=0x08054e53
    .ltorg

@ D22 defaults both windows to dark when its foreground is busy. During a
@ musical wait, show the selected reel steadily and blink the selected splice.
    .global picker_pending_lights
    .thumb_func
picker_pending_lights:
    cmp r6,#7                      @ D22 commit phase
    bne 1f
    ldr r3,=0x20028fa0
    ldr r3,[r3]
    cbz r3,1f
    ldrb r0,[r5,#93]
    and r0,r0,#7
    ldrh r3,[r5,#94]
    and r3,r3,#7
    movw r2,#48000
    cmp r4,r2                      @ r4 = elapsed ticks modulo 96000
    it hs
    movhs r3,#8
    b 2f
1:  movs r3,#8                     @ D22 dark color
    mov r0,r3
2:  ldr pc,=0x080549f9
    .ltorg
