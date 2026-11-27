"""Bank-folder selection and explicit New Reel confirmation on the D20 base."""
from mgmod.module import Module

MODULE = Module(
    name='bank_selector',
    title='Choose a bank, open a recorded splice or confirm a new reel',
    status='on hardware',
    source='selector.S',
    entry='menu_dispatch',
    requires=['bank_existing_reel'],
    replaces_hooks={
        0x08051c22: 'recorded_banks',
        0x080286b0: 'recorded_banks',
        0x080249c6: 'reel_banks',
        0x08023094: 'bank_files',
    },
    hooks=[
        (0x0802486e, 'd9f80010', 'menu_dispatch'),
        (0x0802526e, '92491223', 'menu_short_release'),
        (0x0802550e, 'dff840a1', 'menu_short_confirm'),
        (0x08025532, '13600023', 'selector_accepted_chord'),
        (0x08051c22, '01f0edb9', 'menu_hold'),
        (0x08051cec, '5148012e', 'menu_foreground'),
        (0x080286b0, '2af051bd', 'menu_organize'),
        (0x080249c6, '2df06db9', 'menu_led'),
        (0x08051d28, '8160c160', 'menu_mount'),
        (0x0802323a, '18680968', 'selector_pin_cursor'),
        (0x08023094, '2ff0c1b9', 'selector_manual_open_mode'),
        (0x080230a2, 'd3a81693', 'selector_prepare_manual'),
        (0x080230da, '0022d3a8', 'selector_bad_format'),
        (0x08023b0e, 'dde91843', 'selector_valid_data'),
        (0x08023114, '04f0d8f9', 'selector_parsed'),
        (0x08023886, '03f01ffe', 'selector_transferred'),
    ],
    ram=[(0x20028f58, 0x20028f7f), (0x20028f80, 0x20028f8b)],
)
