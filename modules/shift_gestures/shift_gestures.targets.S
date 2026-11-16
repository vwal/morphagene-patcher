@ Absolute Thumb destinations, linked as a separate object so GAS cannot
@ reduce their typed relocations to untyped *ABS* branches (binutils 2.47).
.syntax unified
.cpu cortex-m4
.thumb
.global P1_RETURN
.thumb_set P1_RETURN, 0x0802486e
.global TIM2_DONE
.thumb_set TIM2_DONE, 0x080248fc
.global NAV_STORE
.thumb_set NAV_STORE, 0x080251e0
.global NAV_SKIP
.thumb_set NAV_SKIP, 0x080251e6
.global RATE_NEXT
.thumb_set RATE_NEXT, 0x08027882
.global RATE_FULL
.thumb_set RATE_FULL, 0x08028824
.global GLIDE_NEXT
.thumb_set GLIDE_NEXT, 0x08027be4
.global RANGE_INDEX_NEXT
.thumb_set RANGE_INDEX_NEXT, 0x802aac8
.global RANGE_FORWARD_NEXT
.thumb_set RANGE_FORWARD_NEXT, 0x802aae0
.global RANGE_REVERSE_NEXT
.thumb_set RANGE_REVERSE_NEXT, 0x802ad0a

.global FORWARD_STOCK, FORWARD_DONE
.thumb_set FORWARD_STOCK, 0x080287e5
.thumb_set FORWARD_DONE, 0x080278cd

@ Gene Size <= 199 uses the stock full-splice/reel lookup copies.
.global FORWARD_FULL_STOCK, FORWARD_FULL_DONE
.thumb_set FORWARD_FULL_STOCK, 0x0802abfe
.thumb_set FORWARD_FULL_DONE, 0x08028a6a
.global RANGE_FULL_INDEX_NEXT, RANGE_FULL_FORWARD_NEXT, RANGE_FULL_REVERSE_NEXT
.thumb_set RANGE_FULL_INDEX_NEXT, 0x08028a52
.thumb_set RANGE_FULL_FORWARD_NEXT, 0x08028a6a
.thumb_set RANGE_FULL_REVERSE_NEXT, 0x0802ad80
.global PRESET_VS_INPUT_NEXT
.thumb_set PRESET_VS_INPUT_NEXT, 0x08027562
.global PRESET_VS_CACHE_NEXT, PRESET_VS_DIRECTION_NEXT
.thumb_set PRESET_VS_CACHE_NEXT, 0x08027784
.thumb_set PRESET_VS_DIRECTION_NEXT, 0x080292a8
