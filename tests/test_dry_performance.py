"""Compare dryk 3's resampled stereo takes with the ordinary Gene mix on mg204."""
import math
import os
import struct
import unittest

from unicorn import UC_HOOK_CODE

from tests.audio import Audio
from tests.test_dry_monitor import (
    INPUT, INOP, LEFT, MIX_SITES, MORPH, PLANE_BYTES, RIGHT, SOS, TAPE,
    record, set_mode,
)
from tests.test_firmware_integration import images
from tests.test_preset_tape_effects import publish, target
from tests.test_unity_center import boundary, configure, rate


HEAD = 0x2002210C
RECORD_SPLICE = 0x20022114
FRAMES = PLANE_BYTES // 2


def input_stereo(audio, left, right):
    audio.uc.mem_write(INPUT, struct.pack('<hh', left, right) * 8)


def setup_audio(mode, percent):
    audio = Audio(images()[1])
    set_mode(audio, mode)
    audio.a.put(SOS, target(percent))
    if mode == 3:
        # These selections would all change recording outside performance mode.
        audio.uc.mem_write(TAPE, b'\x01')
        audio.a.put(INOP, 1)
        publish(audio.a, {7: 7})
    else:
        # Ordinary inop 0 records the selected primary curve and rendered Genes.
        audio.uc.mem_write(TAPE, b'\x00')
        audio.a.put(INOP, 0)

    # Distinct playback on left and right reveals cross-routing errors.
    left = struct.unpack('<48000h', audio.uc.mem_read(LEFT, PLANE_BYTES))
    audio.uc.mem_write(RIGHT, struct.pack('<48000h', *(-s // 2 for s in left)))
    return audio


def start_take(audio, append):
    record(audio)
    start = FRAMES if append else 0
    audio.a.put(HEAD, start)
    audio.a.put(RECORD_SPLICE, 2 if append else 1)
    return start


def recording(audio, start, frames):
    return tuple(bytes(audio.uc.mem_read(plane + 2*start, 2*frames))
                 for plane in (LEFT, RIGHT))


@unittest.skipUnless(os.environ.get('MGMOD_FIRMWARE'), 'requires official firmware')
class PerformanceRecording(unittest.TestCase):
    def test_half_speed_changes_reel_pitch_and_preserves_first_pass_input_pitch(self):
        audio = Audio(images()[1])
        configure(audio.a, (0, 0, 1, 2), centered=1, enabled=1)
        publish(audio.a, {0: 10, 1: 1, 2: 0, 3: 1, 5: 0})
        set_mode(audio, 3)
        audio.a.put(SOS, target(50))
        audio.uc.mem_write(0x2002a607, bytes(1))  # dens 0

        def tone(hz, frame):
            return round(4500 * math.sin(2 * math.pi * hz * frame / 48000))

        # The source exists only on the left, fresh input only on the right.
        audio.uc.mem_write(LEFT, struct.pack('<48000h', *(tone(880, i) for i in range(FRAMES))))
        audio.uc.mem_write(RIGHT, bytes(PLANE_BYTES))
        adc = boundary(audio, lambda speed: speed >= 0.4999) + 5
        self.assertAlmostEqual(rate(audio, adc, fresh=True), 0.5, places=4)
        audio.blocks(1200)
        start = start_take(audio, append=True)
        for frame in range(0, 8400, 8):
            block = b''.join(struct.pack('<hh', 0, tone(660, i)) for i in range(frame, frame + 8))
            audio.uc.mem_write(INPUT, block)
            audio.blocks(1)
        for raw, expected in zip(recording(audio, start, 8400), (440, 660)):
            pcm = struct.unpack('<8400h', raw)[1200:7600]
            crossings = [i for i in range(1, len(pcm)) if pcm[i-1] <= 0 < pcm[i]]
            self.assertGreater(len(crossings), 2)
            hz = 48000 * (len(crossings)-1) / (crossings[-1]-crossings[0])
            self.assertAlmostEqual(hz, expected, delta=2)

    def test_primary_sos_matches_rendered_feedback_across_its_range(self):
        # The append destination keeps the source intact while each recording
        # path receives the same nonzero input and hears the same Gene output.
        saved = []
        for percent in (0, 50, 100):
            with self.subTest(percent=percent):
                takes = []
                for mode in (1, 3):
                    audio = setup_audio(mode, percent)
                    audio.blocks(180)
                    input_stereo(audio, 1100, -1950)
                    original = recording(audio, 0, FRAMES)
                    start = start_take(audio, append=True)
                    heard = audio.blocks(180)
                    self.assertEqual(audio.a.get(HEAD), start+1440)
                    self.assertEqual(original, recording(audio, 0, FRAMES))
                    takes.append((heard, recording(audio, start, 1440)))
                self.assertEqual(takes[0], takes[1])
                saved.append(takes[1])
        self.assertEqual(saved[0][0], saved[1][0])
        self.assertEqual(saved[1][0], saved[2][0])
        # Each S.O.S. setting changes both recorded channels while the wet
        # monitor still carries the same playback at the same level.
        for channel in (0, 1):
            self.assertEqual(len({take[1][channel] for take in saved}), 3)

    def test_each_panel_control_is_printed_into_existing_splice(self):
        # Run identical physical performances in dryk 3 and the ordinary Gene mix and
        # compare the actual recorded samples, rather than the monitor alone.
        controls = ((MORPH, 3900), (0x20021c74, 1550),  # Varispeed
                    (0x20021c78, 2800), (0x20021c7c, 3890))  # Slide, Gene Size
        for control in (None, *controls):
            with self.subTest(control=control):
                takes = []
                for mode in (1, 3):
                    audio = setup_audio(mode, 65)
                    audio.blocks(200)
                    input_stereo(audio, 800, -1700)
                    start_take(audio, append=False)
                    audio.blocks(65)
                    if control is not None:
                        audio.a.put(*control)
                    heard = audio.blocks(480)
                    self.assertEqual(audio.a.get(HEAD), 8*(65+480))
                    takes.append((heard, recording(audio, 0, 8*(65+480))))
                self.assertEqual(takes[0], takes[1])
                if control is None:
                    stationary = takes[1][1]
                else:
                    for reference, performed in zip(stationary, takes[1][1]):
                        self.assertNotEqual(reference, performed)

    def test_empty_first_capture_uses_fresh_stereo_input_at_every_setting(self):
        for percent in (0, 50, 100):
            with self.subTest(percent=percent):
                audio = Audio(images()[1])
                set_mode(audio, 3)
                audio.a.put(0x2002a000, 0)  # first audio block before first SHIFT timer tick
                audio.a.put(0x2002208c, 0)
                audio.a.put(0x20022160, 0)
                audio.a.put(INOP, 1)
                audio.a.put(SOS, target(percent))
                input_stereo(audio, 3500, -1900)
                self.assertFalse(any(audio.blocks(1)))
                record(audio)
                self.assertFalse(any(audio.blocks(8)))
                self.assertEqual(audio.a.get(HEAD), 64)
                self.assertEqual(recording(audio, 0, 64),
                                 (struct.pack('<h', 5250)*64, struct.pack('<h', -2850)*64))

    def test_both_audio_paths_saturate_loud_stereo_feedback(self):
        audio = setup_audio(3, 50)
        for plane, level in ((LEFT, 9000), (RIGHT, -15000)):
            audio.uc.mem_write(plane, struct.pack('<h', level)*FRAMES)
        audio.blocks(200)
        seen = set()
        for site in MIX_SITES:
            audio.uc.hook_add(UC_HOOK_CODE, lambda uc, pc, size, data: seen.add(pc),
                              begin=site, end=site)
        start = start_take(audio, append=True)
        # The raw input alone reaches +/-30,750 after input calibration.
        # Full-scale samples here require playback to be included.
        input_stereo(audio, 20500, -20500)
        audio.blocks(48)
        audio.a.put(MORPH, 4095)
        audio.blocks(652)
        self.assertEqual(seen, set(MIX_SITES))
        left, right = (struct.unpack('<5600h', data) for data in recording(audio, start, 5600))
        self.assertGreaterEqual(max(left), 32766)
        self.assertLessEqual(min(right), -32766)
        self.assertGreater(min(left), 0)
        self.assertLess(max(right), 0)
