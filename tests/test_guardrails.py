import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import guardrails


class GuardrailTests(unittest.TestCase):
    def test_rejects_mpc_capture_audio_and_large_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wav = root / "licensed.wav"
            wav.write_bytes(b"x")
            capture = root / "Song_[ProjectData]" / "notes.txt"
            capture.parent.mkdir()
            capture.write_text("x")
            large = root / "large.bin"
            large.write_bytes(b"1234")
            issues = guardrails.scan([wav, capture, large], max_bytes=3)
            self.assertEqual(len(issues), 3)

    def test_accepts_normal_source_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tool.py"
            path.write_text("pass\n")
            self.assertEqual(guardrails.scan([path]), [])


if __name__ == "__main__":
    unittest.main()
