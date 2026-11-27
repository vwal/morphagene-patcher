/* D18's mounted, quiet foreground is the only caller. FAT I/O is serialized
 * there. Audio and panel interrupts stay enabled throughout. */
#include <stdint.h>

#define WORD(address) (*(volatile uint32_t *)(address))
#define U16(address) (*(volatile uint16_t *)(address))
#define TICKS WORD(0x20021c88)
#define VOLUME_ID U16(0x20024278)
#define RCA WORD(0x200242a4)
#define SD(offset) WORD(0x40012c00u + (offset))

enum {
    POWER = 0x00, CLKCR = 0x04, ARG = 0x08, CMD = 0x0c, RESPCMD = 0x10,
    RESP1 = 0x14, DCOUNT = 0x30, STA = 0x34, ICR = 0x38, MASK = 0x3c,
    CRC_FAIL = 0x01, CMD_TIMEOUT = 0x04, RESPONSE = 0x40, CMD_SENT = 0x80,
    TERMINAL = CRC_FAIL | CMD_TIMEOUT | RESPONSE | CMD_SENT,
    CPSMEN = 1u << 10, CMD_ACTIVE = 1u << 11, DATA_ACTIVE = 3u << 12,
    SEND_STATUS = 13, SHORT_RESPONSE = 0x40,
    PERIOD = 192000, POLL_LIMIT = 1024, STOP_LIMIT = 32,
};

/* First two words also used by the native SDIO command telemetry in presence.S.
 * The application reset clears this mod RAM. The generation binds qualification
 * and both negative results to one completed FatFs mount. */
typedef struct {
    uint32_t commands, activity_at, seen_commands, attempted_at;
    uint16_t volume;
    uint8_t initialized, attempted, qualified, missed;
} Presence;
#define STATE ((volatile Presence *)0x20028f40)
_Static_assert(sizeof(Presence) == 24, "presence RAM ledger mismatch");

static int idle(void) {
    uint32_t phase = WORD(0x2002a820);
    return WORD(0x20001290) == 1 && !WORD(0x20022108) && !WORD(0x20021320)
        && !(WORD(0x20022074) & ~0x80u) && (phase == 0 || phase == 5)
        && !WORD(0x2002a82c) && !WORD(0x2002a910);
}

enum Reply { INDETERMINATE, READY, NO_RESPONSE };

static enum Reply status_command(void) {
    uint32_t address = RCA;
    if (!address || address > 0xffffu)
        return INDETERMINATE;
    if ((SD(POWER) & 3u) != 3u || !(SD(CLKCR) & 0x100u))
        return INDETERMINATE;

    uint32_t old_command = SD(CMD), old_argument = SD(ARG);
    /* CMD55 makes the following command application-specific. SDIO memory
     * operations use the ordinary command mode. Defer to the native driver
     * whenever it has a pending flag, enabled command IRQ, or active transfer. */
    if ((old_command & 0x3fu) == 55u || (old_command & ~(0xffu | CPSMEN))
        || (SD(MASK) & (TERMINAL | CMD_ACTIVE)) || SD(DCOUNT)
        || (SD(STA) & (TERMINAL | CMD_ACTIVE | DATA_ACTIVE)))
        return INDETERMINATE;

    /* The command/argument match the native SEND_STATUS at 0x080350e4.
     * Its flag wait has no software bound. RM0090 specifies a hardware
     * response timeout of 64 SDIO clocks; an independent iteration cap also
     * ends this optional check if the peripheral never supplies a flag. */
    SD(ARG) = address << 16;
    SD(CMD) = CPSMEN | SHORT_RESPONSE | SEND_STATUS;
    uint32_t status = 0;
    for (unsigned i = 0; i < POLL_LIMIT; ++i) {
        status = SD(STA);
        if (status & TERMINAL)
            break;
    }
    uint32_t terminal = status & TERMINAL;
    enum Reply reply = INDETERMINATE;
    if (terminal == RESPONSE && (SD(RESPCMD) & 0x3fu) == SEND_STATUS) {
        /* The native R1 error mask at 0x08035300, plus READY_FOR_DATA
         * and CURRENT_STATE=TRANSFER. A busy or error reply cannot qualify. */
        if ((SD(RESP1) & (0xfdffe008u | 0x1f00u)) == 0x0900u)
            reply = READY;
    } else if (terminal == CMD_TIMEOUT) {
        reply = NO_RESPONSE;
    }

    /* Disable the CPSM even on software expiry. Restoring the old enable bit
     * could send the previous command again. The next native command always
     * programs its own argument and CPSMEN. Clear only flags generated here. */
    SD(CMD) = old_command & ~CPSMEN;
    __asm volatile ("dsb" ::: "memory");
    for (unsigned i = 0; i < STOP_LIMIT; ++i) {
        status = SD(STA);
        if (!(status & CMD_ACTIVE))
            break;
    }
    SD(ARG) = old_argument;
    if (status & TERMINAL)
        SD(ICR) = status & TERMINAL;
    if (status & CMD_ACTIVE)
        return INDETERMINATE;
    return reply;
}

int presence_missing(void) {
    uint32_t now = TICKS, commands = STATE->commands;
    uint16_t volume = VOLUME_ID;
    if (!STATE->initialized || STATE->volume != volume) {
        STATE->initialized = 1;
        STATE->volume = volume;
        STATE->attempted = STATE->qualified = STATE->missed = 0;
    }
    if (STATE->seen_commands != commands) {
        STATE->seen_commands = commands;
        STATE->missed = 0;
    }
    if (!idle()) {
        STATE->missed = 0;
        return 0;
    }
    /* Unsigned time differences also separate votes across counter rollover.
     * A recently used bus needs no probe. Once qualified, use every second
     * quiet interval, except for a confirming check after a hardware timeout. */
    uint32_t gap = (STATE->qualified && !STATE->missed) ? 2u * PERIOD : PERIOD;
    if ((uint32_t)(now - STATE->activity_at) < PERIOD ||
        (STATE->attempted && (uint32_t)(now - STATE->attempted_at) < gap))
        return 0;
    STATE->attempted = 1;
    STATE->attempted_at = now;
    enum Reply reply = status_command();
    if (reply == READY)
        STATE->qualified = 1;
    if (reply != NO_RESPONSE || !STATE->qualified || !idle()
        || VOLUME_ID != volume || STATE->commands != commands) {
        STATE->missed = 0;
        return 0;
    }
    if (!STATE->missed) {
        STATE->missed = 1;
        return 0;
    }
    STATE->qualified = STATE->missed = 0;
    return 1;
}
