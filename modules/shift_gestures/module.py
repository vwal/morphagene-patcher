from mgmod.module import Module

MODULE = Module(
    name='shift_gestures',
    title='Optional +/-4x or forward 8x range; default or SHIFT Varispeed quantization (octaves, fifths, semitones, custom)',
    status='emulated',
    source='shift_gestures.S', entry='p1_session',
    hooks=[
        (0x0802755e, 'c1683c48', 'preset_vs_input'),
        (0x08027780, '64366434', 'preset_vs_cache'),
        (0x080292a4, 'fc686648', 'preset_vs_direction'),
        (0x080287e0, "dfed7aba", "forward_lookup"),
        (0x0802abfa, '9fed338a', 'forward_lookup_full'),
        (0x0802aac4, '774f2097', 'range_index'),
        (0x0802aadc, 'dbf80060', 'range_forward'),
        (0x0802ad06, 'd1ed00fa', 'range_reverse'),
        (0x08028a4e, 'c24f2097', 'range_index_full'),
        (0x08028a66, '1d683d60', 'range_forward_full'),
        (0x0802ad7c, 'd6ed00ca', 'range_reverse_full'),
        (0x0802486a, 'dff82092', 'p1_session'),      # TIM2: SHIFT session, knob claims
        (0x080251dc, 'b449b54b', 'p3_state14'),      # SHIFT release: no navigation after a gesture
        (0x080255da, '012a7ff48ea9', 'p4_record_tap'),
        (0x0802787c, 'c72840f3d187', 'p5_octave'),   # audio: scale snap while locked
        (0x08027bde, '7c48dfed7c0a', 'p6_glide'),
    ],
    mod_bytes=[(0, 15), (92, 93), (128, 130), (208, 211)],     # +128..+130: Organize snapshot and hold
    ram=[(0x2002A620, 0x2002A65F)],  # Development 6 gesture/pickup state
    options_keys=['octl', 'vrng', 'vqnt', 'vuni', 'vctr'],
    gestures=['SHIFT+Varispeed'],
)
