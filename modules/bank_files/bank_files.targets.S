.syntax unified
.cpu cortex-m4
.thumb
.macro target name, address
    .global \name
    .thumb_set \name, \address
.endm
target SELECT,         0x08023080
target NO_SELECTION,   0x08023114
target SELECT_OPEN,    0x08023098
target SELECT_READY,   0x080230a2
target TRY_NEXT,       0x080231c0
target FREE_SLOT,      0x080231de
target NEW_OPEN,       0x080231f6
target NEW_READY,      0x08023202
target BOOT_OPEN,      0x0802371c
target BOOT_READY,     0x08023726
target HEADER,         0x08021b40
target HEADER_BODY,    0x08021b44
target CLOSE_UNMOUNT,  0x08023808
target UNMOUNT,        0x0802380e
