"""Quiet mounted-card check for cached reels on the exact D18 application."""

from mgmod.module import Module

MODULE = Module(
    name='card_presence',
    title='Confirm idle card removal with bounded SD status commands',
    status='on hardware',
    source='presence.S',
    entry='presence_idle',
    requires=['recorded_banks'],
    hooks=[
        (0x0804fcd4, '13f6eeac', 'presence_idle'),       # D18 larger-WAV branch
        (0x0802ce88, '30bc7047', 'presence_activity'),   # native SDIO_SendCommand return
        (0x08022fd0, '04f53b3e', 'presence_elapsed'),    # regular idle check across tick wrap
    ],
    ram=[(0x20028f40, 0x20028f57)],
)
