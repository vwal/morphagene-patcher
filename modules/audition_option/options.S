.syntax unified
.cpu cortex-m4
.thumb
.text

.equ OPTION, 0x20028fa4
.equ STAGED, OPTION+1             @ 0 missing, otherwise digit + 1
.global audt_mount_default, audt_normal_line, audt_write
.global audt_live_begin, audt_live_line, audt_live_seen, audt_live_commit

@ Ordinary mount, after optional firmware installation and before options.txt
@ is opened. This also sets the default when the card has no options.txt.
.thumb_func
audt_mount_default:
    ldr r0, =OPTION
    movs r1, #0
    strb r1, [r0]
    ldr r0, =0x200012e0
    ldr r1, [r0]
    ldr pc, =0x08023295

@ Only the first, complete significant portion of an ordinary option line
@ reaches this call. Preserve D23's overlong-line and continuation guards.
.thumb_func
audt_normal_line:
    bl read_normal_option
    ldr pc, =0x0804bc15

@ Immediately after the bank line, while the file in r6 is still open.
.thumb_func
audt_write:
    mov r0, r6
    ldr r1, =audt_format
    ldr r2, =OPTION
    ldrb r2, [r2]
    blx r7                         @ native FatFs f_printf
    ldr.w sl, [r8, #68]
    ldr pc, =0x0804d0bb

@ Live read_options entry clears related transaction tokens before any I/O.
.thumb_func
audt_live_begin:
    str.w r3, [r5, #232]
    ldr ip, =STAGED
    strb r3, [ip]
    ldr pc, =0x08050b11

@ reload_parse_line has already packed the four leading key bytes into r0.
@ Its ordinary bank dispatch and its audt dispatch share the parser epilogue.
.thumb_func
audt_live_line:
    ldr r3, =0x74647561             @ audt
    cmp r0, r3
    beq 1f
    ldr r3, =0x6b6e6162             @ original comparison against bank
    cmp r0, r3
    ldr pc, =0x08050435
1:  adds r0, r1, #4
    bl stage_live_option
    ldr pc, =0x080503ff

@ Include audt-only files in the recognized-options check after valid EOF.
.thumb_func
audt_live_seen:
    ldr.w r3, [r3, #232]
    ldr r2, =STAGED
    ldrb r2, [r2]
    orrs r3, r2
    ldr pc, =0x08050bbd

@ All validation and the reel seek have passed. This is the same locked
@ audio-block commit as the other live options. An omitted line recalls 0.
.thumb_func
audt_live_commit:
    ldr r2, =OPTION
    ldrb r3, [r2, #1]
    cbz r3, 2f
    subs r3, #1
2:  strb r3, [r2]
    ldr r3, =0x0804ffe5            @ original presets_publish(PRESET_LIVE)
    blx r3
    ldr pc, =0x08050ebd

.ltorg
audt_format:
    .asciz "audt %u //Bank picker: 0 audition, 1 keep current playback.\n"
