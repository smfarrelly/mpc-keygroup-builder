import tempfile
import unittest
import wave
from pathlib import Path

from mpc_keygroup_builder import loop_inventory


class LoopInventoryTests(unittest.TestCase):
    def write_wav(self, path: Path, frames: int, rate: int = 44100) -> None:
        with wave.open(str(path), "wb") as stream:
            stream.setnchannels(2)
            stream.setsampwidth(2)
            stream.setframerate(rate)
            stream.writeframes(b"\0\0\0\0" * frames)

    def test_indexes_bpm_variant_and_integer_beats(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_wav(root / "120 Example Full Vinyl Breaks.wav", 88200)
            self.write_wav(root / "100 Example No Perc Vinyl Breaks.wav", 105840)
            report = loop_inventory.scan(root)
            self.assertEqual(report["count"], 2)
            self.assertEqual((report["bpm_min"], report["bpm_max"]), (100, 120))
            self.assertEqual(report["variants"], {"full": 1, "no-percussion": 1})
            self.assertEqual(report["timing_warnings"], [])
            first = report["loops"][0]
            self.assertEqual(first["nearest_beats"], 4)
            self.assertEqual(first["beat_error"], 0)
            self.assertIn("estimated_beats", loop_inventory.render_csv(report))

    def test_reports_unparseable_names_without_losing_valid_loops(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_wav(root / "090 Valid.wav", 117600)
            self.write_wav(root / "No Tempo.wav", 100)
            report = loop_inventory.scan(root)
            self.assertEqual(report["count"], 1)
            self.assertEqual(len(report["issues"]), 1)
            self.assertIn("no leading three-digit BPM", report["issues"][0])
