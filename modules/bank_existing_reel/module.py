"""Select an existing reel during cross-bank confirmation on Development 19."""

from mgmod.module import Module


MODULE = Module(
    name='bank_existing_reel',
    title='Keep Organize on the destination bank’s existing reels',
    status='on hardware',
    source='organize.S',
    entry='bank_reel_candidate',
    requires=['card_presence'],
    hooks=[
        (0x08051de0, '127812b1', 'bank_reel_candidate'),
        (0x080534e2, '2de9f047', 'bank_apply_existing'),
    ],
)
