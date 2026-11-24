# Every module. Each feature is switched in options.txt (tape, octl, scal, fxsl,
# mcap, sldm, cpul, ingn, mono), so one image covers every combination.
REMIX = dict(
    title='mg204+c5 — performance overdubs and Gene timing',
    description='SHIFT + Gene Size fully CCW selects stock timing. Includes three S.O.S. recording curves, mixed monitoring in dryk 0, and wet-only monitoring in dryk 1–3. First takes on empty reels always capture full input.',
    modules=['record_start_splice', 'shift_gestures', 'tape_sos', 'sd_updater', 'options_keys', 'gene_shape',
             'cpu_meter', 'mono_in', 'settings_reload', 'morph_loop', 'dry_monitor'],
    sha256='f6ce230987d415901f07f18984cc879440323e3ad4290149caccae5bd6e0fc5a',
)
