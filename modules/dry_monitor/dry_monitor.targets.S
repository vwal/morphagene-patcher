    .syntax unified
    .cpu cortex-m4
    .thumb
    .global MONITOR_A_RETURN
    .thumb_set MONITOR_A_RETURN, 0x08028ef8
    .global MONITOR_B_RETURN
    .thumb_set MONITOR_B_RETURN, 0x0802a1c6
