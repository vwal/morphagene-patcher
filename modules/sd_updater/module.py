from mgmod.module import Module

MODULE = Module(
    name='sd_updater',
    title='Firmware updates from mgmod.bin on the SD card',
    status='emulated',
    source='sd_updater.S', entry='upd_hook', defsyms=[('DIAG', 0)],
    patches=[(0x08021454, 'c8430220', '00b80220')],          # reset: clear through the mod arena, before IRQs
    hooks=[(0x08023288, '01460320', 'upd_hook')],              # after the startup card mount
    settings=[0, 1, 2, 3],                                     # "OPTS" magic; also writes the key defaults
    ram=[(0x2002B000, 0x2002B7FF)],                            # FatFs objects and the RAM flasher
)
