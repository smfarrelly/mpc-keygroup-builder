import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import entrypoints, guardrails


class GuardrailTests(unittest.TestCase):
    def test_rejects_mpc_capture_audio_and_large_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wav = root / "licensed.wav"
            wav.write_bytes(b"x")
            syx = root / "controller.syx"
            syx.write_bytes(b"x")
            capture = root / "Song_[ProjectData]" / "notes.txt"
            capture.parent.mkdir()
            capture.write_text("x")
            large = root / "large.bin"
            large.write_bytes(b"1234")
            issues = guardrails.scan([wav, syx, capture, large], max_bytes=3)
            self.assertEqual(len(issues), 4)

    def test_accepts_normal_source_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tool.py"
            path.write_text("pass\n")
            self.assertEqual(guardrails.scan([path]), [])

    def test_non_repository_error_is_actionable_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            error = io.StringIO()
            with contextlib.redirect_stderr(error):
                status = entrypoints.invoke(
                    "mpc-repository-guard", ["--root", directory]
                )
            self.assertEqual(status, 2)
            rendered = error.getvalue()
            self.assertIn("requires a Git worktree", rendered)
            self.assertIn("NEXT:", rendered)
            self.assertNotIn("Traceback", rendered)


if __name__ == "__main__":
    unittest.main()
