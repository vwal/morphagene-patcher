from mgmod.module import Module
# Application at the audio boundary is integrated with settings_reload.
MODULE = Module(name='morph_loop', title='Switchable seamless Morph loop (mlop 1)',
    status='emulated', requires=['settings_reload'],
    ram=[(0x2002A612,0x2002A612)])
