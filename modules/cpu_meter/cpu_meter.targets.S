@ Absolute Thumb destinations, linked as a separate object so GAS cannot
@ reduce their typed relocations to untyped *ABS* branches (binutils 2.47).
.syntax unified
.cpu cortex-m4
.thumb
.global AUDIO_RETURN
.thumb_set AUDIO_RETURN, 0x0802866a
.global LOOP_HEAD
.thumb_set LOOP_HEAD, 0x08022f7e
