@ Module options_keys: mod settings in options.txt (mg204).
@ Requires sd_updater (it resets the settings block to defaults every boot).
@
@ Keys (first four characters, single digit at position 5, like stock keys):
@   tape 0|1   SHIFT+S.O.S.: 0 classic TLA feedback, 1 tape mode (default 1)
@   vqnt 0|1   0 SHIFT-to-lock; 1 quantized normally, SHIFT+Varispeed free
@   octl 0-4   Varispeed scale: 0 off, 1 octaves, 2 octaves + fifths,
@              3 semitones, 4 custom scale (default 1)
@   scal list  custom scale for octl 4: semitones 1-11 above the root,
@              comma or space separated ("scal 3,5,7,10"; default none)
@   fxsl 0-2   SHIFT+Morph effect: 0 off, 1 SRR, 2 warble (default 1)
@   cpul 0|1   CPU log cpulog.txt, for troubleshooting: 0 off, 1 on (default 0; cpu_meter)
@   mcap 0-9   Morph cap while tape-dubbing: 0 none, 1-9 = 0.1-0.9 (default 3)
@   sldm 0|1   Turing mode: 0 off, 1 on (default 0; modules/gene_shape)
@   root 0-100 Turing: chance (percent) that a step plays the root, not a chord
@              ratio (default 50)
@   tlen 1-16  Turing loop length in steps (default 8)
@   ingn 0-3   input gain (REC held + SHIFT taps), saved across power cycles
@              (default 0 = stock)
@   mono 0-2   mono input: 1 copies the left input onto the right, 2 does it
@              only while R in is quiet (auto) (default 0; modules/mono_in)
@ Parser hook: the stock loop reads each line into fp and dispatches on the
@ key at 0x08023326; ours is checked first. Writer hook: the firmware recreates
@ options.txt (stock keys + comments) after parsing; we append our keys before
@ its final f_close, so they persist and are documented in the file.
@ Settings block (SETTINGS): +0 magic "OPTS", +4 tape, +5 octl, +6 fxsl,
@ +7 mono, +8 cpul, +9 mcap, +10 sldm, +11 root, +12 tlen, +13 ingn (the
@ saved gain), +14 applied at boot (0/1), +15 pending gain + 1 (0 = none).
@ The block is full, so scal lives at SCALE: a u16 mask, bit d = d semitones
@ (bits 1-11), reset to 0 every boot by sd_updater.
@
@ Main-loop hook (opt_main, 0x08023ee6): the request dispatcher's test of
@ flag 0x80 (rewrite options.txt), reached only when no other card request is
@ pending. The first pass applies ingn to the codec. After that, a gain
@ changed with REC + SHIFT and left alone for SETTLE blocks, with no
@ recording and the card mounted, is copied to ingn and flag 0x80 is set,
@ so the stock writer rewrites options.txt (as it does after a reel load).

    .syntax unified
    .cpu cortex-m4
    .fpu fpv4-sp-d16
    .thumb

    .equ SETTINGS,       0x2002A0F0
    .equ SETTINGS_MAGIC, 0x5354504f
    .equ F_PRINTF,       0x08034805
    .equ F_CLOSE,        0x080327a9
    .type PARSE_NEXT, %function  @ 0x080232fc; defined in options_keys.targets.S     @ loop head: read the next line
    .type PARSE_STOCK, %function  @ 0x0802332a; defined in options_keys.targets.S     @ after the replaced instruction
    .type WRITE_RETURN, %function  @ 0x08024566; defined in options_keys.targets.S
    .equ KEY_TAPE,       0x65706174     @ "tape" as a little-endian word
    .equ KEY_OCTL,       0x6c74636f     @ "octl"
    .equ KEY_FXSL,       0x6c737866     @ "fxsl"
    .equ KEY_CPUL,       0x6c757063     @ "cpul"
    .equ KEY_MCAP,       0x7061636d     @ "mcap"
    .equ KEY_SLDM,       0x6d646c73     @ "sldm"
    .equ KEY_ROOT,       0x746f6f72     @ "root"
    .equ KEY_TLEN,       0x6e656c74     @ "tlen"
    .equ KEY_INGN,       0x6e676e69     @ "ingn"
    .equ KEY_SCAL,       0x6c616373     @ "scal"
    .equ KEY_MONO,       0x6f6e6f6d     @ "mono"
    .equ KEY_DSTR,       0x72747364     @ dstr: startup Genes/sec, one decimal
    .equ DSTR,           0x2002A614     @ u32 tenths, default 10; zero selects stock timing
    .equ KEY_DENS,       0x736e6564
    .equ KEY_VRNG,       0x676e7276     @ "vrng"
    .equ KEY_VQNT,       0x746e7176     @ "vqnt"
    .equ KEY_VUNI,       0x696e7576
    .equ KEY_VCTR,       0x72746376
    .equ VUNI,           0x2002A618
    .equ VCTR,           0x2002A619
    .equ KEY_MLOP,       0x706f6c6d
    .equ MLOP,           0x2002A611
    .equ VQNT,           0x2002A610
    .equ RANGE,          0x2002A606     @ 0 stock, 1 extended bidirectional
    .equ SCALE,          0x2002A604     @ scal mask (u16)
    .equ GAIN,           0x20001068     @ stock input-gain index 0-3
    .equ SET_GAIN,       0x080257dd     @ stock: codec line-in volume = 0x13 + 4 * gain
    .equ FLAGS,          0x20022074     @ main-loop request flags; 0x80 = rewrite options.txt
    .equ CARD_OK,        0x20001290     @ 1 = card mounted
    .equ REC_ACTIVE,     0x20022108
    .equ BLOCKS,         0x20021394     @ +1 per audio block (6000 per second)
    .equ STAMP,          0x2002A600     @ BLOCKS when the pending gain was first seen
    .equ SETTLE,         18000          @ 3 s without a gain change before saving
    .type WRITE_OPTIONS, %function  @ 0x080241e6; defined in options_keys.targets.S     @ stock: flag 0x80 set
    .type LOOP_IDLE, %function  @ 0x08023eec; defined in options_keys.targets.S     @ stock: flag 0x80 clear (cpu_meter's M1)

    .text
    .global opt_parse, opt_write, opt_main

@ Live: fp = line buffer, r9 = line number, sl = fp[0]. Free: r0-r3, ip, lr.
    .thumb_func
opt_parse:
    ldr     r0, =0x2002AE4C             @ PRESET_NORMAL->parse_mode
    ldr     r0, [r0]
    cmp     r0, #2                      @ SKIP_CHUNK: header or continuation
    beq.w   PARSE_NEXT
    cbz     r0, opt_parse_ordinary
    push    {r4, lr}
    mov     r0, fp
    bl      presets_normal_parse
    pop     {r4, lr}
    cmp     r0, #0
    bne.w   PARSE_NEXT
opt_parse_ordinary:
    ldrb    r0, [fp]                    @ key bytes (buffer may be unaligned)
    ldrb    r1, [fp, #1]
    orr     r0, r0, r1, lsl #8
    ldrb    r1, [fp, #2]
    orr     r0, r0, r1, lsl #16
    ldrb    r1, [fp, #3]
    orr     r0, r0, r1, lsl #24
    ldr     r2, =SETTINGS
    ldr     r1, =KEY_TAPE
    cmp     r0, r1
    beq     1f
    ldr     r1, =KEY_OCTL
    cmp     r0, r1
    beq     2f
    ldr     r1, =KEY_FXSL
    cmp     r0, r1
    beq     5f
    ldr     r1, =KEY_CPUL
    cmp     r0, r1
    beq     7f
    ldr     r1, =KEY_MCAP
    cmp     r0, r1
    beq     8f
    ldr     r1, =KEY_SLDM
    cmp     r0, r1
    beq     10f
    ldr     r1, =KEY_ROOT
    cmp     r0, r1
    beq     11f
    ldr     r1, =KEY_TLEN
    cmp     r0, r1
    beq     12f
    ldr     r1, =KEY_INGN
    cmp     r0, r1
    beq     17f
    ldr     r1, =KEY_SCAL
    cmp     r0, r1
    beq     18f
    ldr     r1, =KEY_DSTR
    cmp     r0, r1
    beq     parse_dstr
    ldr     r1, =KEY_DENS
    cmp     r0, r1
    beq     42f
    ldr     r1, =KEY_MLOP
    cmp     r0, r1
    beq     44f
    ldr     r1, =KEY_VUNI
    cmp     r0, r1
    beq     parse_vuni
    ldr     r1, =KEY_VCTR
    cmp     r0, r1
    beq     parse_vctr
    ldr     r1, =KEY_VQNT
    cmp     r0, r1
    beq     43f
    ldr     r1, =KEY_VRNG
    cmp     r0, r1
    beq     40f
    ldr     r1, =KEY_MONO
    cmp     r0, r1
    beq     6f
    ldrb.w  ip, [fp, #1]                @ replaced instruction: stock keys
    b.w     PARSE_STOCK
parse_vuni:
    ldr     r2, =VUNI
    b       3f
parse_vctr:
    ldr     r2, =VCTR
    b       3f
44: ldr     r2, =MLOP
    b       3f
43: ldr     r2, =VQNT
    b       3f
42: ldr     r2, =0x2002A607
    b       3f
40: ldr     r2, =RANGE
    b       3f
8:  adds    r2, r2, #9                  @ mcap -> +9, digits 0-9
    movs    r3, #9
    b       9f
10: adds    r2, r2, #10                 @ sldm -> +10
    b       3f
1:  adds    r2, r2, #4                  @ tape -> +4
    b       3f
2:  adds    r2, r2, #5                  @ octl -> +5, digits 0-4
    movs    r3, #4
    b       9f
5:  adds    r2, r2, #6                  @ fxsl -> +6, digits 0-2
    movs    r3, #2
    b       9f
7:  adds    r2, r2, #8                  @ cpul -> +8
    b       3f
6:  adds    r2, r2, #7                  @ mono -> +7, digits 0-2
    movs    r3, #2
    b       9f
17: adds    r2, r2, #13                 @ ingn -> +13, digits 0-3
    movs    r3, #3
    b       9f
3:  movs    r3, #1                      @ on/off keys: only 0 or 1 accepted
9:  ldrb    r1, [fp, #4]               @ require key/value separator, not stale bytes
    cmp     r1, #' '
    bne     4f
    ldrb    r0, [fp, #6]               @ a single digit must end before whitespace/comment
    cmp     r0, #0
    beq     41f
    cmp     r0, #10
    beq     41f
    cmp     r0, #13
    beq     41f
    cmp     r0, #' '
    beq     41f
    cmp     r0, #9
    beq     41f
    cmp     r0, #'/'
    bne     4f
41: ldrb    r1, [fp, #5]
    subs    r1, r1, #'0'
    cmp     r1, r3
    bhi     4f
    strb    r1, [r2]
4:  b.w     PARSE_NEXT
11: adds    r2, r2, #11                 @ root -> +11, 0-100
    movs    r3, #100
    b       13f
12: adds    r2, r2, #12                 @ tlen -> +12, 1-16
    movs    r3, #16
13: movs    r0, #0                      @ decimal value of up to four digits
    mov     ip, #5
14: ldrb    r1, [fp, ip]
    subs    r1, r1, #'0'
    cmp     r1, #9
    bhi     15f
    add     r0, r0, r0, lsl #2
    add     r0, r1, r0, lsl #1
    add     ip, ip, #1
    cmp     ip, #9
    blo     14b
15: cmp     ip, #5                      @ no digits
    beq     4b
    cmp     r0, r3
    bhi     4b
    cmp     r3, #16                     @ tlen 0 is not a length
    bne     16f
    cmp     r0, #0
    beq     4b
16: strb    r0, [r2]
    b       4b
18: movs    r0, #0                      @ scal: a list of numbers 1-11 -> mask
    mov     ip, #5
19: ldrb    r1, [fp, ip]
    cmp     r1, #','
    beq     20f
    cmp     r1, #' '
    beq     20f
    subs    r1, r1, #'0'
    cmp     r1, #9
    bhi     22f                         @ end of line, comment or junk
    movs    r3, #0
21: add     r3, r3, r3, lsl #2          @ r3 = 10 * r3 + digit
    add     r3, r1, r3, lsl #1
    add     ip, ip, #1
    ldrb    r1, [fp, ip]
    subs    r1, r1, #'0'
    cmp     r1, #9
    bhi     23f
    cmp     r3, #100                    @ three digits: not a semitone
    blo     21b
23: subs    r3, r3, #1                  @ 1-11 only (0 is the root, always on)
    cmp     r3, #10
    bhi     19b
    adds    r3, r3, #1
    movs    r1, #1
    lsls    r1, r1, r3
    orrs    r0, r0, r1
    b       19b
20: add     ip, ip, #1
    cmp     ip, #64
    blo     19b
22: ldr     r2, =SCALE
    strh    r0, [r2]
    b       4b

@ Strict decimal startup rate: 0 for stock timing, otherwise 0.1..128.0, at most one fractional digit.
@ No changes until the entire significant value is valid. No libc/FPU needed.
parse_dstr:
    add     ip, fp, #4
    ldrb    r1, [ip], #1
    cmp     r1, #' '
    beq     dstr_space
    cmp     r1, #9
    bne     dstr_done
dstr_space:
    ldrb    r1, [ip], #1
    cmp     r1, #' '
    beq     dstr_space
    cmp     r1, #9
    beq     dstr_space
    subs    r1, #'0'
    cmp     r1, #9
    bhi     dstr_done
    movs    r0, #0
    movs    r2, #0
dstr_whole:
    adds    r2, #1
    cmp     r2, #3
    bhi     dstr_done
    add     r0, r0, r0, lsl #2
    add     r0, r1, r0, lsl #1
    ldrb    r1, [ip], #1
    subs    r1, #'0'
    cmp     r1, #9
    bls     dstr_whole
    adds    r1, #'0'
    cmp     r0, #128
    bhi     dstr_done
    add     r0, r0, r0, lsl #2
    lsls    r0, #1
    cmp     r1, #'.'
    bne     dstr_tail
    ldrb    r1, [ip], #1
    subs    r1, #'0'
    cmp     r1, #9
    bhi     dstr_done
    adds    r0, r1
    ldrb    r1, [ip], #1
dstr_tail:
    cmp     r1, #' '
    beq     dstr_tail_next
    cmp     r1, #9
    beq     dstr_tail_next
    cmp     r1, #13
    beq     dstr_tail_next
    cmp     r1, #0
    beq     dstr_valid
    cmp     r1, #10
    beq     dstr_valid
    cmp     r1, #'/'
    bne     dstr_done
    ldrb    r1, [ip]
    cmp     r1, #'/'
    bne     dstr_done
    b       dstr_valid
dstr_tail_next:
    ldrb    r1, [ip], #1
    b       dstr_tail
dstr_valid:
    cmp     r0, #1280
    bhi     dstr_done
    ldr     r2, =DSTR
    str     r0, [r2]
    @ Audio can have seen dens before this line during an ordinary mount.
    @ Reinitialize from the configured value on the next enabled block.
    ldr     r2, =0x2002A800
    movs    r0, #0
    str     r0, [r2]
dstr_done:
    b.w     PARSE_NEXT
    .ltorg

@ Writer: r0 is free; the FIL is at sp + 1396 (as the stock code computes).
    .thumb_func
opt_write:
    ldr     r3, =SETTINGS
    ldr     r2, [r3]
    ldr     r1, =SETTINGS_MAGIC
    cmp     r2, r1
    ite     eq
    ldrbeq  r2, [r3, #4]
    movne   r2, #1
    addw    r0, sp, #1396
    ldr     r1, =fmt_tape
    ldr     r3, =F_PRINTF
    blx     r3
    ldr     r3, =SETTINGS
    ldr     r2, [r3]
    ldr     r1, =SETTINGS_MAGIC
    cmp     r2, r1
    ite     eq
    ldrbeq  r2, [r3, #5]
    movne   r2, #1
    addw    r0, sp, #1396
    ldr     r1, =fmt_octl
    ldr     r3, =F_PRINTF
    blx     r3
    push    {r4-r6, lr}                 @ FIL now at sp + 1412
    ldr     r4, =SCALE                  @ scal: the mask as a list, "0" if empty
    ldrh    r4, [r4]
    movw    r1, #0xffe
    ands    r4, r4, r1
    addw    r0, sp, #1412
    ldr     r1, =fmt_scal
    ldr     r3, =F_PRINTF
    blx     r3
    cbnz    r4, 31f
    addw    r0, sp, #1412
    ldr     r1, =fmt_num
    movs    r2, #0
    ldr     r3, =F_PRINTF
    blx     r3
    b       33f
31: movs    r5, #1                      @ semitone
    ldr     r6, =fmt_num                @ first entry without a comma
32: lsr     r0, r4, r5
    tst     r0, #1
    beq     34f
    addw    r0, sp, #1412
    mov     r1, r6
    mov     r2, r5
    ldr     r3, =F_PRINTF
    blx     r3
    ldr     r6, =fmt_cnum
34: adds    r5, r5, #1
    cmp     r5, #12
    blo     32b
33: addw    r0, sp, #1412
    ldr     r1, =fmt_scal_end
    ldr     r3, =F_PRINTF
    blx     r3
    pop     {r4-r6, lr}
    ldr     r3, =SETTINGS
    ldr     r2, [r3]
    ldr     r1, =SETTINGS_MAGIC
    cmp     r2, r1
    ite     eq
    ldrbeq  r2, [r3, #6]
    movne   r2, #1
    addw    r0, sp, #1396
    ldr     r1, =fmt_fxsl
    ldr     r3, =F_PRINTF
    blx     r3
    ldr     r3, =SETTINGS
    ldr     r2, [r3]
    ldr     r1, =SETTINGS_MAGIC
    cmp     r2, r1
    ite     eq
    ldrbeq  r2, [r3, #8]
    movne   r2, #0                      @ cpul default 0
    addw    r0, sp, #1396
    ldr     r1, =fmt_cpul
    ldr     r3, =F_PRINTF
    blx     r3
    ldr     r3, =SETTINGS
    ldr     r2, [r3]
    ldr     r1, =SETTINGS_MAGIC
    cmp     r2, r1
    ite     eq
    ldrbeq  r2, [r3, #9]
    movne   r2, #3
    addw    r0, sp, #1396
    ldr     r1, =fmt_mcap
    ldr     r3, =F_PRINTF
    blx     r3
    ldr     r3, =SETTINGS
    ldr     r2, [r3]
    ldr     r1, =SETTINGS_MAGIC
    cmp     r2, r1
    ite     eq
    ldrbeq  r2, [r3, #10]
    movne   r2, #0
    addw    r0, sp, #1396
    ldr     r1, =fmt_sldm
    ldr     r3, =F_PRINTF
    blx     r3
    ldr     r3, =SETTINGS
    ldr     r2, [r3]
    ldr     r1, =SETTINGS_MAGIC
    cmp     r2, r1
    ite     eq
    ldrbeq  r2, [r3, #11]
    movne   r2, #50
    addw    r0, sp, #1396
    ldr     r1, =fmt_root
    ldr     r3, =F_PRINTF
    blx     r3
    ldr     r3, =SETTINGS
    ldr     r2, [r3]
    ldr     r1, =SETTINGS_MAGIC
    cmp     r2, r1
    ite     eq
    ldrbeq  r2, [r3, #12]
    movne   r2, #8
    addw    r0, sp, #1396
    ldr     r1, =fmt_tlen
    ldr     r3, =F_PRINTF
    blx     r3
    ldr     r2, =GAIN                   @ the live gain, so every rewrite keeps it
    ldr     r2, [r2]
    addw    r0, sp, #1396
    ldr     r1, =fmt_ingn
    ldr     r3, =F_PRINTF
    blx     r3
    ldr     r3, =SETTINGS
    ldr     r2, [r3]
    ldr     r1, =SETTINGS_MAGIC
    cmp     r2, r1
    ite     eq
    ldrbeq  r2, [r3, #7]
    movne   r2, #0
    addw    r0, sp, #1396
    ldr     r1, =fmt_mono
    ldr     r3, =F_PRINTF
    blx     r3
    ldr     r2, =RANGE
    ldrb    r2, [r2]
    addw    r0, sp, #1396
    ldr     r1, =fmt_vrng
    ldr     r3, =F_PRINTF
    blx     r3
    ldr     r2, =0x2002A607
    ldrb    r2, [r2]
    addw    r0, sp, #1396
    ldr     r1, =fmt_dens
    ldr     r3, =F_PRINTF
    blx     r3
    ldr     r2, =DSTR
    ldr     r2, [r2]
    movs    r0, #10
    udiv    r3, r2, r0
    mls     r2, r3, r0, r2
    mov     r0, r2                    @ fraction
    mov     r2, r3                    @ whole Genes/sec
    mov     r3, r0
    addw    r0, sp, #1396
    ldr     r1, =fmt_dstr
    ldr     ip, =F_PRINTF
    blx     ip
    ldr     r2, =VQNT
    ldrb    r2, [r2]
    addw    r0, sp, #1396
    ldr     r1, =fmt_vqnt
    ldr     r3, =F_PRINTF
    blx     r3
    ldr     r2, =MLOP
    ldrb    r2, [r2]
    addw    r0, sp, #1396
    ldr     r1, =fmt_mlop
    ldr     r3, =F_PRINTF
    blx     r3
    ldr     r2, =VUNI
    ldrb    r2, [r2]
    addw    r0, sp, #1396
    ldr     r1, =fmt_vuni
    ldr     r3, =F_PRINTF
    blx     r3
    ldr     r2, =VCTR
    ldrb    r2, [r2]
    addw    r0, sp, #1396
    ldr     r1, =fmt_vctr
    ldr     r3, =F_PRINTF
    blx     r3
    addw    r0, sp, #1396
    push    {r4, lr}
    bl      presets_write
    pop     {r4, lr}
    addw    r0, sp, #1396               @ replaced: f_close(options.txt)
    ldr     r3, =F_CLOSE
    blx     r3
    b.w     WRITE_RETURN

@ Main loop, replacing "lsls r1,r5,#24; bmi.w WRITE_OPTIONS" at 0x08023ee6.
@ Live: r5 = request flags as loaded, r6 = card state, r7 = &FLAGS; r1 is
@ free (the replaced lsls writes it). Everything else is preserved.
    .thumb_func
opt_main:
    push    {r0-r4, r6-r12, lr}         @ 13 words; + 4 keeps sp 8-byte aligned
    sub     sp, sp, #4
    ldr     r4, =SETTINGS
    ldr     r0, [r4]
    ldr     r1, =SETTINGS_MAGIC
    cmp     r0, r1
    bne     90f
    ldr     r6, =GAIN
    ldrb    r0, [r4, #14]
    cbnz    r0, 20f
    movs    r0, #1                      @ first pass: apply the saved gain once
    strb    r0, [r4, #14]
    ldrb    r0, [r4, #13]
    ldr     r1, [r6]
    cmp     r0, r1
    beq     90f
    str     r0, [r6]
    ldr     r3, =SET_GAIN
    blx     r3
    b       90f
20: ldr     r0, [r6]                    @ later passes: watch for a change
    ldrb    r1, [r4, #13]
    cmp     r0, r1
    bne     30f
    movs    r1, #0                      @ back to the saved value: nothing pending
    strb    r1, [r4, #15]
    b       90f
30: ldr     r3, =BLOCKS
    ldr     r3, [r3]
    ldr     r2, =STAMP
    adds    r1, r0, #1
    ldrb    r12, [r4, #15]
    cmp     r12, r1
    beq     31f
    strb    r1, [r4, #15]               @ new pending value: restart the wait
    str     r3, [r2]
    b       90f
31: ldr     r1, [r2]
    subs    r1, r3, r1
    ldr     r2, =SETTLE
    cmp     r1, r2
    blo     90f
    ldr     r1, =REC_ACTIVE             @ never while recording
    ldr     r1, [r1]
    cbnz    r1, 90f
    ldr     r1, =CARD_OK
    ldr     r1, [r1]
    cmp     r1, #1
    bne     90f
    strb    r0, [r4, #13]               @ saved: ingn = gain
    movs    r1, #0
    strb    r1, [r4, #15]
    mrs     r2, primask                 @ request the rewrite (the timer ISR also
    cpsid   i                           @ sets bits in FLAGS)
    ldr     r1, =FLAGS
    ldr     r0, [r1]
    orr     r0, r0, #0x80
    str     r0, [r1]
    msr     primask, r2
90: add     sp, sp, #4
    pop     {r0-r4, r6-r12, lr}
    ldr     r1, =FLAGS                  @ pick up our request in this pass
    ldr     r1, [r1]
    tst     r1, #0x80
    it      ne
    orrne   r5, r5, #0x80
    lsls    r1, r5, #24                 @ replaced: flag 0x80 -> stock writer
    bpl     91f
    b.w     WRITE_OPTIONS
91: b.w     LOOP_IDLE
    .ltorg

    .align 2
fmt_tape: .asciz "//\n//Morphagene Study mods\ntape %d //SHIFT+S.O.S.: 0 classic TLA feedback (input + feedback x Gene playback), 1 tape mode (Varispeed tape head in the Slide/Gene Size window)\n"
    .align 2
fmt_octl: .asciz "octl %d //Varispeed scale: 0 off, 1 octaves, 2 octaves + fifths, 3 semitones, 4 custom scale (scal); vqnt selects gesture behavior\n"
    .align 2
fmt_scal: .asciz "scal "
    .align 2
fmt_num:  .asciz "%d"
    .align 2
fmt_cnum: .asciz ",%d"
    .align 2
fmt_scal_end: .asciz " //Custom scale for octl 4: semitones 1-11 above the root, e.g. 3,5,7,10 = minor pentatonic (root and octaves always on)\n"
    .align 2
fmt_fxsl: .asciz "fxsl %d //SHIFT+Morph effect: 0 off (Morph stays stock), 1 SRR (sample-rate reduction), 2 warble (tape wow and flutter on the Gene playback)\n//SHIFT+Slide: Gene start jitter amount (left = off)\n"
    .align 2
fmt_cpul: .asciz "cpul %d //CPU log, for troubleshooting only: 0 off, 1 on (writes cpulog.txt every 10 s; turn it off again afterwards)\n"
    .align 2
fmt_mcap: .asciz "mcap %d //Morph cap while tape-dubbing: 0 none, 1-9 = Morph limited to 0.1-0.9 (CPU safety; 3 = 0.3)\n"
    .align 2
fmt_sldm: .asciz "sldm %d //Turing mode: 0 off, 1 on: a loop of random seeds decides each Gene's chord ratio, scatter and stereo. SHIFT+Organize = evolution (left = locked loop, right = normal randomness), SHIFT+Gene Size = Genes per step (1-16), SHIFT+Slide = spread (start jitter, repeats when locked)\n"
    .align 2
fmt_root: .asciz "root %d //Turing: chance in percent that a step plays the root rather than a chord ratio (mcr1-mcr3)\n"
    .align 2
fmt_tlen: .asciz "tlen %d //Turing loop length in steps, 1-16\n"
    .align 2
fmt_ingn: .asciz "ingn %d //Input gain 0-3 (REC held + SHIFT taps); saved automatically a few seconds after a change\n"
    .align 2
fmt_dens: .asciz "dens %d //SHIFT+Gene Size: CCW stock timing, then 0.1-128 Hz.\n"
    .align 2
fmt_vrng: .asciz "vrng %d //0 stock, 1 +/-4x bidirectional or 0-8x forward\n"
    .align 2
fmt_vqnt: .asciz "vqnt %d //Varispeed quantization: 0 SHIFT+Varispeed locks, 1 quantized normally and SHIFT+Varispeed temporarily free; release snaps back; scale from octl/scal\n"
    .align 2
fmt_mono: .asciz "mono %d //Mono input: 0 off (stereo), 1 left input copied to the right (heard and recorded on both channels; R in is ignored), 2 auto: only while nothing is playing into R in\n"
    .ltorg

    .align 2
fmt_dstr: .asciz "dstr %d.%d //0 stock timing, 0.1-128 Genes/sec. Default 1.0.\n"
    .align 2
fmt_mlop: .asciz "mlop %d //Morph loop: 0 stock gaps (default), 1 seamless loop at minimum Morph\n"

fmt_vuni: .asciz "vuni %d //0 off; 1 SHIFT hold >=0.5 sec then release recalls +1x with pickup. Manual use: SHIFT jack must be unpatched. Other controls cancel.\n"
fmt_vctr: .asciz "vctr %d //0 original mapping; 1 +1x at calibrated knob noon with zero CV, all ranges/layouts; reverse and stop compressed into left half.\n"

@ Normal options-file transaction boundaries. No runtime control is changed
@ while individual lines are parsed; reload_service publishes after reel load.
.macro preset_io_save
    push {r0-r3,r12,lr}
    vpush {s0-s15}
    mrs r0, APSR
    vmrs r1, FPSCR
    push {r0,r1}
.endm
.macro preset_io_restore
    pop {r0,r1}
    msr APSR_nzcvq, r0
    vmsr FPSCR, r1
    vpop {s0-s15}
    pop {r0-r3,r12,lr}
.endm
.align 2
.global opt_preset_begin, opt_prepare_read, opt_preset_chunk, opt_preset_end
.type PRESET_BEGIN_RETURN, %function
.type OPTIONS_GETS_CALL, %function
.type PRESET_CHUNK_RETURN, %function
.type PRESET_END_RETURN, %function
.thumb_func
opt_preset_begin:
    preset_io_save
    bl presets_normal_begin
    preset_io_restore
    ldr r6, =0x726d6f64
    ldr r5, =0x73746570
    b.w PRESET_BEGIN_RETURN
.thumb_func
opt_prepare_read:
    @ FatFs returns a pointer, with no byte count. Fill the word-aligned
    @ options buffer so its last NUL after fgets identifies its actual end.
    mov r0, fp
    mov.w r1, #-1
    add.w r3, fp, #64
1:  str r1, [r0], #4
    cmp r0, r3
    bne 1b
    movs r1, #64
    mov r0, fp                         @ r2 still points to the options FIL
    b.w OPTIONS_GETS_CALL
.thumb_func
opt_preset_chunk:
    preset_io_save
    ldr r1, [sp, #72]                  @ original fgets result (NULL at EOF)
    mov r0, fp
    bl presets_normal_chunk
    preset_io_restore
    add.w r9, r9, #1                  @ displaced stock chunk counter
    b.w PRESET_CHUNK_RETURN
.thumb_func
opt_preset_end:
    preset_io_save
    addw r0, sp, #(1396+96)
    bl presets_normal_end
    preset_io_restore
    mov r9, r0
    addw r0, sp, #1396
    b.w PRESET_END_RETURN
    .ltorg

@ Keep stock numeric metadata on line 1; identify the modified format in the
@ human-readable version comment, including the legacy calibration branch.
.align 2
.global opt_version
.type VERSION_RETURN, %function
.thumb_func
opt_version:
    ldr r1, =fmt_version
    addw r0, sp, #1396
    b.w VERSION_RETURN
fmt_version:
    .asciz "// firmware version 204+c6\n"
    .space 8   @ Retain the version field footprint across test and release labels.
