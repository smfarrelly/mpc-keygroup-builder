import contextlib
import io
from pathlib import Path
import tempfile
import struct
import unittest
import wave

from mpc_keygroup_builder import audition, entrypoints
from mpc_keygroup_builder.wave_io import complete_riff_view, inspect_pcm_file


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

    def test_stale_riff_length_preserves_complete_pcm_without_mutating_source(self):
        raw = wav_bytes()
        # Simulate metadata inserted before data without updating the outer RIFF size.
        metadata = b'atem' + struct.pack('<I', 4) + b'abcd'
        malformed = raw[:36] + metadata + raw[36:]
        source = io.BytesIO(malformed)
        self.assertEqual(audition.read_pcm_channels(source), audition.read_pcm_channels(io.BytesIO(raw)))
        self.assertFalse(source.closed)
        self.assertEqual(source.getvalue(), malformed)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'vendor.wav'
            path.write_bytes(malformed)
            self.assertEqual(audition.read_pcm_channels(path)[0], [[-1.0, 0.0, 0.5]]*2)
            self.assertEqual(path.read_bytes(), malformed)

    def test_stale_riff_does_not_hide_truncated_chunk(self):
        raw = wav_bytes()
        metadata = b'atem' + struct.pack('<I', 4) + b'abcd'
        malformed = (raw[:36] + metadata + raw[36:])[:-4]
        with self.assertRaisesRegex(ValueError, 'truncated WAV'):
            audition.read_pcm_channels(io.BytesIO(malformed))

    def test_riff_view_handles_padded_metadata_and_fragmented_header_reads(self):
        raw = wav_bytes()
        metadata = b'JUNK' + struct.pack('<I', 3) + b'abc\0'
        source = io.BytesIO(raw[:36] + metadata + raw[36:])
        view = complete_riff_view(source)
        header = b''.join(view.read(1) for _ in range(12))
        self.assertEqual(struct.unpack_from('<I', header, 4)[0], len(source.getvalue())-8)
        view.seek(0)
        with wave.open(view) as stream:
            self.assertEqual(len(stream.readframes(3)), 12)
        self.assertFalse(source.closed)

    def test_unexplained_trailing_bytes_and_duplicate_data_are_not_repaired(self):
        raw = wav_bytes()
        for suffix in (b'junk', b'data'+struct.pack('<I', 4)+b'xxxx'):
            with self.subTest(suffix=suffix):
                source = io.BytesIO(raw+suffix)
                self.assertIs(complete_riff_view(source), source)
                self.assertEqual(source.tell(), 0)

    def test_complete_odd_sized_final_pcm_chunk_needs_no_extra_padding(self):
        raw = wav_bytes(width=3, channels=1)
        metadata = b'atem' + struct.pack('<I', 4) + b'abcd'
        malformed = raw[:36] + metadata + raw[36:]
        self.assertEqual(audition.read_pcm_channels(io.BytesIO(malformed)),
                         audition.read_pcm_channels(io.BytesIO(raw)))

    def test_stream_verification_rejects_partial_frame_in_data_chunk(self):
        raw = bytearray(wav_bytes())
        raw += b'x'
        struct.pack_into('<I', raw, 4, len(raw)-8)
        struct.pack_into('<I', raw, 40, 13)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'partial-frame.wav'
            path.write_bytes(raw)
            with self.assertRaisesRegex(ValueError, 'incomplete PCM frame'):
                inspect_pcm_file(path)
            with self.assertRaisesRegex(ValueError, 'incomplete PCM frame'):
                audition.read_pcm_channels(path)

    def test_counted_zero_pad_in_odd_mono_24bit_data_is_explicit(self):
        raw = wav_bytes(width=3, channels=1)
        padded = bytearray(raw+b'\0')
        struct.pack_into('<I', padded, 4, len(padded)-8)
        struct.pack_into('<I', padded, 40, 10)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'vendor.wav'
            path.write_bytes(padded)
            result = inspect_pcm_file(path)
            self.assertTrue(result['data_padding_ignored'])
            self.assertEqual(result['pcm_bytes'], 9)
            self.assertEqual(audition.read_pcm_channels(path), audition.read_pcm_channels(io.BytesIO(raw)))
            self.assertEqual(path.read_bytes(), padded)
            for body in (raw[44:]+b'x', raw[44:]+b'\0\0', raw[44:50]+b'\0'):
                malformed = bytearray(raw[:44]+body)
                struct.pack_into('<I', malformed, 4, len(malformed)-8)
                struct.pack_into('<I', malformed, 40, len(body))
                path.write_bytes(malformed)
                with self.assertRaisesRegex(ValueError, 'incomplete PCM frame'):
                    inspect_pcm_file(path)
                with self.assertRaisesRegex(ValueError, 'incomplete PCM frame'):
                    audition.read_pcm_channels(path)

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
