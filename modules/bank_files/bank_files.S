@ mg204 main-loop banked WAV opens. Preserve the three native BL f_open
@ instructions so settings_reload can identify the main FIL by its caller.
.syntax unified
.cpu cortex-m4
.thumb
.text
.equ BANK,  0x2002a61f
.equ COUNT, 0x200012a0
.equ OPEN_EXISTING, 3             @ FA_READ | FA_WRITE
.equ CREATE_NEW,    7             @ FA_READ | FA_WRITE | FA_CREATE_NEW
.equ OPEN_ALWAYS,   19            @ original stock mode
.global bank_request_new, bank_request_existing, bank_free_result
.global bank_create_mode, bank_boot_mode, bank_select_mode
.global bank_create_result, bank_boot_result, bank_select_result, bank_header
.type SELECT,%function
.type NO_SELECTION,%function
.type SELECT_OPEN,%function
.type SELECT_READY,%function
.type TRY_NEXT,%function
.type FREE_SLOT,%function
.type NEW_OPEN,%function
.type NEW_READY,%function
.type BOOT_OPEN,%function
.type BOOT_READY,%function
.type HEADER,%function
.type HEADER_BODY,%function
.type CLOSE_UNMOUNT,%function
.type UNMOUNT,%function

@ The native manual select and new-reel branches join at SELECT, where the
@ old FIL is closed. [sp,#88] is otherwise unused until *after* this open,
@ when stock overwrites it with 99 before parsing the replacement WAV.
.thumb_func
bank_request_new:
    str r0,[r5]
    str r0,[r1]
    movs r2,#CREATE_NEW
    str r2,[sp,#88]
    b.w SELECT

.thumb_func
bank_request_existing:
    cmp r0,r1
    blt.w NO_SELECTION
    movs r2,#OPEN_EXISTING
    str r2,[sp,#88]
    b.w SELECT

.thumb_func
bank_select_mode:
    ldr r2,=BANK
    ldrb r2,[r2]
    cbz r2,1f
    ldr r2,[sp,#88]
    b 2f
1:  movs r2,#OPEN_ALWAYS
2:  add r1,sp,#132
    b.w SELECT_OPEN

@ A transient read error is not a vacant slot. Even if the directory entry
@ changes after the scan, CREATE_NEW cannot open an already occupied slot.
.thumb_func
bank_free_result:
    ldr r1,=BANK
    ldrb r1,[r1]
    cbz r0,2f
    cbz r1,1f
    cmp r0,#4                       @ FR_NO_FILE is the only free result
    bne .Lfailed_open
1:  b.w FREE_SLOT
2:  cbz r1,3f
    ldr r1,[r8]                     @ stock exclusive limit
    subs r1,#1
    cmp r4,r1
    bhs .Lfailed_open               @ exhausted a catalog that changed since counting
3:  b.w TRY_NEXT

.thumb_func
bank_create_mode:
    ldr r2,=BANK
    ldrb r2,[r2]
    cmp r2,#0
    ite eq
    moveq r2,#OPEN_ALWAYS
    movne r2,#CREATE_NEW
    add r0,sp,#844
    b.w NEW_OPEN

.thumb_func
bank_boot_mode:
    ldr r2,=BANK
    ldrb r2,[r2]
    cbz r2,1f
    ldr r2,=COUNT
    ldr r2,[r2]
    cmp r2,#0
    ite eq
    moveq r2,#CREATE_NEW
    movne r2,#OPEN_EXISTING
    b 2f
1:  movs r2,#OPEN_ALWAYS
2:  add r1,sp,#132
    b.w BOOT_OPEN

.macro check_open
    cbz r0,1f
    ldr r2,=BANK
    ldrb r2,[r2]
    cmp r2,#0
    bne .Lfailed_open
1:
.endm

.thumb_func
bank_select_result:
    check_open
    movs r3,#99
    movs r1,#0
    b.w SELECT_READY
.thumb_func
bank_boot_result:
    check_open
    movs r6,#99
    mov r1,r4
    b.w BOOT_READY
.thumb_func
bank_create_result:
    check_open
    add r0,sp,#844
    bl HEADER
    b.w NEW_READY

@ Three direct calls, all from the main frame before any WAV header is
@ written. Reject damaged/nonempty audio on a parse/read error. A fresh
@ empty file still receives the stock header at the usual time.
.thumb_func
bank_header:
    ldr r1,=BANK
    ldrb r1,[r1]
    cbz r1,1f
    ldr r1,[r0,#12]                @ FatFs fsize
    ldrb r2,[r0,#7]                @ sticky FatFs I/O error
    orrs r1,r2
    bne .Lfailed_header
1:  push {r4,r5,lr}
    sub sp,sp,#52
    b.w HEADER_BODY

.Lfailed_header:
    ldr r2,=0x20028ff0
    movs r5,#0
    movs r6,#1
    strh r5,[r2]
    b.w CLOSE_UNMOUNT               @ valid primary FIL was opened read/write
.Lfailed_open:
    ldr r2,=0x20028ff0
    movs r5,#0
    movs r6,#1
    strh r5,[r2]
    b.w UNMOUNT
.ltorg
