# Every module. Each feature is switched in options.txt (tape, octl, scal, fxsl,
# mcap, sldm, cpul, ingn, mono), so one image covers every combination.
REMIX = dict(
    title='mg204+c3 — Varispeed settings fix',
    description='Keeps the selected Varispeed layout across card mounts and power cycles. Includes return to 1:1, complete presets, independent Gene density, expanded Varispeed, switchable Morph Loop and live settings reload. Built on Briskcat’s Morphagene mods.',
    modules=['record_start_splice', 'shift_gestures', 'tape_sos', 'sd_updater', 'options_keys', 'gene_shape',
             'cpu_meter', 'mono_in', 'settings_reload', 'morph_loop'],
    sha256='6fa86c9c4af564f75fa724780cfb504d95db8a562f3d88071ea84344552bceed',
)
