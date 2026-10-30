import contextlib
import io
from pathlib import Path
import tempfile
import unittest
import wave

from mpc_keygroup_builder import audition, entrypoints


def wav_bytes(width=2, channels=2, empty=False):
    buffer = io.BytesIO()
    maximum = 2 ** (8 * width - 1)
    with wave.open(buffer, 'wb') as stream:
        stream.setparams((channels, width, 44100, 0, 'NONE', 'not compressed'))
        pcm = bytearray()
        if not empty:
            for value in [-maximum, 0, maximum // 2]:
                encoded = bytes([value + 128]) if width == 1 else value.to_bytes(width, 'little', signed=True)
                pcm.extend(encoded * channels)
        stream.writeframes(pcm)
    return buffer.getvalue()


class PCMTests(unittest.TestCase):
    def test_supported_widths_preserve_channel_and_mono_values(self):
        for width in (1, 2, 3, 4):
            with self.subTest(width=width):
                raw = wav_bytes(width)
                channels, rate = audition.read_pcm_channels(io.BytesIO(raw))
                self.assertEqual(rate, 44100)
                self.assertEqual(channels, [[-1.0, 0.0, 0.5]] * 2)
                self.assertEqual(audition.read_pcm_mono(io.BytesIO(raw)), (channels[0], rate))

    def test_incomplete_frames_and_missing_frames_are_rejected(self):
        raw = wav_bytes()
        for removed in (1, 4):
            with self.subTest(removed=removed), self.assertRaisesRegex(ValueError, 'truncated WAV'):
                audition.read_pcm_channels(io.BytesIO(raw[:-removed]))

    def test_empty_corrupt_and_unsupported_channel_inputs_are_clear(self):
        for raw, message in ((wav_bytes(empty=True), 'empty WAV'),
                             (b'not a WAV', 'unreadable WAV'),
                             (wav_bytes(channels=3), 'unsupported channel count')):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                audition.read_pcm_channels(io.BytesIO(raw))

    def test_level_cli_reports_corrupt_wav_without_traceback_or_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root/'damaged.wav'
            path.write_bytes(wav_bytes()[:-1])
            report = root/'levels.json'
            error = io.StringIO()
            with contextlib.redirect_stderr(error):
                status = entrypoints.invoke('mpc-audio-levels', [str(path), '--output', str(report)])
            self.assertEqual(status, 2)
            self.assertIn('truncated WAV', error.getvalue())
            self.assertNotIn('Traceback', error.getvalue())
            self.assertFalse(report.exists())
