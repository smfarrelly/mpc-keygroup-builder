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


if __name__ == "__main__":
    unittest.main()
