"""Keep the current performance playing during the D22 bank selector."""
from mgmod.module import Module

MODULE = Module(
    name='picker_playback',
    title='Continue current playback while choosing a bank, reel and splice',
    status='on hardware',
    source='playback.S', entry='picker_active',
    requires=['bank_selector'],
    replaces_hooks={
        0x080276f0: 'gene_shape',
    },
    hooks=[
        (0x08023cfc, '2e68d699', 'picker_transfer_mode'),
        (0x08024854, 'b9f1010f', 'picker_play_gate'),
        (0x08025246, 'a3490123', 'picker_transfer_abort'),
        (0x0802759e, 'dff8e4e0', 'picker_audio_mode'),
        (0x08052c86, '60490968', 'picker_thru_mode'),
        (0x08052d48, '70b50446', 'picker_gene_birth'),
        (0x080276f0, '26f066bc', 'picker_organize'),
        (0x0802782e, 'f1ee10fa', 'picker_idle_resolver'),
        (0x08054050, 'd1f76eb8', 'picker_enter'),
        (0x0805408a, '35491223', 'picker_short'),
        (0x080542ac, '074b1a6e', 'picker_leave'),
        (0x080548fe, '012b02d1', 'picker_wait_for_sd'),
        (0x0805497c, '0723e6e7', 'picker_final_recorded_chord'),
        (0x08054a30, '08231846', 'picker_pending_lights'),
        (0x08054e4e, 'fff701ff', 'picker_timed_commit'),
        (0x08054146, 'cff7dcbc', 'picker_mount'),
    ],
    ram=[(0x20028f8c, 0x20028fa3)],
)
