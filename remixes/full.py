# Every module. Each feature is switched in options.txt (tape, octl, scal, fxsl,
# mcap, sldm, cpul, ingn, mono), so one image covers every combination.
REMIX = dict(
    title='mg204+c4 — wet-only monitoring and overdubs',
    description='Wet-only stereo output, S.O.S.-controlled overdub feedback and selectable overdub length. Dry kill is off by default.',
    modules=['record_start_splice', 'shift_gestures', 'tape_sos', 'sd_updater', 'options_keys', 'gene_shape',
             'cpu_meter', 'mono_in', 'settings_reload', 'morph_loop', 'dry_monitor'],
    sha256='8ae6bf2aefe8061efdf06d5063d05fb058571d891be076b8b866d3e127e0bb31',
)
