@ Stock Thumb destinations used by the audio and EOSG hooks.
.syntax unified
.cpu cortex-m4
.thumb
.global MAP_RETURN, EOS_RETURN
.thumb_set MAP_RETURN, 0x080277d2
.thumb_set EOS_RETURN, 0x08024d32
