# Full public release. Later modules wrap specific hooks in their prerequisites.
REMIX = dict(
    title='mg204+c7 — reel banks and splice play-through',
    description='Browse up to eight reel banks, audition recorded splices, and switch at a Gene boundary or immediately. Add forward or reverse unity notches and let Organize advance splices in order or follow playback direction.',
    modules=['record_start_splice', 'shift_gestures', 'tape_sos', 'sd_updater', 'options_keys',
             'gene_shape', 'cpu_meter', 'mono_in', 'settings_reload', 'morph_loop', 'dry_monitor',
             'splice_thru', 'reel_banks', 'bank_files', 'card_rearm', 'playback', 'recorded_banks',
             'card_presence', 'bank_existing_reel', 'bank_selector', 'picker_playback',
             'audition_option', 'picker_audition'],
    fixed_layout=True,  # later hooks call compiled entry points in earlier modules
    sha256='6947fd4ef33b750a1dd9ad6afa6f8a781543b937e1b5c9ca2188f2f973b887e1',
)
