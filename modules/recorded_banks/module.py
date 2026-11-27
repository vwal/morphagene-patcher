"""Panel-only bank selection overlay for the exact Development 17 application."""

from mgmod.module import Module

MODULE = Module(
    name='recorded_banks',
    title='Inventory recorded reel files for the bank controls',
    status='on hardware',
    source='banks.S',
    entry='rb_hold_active',
    requires=['playback'],
    hooks=[
        (0x08051c22, '20688849', 'rb_hold_active'),  # after all D15 bank-enable checks
        (0x08051d04, '00224273', 'rb_pending'),      # existing nonzero bank request only
        (0x08051cb0, '177b5fb9', 'rb_led_pending'),  # active bank UI, after bank magic check
        (0x080286b0, '082e40f3e280', 'rb_organize'),
        (0x08051e20, '03b40449', 'rb_confirm'),
    ],
    ram=[(0x20028f30, 0x20028f3c)],
)
