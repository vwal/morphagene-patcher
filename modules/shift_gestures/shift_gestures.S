@ Module shift_gestures: SHIFT knob gestures + Varispeed scale lock (mg204).
@ Linked after the previous module's code (mgmod/module.py).
@ Design: README.md beside this file.
@
@ State block MOD (SRAM, inside the heap/stack gap; cleared at reset):
@   +0  magic "SHFT"
@   +4  active   u8  SHIFT session in progress (state 14, or state 4 latch armed)
@   +5  consumed u8  a knob moved more than T during this session
@   +6  owner    u8  1 = S.O.S., 2 = Varispeed, 3 = Morph (SRR), 4 = Gene Size, 5 = Slide,
@                    6 = Organize (Turing evolution, sldm 1)
@   +7  lock     u8  scale lock engaged
@   +8  ref_sos  u16 / +10 ref_vs u16   snapshots at session start
@   +12 lock_m   u16 locked lookup index m (4..392, a multiple of 2)
@   +14 release_vs u16 Varispeed reading at SHIFT release (0xffff while held)
@   +16..+127 reserved for sos_feedback.S and tape_sos.S (zeroed here)
@   +208 ref_gs u16 / +210 ref_slide u16  snapshots for gene_shape.S (owners 4, 5)
@   +128..+231 zeroed here too; P7/P10 own +232..+239 on every audio block
@   +128 ref_org u16 (Organize at session start), +130 Organize held u8

    .syntax unified
    .cpu cortex-m4
    .fpu fpv4-sp-d16
    .thumb

    .equ MOD,          0x2002A000
    .equ MAGIC,        0x53484654
    .equ STATE,        0x20001020
    .equ SHIFT_LATCH,  0x2002139c
    .equ NAVIGATION,   0x200012e0
    .equ RELEASE_TIME, 0x20001024
    .equ SOS_ADC,      0x20021c68
    .equ ORG_ADC,      0x20021c70  @ Organize (64-sample average)
    .equ VS_ADC,       0x20021c74
    .equ MORPH_ADC,    0x20021c6c
    .equ VSOP,         0x200012a8
    .equ SLIDE_PTR,    0x20022154
    .equ SLIDE_ADC,    0x20021c78
    .equ GS_ADC,       0x20021c7c
    .equ T_SLIDE,      96          @ Slide is a 4-sample average: wider claim threshold
    .equ T_KNOB,       48          @ counts of movement that claim a SHIFT gesture
    .equ T_PICKUP,     231         @ counts (about half an octave) that release a lock
    .equ SETTINGS,     0x2002A0F0  @ options.txt settings (options_keys / sd_updater)
    .equ SETTINGS_MAGIC, 0x5354504f
    .equ RANGE,        0x2002A606
    .equ VQNT,         0x2002A610  @ 1: quantized normally, SHIFT+Varispeed is free
    .equ SCALE,        0x2002A604  @ options.txt scal mask (options_keys)
    .equ M_WIDE,       128         @ hysteresis in 1/16 lookup units: 2 semitones (octl 1-2)
    .equ M_NARROW,     48          @ 3/4 semitone (octl 3-4, steps down to a semitone)

    @ Return addresses in the stock image.
    .type P1_RETURN, %function  @ 0x0802486e; defined in shift_gestures.targets.S
    .type TIM2_DONE, %function  @ 0x080248fc; defined in shift_gestures.targets.S
    .type NAV_STORE, %function  @ 0x080251e0; defined in shift_gestures.targets.S
    .type NAV_SKIP, %function  @ 0x080251e6; defined in shift_gestures.targets.S
    .type RATE_NEXT, %function  @ 0x08027882; defined in shift_gestures.targets.S
    .type RATE_FULL, %function  @ 0x08028824; defined in shift_gestures.targets.S
    .type GLIDE_NEXT, %function  @ 0x08027be4; defined in shift_gestures.targets.S
    .type PRESET_VS_INPUT_NEXT, %function
    .include "../preset_recall/preset_asm.inc"
    .include "../preset_recall/varispeed_asm.inc"

    .text
    .global p1_session, p3_state14, p4_record_tap, p5_octave, p6_glide

@ Stock's Varispeed motion detector runs before its pitch lookup. The preset
@ must supply the same virtual input to both, without touching physical ADC.
    .global preset_vs_input
    .thumb_func
preset_vs_input:
    ldr r1, [r0, #12]
    preset_post preset_varispeed_prepare, 4, 4
    ldr r0, =0x200220a4
    b.w PRESET_VS_INPUT_NEXT
    .ltorg

@ Stock initializes accepted-control caches after Organize changes, and later
@ consults raw Varispeed for playhead adjustment direction. Both must agree
@ with the virtual input used by the pitch lookup and movement history.
    .type PRESET_VS_CACHE_NEXT, %function
    .type PRESET_VS_DIRECTION_NEXT, %function
    .global preset_vs_cache, preset_vs_direction
    .thumb_func
preset_vs_cache:
    preset_vs_cached r6
    adds r6, #100
    adds r4, #100
    b.w PRESET_VS_CACHE_NEXT
    .thumb_func
preset_vs_direction:
    ldr r4, [r7, #12]
    preset_vs_cached r4
    ldr r0, =0x20021de4
    b.w PRESET_VS_DIRECTION_NEXT
    .ltorg

@ P1 (hook at 0x0802486a, TIM2 control ISR, after debounce, before dispatch).
@ Live: ip = SHIFT integrator, r2 = REC, r3 = SPLICE, lr = now.
    .thumb_func
p1_session:
    push    {r0-r2,lr}                  @ LR is the live stock sample timestamp
    ldr     r0, =0x2002A618
    ldrb    r1, [r0]
    cmp     r1, #1
    bne     unity_buttons_off
    cmp     ip, #0
    bne     unity_buttons_call
    ldr     r0, =0x2002A620
    ldr     r0, [r0]
    cbz     r0, unity_buttons_done
unity_buttons_call:
    bl      unity_button_hook
    b       unity_buttons_done
unity_buttons_off:
    ldr     r0, =0x2002A620
    movs    r1, #0
    str     r1, [r0]
unity_buttons_done:
    pop     {r0-r2,lr}
    push    {r0-r4}
    ldr     r4, =MOD
    ldr     r1, [r4]
    ldr     r0, =MAGIC
    cmp     r1, r0
    beq     1f
    str     r0, [r4]
    movs    r0, #0                      @ reset gesture, tape and Gene state
    movs    r1, #4
0:  cmp     r1, #132                    @ preserve the current audio block's input gain
    it      ne
    strne   r0, [r4, r1]
    adds    r1, r1, #4
    cmp     r1, #232                    @ leave the current audio block's routing/gain intact
    blt     0b
1:  ldr     r1, =STATE
    ldr     r1, [r1]
    cmp     r1, #14
    beq     2f
    cmp     r1, #4
    bne     9f
    ldr     r0, =SHIFT_LATCH
    ldr     r0, [r0]
    cmp     r0, #1
    bne     9f
2:  ldrb    r0, [r4, #4]                @ session: snapshot once
    cbnz    r0, 3f
    ldr     r0, =SOS_ADC
    ldr     r0, [r0]
    strh    r0, [r4, #8]
    ldr     r0, =VS_ADC
    ldr     r0, [r0]
    strh    r0, [r4, #10]
    ldr     r0, =MORPH_ADC
    ldr     r0, [r0]
    strh    r0, [r4, #92]               @ ref_morph (used by the SRR gesture)
    ldr     r0, =GS_ADC
    ldr     r0, [r0]
    strh    r0, [r4, #208]              @ ref_gs (window gesture)
    ldr     r0, =SLIDE_ADC
    ldr     r0, [r0]
    strh    r0, [r4, #210]              @ ref_slide (jitter gesture)
    ldr     r0, =ORG_ADC
    ldr     r0, [r0]
    strh    r0, [r4, #128]              @ ref_org (Turing evolution gesture)
    movs    r0, #0
    strb    r0, [r4, #5]
    strb    r0, [r4, #6]
    movs    r0, #1
    strb    r0, [r4, #4]
3:  cmp     ip, #0                      @ detect only with SHIFT alone
    beq     8f
    cmp     r2, #0
    bne     8f
    cmp     r3, #0
    bne     8f
    ldrb    r0, [r4, #5]
    cmp     r0, #0
    bne     8f
    ldr     r0, =SOS_ADC
    ldr     r0, [r0]
    ldrh    r1, [r4, #8]
    subs    r0, r0, r1
    it      mi
    rsbmi   r0, r0, #0
    cmp     r0, #T_KNOB
    ble     4f
    movs    r0, #1
    strb    r0, [r4, #5]
    strb    r0, [r4, #6]
    b       8f
4:  ldr     r0, =SETTINGS           @ options.txt "octl 0": no Varispeed claim
    ldr     r1, [r0]
    ldr     r0, =SETTINGS_MAGIC
    cmp     r1, r0
    bne     5f
    ldr     r0, =SETTINGS
    ldrb    r0, [r0, #5]
    cmp     r0, #0
    beq     6f
5:  ldr     r0, =VS_ADC
    ldr     r0, [r0]
    ldrh    r1, [r4, #10]
    subs    r0, r0, r1
    it      mi
    rsbmi   r0, r0, #0
    ldr     r1, =VQNT
    ldrb    r1, [r1]
    cmp     r1, #1
    ite     eq
    moveq   r1, #8                     @ responsive free-pitch gesture in vqnt mode
    movne   r1, #T_KNOB
    cmp     r0, r1
    ble     6f
    movs    r0, #1
    strb    r0, [r4, #5]
    movs    r0, #2
    strb    r0, [r4, #6]
    b       8f
6:  ldr     r0, =SETTINGS           @ options.txt "fxsl 0": no Morph claim
    ldr     r1, [r0]
    ldr     r0, =SETTINGS_MAGIC
    cmp     r1, r0
    bne     12f
    ldr     r0, =SETTINGS
    ldrb    r0, [r0, #6]
    cmp     r0, #0
    beq     7f
12: ldr     r0, =MORPH_ADC              @ SHIFT + Morph: SRR amount (owner 3)
    ldr     r0, [r0]
    ldrh    r1, [r4, #92]
    subs    r0, r0, r1
    it      mi
    rsbmi   r0, r0, #0
    cmp     r0, #T_KNOB
    ble     7f
    movs    r0, #1
    strb    r0, [r4, #5]
    movs    r0, #3
    strb    r0, [r4, #6]
    b       8f
7:  ldr     r0, =SETTINGS               @ SHIFT + Gene Size (owner 4): the Turing
    ldr     r1, [r0]                    @ pattern rate, only with options.txt "sldm 1"
    ldr     r0, =SETTINGS_MAGIC
    cmp     r1, r0
    bne     11f
    ldr     r0, =0x2002A607
    ldrb    r0, [r0]
    cmp     r0, #1
    beq     14f
    ldr     r0, =SETTINGS
    ldrb    r0, [r0, #10]
    cmp     r0, #1
    bne     11f
14:
    ldr     r0, =GS_ADC
    ldr     r0, [r0]
    ldrh    r1, [r4, #208]
    subs    r0, r0, r1
    it      mi
    rsbmi   r0, r0, #0
    cmp     r0, #T_KNOB
    ble     11f
    movs    r0, #1
    strb    r0, [r4, #5]
    movs    r0, #4
    strb    r0, [r4, #6]
    b       8f
11: ldr     r0, =SLIDE_ADC              @ SHIFT + Slide: jitter / spread (owner 5)
    ldr     r0, [r0]
    ldrh    r1, [r4, #210]
    subs    r0, r0, r1
    it      mi
    rsbmi   r0, r0, #0
    cmp     r0, #T_SLIDE
    ble     13f
    movs    r0, #1
    strb    r0, [r4, #5]
    movs    r0, #5
    strb    r0, [r4, #6]
    b       8f
13: ldr     r0, =SETTINGS               @ SHIFT + Organize: Turing evolution
    ldr     r1, [r0]                    @ (owner 6), only with options.txt "sldm 1"
    ldr     r0, =SETTINGS_MAGIC
    cmp     r1, r0
    bne     8f
    ldr     r0, =SETTINGS
    ldrb    r0, [r0, #10]
    cmp     r0, #1
    bne     8f
    ldr     r0, =ORG_ADC
    ldr     r0, [r0]
    ldrh    r1, [r4, #128]
    subs    r0, r0, r1
    it      mi
    rsbmi   r0, r0, #0
    cmp     r0, #T_KNOB
    ble     8f
    movs    r0, #1
    strb    r0, [r4, #5]
    strb    r0, [r4, #130]              @ hold Organize (no splice change)
    movs    r0, #6
    strb    r0, [r4, #6]
8:  ldr     r1, =STATE                  @ consumed in state 14: hide REC/SPLICE
    ldr     r1, [r1]                    @ from the combo checks (no deletes)
    cmp     r1, #14
    bne     10f
    ldrb    r0, [r4, #4]
    cbz     r0, 10f
    ldrb    r0, [r4, #5]
    cbz     r0, 10f
    movs    r0, #0
    str     r0, [sp, #8]                @ saved r2
    str     r0, [sp, #12]               @ saved r3
    b       10f
9:  movs    r0, #0                      @ not a session: keep consumed/owner
    strb    r0, [r4, #4]
10: pop     {r0-r4}
    ldr     r9, =STATE                  @ replaced instruction
    b.w     P1_RETURN

@ P3 (hook at 0x080251dc, state 14 navigation block; also the gate-edge path).
@ Skip the navigation write only on a real release (ip == 0) of a consumed session.
    .thumb_func
p3_state14:
    cmp     ip, #0
    bne     1f
    ldr     r0, =MOD
    ldrb    r1, [r0, #4]
    cbz     r1, 1f
    ldrb    r1, [r0, #5]
    cbz     r1, 1f
    ldr     r1, =NAVIGATION
    ldr     r3, =SHIFT_LATCH
    ldr     r2, =RELEASE_TIME
    movs    r0, #1
    b.w     NAV_SKIP
1:  ldr     r1, =NAVIGATION             @ replaced instructions
    ldr     r3, =SHIFT_LATCH
    b.w     NAV_STORE

@ P4 (hook at 0x080255da, state 4 SHIFT release while recording).
    .thumb_func
p4_record_tap:
    cmp     r2, #1
    bne.w   TIM2_DONE
    ldr     r3, =NAVIGATION
    str     ip, [r0]                    @ latch = 0
    ldr     r2, =MOD
    ldrb    r2, [r2, #4]
    cbz     r2, 1f
    ldr     r2, =MOD
    ldrb    r2, [r2, #5]
    cbz     r2, 1f
    movs    r2, #1                      @ consumed: no navigation
    b.w     TIM2_DONE
1:  movs    r2, #1
    str     r2, [r3]
    b.w     TIM2_DONE

@ P5 (hook at 0x0802787c, audio block, s18 = calibrated Varispeed x in 0..1).
@ While a SHIFT+Varispeed edit is held, snap x to the nearest rate of the
@ octl scale with hysteresis; after release keep it until the reading moves
@ T_PICKUP counts. vqnt 1 instead quantizes normally and bypasses during a
@ Varispeed gesture; forward.inc handles both forward ranges in that mode.
@
@ Grid g = m/2 (2..196). Standard range permits even g only: four table
@ indices per semitone. Extended range squares the magnitude and permits
@ every g: two indices per semitone. In extended mode, forward pitch is
@ g-172 semitones, reverse pitch is 26-g; standard divides these by two.
@ g=100 is stop; g=98 and 99 are redundant zero positions, never scale steps.
@ Octave endpoints g=2 and 196 terminate the searches in either range.
@ Preserves every register it uses: the audio routine keeps pointers live in
@ r4-r12 across this point (ip is read again at 0x08027bae).
    .thumb_func
p5_octave:
    push    {r0-r10, lr}
    vpush   {s0-s1}
    ldr     r0, =0x2002A660             @ presets can map Varispeed with unity options off
    ldr     r0, [r0]
    ldr     r1, =0x54535250
    cmp     r0, r1
    beq     unity_map_call
    ldr     r0, =0x2002A618
    ldrh    r0, [r0]
    cbnz    r0, unity_map_call
    ldr     r0, =0x2002A654             @ enabled-config marker: process disabling once
    ldr     r0, [r0]
    cbz     r0, unity_map_done
unity_map_call:
    bl      unity_map_hook
    ldr     r0, =0x2002A65C             @ unity override, independent of quantization
    ldr     r0, [r0]
    cmp     r0, #0
    bne.w   p5_done
unity_map_done:
    ldr     r3, =MOD
    ldr     r8, =RANGE
    ldrb    r8, [r8]
    ldr     r1, [r3]
    ldr     r2, =MAGIC
    cmp     r1, r2
    bne     9f
    ldr     r1, =SETTINGS
    ldr     r2, [r1]
    ldr     r4, =SETTINGS_MAGIC
    cmp     r2, r4
    bne     p5_legacy
    ldrb    r2, [r1, #5]
    cmp     r2, #0
    beq     p5_free                     @ octl 0 disables either quantizer mode
    ldr     r1, =VQNT
    ldrb    r1, [r1]
    cmp     r1, #1
    bne     p5_legacy
    @ A Varispeed gesture temporarily bypasses the quantizer. Other SHIFT
    @ gestures and plain navigation taps retain the current pitch scale.
    ldrb    r1, [r3, #4]
    cbz     r1, p5_default_quantize
    ldrb    r1, [r3, #5]
    cbz     r1, p5_default_quantize
    ldrb    r1, [r3, #6]
    cmp     r1, #2
    beq     p5_free
p5_default_quantize:
    ldr     r1, =VSOP
    ldr     r1, [r1]
    cmp     r1, #2
    beq     forward_quantize
    bhi     p5_free
    b       bidirectional_quantize
p5_free:
    movs    r1, #0
    strb    r1, [r3, #7]               @ restore stock glide; no latched fine value
    b       p5_done
p5_legacy:
    ldr     r1, =VSOP
    ldr     r1, [r1]
    cmp     r1, #2
    beq     p5_forward
    bhi     9f
    ldrb    r1, [r3, #6]
    cmp     r1, #2
    bne     5f
    ldrb    r1, [r3, #5]
    cmp     r1, #0
    beq     5f
    ldrb    r1, [r3, #4]
    cmp     r1, #0
    beq     5f
bidirectional_quantize:
    @ Held edit: u = trunc(x * 6400), the lookup index in 1/16 units.
    vldr    s0, k6400
    vmul.f32 s0, s18, s0
    vcvt.s32.f32 s0, s0
    vmov    r0, s0
    @ Scale mask (r6) and hysteresis (r7) from octl.
    movs    r6, #1
    movs    r7, #M_WIDE
    ldr     r1, =SETTINGS
    ldr     r2, [r1]
    ldr     r4, =SETTINGS_MAGIC
    cmp     r2, r4
    bne     11f
    ldrb    r2, [r1, #5]
    cmp     r2, #2
    it      eq
    moveq   r6, #0x81                   @ octaves + fifths
    cmp     r2, #3
    blo     11f
    mov     r7, #M_NARROW               @ (no flags: beq below)
    movw    r6, #0xfff                  @ every semitone
    beq     11f
    ldr     r1, =SCALE                  @ octl 4: custom
    ldrh    r6, [r1]
    movw    r1, #0xffe
    ands    r6, r6, r1
    orr     r6, r6, #1
11: cmp     r8, #1
    it      eq
    lsreq   r7, r7, #1                 @ same hysteresis in musical intervals
    subs    r1, r0, #8                  @ nearest grid point; midpoint ties rounded down
    adds    r1, r1, #15                 @ exact midpoint ties go to the lower index
    asrs    r1, r1, #5
    cmp     r1, #2
    it      lt
    movlt   r1, #2
    cmp     r1, #196
    it      gt
    movgt   r1, #196
    mov     r4, r1                      @ r4: nearest allowed at or below g0
12: bl      allowed
    cbnz    r2, 13f
    subs    r4, r4, #1
    b       12b
13: mov     r5, r4                      @ keep; r4 walks up from g0
    mov     r4, r1
14: bl      allowed
    cbnz    r2, 15f
    adds    r4, r4, #1
    b       14b
15: lsls    r1, r5, #5                  @ distances |u - (32 g + 8)|
    adds    r1, r1, #8
    subs    r1, r0, r1
    it      mi
    rsbmi   r1, r1, #0
    lsls    r2, r4, #5
    adds    r2, r2, #8
    subs    r2, r0, r2
    it      mi
    rsbmi   r2, r2, #0
    cmp     r2, r1                      @ ties go to the lower rate index
    itt     lt
    movlt   r5, r4
    movlt   r1, r2
    lsls    r5, r5, #1                  @ best m = 2 g, distance r1
    ldrb    r2, [r3, #7]                @ locked: keep the current rate unless
    cbz     r2, 2f                      @ the best one is M nearer
    ldrh    r2, [r3, #12]
    subs    r4, r2, #4                  @ only a valid m (4..392, multiple of 2)
    cmp     r4, #388
    bhi     2f
    tst     r2, #1
    bne     2f
    lsrs    r4, r2, #1                  @ and still in the scale (options re-read)
    bl      allowed
    cbz     r2, 2f
    ldrh    r2, [r3, #12]
    lsls    r2, r2, #4
    adds    r2, r2, #8
    subs    r2, r0, r2
    it      mi
    rsbmi   r2, r2, #0
    add     r1, r1, r7
    cmp     r2, r1
    ble     3f
2:  strh    r5, [r3, #12]
3:  movs    r0, #1
    strb    r0, [r3, #7]
    movw    r0, #0xffff
    strh    r0, [r3, #14]
    b       7f
5:  ldrb    r1, [r3, #7]                @ not editing: latched lock?
    cbz     r1, 9f
    ldr     r0, =VS_ADC
    ldr     r0, [r0]
    ldrh    r1, [r3, #14]
    movw    r2, #0xffff
    cmp     r1, r2
    bne     6f
    strh    r0, [r3, #14]               @ first block after release
    mov     r1, r0
6:  subs    r1, r0, r1
    it      mi
    rsbmi   r1, r1, #0
    movw    r2, #T_PICKUP
    cmp     r8, #1
    it      eq
    lsreq   r2, r2, #1
    cmp     r1, r2
    ble     7f
    movs    r0, #0                      @ moved away: back to continuous
    strb    r0, [r3, #7]
    b       9f
7:  ldrh    r0, [r3, #12]               @ s18 = (m + 0.5) / 400
    vmov    s0, r0
    vcvt.f32.s32 s0, s0
    vldr    s1, k0p5
    vadd.f32 s0, s0, s1
    vldr    s1, k1over400
    vmul.f32 s18, s0, s1
9:
p5_done:
    vpop    {s0-s1}
    pop     {r0-r10, lr}
    cmp     r0, #199                    @ replaced instructions
    ble.w   RATE_FULL
    b.w     RATE_NEXT

@ r2 = 1 when grid point r4 is in scale mask r6. Reads r8 (range); changes r2 only.
    .thumb_func
allowed:
    cmp     r4, #100                    @ stop
    beq     2f
    cmp     r4, #98                     @ duplicate zero entries, not steps
    beq     1f
    cmp     r4, #99
    beq     1f
    ite     gt
    subgt   r2, r4, #100                @ forward: semitones + 72 in extended mode
    rsble   r2, r4, #98                 @ reverse: semitones + 72
    cmp     r8, #1
    beq     0f
    tst     r2, #1                     @ standard mode uses every other grid point
    bne     1f
    lsrs    r2, r2, #1                 @ standard: semitones + 36
0:  cmp     r2, #12
    itt     hs
    subhs   r2, r2, #12
    bhs     0b
    lsr     r2, r6, r2
    and     r2, r2, #1
    bx      lr
1:  movs    r2, #0
    bx      lr
2:  movs    r2, #1
    bx      lr

@ P6 (hook at 0x08027bde, after the glide coefficient is chosen).
@ While locked, glide with k = 1 so the rate lands exactly on the scale step.
    .thumb_func
p6_glide:
    ldr     r0, =MOD
    ldrb    r0, [r0, #7]
    cbnz    r0, unity_glide
    ldr     r0, =0x2002A658
    ldr     r0, [r0]
    cbz     r0, 1f
unity_glide:
    vmov.f32 s1, #1.0
    vstr    s1, [sp, #192]
1:  vldr    s1, k0p02                   @ replaced instructions
    ldr     r0, =SLIDE_PTR
    b.w     GLIDE_NEXT

    .align 2
k6400:      .float 6400.0
k0p5:       .float 0.5
k1over400:  .float 0.0025
k0p02:      .word 0x3ca3d70a
    .ltorg

@ R1: common bidirectional table setup. r5 still has the raw 0..399 index.
@ vsop 1 ordinarily clears two low bits; extended mode needs two indices
@ per semitone, so clear only one. vsop 2 never reaches these hooks.
    .global range_index, range_forward, range_reverse
    .type RANGE_INDEX_NEXT, %function
    .type RANGE_FORWARD_NEXT, %function
    .type RANGE_REVERSE_NEXT, %function
    .thumb_func
range_index:
    push    {r0}
    ldr     r0, =RANGE
    ldrb    r0, [r0]
    cmp     r0, #1
    it      eq
    biceq   r1, r5, #1
    pop     {r0}
    ldr     r7, =0x200220e8             @ replaced literal load + stack store
    str     r7, [sp, #128]
    b.w     RANGE_INDEX_NEXT

    .thumb_func
range_forward:
    ldr.w   r6, [fp]                   @ replaced table load
    push    {r0}
    ldr     r0, =RANGE
    ldrb    r0, [r0]
    cmp     r0, #1
    bne     1f
    vpush   {s0-s1}
    vmov    s0, r6
    vmul.f32 s0, s0, s0
    vmov    r6, s0
    vpop    {s0-s1}
1:  pop     {r0}
    b.w     RANGE_FORWARD_NEXT

    .thumb_func
range_reverse:
    vldr    s31, [r1]                  @ replaced table load; stock negates next
    push    {r0}
    ldr     r0, =RANGE
    ldrb    r0, [r0]
    cmp     r0, #1
    it      eq
    vmuleq.f32 s31, s31, s31
    pop     {r0}
    b.w     RANGE_REVERSE_NEXT
    .ltorg

@ Matching bidirectional lookup copies for Gene Size <= 199. These use
@ different registers and return to the stock full-splice/reel engine path.
    .global range_index_full, range_forward_full, range_reverse_full
    .type RANGE_FULL_INDEX_NEXT, %function
    .type RANGE_FULL_FORWARD_NEXT, %function
    .type RANGE_FULL_REVERSE_NEXT, %function
    .thumb_func
range_index_full:
    push    {r0}
    ldr     r0, =RANGE
    ldrb    r0, [r0]
    cmp     r0, #1
    it      eq
    biceq   r3, r1, #1
    pop     {r0}
    ldr     r7, =0x200220e8             @ replaced literal load + stack store
    str     r7, [sp, #128]
    b.w     RANGE_FULL_INDEX_NEXT

    .thumb_func
range_forward_full:
    ldr     r5, [r3]                   @ replaced table load
    push    {r0}
    ldr     r0, =RANGE
    ldrb    r0, [r0]
    cmp     r0, #1
    bne     1f
    vpush   {s0-s1}
    vmov    s0, r5
    vmul.f32 s0, s0, s0
    vmov    r5, s0
    vpop    {s0-s1}
1:  pop     {r0}
    str     r5, [r7]                   @ replaced target store
    b.w     RANGE_FULL_FORWARD_NEXT

    .thumb_func
range_reverse_full:
    vldr    s25, [r6]                  @ stock negates the loaded value next
    push    {r0}
    ldr     r0, =RANGE
    ldrb    r0, [r0]
    cmp     r0, #1
    it      eq
    vmuleq.f32 s25, s25, s25
    pop     {r0}
    b.w     RANGE_FULL_REVERSE_NEXT
    .ltorg

    .include "forward.inc"

    .include "unity.inc"
