"""Stream a highlighted WAV splice on the outputs while the D23 reel runs."""
from mgmod.module import Module

MODULE = Module(
    name='picker_audition',
    title='Audition recorded reel and splice choices at their recorded speed',
    status='on hardware',
    source='audition.S', entry='audition_foreground',
    requires=['audition_option'],
    hooks=[
        (0x080540da, '1c480178', 'audition_foreground'),
        (0x0804fdf8, '2de9f04f', 'audition_audio_entry'),
    ],
    ram=[(0x20025000, 0x20027a27), (0x20028fa8, 0x20028fd7)],
)
