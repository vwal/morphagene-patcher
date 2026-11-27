@ Gesture and colour display adapted from Carlos de Paula (MIT), fork commit
@ 3305b8566641ed24bb176c98e243831bbf1e21f8. See LICENSES/Briskcat-MIT.txt.
    .syntax unified
    .cpu cortex-m4
    .thumb

    .equ SETTINGS,       0x2002A0F0
    .equ SETTINGS_MAGIC, 0x5354504f
    .equ BANK,           0x2002A61F     @ options.txt bank (options_keys), u8 1-8
    .equ RB,             0x20028F00     @ state block, see below
    .equ RB_MAGIC,       0x4b4e4142     @ "BANK"
    .equ PATH,           0x20028F10     @ 32-byte name buffer (RB + 16)
    @ RB: +0 magic, +4 stamp (the hold already used), +8 show-until time,
    @     +12 pending bank, +13 requested bank, +14 awaiting confirmation,
    @     +15 post-release color active (all initialized to zero)

    .equ HOLD_T0,        0x20001024
    .equ NOW,            0x20021c88
    .equ REEL_COLOR,     0x20001038

    .equ HOLD_TICKS,     288000         @ 3 s
    .equ STEP_TICKS,     96000          @ 1 s per further bank
    .equ SHOW_TICKS,     144000         @ bank shown 1.5 s after release

    .type BOOT_RETURN, %function
    .type HOLD_WAIT, %function
    .type HOLD_RELEASED, %function
    .type LED_RETURN, %function
    .type MAIN_ON, %function
    .type MAIN_OFF, %function
    .type MOUNT_DEFER, %function
    .type MOUNT_FAIL, %function
    .type CLOSE_AND_UNMOUNT, %function
    .type MAINT_STOCK, %function
    .type MAINT_RESUME, %function
    .type AFTER_STOCK, %function
    .type AFTER_RESUME, %function
    .type DELETE_STOCK, %function
    .type DELETE_CALL_RETURN, %function
    .text
    .global rb_defer, rb_boot, rb_hold, rb_led, rb_main
    .global rb_maintenance, rb_after_create, rb_delete_hook, rb_checked_delete

@ H1: TIM2 state 17, replacing "ldr r2,[sp,#4]; cmp r2,#0; bne.w done" at
@ 0x08025266. Live: r2 = REC, r3 = SPLICE, ip = SHIFT (non-zero = held),
@ lr = now, sb = &state, [sp, #4] = buttons down. Keeps everything but r2.
    .thumb_func
rb_hold:
    push    {r0, r1, r4, lr}
    ldr     r4, =RB
    ldr     r0, =BANK
    ldrb    r0, [r0]
    cmp     r0, #1
    blo     .Lcancel
    cmp     r0, #8
    bhi     .Lcancel
    ldr     r0, =0x20001290
    ldr     r0, [r0]
    cmp     r0, #1
    bne     .Lcancel
    ldr     r0, =SETTINGS
    ldr     r0, [r0]
    ldr     r1, =SETTINGS_MAGIC
    cmp     r0, r1
    bne     .Lcancel
    ldr     r0, [r4]
    ldr     r1, =RB_MAGIC
    cmp     r0, r1
    beq     1f
    str     r1, [r4]
    ldr     r0, =HOLD_T0
    ldr     r0, [r0]
    mvns    r0, r0                      @ allow a first hold timestamp of zero
    str     r0, [r4, #4]
    movs    r0, #0
    str     r0, [r4, #8]
    strh    r0, [r4, #12]
1:  ldr     r1, =HOLD_T0
    ldr     r1, [r1]
    cmp     ip, #0
    bne     .Lshift_cancel
    cmp     r2, #0
    beq     5f
    cmp     r3, #0
    beq     5f
    ldr     r0, [r4, #4]                @ this hold already switched
    cmp     r0, r1
    beq     9f
    subs    r0, lr, r1
    ldr     r1, =HOLD_TICKS
    subs    r0, r0, r1
    bmi     9f
    ldr     r1, =STEP_TICKS
    udiv    r0, r0, r1
    mov     r1, r0
    ldr     r0, =BANK
    ldrb    r0, [r0]
    add     r0, r0, r1                  @ bank + steps - 1 + 1, wrapped to 1-8
    and     r0, r0, #7
    adds    r0, r0, #1
    strb    r0, [r4, #12]
    b       9f
5:  ldrb    r0, [r4, #12]               @ a button released
    cbz     r0, 9f
    strb    r0, [r4, #13]
    movs    r0, #0
    strb    r0, [r4, #12]
    str     r1, [r4, #4]
    ldr     r0, =SHOW_TICKS
    add     r0, r0, lr
    str     r0, [r4, #8]
    movs    r0, #1
    strb    r0, [r4, #15]
    b       9f
.Lshift_cancel:
    str     r1, [r4, #4]                @ SHIFT cancels for the rest of this hold
.Lcancel:
    movs    r0, #0
    strh    r0, [r4, #12]
9:  pop     {r0, r1, r4, lr}
    ldr     r2, [sp, #4]
    cmp     r2, #0
    bne     8f
    b.w     HOLD_RELEASED
8:  b.w     HOLD_WAIT

@ L1: TIM2, replacing "ldr r2,=0x20001058; ldr r7,[r2]; cmp r7,#1" at
@ 0x080249c6, after the reel window colour is chosen. Keeps all but r2, r7.
    .thumb_func
rb_led:
    push    {r1, r3}
    ldr     r2, =RB
    ldr     r7, [r2]
    ldr     r3, =RB_MAGIC
    cmp     r7, r3
    bne     9f
    ldrb    r7, [r2, #12]               @ pending
    cbnz    r7, 5f
    ldrb    r7, [r2, #15]
    cbz     r7, 9f
    ldr     r1, =NOW
    ldr     r1, [r1]
    ldr     r3, [r2, #8]
    subs    r3, r3, r1                  @ show time left
    ble     8f
    ldr     r1, =SHOW_TICKS
    cmp     r3, r1
    bhi     8f
    ldr     r7, =BANK
    ldrb    r7, [r7]
5:  and     r7, r7, #7
    ldr     r2, =REEL_COLOR
    str     r7, [r2]
    b       9f
8:  movs    r7, #0
    strb    r7, [r2, #15]
9:  pop     {r1, r3}
    ldr     r2, =0x20001058
    ldr     r7, [r2]
    cmp     r7, #1
    b.w     LED_RETURN

@ M1: main loop, replacing "cmp r6,#1; ldr r5,[r7]; bne.w loop" at
@ 0x08022fbc. Live: r6 = card state (1 = mounted), r7 = &FLAGS.
    .thumb_func
rb_main:
    push    {r0-r4, ip, lr}
    sub     sp, sp, #4
    ldr     r0, =RB
    cmp     r6, #1
    beq     1f
    movs    r1, #0
    strh    r1, [r0, #12]
    b       8f
1:
    ldr     r1, [r0]
    ldr     r2, =RB_MAGIC
    cmp     r1, r2
    bne     8f
    ldrb    r1, [r0, #13]
    cbz     r1, 8f
    movs    r2, #0
    strb    r2, [r0, #13]
    mov     r0, r1
    bl      rb_apply
8:  add     sp, sp, #4
    pop     {r0-r4, ip, lr}
    ldr     r5, [r7]
    cmp     r6, #1
    bne     9f
    b.w     MAIN_ON
9:  b.w     MAIN_OFF

@ Before options are read, leave every directory untouched. The common EOF
@ hook handles normal cards, including a newly created/empty options.txt.
.thumb_func
rb_defer:
    ldr r0, =RB
    movs r1, #0
    str r1, [r0]
    str r1, [r0, #8]
    str r1, [r0, #12]
    b.w MOUNT_DEFER

.thumb_func
rb_boot:
    bl rb_boot_catalog
    cmp r0, #0
    bmi .Lmount_fail
    ldr r0, =PATH
    movs r1, #1
    bl rb_name
    ldr r2, [r7]
    orr r3, r2, #0x80
    ldr r0, =PATH
    b.w BOOT_RETURN

@ Stock's unmount/error exit takes (r5=0, r6=1).
.Lmount_fail:
    movs r5, #0
    movs r6, #1
    b.w MOUNT_FAIL
.Lclose_fail:
    movs r5, #0
    movs r6, #1
    b.w CLOSE_AND_UNMOUNT

@ Both stock inline compaction loops have multiple entry edges. These
@ intercept their common first iteration, retaining stock paths in bank 0.
.thumb_func
rb_maintenance:
    bl bank_get
    cbnz r0, 1f
    movs r6,#1
    mov r4,r6
    b.w MAINT_STOCK
1:  bl rb_recount
    cmp r0,#0
    bmi .Lclose_fail
    b.w MAINT_RESUME

.thumb_func
rb_after_create:
    bl bank_get
    cbnz r0, 1f
    movs r5,#1
    mov r4,r5
    b.w AFTER_STOCK
1:  bl rb_recount
    cmp r0,#0
    bmi .Lclose_fail
    mov r5,r0
    b.w AFTER_RESUME

@ Caller closed the live FIL. In enabled banks a WAV and its legacy
@ splice file are deleted together before numbering the remaining reels.
.thumb_func
rb_delete_hook:
    @ The native caller closed the primary FIL, including on failure.
    ldr r1,=0x20028ff0
    movs r2,#0
    strh r2,[r1]
    ldr r1,=RB
    strb r2,[r1,#14]
    push {r0,lr}
    bl bank_get
    cmp r0,#0
    pop {r0,lr}
    bne rb_delete
    push {r4,r5,r6,lr}
    sub sp,sp,#96
    b.w DELETE_STOCK

.thumb_func
rb_checked_delete:
    bl rb_delete_hook
    @ Stock's own delete has no defined result. Check only our path.
    ldr r1, =BANK
    ldrb r1, [r1]
    cbz r1, 1f
    cmp r0, #0
    bmi .Lmount_fail
1:  b.w DELETE_CALL_RETURN

@ The firmware stores 33 as the exclusive scan limit but uses it inclusively
@ when offering the "new reel" slot. Match the 32 real slots in bank mode.
.global rb_new_limit, rb_browse_limit, rb_first_free
.type NEW_RETURN, %function
.type BROWSE_RETURN, %function
.type FIRST_RETURN, %function
.thumb_func
rb_new_limit:
    ldr r6,[r8]
    push {r2}
    ldr r2,=BANK
    ldrb r2,[r2]
    cbz r2,1f
    movs r6,#32
1:  pop {r2}
    cmp r6,r0
    b.w NEW_RETURN

.thumb_func
rb_browse_limit:
    @ Clamp before comparing to the old cursor. A knob at its CW limit in a
    @ full bank otherwise requests reel 32 repeatedly (raw candidate = 33).
    push {r2}
    ldr r2, =BANK
    ldrb r2, [r2]
    cbz r2, 1f
    cmp r0,#32
    it hi
    movhi r0,#32
1:  pop {r2}
    cmp r7,r0
    beq.w PREVIEW_DONE
    b.w BROWSE_RETURN

.thumb_func
rb_first_free:
    ldr r5,[r8]
    ldr r1,=BANK
    ldrb r1,[r1]
    cbz r1,1f
    ldr r1,=0x200012a0
    ldr r1,[r1]
    cmp r1,#32
    bhs .Lmount_fail
1:  cmp r5,#1
    b.w FIRST_RETURN

@ Native Organize updates the cursor before requesting a preview load. After
@ a bank change skip only that load; preserve previews for stock reel mode.
.global rb_preview, rb_confirm
.type PREVIEW_QUEUE, %function
.type PREVIEW_DONE, %function
.type CONFIRM_RETURN, %function
.thumb_func
rb_preview:
    ldr r4,=RB
    ldrb r6,[r4,#14]
    cbnz r6,1f
    ldr r4,=0x20022074
    ldr r6,[r4]
    b.w PREVIEW_QUEUE
1:  b.w PREVIEW_DONE

.thumb_func
rb_confirm:
    @ r2 is live (&FLAGS), and r3 still holds the stock request mask.
    push {r0,r1}
    ldr r1,=RB
    movs r0,#0
    strb r0,[r1,#14]
    pop {r0,r1}
    orr.w r3,r3,#4096
    b.w CONFIRM_RETURN
.ltorg
