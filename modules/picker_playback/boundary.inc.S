@ The native scheduler has accepted a Gene and is taking the requested
@ splice for this voice. Both render paths call D18's whole_birth here,
@ including short, overlapping, externally clocked and reversed Genes.
@ Mode 0 permits older voices to overlap the newly selected voice.
    .fpu fpv4-sp-d16
    .global picker_gene_birth, picker_idle_resolver, picker_has_gene_to_wait_for
    .thumb_func
picker_gene_birth:
    push    {r4-r6,lr}              @ D18 displaced prologue
    mov     r4,r0
    mov     r5,r1
    bl      .Lpublish_boundary
    mov     r0,r4                  @ original requested splice and prior voice
    mov     r1,r5
    ldr     pc,=0x08052d4d         @ D18 saves previous voice (r1), unchanged

@ The stock resolver uses the request directly when the envelopes are all
@ silent. Catch this block even if the foreground misses the silent gap.
    .thumb_func
picker_idle_resolver:
    vmrs    APSR_nzcv,fpscr         @ original VCMP s16,#0: s16 is the sum
    bgt     .Lresolved
    push    {r0-r3,ip,lr}
    bl      .Lpublish_boundary
    pop     {r0-r3,ip,lr}
    vmrs    APSR_nzcv,fpscr
.Lresolved:
    ldr     pc,=0x08027833

    .thumb_func
.Lpublish_boundary:
    ldr     r0,=0x20028fa0          @ 0 idle, 1 waiting, 2 ready for foreground
    ldr     r1,[r0]
    cmp     r1,#1
    bne     .Lpublished
    @ Retest while interrupts are masked so a TIM2 cancellation cannot
    @ resurrect the old request. Foreground cannot preempt this DMA handler.
    mrs     r2,primask
    cpsid   i
    ldr     r1,[r0]
    cmp     r1,#1
    itt     eq
    moveq   r1,#2
    streq   r1,[r0]
    msr     primask,r2
.Lpublished:
    bx      lr

@ Called in the foreground while WAIT is armed. No currently sounding Gene
@ means native Organize can apply immediately. A stopped tape head has no
@ playback boundary to await. Keep waiting through any nonzero speed slew.
    .thumb_func
picker_has_gene_to_wait_for:
    ldr     r0,=0x2002208c          @ splice count
    ldr     r0,[r0]
    cbz     r0,.Lboundary_idle
    @ PLAY low can finish a classic Gene, fade a momentary Gene, or keep
    @ trigger-loop running. Let native envelopes and births distinguish these.
    ldr     r1,=0x200220e0          @ effective rate; target at +8
    ldr     r0,[r1]
    lsls    r0,r0,#1               @ ignore the sign of IEEE zero
    bne     .Lboundary_voices
    ldr     r0,[r1,#8]
    lsls    r0,r0,#1
    beq     .Lboundary_idle
.Lboundary_voices:
    ldr     r1,=0x20021e64          @ idle voices may hold the native -1e-8
    movs    r2,#4                  @ stereo channels share these envelopes
.Lnext_envelope:
    ldr     r0,[r1],#4
    cmp     r0,#0                  @ positive float bits are signed-positive
    bgt     .Lboundary_busy
    subs    r2,#1
    bne     .Lnext_envelope
.Lboundary_idle:
    movs    r0,#0
    bx      lr
.Lboundary_busy:
    movs    r0,#1
    bx      lr
    .ltorg
