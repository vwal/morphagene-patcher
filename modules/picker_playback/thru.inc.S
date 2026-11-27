@ Both full-Gene births and short/clocked EOSG events call D18 step_direction.
@ While the bank picker owns Organize, use its last accepted playback value.
@ All normal checks for recording, direction, stop and pending navigation
@ still run at the original sites. The caller already saved lr and put the
@ thru option in r4; it uses r0 for the eventual return value.
    .global picker_thru_mode
    .thumb_func
picker_thru_mode:
    ldr r1, =0x20021338
    ldr r1, [r1]
    cbz r1, 1f
    bl picker_active
    cbnz r0, 1f
    ldr pc, =0x08052d09             @ native inactive return
1:  ldr pc, =0x08052c8d             @ native recording and navigation guards
    .ltorg
