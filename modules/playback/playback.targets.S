@ Stock Thumb destinations used by the audio and EOSG hooks.
.syntax unified
.cpu cortex-m4
.thumb
.global MAP_RETURN, EOS_RETURN
.thumb_set MAP_RETURN, 0x080277d2
.thumb_set EOS_RETURN, 0x08024d32

.global BIRTH_A_RETURN, BIRTH_B_RETURN
.thumb_set BIRTH_A_RETURN, 0x0802a8d4
.thumb_set BIRTH_B_RETURN, 0x0802a8aa

.global PICKUP_LAYOUT_RETURN
.thumb_set PICKUP_LAYOUT_RETURN, 0x0804ede0
