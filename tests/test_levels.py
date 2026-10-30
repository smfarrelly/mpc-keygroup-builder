import contextlib
import io
import math
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from mpc_keygroup_builder import entrypoints, levels


def write_tone(path: Path, amplitude: float, dc: float = 0.0) -> None:
    values = [max(-1, min(1, dc + amplitude * math.sin(2 * math.pi * 440 * i / 44100))) for i in range(4410)]
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(44100)
        stream.writeframes(b"".join(struct.pack("<h", round(value * 32767)) for value in values))


class LevelTests(unittest.TestCase):
    def write_stereo(self, path, left, right):
        with wave.open(str(path), 'wb') as stream:
            stream.setparams((2, 2, 44100, 0, 'NONE', 'not compressed'))
            stream.writeframes(b''.join(struct.pack('<hh', a, b) for a, b in zip(left, right)))

    def test_opposite_polarity_stereo_is_audible_but_cancels_in_mono(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'stereo.wav'
            left = [16384, -16384] * 100
            self.write_stereo(path, left, [-value for value in left])
            row = levels.analyze([path])[0]
            self.assertEqual(row['channels'], 2)
            self.assertAlmostEqual(row['rms_dbfs'], -6.0206, places=4)
            self.assertEqual(row['silent_fraction'], 0)
            self.assertNotIn('silent', row['flags'])
            self.assertIn('mono-cancellation', row['flags'])
            self.assertIsNone(row['mono_rms_dbfs'])

    def test_clipping_on_one_stereo_channel_is_not_hidden(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'clip.wav'
            self.write_stereo(path, [32767, -32767]*100, [0]*200)
            row = levels.analyze([path])[0]
            self.assertEqual(row['clipped_fraction'], 1)
            self.assertIn('clipping', row['flags'])
            self.assertNotIn('mono-cancellation', row['flags'])

    def test_identical_channels_and_stereo_silence_are_not_cancellation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'coherent.wav'
            self.write_stereo(path, [16384, -16384]*100, [16384, -16384]*100)
            row = levels.analyze([path])[0]
            self.assertAlmostEqual(row['mono_cancellation_db'], 0)
            self.assertEqual(row['flags'], [])
            self.write_stereo(path, [0]*200, [0]*200)
            row = levels.analyze([path])[0]
            self.assertIn('silent', row['flags'])
            self.assertNotIn('mono-cancellation', row['flags'])

    def test_flags_level_outlier_silence_and_dc(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_tone(root / "normal.wav", 0.5)
            write_tone(root / "quiet.wav", 0.02)
            write_tone(root / "silent.wav", 0.0)
            write_tone(root / "dc.wav", 0.5, 0.05)
            rows = levels.analyze(sorted(root.glob("*.wav")), tolerance_db=6)
            flags = {Path(str(row["path"])).name: row["flags"] for row in rows}
            self.assertIn("level-outlier", flags["quiet.wav"])
            self.assertIn("silent", flags["silent.wav"])
            self.assertIn("dc-offset", flags["dc.wav"])
            normal = next(row for row in rows if Path(str(row["path"])).name == "normal.wav")
            self.assertIn("onset_rms_dbfs", normal)
            self.assertIn("body_rms_dbfs", normal)
            self.assertIn("onset_to_body_db", normal)
            self.assertGreaterEqual(normal["attack_milliseconds"], 0)

    def test_discovers_wav_extensions_case_insensitively(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_tone(root / "UPPER.WAV", 0.5)
            (root / "notes.txt").write_text("ignore")
            self.assertEqual(
                [path.name for path in levels.discover([root])], ["UPPER.WAV"]
            )

    def test_rejects_invalid_tolerances_before_analysis(self):
        for tolerance in (-1.0, math.nan, math.inf):
            with self.subTest(tolerance=tolerance):
                with self.assertRaisesRegex(ValueError, "finite nonnegative"):
                    levels.analyze([], tolerance)

    def test_empty_directory_is_friendly_through_installed_command(self):
        with tempfile.TemporaryDirectory() as directory:
            error = io.StringIO()
            with contextlib.redirect_stderr(error):
                status = entrypoints.invoke("mpc-audio-levels", [directory])
            self.assertEqual(status, 2)
            self.assertIn("no WAV files found", error.getvalue())
            self.assertNotIn("Traceback", error.getvalue())

    def test_report_may_not_replace_an_input_or_follow_a_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.wav"
            write_tone(source, 0.5)
            before = source.read_bytes()
            with self.assertRaisesRegex(ValueError, "replace an input WAV"):
                levels.write_report(source, [source], "report")
            self.assertEqual(source.read_bytes(), before)

            external = root / "external.json"
            external.write_text("preserve")
            linked = root / "report.json"
            linked.symlink_to(external)
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                levels.write_report(linked, [source], "report")
            self.assertEqual(external.read_text(), "preserve")

    def test_report_creates_parent_and_replaces_regular_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "nested" / "levels.json"
            self.assertEqual(levels.write_report(output, [], "first"), output.resolve())
            self.assertEqual(output.read_text(), "first")
            levels.write_report(output, [], "second")
            self.assertEqual(output.read_text(), "second")


if __name__ == "__main__":
    unittest.main()
