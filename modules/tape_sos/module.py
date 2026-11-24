from mgmod.module import Module

MODULE = Module(
    name='tape_sos',
    title='SHIFT + S.O.S.: tape mode or classic TLA feedback; SHIFT + Morph: SRR or warble',
    status='emulated',
    source='tape_sos.S', entry='p7_sos_block',
    requires=['shift_gestures'],
    hooks=[
        (0x080276c4, '0d68dfedbd0a', 'p7_sos_block'),          # per block: S.O.S. edit, retention
        (0x0802a9f8, '0023ed00', 'length_start'),               # native record start, resolved index and head
        (0x0802736a, '33602b60', 'length_stop'),                # native finalization, after REC clears
        (0x080291d8, '9a4c9b4d', 'wa_tape'),                   # branch A write block: tape head
        (0x0802a4bc, '6b4c6c4d', 'wb_tape'),                   # branch B write block
        (0x08027984, '0fee907afaeecafa', 'p10_morph_cap'),     # per block: SRR amount, Morph cap
        (0x08028e7a, '38ee424a79eee13a', 'p11_mix_a'),         # per sample, branch A: SRR + mix
        (0x0802a148, '7deee30a7cee438a', 'p12_mix_b'),         # per sample, branch B
        (0x08024af8, 'be49d1ed006a', 'led_rate'),              # Varispeed LED: clean target while warbling
    ],
    mod_bytes=[(16, 91), (94, 127), (132, 135), (144, 207), (232, 234), (236, 239)],
    ram=[(0x2002A100, 0x2002A5FF),                             # engine copied to SRAM
         (0x2002A700, 0x2002A73F)],                            # warble at +0..31, optional replacement at +32..51
    options_keys=['tape', 'fxsl', 'mcap'],
    gestures=['SHIFT+S.O.S.', 'SHIFT+Morph'],
)
