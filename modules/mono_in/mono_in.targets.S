@ Absolute Thumb destinations, linked as a separate object so GAS cannot
@ reduce their typed relocations to untyped *ABS* branches (binutils 2.47).
.syntax unified
.cpu cortex-m4
.thumb
.global BLOCK_STOCK
.thumb_set BLOCK_STOCK, 0x08027520
