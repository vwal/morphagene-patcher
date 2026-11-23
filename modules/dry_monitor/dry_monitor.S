@ Select the monitor pair after stock S.O.S./inop and splice filtering have
@ finished selecting the record pair. Both stock and tape paths rejoin here.
@ The Gene samples include SRR. Keeping the record registers intact lets the
@ remainder of the stock engine handle new takes, overdubs and output limiting.
    .syntax unified
    .cpu cortex-m4
    .fpu fpv4-sp-d16
    .thumb
    .text
    .equ BLOCK_DRYK, 0x2002a0ea       @ MOD+234, validated by tape_sos at P7
    .type MONITOR_A_RETURN, %function
    .type MONITOR_B_RETURN, %function
    .global monitor_a, monitor_b

    .macro MONITOR name, left, right, gene_left, gene_right, pointer, resume
    .thumb_func
\name:
    ldr     r1, =BLOCK_DRYK
    ldrb    r1, [r1]
    cbz     r1, 1f
    vmov.f32 \left, \gene_left
    vmov.f32 \right, \gene_right
1:  ldr     \pointer, [sp, #172]      @ replay both displaced stock loads
    ldr     r1, [\pointer]
    b.w     \resume
    .endm

    MONITOR monitor_a, s13, s30, s16, s19, r7, MONITOR_A_RETURN
    MONITOR monitor_b, s30, s22, s27, s24, r0, MONITOR_B_RETURN
    .ltorg
