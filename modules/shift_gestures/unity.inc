@ C helper calls preserve volatile CPU/FP registers, flags and alignment.
@ Fast paths avoid the C calls when both options/state are inactive.
.macro unity_save
    push {r0-r3,r12,lr}
    vpush {s0-s15}
    mrs r0, APSR
    vmrs r1, FPSCR
    push {r0,r1}
.endm
.macro unity_restore
    pop {r0,r1}
    msr APSR_nzcvq, r0
    vmsr FPSCR, r1
    vpop {s0-s15}
    pop {r0-r3,r12,lr}
.endm

.thumb_func
unity_button_hook:
    unity_save
    mov r0, r12
    mov r1, r2
    mov r2, r3
    bl unity_buttons
    unity_restore
    bx lr

.thumb_func
unity_map_hook:
    unity_save
    vmov r0, s18
    bl unity_map
    vmov s18, r0
    unity_restore
    bx lr
