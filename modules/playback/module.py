"""Install the tested splice scheduler and its preset layout on Development 17."""

from mgmod.module import Module


MODULE = Module(
    name='playback',
    title='Single-pass and direction-aware Organize playback',
    status='on hardware',
    source='playback.S',
    entry='o1_map',
    requires=['card_rearm'],
    replaces_hooks={
        0x080277b0: 'splice_thru',
        0x08024d2a: 'splice_thru',
    },
    hooks=[
        # Replace the two branches into the existing D15 play-through code.
        (0x080277b0, '2af032b8', 'o1_map'),
        (0x08024d2a, '2cf0a6bd', 'e1_eos'),
        # Decide the splice immediately before the next voice reads its bounds.
        (0x0802a8d0, '0b9a239c', 'thru_birth_a'),
        (0x0802a8a6, '089d2399', 'thru_birth_b'),
        # Replace the old (thru == 1) predicate in compiled preset_organize.
        (0x0804edda, '531e5a425a41', 'preset_thru_layout'),
    ],
)
