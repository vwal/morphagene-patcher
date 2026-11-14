@ Absolute Thumb destinations, linked as a separate object so GAS cannot
@ reduce their typed relocations to untyped *ABS* branches (binutils 2.47).
.syntax unified
.cpu cortex-m4
.thumb
.global G2_RETURN
.thumb_set G2_RETURN, 0x0802780c
.global G3_RETURN
.thumb_set G3_RETURN, 0x080288f2
.global GS_RETURN
.thumb_set GS_RETURN, 0x08027978
.global CA_RETURN
.thumb_set CA_RETURN, 0x08028494
.global CB_RETURN
.thumb_set CB_RETURN, 0x08029cb8
.global O1_RETURN
.thumb_set O1_RETURN, 0x080276f4
.global GA_RETURN
.thumb_set GA_RETURN, 0x0802838e
.global GB_RETURN
.thumb_set GB_RETURN, 0x08029bbc

.global DENS_A_NEXT, DENS_B_NEXT
.thumb_set DENS_A_NEXT, 0x080280e1
.thumb_set DENS_B_NEXT, 0x08029945
