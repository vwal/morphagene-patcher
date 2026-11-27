from mgmod.module import Module

MODULE = Module(
    name='reel_banks',
    title='Optional reel banks at the root and in bank2 through bank8',
    status='on hardware',
    source='reel_banks.S', entry='rb_name',
    requires=['sd_updater', 'options_keys', 'settings_reload'],
    hooks=[
        (0x08021f74, 'f0b48ab0', 'rb_name'),
        (0x08022060, 'f0b48ab0', 'rb_splice'),
        (0x0802329c, 'd8f80060', 'rb_defer'),
        (0x080236d2, '3a68594842f08003', 'rb_boot'),
        (0x08025266, '019a002a7ff447ab', 'rb_hold'),
        (0x080249c6, '2b4a1768012f', 'rb_led'),
        (0x08022fbc, '012e3d68e9d1', 'rb_main'),
        (0x08023018, '01263446', 'rb_maintenance'),
        (0x08023778, '01252c46', 'rb_after_create'),
        (0x080222f0, '70b598b0', 'rb_delete_hook'),
        (0x0802434e, 'fdf7cfff', 'rb_checked_delete'),
        (0x0802306c, 'd8f800608642', 'rb_new_limit'),
        (0x08028702, '874200f0c380', 'rb_browse_limit'),
        (0x08023152, 'd8f80050012d', 'rb_first_free'),
        (0x0802ad54, '364c2668', 'rb_preview'),
        (0x0802552e, '43f48053', 'rb_confirm'),
    ],
    ram=[(0x20028f00, 0x20028f2f)],
    gestures=['SPLICE+REC hold'],
)
