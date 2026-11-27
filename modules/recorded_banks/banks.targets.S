.syntax unified
.cpu cortex-m4
.thumb
.global HOLD_WAIT, HOLD_RELEASED, D15_MAIN_DONE
.global D15_LED_SHOW, D15_LED_COOLDOWN, D15_LED_DONE
.global ORGANIZE_READ, ORGANIZE_UNMOVED, CONFIRM_RETURN
.thumb_set HOLD_WAIT,         0x080248fc
.thumb_set HOLD_RELEASED,     0x0802526e
.thumb_set D15_MAIN_DONE,     0x08051d0e
.thumb_set D15_LED_SHOW,     0x08051ccc
.thumb_set D15_LED_COOLDOWN, 0x08051cb8
.thumb_set D15_LED_DONE,     0x08051cda
.thumb_set ORGANIZE_READ,     0x080286b6
.thumb_set ORGANIZE_UNMOVED,  0x0802887a
.thumb_set CONFIRM_RETURN,    0x08025532
