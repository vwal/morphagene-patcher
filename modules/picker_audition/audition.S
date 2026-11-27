    .syntax unified
    .cpu cortex-m4
    .thumb
    .text
    .global audition_foreground, audition_audio_entry

@ D15's main hook already saved scratch registers and aligned the stack.
@ Close any preview before D22 inventories another reel or commits a switch.
@ Service a newly published CHOOSE stage on the very same main iteration.
    .thumb_func
audition_foreground:
    ldr r0,=0x20028f58
    ldrb r0,[r0]
    cmp r0,#4
    beq 2f
    cmp r0,#6
    beq 2f
    ldr r1,=0x20028fa8
    ldr r1,[r1,#4]             @ target key (also set for a waiting/failed target)
    cbz r1,1f
    bl preview_discard
1:  ldr r0,=0x20028f58
    ldrb r0,[r0]
    cbz r0,3f
    ldr r1,=0x08054ddd         @ D22 panel_service
    blx r1
2:  bl preview_service
3:  ldr pc,=0x08051d0f         @ D15 main hook restores saved registers

@ D4 has already applied any pending live settings. On the ordinary audio
@ path only test the published preview word, then replay the displaced PUSH.
@ Otherwise call the entire D23 renderer before replacing its finished I2S
@ output. D23 continues clocking, reading the inputs and rendering its voices.
    .thumb_func
audition_audio_entry:
    ldr ip,=0x20028fa8
    ldr ip,[ip]
    cmp ip,#0
    beq 1f
    push {r1-r3,lr}
    bl 1f
    pop {r0,r1,r3,lr}           @ r0=original TX pointer, r1=stereo halfwords
    b preview_output
1:  push {r4-r11,lr}
    ldr pc,=0x0802751d
    .ltorg
