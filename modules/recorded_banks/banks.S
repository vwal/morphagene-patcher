@ Gesture and colour display adapted from Carlos de Paula (MIT), fork commit
@ 3305b8566641ed24bb176c98e243831bbf1e21f8. See LICENSES/Briskcat-MIT.txt.
    .syntax unified
    .cpu cortex-m4
    .thumb

    .equ BANK,           0x2002A61F     @ options.txt bank (options_keys), u8 1-8
    .equ RB,             0x20028F00     @ state block, see below
    .equ RB_MAGIC,       0x4b4e4142     @ "BANK"
    @ RB: +0 magic, +4 stamp (the hold already used), +8 show-until time,
    @     +12 pending bank, +13 requested bank, +14 awaiting confirmation,
    @     +15 post-release color active, +48 inventory state, +49 bank mask,
    @     +50 mount generation, +52 first color time, +56 observed chord start,
    @     +60 chord still down (kept across ordinary and protected remounts)

    .equ HOLD_T0,        0x20001024
    .equ FS_GENERATION,  0x20024278     @ native FatFs increments on each successful mount

    .equ STEP_TICKS,     96000          @ 1 s per further bank
    .equ SHOW_TICKS,     144000         @ bank shown 1.5 s after release

.type HOLD_WAIT, %function
.type HOLD_RELEASED, %function
.type D15_MAIN_DONE, %function
.type D15_LED_SHOW, %function
.type D15_LED_COOLDOWN, %function
.type D15_LED_DONE, %function
.text
.global rb_hold_active, rb_pending, rb_led_pending

@ D15 has already confirmed a mounted card, enabled bank and initialized
@ settings. Its state-17 entry saved r0,r1,r4,lr and points r4 at RB.
.thumb_func
rb_hold_active:
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
    strh    r0, [r4, #48]
1:  ldr     r0, =FS_GENERATION
    ldrh    r0, [r0]
    ldrh    r1, [r4, #50]
    cmp     r0, r1
    beq     7f
    strh    r0, [r4, #50]
    ldrb    r0, [r4, #60]
    cbz     r0, .Lnew_mount
    ldr     r1, =HOLD_T0
    ldr     r1, [r1]
    ldr     r0, [r4, #56]
    cmp     r0, r1
    it      eq
    streq   r1, [r4, #4]                @ do not restart a chord held across the mount
.Lnew_mount:
    movs    r0, #0
    strh    r0, [r4, #48]               @ discard any mask from a previous mount
    strh    r0, [r4, #12]
    strb    r0, [r4, #15]
7:  ldr     r1, =HOLD_T0
    ldr     r1, [r1]
    cmp     ip, #0
    bne     .Lshift_cancel
    cmp     r2, #0
    beq     5f
    cmp     r3, #0
    beq     5f
    str     r1, [r4, #56]
    movs    r0, #1
    strb    r0, [r4, #60]
    ldr     r0, [r4, #4]                @ this hold completed or crossed a mount
    cmp     r0, r1
    beq     9f
    subs    r0, lr, r1
    ldr     r1, =STEP_TICKS              @ short reel-mode entries never request a scan
    cmp     r0, r1
    blo     9f
    ldrb    r0, [r4, #48]
    cbnz    r0, 2f
    movs    r0, #1                      @ one foreground inventory per deliberate hold
    strb    r0, [r4, #48]
    movs    r0, #9                      @ inventory via the existing pending-work byte
    strb    r0, [r4, #13]
    movs    r0, #0
    strb    r0, [r4, #15]
    b       9f
2:  cmp     r0, #2                      @ wait for a complete inventory
    bne     9f
    ldr     r0, [r4, #52]
    subs    r0, lr, r0
    bmi     9f
    push    {r2,r3,ip,lr}
    udiv    r2, r0, r1
    ldrb    r1, [r4, #49]
    ldr     r0, =BANK
    ldrb    r0, [r0]
    bl      rb_step
    pop     {r2,r3,ip,lr}
    strb    r0, [r4, #12]
    b       9f
5:  str     r1, [r4, #4]                @ a release ends this chord, even without a choice
    movs    r0, #0
    strb    r0, [r4, #48]
    strb    r0, [r4, #60]
    ldrb    r0, [r4, #13]
    cmp     r0, #9
    bne     6f
    movs    r0, #0
    strb    r0, [r4, #13]               @ released before foreground completed
6:
    ldrb    r0, [r4, #12]               @ a button released
    cbz     r0, 9f
    strb    r0, [r4, #13]
    movs    r0, #0
    strb    r0, [r4, #12]
    ldr     r0, =SHOW_TICKS
    add     r0, r0, lr
    str     r0, [r4, #8]
    b       9f
.Lshift_cancel:
    str     r1, [r4, #4]                @ SHIFT cancels for the rest of this hold
    movs    r0, #0
    strb    r0, [r4, #48]
    strb    r0, [r4, #60]
    strh    r0, [r4, #12]
9:  pop     {r0, r1, r4, lr}
    ldr     r2, [sp, #4]
    cmp     r2, #0
    bne     8f
    b.w     HOLD_RELEASED
8:  b.w     HOLD_WAIT

@ D15 rb_main has already checked card state, bank magic and a nonzero
@ request in r1. Stock main and the ordinary mounted idle path bypass this.
.thumb_func
rb_pending:
    mov     r4, r0                      @ D15 saved the live r4 on entry
    ldr     r0, =FS_GENERATION
    ldrh    r0, [r0]
    ldrh    r2, [r4, #50]
    cmp     r0, r2
    beq     2f
    movs    r0, #0                      @ a new mount cannot inherit the old request
    strh    r0, [r4, #12]
    strh    r0, [r4, #48]
    strb    r0, [r4, #15]
    b.w     D15_MAIN_DONE
2:  cmp     r1, #9
    bne     1f
    bl      rb_inventory
    b.w     D15_MAIN_DONE
1:  mov     r0, r1
    bl      rb_apply
    cmp     r0, #0                      @ stock I/O takes priority
    beq.w   D15_MAIN_DONE
    movs    r0, #0
    strb    r0, [r4, #13]
    b.w     D15_MAIN_DONE

@ D15 already checked bank magic. The scan sentinel
@ is never a displayed bank. A released choice stays visible until main runs.
.thumb_func
rb_led_pending:
    ldr     r7, =FS_GENERATION
    ldrh    r7, [r7]
    ldrh    r1, [r2, #50]
    cmp     r7, r1
    bne.w   D15_LED_DONE
    ldrb    r7, [r2, #12]
    cmp     r7, #0
    bne.w   D15_LED_SHOW
    ldrb    r7, [r2, #13]
    subs    r7, #1
    cmp     r7, #7
    bhi     1f
    adds    r7, #1
    b.w     D15_LED_SHOW
1:  ldrb    r7, [r2, #15]
    cmp     r7, #0
    beq.w   D15_LED_DONE
    b.w     D15_LED_COOLDOWN

@ While the initiating SPLICE+REC chord is still down it can become a long
@ hold. Leave Organize's accepted ADC value alone until release. A short
@ entry then previews normally, and a long entry never previews the old bank.
.global rb_organize
.type ORGANIZE_READ, %function
.type ORGANIZE_UNMOVED, %function
.thumb_func
rb_organize:
    cmp r6,#8                         @ native Organize hysteresis
    ble.w ORGANIZE_UNMOVED
    cmp r3,#1                         @ active reel mode only
    bne.w ORGANIZE_READ
    push {r1}
    ldr r1,=BANK
    ldrb r1,[r1]
    cbz r1,1f
    ldr r1,=RB
    ldrb r1,[r1,#13]
    cbnz r1,2f                        @ request waits for foreground
    ldr r1,=0x20001020                @ native button state
    ldr r1,[r1]
    subs r1,#16                       @ 16 entering, 17 waiting for release
    cmp r1,#1
    bls 2f
1:  pop {r1}
    b.w ORGANIZE_READ
2:  pop {r1}
    b.w ORGANIZE_UNMOVED

.global rb_confirm
.type CONFIRM_RETURN, %function
.thumb_func
rb_confirm:
    @ r2 is live (&FLAGS), and r3 still holds the stock request mask.
    push {r0,r1}
    ldr r1,=RB
    ldrb r0,[r1,#13]
    cbnz r0,1f                        @ still browsing the old directory
    ldrb r0,[r1,#14]
    cbz r0,2f
    ldr r0,=0x200220ac                @ bank committed: wait for first Organize reading
    ldr r0,[r0]
    cmp r0,#0                         @ rb_apply uses -100000, ADC is nonnegative
    bmi 1f
    movs r0,#0
    strb r0,[r1,#14]
2:  pop {r0,r1}
    orr.w r3,r3,#4096
    b.w CONFIRM_RETURN
1:  pop {r0,r1}
    b.w HOLD_WAIT                     @ held confirm is retried next TIM2 tick
.ltorg
