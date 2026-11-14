# Every module. Each feature is switched in options.txt (tape, octl, scal, fxsl,
# mcap, sldm, cpul, ingn, mono), so one image covers every combination.
REMIX = dict(
    title='mg204+c',
    description='mg204+c: trusted-card reload and switchable Morph loop. settings-only reload plus optional quantized-by-default Varispeed, forward 8x and independent Gene density. Every module: Varispeed scale lock, tape / TLA feedback, SRR, warble, Slide jitter, '
                'Turing mode, mono input, SD-card updates, options.txt settings, always-on flash prefetch and a troubleshooting CPU log.',
    modules=['record_start_splice', 'shift_gestures', 'tape_sos', 'sd_updater', 'options_keys', 'gene_shape',
             'cpu_meter', 'mono_in', 'settings_reload', 'morph_loop'],
    sha256='5c150c24540517af487693c53f5b4e7fa9b9dc5c33147ba6ab801ded60912335',
)
