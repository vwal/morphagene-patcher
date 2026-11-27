# Adapted from Carlos de Paula's splice_thru, under LICENSES/Briskcat-MIT.txt.
from mgmod.module import Module

MODULE = Module(
    name='splice_thru',
    title='Organize fully clockwise plays the reel through, splice after splice (thru)',
    status='on hardware',
    source='splice_thru.S', entry='o1_map',
    requires=['sd_updater', 'options_keys'],
    hooks=[
        (0x080277b0, '9fed8cfa874807ee102a7aeecffaf8eec77a27eeaf0afdeec06a16ee903a01330360', 'o1_map'),
                                                               # audio: Organize -> selected splice
        (0x08024d2a, 'dff82491d9f80020', 'e1_eos'),            # TIM2: end-of-splice trigger
    ],
)
