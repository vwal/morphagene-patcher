/* Primary mix recall is independent of SHIFT+S.O.S. feedback. */
unsigned preset_sos(unsigned effective) {
    return preset_control(PRESET_SOS, PRESET_U32(0x20021c68), effective);
}
