from mgmod.module import Module

MODULE = Module(
    name='dry_monitor',
    title='Wet-only stereo return for dryk 1 and 2',
    status='tested',
    source='dry_monitor.S', entry='monitor_a',
    requires=['tape_sos'],
    hooks=[
        (0x08028ef4, '2b9f3968', 'monitor_a'),
        (0x0802a1c2, '2b980168', 'monitor_b'),
    ],
)
