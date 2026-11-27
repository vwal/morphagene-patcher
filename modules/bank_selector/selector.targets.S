    .syntax unified
    .cpu cortex-m4
    .thumb
    .global TIM_DISPATCH, TIM_DONE, TIM_ENTER_REEL, D18_HOLD_END
    .global D15_MAIN_END, D18_ORGANIZE, SKIP_ORGANIZE
    .global D15_LED_START, D15_LED_END, NATIVE_MOUNT
    .global TIM_SHORT_RELEASE_END, TIM_SHORT_CONFIRM, TIM_CONFIRM_DELAY
    .thumb_set TIM_DISPATCH,   0x08024872
    .thumb_set TIM_DONE,       0x080248fc
    .thumb_set TIM_ENTER_REEL, 0x08025130
    .thumb_set D18_HOLD_END,   0x080530de
    .thumb_set D15_MAIN_END,   0x08051d0e
    .thumb_set D18_ORGANIZE,   0x08053156
    .thumb_set SKIP_ORGANIZE,  0x0802887a
    .thumb_set D15_LED_START,  0x08051ca4
    .thumb_set D15_LED_END,    0x08051cda
    .thumb_set NATIVE_MOUNT,   0x08023b02
    .thumb_set TIM_SHORT_RELEASE_END, 0x08025272
    .thumb_set TIM_SHORT_CONFIRM,     0x08025522
    .thumb_set TIM_CONFIRM_DELAY,     0x08025512
