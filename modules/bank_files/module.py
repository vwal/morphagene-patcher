from mgmod.module import Module

MODULE = Module(
    name='bank_files',
    title='Protect banked WAVs during reel creation and loading',
    status='on hardware', source='bank_files.S', entry='bank_header',
    requires=['reel_banks'],
    hooks=[
        (0x0802307c, '28600860', 'bank_request_new'),
        (0x08023250, '8842fff65faf', 'bank_request_existing'),
        (0x08023094, '21a91322', 'bank_select_mode'),
        (0x080231da, '0028f0d0', 'bank_free_result'),
        (0x080231f2, '1322d3a8', 'bank_create_mode'),
        (0x08023718, '21a91322', 'bank_boot_mode'),
        (0x0802309e, '63230021', 'bank_select_result'),
        (0x080231fc, 'd3a8fef79ffc', 'bank_create_result'),
        (0x08023722, '63262146', 'bank_boot_result'),
        (0x08021b40, '30b58db0', 'bank_header'),
    ],
)
