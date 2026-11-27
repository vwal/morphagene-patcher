    .syntax unified
    .cpu cortex-m4
    .thumb
    .global D18_SMALL_WAV, MEDIA_OK, MEDIA_LOST, NATIVE_DUE_BRANCH
    .thumb_set D18_SMALL_WAV, 0x0804fcd8
    .thumb_set MEDIA_OK, 0x080236b4
    .thumb_set MEDIA_LOST, 0x08023808
    .thumb_set NATIVE_DUE_BRANCH, 0x08022fda
