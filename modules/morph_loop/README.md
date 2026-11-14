# Switchable Morph Loop

Full always includes this feature; `mlop 0` is the default. Upstream implemented
it as five fixed initialized-data edits and therefore offered a separate build.
Our supplied upstream mgmod.bin matches a local build of that source exactly.

The flash tables now remain stock. `options_keys` owns byte 0x2002A611 (mlop),
reset to zero by sd_updater. Byte 0x2002A612 records the applied state and is
zeroed by the reset arena clear. `settings_reload` integrates application into
its existing audio-entry hook: if pending settings or mlop/applied differ, call
reload_commit. The C helper updates all five RAM table words under a short
PRIMASK-preserving lock, before audio processing. No SD access or allocation
occurs there. Ordinary boot parsing is picked up at the next audio boundary;
live reload applies the option and tables in the same commit.

| RAM word | mlop 0 | mlop 1 |
|---|---|---|
| 0x200003e0 | float 2 | float 1 |
| 0x200003e4 | float 1.5 | float 1 |
| 0x200003e8 | 0x3faaaaa8 | float 1 |
| 0x200004f4 | integer 2 | integer 1 |
| 0x200004f8 | integer 3 | integer 1 |

These are existing stock state, not mod-arena allocations. The ledger claims
the applied-state byte; the integrated settings_reload helper is the sole
writer of the stock tables after initialization. Tests cover parser rejection,
writer/default persistence, toggling, and real audio equivalence against both
previous variants at low/high Morph and both Gene envelope modes.

Clock/recording transitions and physical audio continuity still need hardware
validation. Upstream observed a brief pause when turning down from higher Morph.
