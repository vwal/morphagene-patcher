@ Post-process an existing primary-control hold. Argument/result offsets name
@ the saved r0-r3 slots (0,4,8,12). Stock code resets flags after these sites.
@ Fast path avoids C/FP saves entirely when no preset has ever been recalled.
.macro preset_post function, source=0, result=0
    push {r1,r2}
    ldr r1, =0x2002a660
    ldr r1, [r1]
    ldr r2, =0x54535250
    cmp r1, r2
    pop {r1,r2}
    bne 99f
    push {r0-r3,r12,lr}
    vpush {s0-s15}
    mrs r0, APSR
    vmrs r1, FPSCR
    push {r0,r1}
    mov r2, sp
    bic r3, r2, #7
    sub r3, r3, #8
    mov sp, r3                         @ C ABI alignment, even inside stock hooks
    str r2, [sp]
    ldr r0, [r2, #(72+\source)]
    bl \function
    ldr r2, [sp]
    mov sp, r2
    str r0, [sp, #(72+\result)]
    pop {r0,r1}
    msr APSR_nzcvq, r0
    vmsr FPSCR, r1
    vpop {s0-s15}
    pop {r0-r3,r12,lr}
99:
.endm
