"""Rearm SHIFT reload after a recognized card removal."""
from mgmod.module import Module

MODULE = Module(
    name='card_rearm', title='Rearm the settings-only reload after card removal',
    status='on hardware', source='rearm.S', entry='rearm_button_state',
    requires=['bank_files'],
    hooks=[
        (0x08050268, '134b1b6a', 'rearm_button_state'),
        (0x080502ec, '2b6a0e2b', 'rearm_mount_state'),
        (0x08050a1e, 'ac6a002c', 'rearm_parked'),
    ],
)
