"""Extend D23's two options readers and its native FatFs writer with audt."""
from mgmod.module import Module

MODULE = Module(
    name='audition_option', title='Bank picker audition option',
    status='on hardware', source='options.S', entry='audt_mount_default',
    requires=['picker_playback'],
    hooks=[
        (0x08023290, '94480168', 'audt_mount_default'),
        (0x0804bc10, '01f0eaf8', 'audt_normal_line'),
        (0x0804d0b6, 'd8f844a0', 'audt_write'),
        (0x08050430, '824b9842', 'audt_live_line'),
        (0x08050b0c, 'c5f8e830', 'audt_live_begin'),
        (0x08050bb8, 'd3f8e830', 'audt_live_seen'),
        (0x08050eb8, 'fff794f8', 'audt_live_commit'),
    ],
    ram=[(0x20028fa4, 0x20028fa5)], options_keys=['audt'],
)
