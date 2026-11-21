# Every module. Each feature is switched in options.txt (tape, octl, scal, fxsl,
# mcap, sldm, cpul, ingn, mono), so one image covers every combination.
REMIX = dict(
    title='mg204+c2 — unity recall and complete presets',
    description='mg204+c2: optional SHIFT hold/release return to exact forward +1x, unity at noon, and complete preset recall with soft pickup. Includes all original mg204+c features, selectable Morph Loop, independent density, expanded Varispeed and trusted-card settings reload. Built on Briskcat’s Morphagene mods.',
    modules=['record_start_splice', 'shift_gestures', 'tape_sos', 'sd_updater', 'options_keys', 'gene_shape',
             'cpu_meter', 'mono_in', 'settings_reload', 'morph_loop'],
    sha256='587b3721479b719aa258418bb9a30a5c07ae765aaa2fe97c4b0d1c6a89fcdcf4',
)
