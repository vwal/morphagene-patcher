/* mg204 reel storage. Paths are relative to drive 0. Only the main loop
 * calls FatFs. Audio/TIM2 continue during directory access. */
#include <stdint.h>

#define U32(a) (*(volatile uint32_t *)(a))
#define U8(a) (*(volatile uint8_t *)(a))
#define BANK U8(0x2002a61f)
#define COUNT U32(0x200012a0)
#define CURSOR U32(0x20001040)
#define FLAGS U32(0x20022074)
#define CARD U32(0x20001290)
#define MODE U32(0x20021338)
#define REC U32(0x20022108)
#define REC_REQUEST U32(0x20021320)
#define LOADED_BANK U8(0x20028ff0)
#define LOADED_SLOT U8(0x20028ff1)

typedef int (*Stat)(const char *, void *);
typedef int (*Path)(const char *);
typedef int (*Move)(const char *, const char *);
#define f_stat ((Stat)0x08033129)
#define f_mkdir ((Path)0x080334d5)
#define f_rename ((Move)0x08033849)
#define f_unlink ((Path)0x080333dd)
#define stock_compact ((void (*)(void))0x0802214d)
enum { FR_OK = 0, FR_NO_FILE = 4, FR_DENIED = 7, FR_EXIST = 8, AM_DIR = 0x10 };

unsigned bank_get(void) {
    unsigned bank = BANK;
    return U32(0x2002a0f0) == 0x5354504fu && bank <= 8 ? bank : 0;
}

static char *folder_name(char *p, unsigned bank) {
    *p++ = 'b'; *p++ = 'a'; *p++ = 'n'; *p++ = 'k';
    *p++ = '0' + bank;
    *p = 0;
    return p;
}

static void make_name(char *out, unsigned bank, unsigned reel, int marker) {
    char *p = out;
    if (bank > 1) {
        p = folder_name(p, bank);
        *p++ = '/';
    }
    const char *part = marker ? "splice" : "mg";
    while (*part) *p++ = *part++;
    *p++ = reel <= 9 ? '0' + reel : 'a' + reel - 10;
    part = marker ? ".txt" : ".wav";
    while (*part) *p++ = *part++;
    while (p < out + 32) *p++ = 0;
}

int rb_name(char *out, unsigned slot) {
    make_name(out, bank_get(), slot, 0);
    return 0;
}
int rb_splice(char *out, unsigned slot) {
    make_name(out, bank_get(), slot, 1);
    return 0;
}

/* mg204 FILINFO: attributes at +8, optional long-name pointer at +24.
 * Aligned words accommodate the FAT driver's field accesses. */
static int inspect(const char *path, int want_folder) {
    uint32_t info[8];
    info[6] = 0;
    int error = f_stat(path, info);
    if (!error && (!!(info[2] & AM_DIR) != want_folder)) return FR_DENIED;
    return error;
}

static int open_folder(unsigned bank) {
    if (bank <= 1) return 0;
    char dir[6];
    folder_name(dir, bank);
    int error = inspect(dir, 1);
    if (error != FR_NO_FILE) return error;
    error = f_mkdir(dir);
    return error == FR_EXIST ? inspect(dir, 1) : error;
}

/* Check the whole directory before moving files. Reject orphan sidecars so
 * an interruption between the two FAT renames cannot assign somebody else's
 * markers to a new take. Embedded WAV cues travel with their audio. */
static int catalog(unsigned bank, int protect_open, unsigned *boot_slot) {
    uint32_t wavs = 0, markers = 0;
    char src[32], dst[32], old_marker[32], new_marker[32];
    for (unsigned n = 1; n <= 32; ++n) {
        uint32_t bit = 1u << (n - 1);
        make_name(src, bank, n, 0);
        int wav = inspect(src, 0);
        if (wav != FR_OK && wav != FR_NO_FILE) return -1;
        make_name(src, bank, n, 1);
        int marker = inspect(src, 0);
        if (marker != FR_OK && marker != FR_NO_FILE) return -1;
        if (marker == FR_OK && wav != FR_OK) return -1;
        if (wav == FR_OK) wavs |= bit;
        if (marker == FR_OK) markers |= bit;
    }
    unsigned selected = boot_slot ? *boot_slot : 0;
    unsigned open = protect_open && LOADED_BANK == bank ? LOADED_SLOT : 0;
    if (open >= 1 && open <= 32) {
        uint32_t below = (1u << (open - 1)) - 1;
        if ((wavs & (1u << (open - 1))) && (wavs & below) != below) return -1;
    }
    if (boot_slot) *boot_slot = 1;
    unsigned count = 0;
    for (unsigned n = 1; n <= 32; ++n) {
        uint32_t bit = 1u << (n - 1);
        if (!(wavs & bit)) continue;
        ++count;
        /* If normal mount renumbers the saved file, follow its new slot. */
        if (boot_slot && n == selected) *boot_slot = count;
        if (count == n) continue;
        make_name(src, bank, n, 0);
        make_name(dst, bank, count, 0);
        if (markers & bit) {
            make_name(old_marker, bank, n, 1);
            make_name(new_marker, bank, count, 1);
            if (f_rename(old_marker, new_marker)) return -1;
        }
        if (f_rename(src, dst)) {
            if (markers & bit) (void)f_rename(new_marker, old_marker);
            return -1;
        }
    }
    return (int)count;
}

int rb_boot_catalog(void) {
    unsigned bank = bank_get();
    if (!bank) {
        stock_compact();
        return (int)COUNT;
    }
    if (open_folder(bank)) return -1;
    unsigned selected = CURSOR;
    int count = catalog(bank, 0, &selected);
    if (count >= 0) {
        COUNT = (unsigned)count;
        CURSOR = selected;
    }
    return count;
}

int rb_recount(unsigned bank) { return catalog(bank, 1, 0); }

int rb_delete(unsigned slot) {
    unsigned bank = bank_get();
    if (!bank || slot < 1 || slot > COUNT || slot > 32) return (int)COUNT;
    char wav[32], marker[32];
    make_name(wav, bank, slot, 0);
    make_name(marker, bank, slot, 1);
    int present = inspect(marker, 0);
    if (present != FR_OK && present != FR_NO_FILE) return -1;
    /* Start with the WAV. If media disappears before marker removal, the
     * orphan remains detectable and blocks subsequent re-use of this slot. */
    if (f_unlink(wav)) return -1;
    if (present == FR_OK && f_unlink(marker)) return -1;
    int count = catalog(bank, 0, 0); /* stock closed the live file before delete */
    if (count >= 0) COUNT = (unsigned)count;
    return count;
}

static int browse_allowed(void) {
    return CARD == 1 && MODE == 1 && !REC && !REC_REQUEST && !(FLAGS & ~0x80u);
}

/* Called only on release. Recheck after FatFs I/O and publish browse state
 * together so the panel cannot observe indices from two different banks. */
void rb_apply(unsigned target) {
    unsigned bank = bank_get();
    if (!bank || !target || target > 8 || target == bank || !browse_allowed()) return;
    if (open_folder(target)) return;
    int count = catalog(target, 1, 0);
    if (count < 0) return;
    uint32_t saved;
    __asm__ volatile ("mrs %0, primask\n cpsid i" : "=r"(saved) :: "memory");
    if (browse_allowed() && bank_get() == bank) {
        COUNT = (unsigned)count;
        CURSOR = count ? 1 : 1000;
        U32(0x200220ac) = (uint32_t)-100000;
        U8(0x20028f0e) = 1; /* Organize browses until SPLICE + REC confirms. */
        BANK = target;
        FLAGS |= 0x80u;
    }
    __asm__ volatile ("msr primask, %0" :: "r"(saved) : "memory");
}
