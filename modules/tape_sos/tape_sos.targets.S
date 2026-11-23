@ Absolute Thumb destinations, linked as a separate object so GAS cannot
@ reduce their typed relocations to untyped *ABS* branches (binutils 2.47).
.syntax unified
.cpu cortex-m4
.thumb
.global LED_RETURN
.thumb_set LED_RETURN, 0x08024afe
.global P7_RETURN
.thumb_set P7_RETURN, 0x080276ca
.global A_AFTER_FILTER
.thumb_set A_AFTER_FILTER, 0x08028ef4
.global A_STOCK
.thumb_set A_STOCK, 0x08028e94
.global B_AFTER_FILTER
.thumb_set B_AFTER_FILTER, 0x0802a1c2
.global B_STOCK
.thumb_set B_STOCK, 0x0802a162
.global P10_RETURN
.thumb_set P10_RETURN, 0x0802798c
.global A_SKIP
.thumb_set A_SKIP, 0x08028ea0
.global B_SKIP
.thumb_set B_SKIP, 0x0802a16e
.global WA_STOCK
.thumb_set WA_STOCK, 0x080291dc
.global WA_DONE
.thumb_set WA_DONE, 0x08029234
.global WB_STOCK
.thumb_set WB_STOCK, 0x0802a4c0
.global WB_DONE
.thumb_set WB_DONE, 0x0802a518

.global LENGTH_START_RETURN
.thumb_set LENGTH_START_RETURN, 0x0802a9fc
.global LENGTH_STOP_RETURN
.thumb_set LENGTH_STOP_RETURN, 0x0802736e
.global STOCK_RECORD_STOP
.thumb_set STOCK_RECORD_STOP, 0x0802734c
