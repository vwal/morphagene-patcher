    .syntax unified
    .cpu cortex-m4
    .thumb
    .text
    .global selector_pin_cursor, selector_parsed, selector_transferred
    .global selector_bad_format, selector_valid_data
    .global selector_prepare_manual, selector_manual_open_mode, selector_accepted_chord

@ r3 and r1 address the native count and cursor, r2 has the hardware state.
@ No floating point registers are used by the called C functions.
    .thumb_func
selector_pin_cursor:
    push {r0-r3,ip,lr}
    bl selector_open_cursor
    cmp r0,#0
    pop {r0-r3,ip,lr}
    ldr r0,[r3]
    ldr r1,[r1]
    bmi .Lstale_request
    beq 1f
    ldr pc,=0x0802306d              @ committed New; native still enforces capacity
1:  ldr pc,=0x0802323f              @ normal preview/selection applies stock SHIFT guard
.Lstale_request:
    b .Lbad_selected_file           @ previous FIL is still open at this point

    .thumb_func
selector_accepted_chord:
    push {r0-r3,ip,lr}
    bl selector_capture_new
    pop {r0-r3,ip,lr}
    str r3,[r2]                     @ native posts its confirmed LOAD event
    movs r3,#0
    ldr pc,=0x08025537

@ Retain the real native f_open BL (used to identify the new live FIL). An
@ explicitly new reel uses FA_CREATE_NEW in both banked and root-only mode.
@ For ordinary existing selections, bank 0 retains its native open flags.
    .thumb_func
selector_manual_open_mode:
    ldr r2,[sp,#88]                 @ bank_request_new/existing left 7 or 3
    cmp r2,#7
    beq 1f
    ldr r1,=0x2002a61f
    ldrb r1,[r1]
    cbnz r1,1f
    movs r2,#19
1:  add r1,sp,#132
    ldr pc,=0x08023099

@ At the native return from f_open the request mode is still in [sp,#88].
@ stock overwrites it here with 99 before parsing. A new file has no RIFF
@ chunks: running that parser with a writable handle can follow stale cue
@ length bytes from the prior reel and repeatedly seek/extend beyond EOF.
    .thumb_func
selector_prepare_manual:
    cmp r0,#0                        @ native bank-0 code can ignore an open error
    bne .Lfailed_manual_open
    add r0,sp,#844
    ldr r2,[sp,#88]
    str r3,[sp,#88]                 @ displaced instruction
    ldr r3,[r0,#12]                 @ FIL.fsize of this actual open
    cbnz r3,.Lnonempty
    cmp r2,#7
    bne .Lbad_selected_file          @ existing zero-byte file is not a charted blank
    movs r2,#0                      @ native initializes its header, bypass RIFF parser
    ldr pc,=0x080230df
.Lnonempty:
    cmp r2,#7
    beq .Lbad_selected_file          @ a genuinely new file must start empty
    ldr pc,=0x080230a7

.Lfailed_manual_open:
    movs r5,#0
    movs r6,#1
    ldr r2,=0x20028f80
    str r5,[r2]
    ldr r2,=0x20028ff0
    strh r5,[r2]
    ldr pc,=0x0802380f              @ stock unmount with no newly opened FIL

@ Preserve the stock knob-reset call at both successful stages of a manual
@ reel load. Those calls output no value. Keep the surrounding main frame.
    .thumb_func
selector_parsed:
    ldr r0,=0x080274c9
    blx r0
    movs r0,#0
    bl selector_finish_load
    cmp r0,#0
    bne .Lbad_selected_file
    ldr pc,=0x08023119

    .thumb_func
selector_transferred:
    ldr r0,=0x080274c9
    blx r0
    movs r0,#1
    bl selector_finish_load
    ldr pc,=0x0802388b

@ Normal selection of a just-created empty WAV uses the stock header writer.
@ During an existing-only bank confirmation the same branch means the
@ destination changed or a read failed. Do not initialize or truncate it.
    .thumb_func
selector_bad_format:
    ldr r0,=0x20028f80
    ldr r0,[r0]
    ldr r1,=0x31444c53
    cmp r0,r1
    beq .Lbad_selected_file
    movs r2,#0
    add r0,sp,#844
    ldr pc,=0x080230df

@ Revalidate what the native parser actually saw if the file was swapped
@ after confirmation. r4 is the data length; r3 is its file offset.
    .thumb_func
selector_valid_data:
    ldrd r4,r3,[sp,#96]
    ldr r0,=0x20028f80
    ldr r0,[r0]
    ldr r1,=0x31444c53
    cmp r0,r1
    bne .Lvalid
    ldr r0,=0x20028f80
    ldrh r0,[r0,#6]                 @ selected splice (zero = select/create blank)
    cbnz r0,.Laudio
    cmp r4,#0
    bne .Lbad_selected_file          @ blank candidate acquired PCM after confirmation
    b .Lvalid
.Laudio:
    cmp r4,#0
    beq .Lbad_selected_file
    tst r4,#7
    bne .Lbad_selected_file
    cmp r4,#0x4000000
    bhi .Lbad_selected_file
    ldr r0,[sp,#856]                @ native primary FIL.fsize
    subs r0,r0,r3
    blo .Lbad_selected_file
    cmp r4,r0
    bhi .Lbad_selected_file
.Lvalid:
    ldr pc,=0x08023b13

.Lbad_selected_file:
    movs r5,#0
    movs r6,#1
    ldr r0,=0x20028f80
    str r5,[r0]
    ldr r0,=0x20028ff0
    strh r5,[r0]                    @ no cached live bank/slot after failure
    ldr pc,=0x08023809              @ stock close the open FIL, unmount
    .ltorg
