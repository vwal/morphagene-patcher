from mgmod.module import Module

MODULE = Module(
    name='settings_reload',
    title='Hold SHIFT before card insertion: reload settings and reconnect the live reel without restarting playback',
    status='emulated', source='settings_reload.S', entry='reload_mount',
    requires=['shift_gestures', 'sd_updater', 'options_keys'],
    hooks=[
        (0x0802312a, '012221490df29c70', 'reload_mount'),
        (0x08023136, '002800f0a680', 'reload_mount_done'),
        (0x080236ae, '002840f0aa80', 'reload_idle_media'),
        (0x08022f7e, 'eeb9049a', 'reload_main'),
        (0x0802484e, '7d4ed6f80090', 'reload_buttons'),
        (0x0802493e, '354823fa01f2', 'reload_led'),
        (0x08027518, '2de9f04f', 'reload_audio'),
        (0x08031124, '2de9f04f', 'reload_write'),
        (0x08032260, '2de9f043', 'reload_open'),
    ],
    ram=[(0x2002A820, 0x2002AFFF)],
    gestures=['SHIFT held for 1 second before SD insertion'],
)
