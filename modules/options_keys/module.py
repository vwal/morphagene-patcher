from mgmod.module import Module

MODULE = Module(
    name='options_keys',
    title='Mod settings in options.txt (vrng, vqnt, dens, dstr, tape, octl, scal, fxsl, cpul, mcap, sldm, root, tlen, ingn, mono)',
    status='emulated',
    source='options_keys.S', entry='opt_parse',
    requires=['sd_updater'],
    hooks=[
        (0x08023326, '9bf801c0', 'opt_parse'),                 # parser: our keys first
        (0x0802455e, '0df274500ef021f9', 'opt_write'),         # writer: append our section
        (0x08023ee6, '290600f17d81', 'opt_main'),              # main loop, flag 0x80 test: apply/save ingn
    ],
    settings=[4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
    ram=[(0x2002A600, 0x2002A603),                             # ingn: when the pending gain was first seen
         (0x2002A604, 0x2002A607),                            # scal mask, vrng, dens
         (0x2002A610, 0x2002A611), (0x2002A614, 0x2002A617)],                           # vqnt (after mono state)
    options_keys=['ingn', 'scal', 'mlop', 'dstr'],
)
