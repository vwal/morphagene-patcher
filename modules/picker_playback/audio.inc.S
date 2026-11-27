@ At 0x0802759e the stock audio block assigns lr the address of reel mode.
@ The same pointer gates clock edges, Organize, virtual splice 302, audition
@ control readings and finally the explicit +1x write at 0x08027968.
@ For a protected browse, route these audio-local reads to normal playback.
@ TIM2 and the SD dispatcher continue to see the real mode throughout.
    .global picker_audio_mode
    .thumb_func
picker_audio_mode:
    ldr     lr,=0x20021338
    ldr     r3,[lr]
    cbz     r3,.Lnormal_audio       @ ordinary playback: no helper call
    mov     r3,r0                   @ r3 is overwritten at 0x080275a4
    bl      picker_active           @ preserves r1-r12
    ldr     lr,=0x20021338
    cmp     r0,#0
    mov     r0,r3
    beq     .Lmode_selected         @ ordinary reel preview still sees stock mode
.Lnormal_audio:
    adr.w   lr,.Lplay_mode
.Lmode_selected:
    ldr     pc,=0x080275a3
    .balign 4
.Lplay_mode:
    .word   0
    .ltorg

@ TIM2 has already serviced the physical PLAY jack. Stock reel mode then
@ unconditionally overwrites the play gate and its debounce count with ON.
@ While browsing, retain the transport result just produced by pmod.
    .global picker_play_gate
    .thumb_func
picker_play_gate:
    cmp.w   r9,#1
    bne     .Ltested_gate_mode
    push    {r0,lr}                 @ lr holds the current sample counter
    bl      picker_active
    rsbs    r0,r0,#0                @ flags of CMP effective_mode,#1
    pop     {r0,lr}                 @ keep real mode in r9 for the UI
.Ltested_gate_mode:
    ldr     pc,=0x08024859          @ original BNE skips force-play
    .ltorg
