@ Absolute Thumb destinations, linked as a separate object so GAS cannot
@ reduce their typed relocations to untyped *ABS* branches (binutils 2.47).
.syntax unified
.cpu cortex-m4
.thumb
.global PARSE_NEXT
.thumb_set PARSE_NEXT, 0x080232fc
.global PARSE_STOCK
.thumb_set PARSE_STOCK, 0x0802332a
.global WRITE_RETURN
.thumb_set WRITE_RETURN, 0x08024566
.global WRITE_OPTIONS
.thumb_set WRITE_OPTIONS, 0x080241e6
.global LOOP_IDLE
.thumb_set LOOP_IDLE, 0x08023eec
