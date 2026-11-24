# Every module. Each feature is switched in options.txt (tape, octl, scal, fxsl,
# mcap, sldm, cpul, ingn, mono), so one image covers every combination.
REMIX = dict(
    title='mg204+c6 — stock Gene timing recall',
    description='Set dens 1 and dstr 0 to recall stock timing at startup and on settings-only reload. Omit dstr for a 1 Gene/sec startup rate and preserve live timing on reload. Includes three S.O.S. recording curves, mixed monitoring in dryk 0, and wet-only monitoring in dryk 1–3. First takes on empty reels always capture full input.',
    modules=['record_start_splice', 'shift_gestures', 'tape_sos', 'sd_updater', 'options_keys', 'gene_shape',
             'cpu_meter', 'mono_in', 'settings_reload', 'morph_loop', 'dry_monitor'],
    sha256='4596b236d5a0b82e56aaba6c6c4ed2204677b2224362356e2a1369cd681e7ab4',
)
