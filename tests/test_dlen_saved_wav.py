"""Follow a growing take from REC through the stock SD writer and a FAT remount."""
import os
import struct
import unittest

from tests.arm import (Arm, SP, bits, UC_ARM_REG_R6, UC_ARM_REG_R7, UC_ARM_REG_R8,
                       UC_ARM_REG_S16, UC_ARM_REG_SP)
from tests.audio import Audio
from tests.test_firmware_integration import images
from tests.test_reload_filesystem import FatDisk
from tests.test_settings_reload import CARD, CLOSE, FLAGS, FS, LIVE, MOUNT, OPEN, READ, call


REC_REQUEST = 0x20021320
MARKER_ZERO = 0x2002215c
LEFT, RIGHT = 0xd0000000, 0xd1000000


def set_input(audio, left, right):
    audio.uc.mem_write(0x20028000, struct.pack('<16h', *([left, right] * 8)))


def short_replacement(image):
    audio = Audio(image)
    for address in (0x2002208c, 0x20022160, 0x20021fbc, 0x20021c68,
                    0x20021c78, 0x20021c7c, 0x20021c6c, 0x20021de4):
        audio.a.put(address, 0)
    audio.a.put(0x20021c74, 2048)
    audio.a.put(CARD, 1)
    audio.uc.mem_write(0x2002a619, b'\x01\x02\x01')  # vctr, dryk, dlen
    audio.uc.mem_write(0x2002a611, b'\x01')  # mlop
    audio.blocks(200)
    ends = []
    for levels in (((600, -900), (600, -900)), ((-2100, 1200), (-1200, 2400), (-900, 3600))):
        audio.a.put(FLAGS, 0)
        audio.a.put(REC_REQUEST, 1)
        for left, right in levels:
            set_input(audio, left, right)
            audio.blocks(30)  # 240 stereo frames
        audio.a.put(REC_REQUEST, 0)
        audio.blocks(6)
        ends.append(audio.a.get(MARKER_ZERO + 4))
    return audio, ends


def saved_wav(image, recorded, original_end, end, fat32):
    # Model the foreground loop on a mounted card with a handle open for update.
    main = Arm('shift_gestures', 'p1_session')
    mem = main.uc
    mem.mem_write(0x08020000, image)
    mem.mem_write(0x20000000, image[0x27250:0x28400])
    mem.mem_map(RIGHT, 0x20000)
    disk = FatDisk(main, fat32=fat32)
    header = struct.pack('<4sI4s4sIHHIIHH4sI', b'RIFF', 36+8*original_end, b'WAVE',
                         b'fmt ', 16, 3, 2, 48000, 384000, 8, 32, b'data', 8*original_end)
    old_cue = struct.pack('<4sIIII4sIII', b'cue ', 28, 1, 0, original_end,
                          b'data', 0, 0, original_end)
    disk.file(1, b'MG9     WAV', disk.reel_cluster, header + bytes(8*original_end) + old_cue)
    path = 0x20028000
    mem.mem_write(path, b'\0mg9.wav\0')
    main.syms.update(mount=MOUNT, open=OPEN, close=CLOSE, read=READ, save=0x08023cba)
    assert call(main, 'mount', FS, path, 1) == 0
    assert call(main, 'open', LIVE, path+1, 3) == 0
    for plane in (LEFT, RIGHT):
        mem.mem_write(plane, bytes(recorded.uc.mem_read(plane, end*2)))
    for addr in (0x2002208c, MARKER_ZERO, MARKER_ZERO+4, 0x20021314, FLAGS):
        main.put(addr, recorded.a.get(addr))
    for addr, val in {0x20001064: 44, 0x200220fc: LEFT, 0x20022100: RIGHT,
                      0x20022110: 0xd0020000, 0x20001040: 9, 0x200012a0: 1, CARD: 1}.items():
        main.put(addr, val)
    for reg, val in ((UC_ARM_REG_R6, 1), (UC_ARM_REG_R7, FLAGS), (UC_ARM_REG_R8, 0x200012a0),
                     (UC_ARM_REG_S16, bits(1/32768)), (UC_ARM_REG_SP, LIVE-844)):
        mem.reg_write(reg, val)
    # Background rewrite initiated by the actual flags from REC stop.
    assert main.get(FLAGS) & 0x800
    main.run('save', [0x0802300e], count=4_000_000)
    mem.reg_write(UC_ARM_REG_SP, SP)
    mem.mem_write(path, b'\0mg9.wav\0')
    assert call(main, 'close', LIVE) == 0
    assert call(main, 'mount', 0, path, 0) == 0
    assert call(main, 'mount', FS, path, 1) == 0
    assert call(main, 'open', LIVE, path+1, 1) == 0
    assert call(main, 'read', LIVE, 0xd0010000, end*8+512, 0x20027000) == 0
    return bytes(mem.mem_read(0xd0010000, main.get(0x20027000)))


@unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'), 'requires official mg204')
class SavedLength(unittest.TestCase):
    def test_growing_recording_updates_stereo_wav_and_embedded_splice_after_remount(self):
        image = images()[1]
        recorded, (old_end, end) = short_replacement(image)
        self.assertIn(old_end, range(480, 483))
        self.assertIn(end, range(720, 723))
        self.assertEqual(recorded.a.get(0x2002208c), 1)
        buffers = [struct.unpack(f'<{end}h', recorded.uc.mem_read(plane, 2*end))
                   for plane in (LEFT, RIGHT)]
        self.assertTrue(all(x < 0 for x in buffers[0]))
        self.assertTrue(all(x > 0 for x in buffers[1]))
        for i, stereo in enumerate(((-3150, 1800), (-1800, 3600), (-1350, 5400))):
            for channel, level in zip(buffers, stereo):
                self.assertAlmostEqual(channel[120 + i*240], level, delta=1)
        for fat32 in (False, True):
            with self.subTest(fat32=fat32):
                wav = saved_wav(image, recorded, old_end, end, fat32)
                self.assertEqual(struct.unpack_from('<I', wav, 40)[0], end*8)
                payload = struct.unpack_from(f'<{2*end}f', wav, 44)
                self.assertEqual(payload, tuple(x/32768 for frame in zip(*buffers) for x in frame))
                self.assertEqual(struct.unpack_from('<4sIIII4sIII', wav, 44+end*8),
                                 (b'cue ', 28, 1, 0, end, b'data', 0, 0, end))

    def test_performance_overdub_survives_card_remount_with_original_marker(self):
        image = images()[1]
        audio, (_, end) = short_replacement(image)
        original = [bytes(audio.uc.mem_read(plane, 2*end)) for plane in (LEFT, RIGHT)]
        audio.uc.mem_write(0x2002a61a, bytes([3]))  # live change after the mode-2 take
        audio.a.put(0x20021c68, 4095)  # include full Gene playback in the recording
        audio.a.put(0x20021c74, 600)   # reverse playback
        audio.a.put(0x20021c7c, 3000)
        set_input(audio, 0, 0)
        audio.blocks(64)
        audio.a.put(FLAGS, 0)
        audio.a.put(REC_REQUEST, 1)
        audio.blocks(55)
        audio.a.put(REC_REQUEST, 0)
        audio.blocks(6)

        self.assertEqual(audio.a.get(MARKER_ZERO+4), end)
        after = [bytes(audio.uc.mem_read(plane, 2*end)) for plane in (LEFT, RIGHT)]
        for old, captured in zip(original, after):
            old_samples = struct.unpack(f'<{end}h', old)
            new_samples = struct.unpack(f'<{end}h', captured)
            self.assertTrue(any(new and new != prior for new, prior in zip(new_samples, old_samples)))
        channels = [struct.unpack(f'<{end}h', channel) for channel in after]
        expected = tuple(x/32768 for frame in zip(*channels) for x in frame)
        for fat32 in (False, True):
            with self.subTest(fat32=fat32):
                wav = saved_wav(image, audio, end, end, fat32)
                self.assertEqual(struct.unpack_from('<I', wav, 40)[0], end*8)
                self.assertEqual(struct.unpack_from(f'<{2*end}f', wav, 44), expected)
                self.assertEqual(struct.unpack_from('<4sIIII4sIII', wav, 44+end*8),
                                 (b'cue ', 28, 1, 0, end, b'data', 0, 0, end))
