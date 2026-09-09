import tempfile
import unittest
import wave
from pathlib import Path

from mpc_keygroup_builder import audition
from tests.test_testing_framework import write_keygroup


class AuditionTests(unittest.TestCase):
    def test_keygroup_render_writes_audio_and_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            program = write_keygroup(root)
            output = root / "audition.wav"
            manifest = audition.render(program, output)
            self.assertTrue(output.is_file())
            self.assertTrue(output.with_suffix(".json").is_file())
            self.assertEqual(len(manifest["events"]), len(audition.KEYGROUP_NOTES))
            with wave.open(str(output), "rb") as stream:
                self.assertEqual(stream.getframerate(), audition.OUTPUT_RATE)
                self.assertGreater(stream.getnframes(), 0)

    def test_output_requires_wav_and_cannot_replace_program(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            program = write_keygroup(root)
            original = program.read_bytes()
            with self.assertRaisesRegex(ValueError, r"\.wav extension"):
                audition.render(program, root / "audition.json")
            wav_named_program = program.with_suffix(".wav")
            program.rename(wav_named_program)
            with self.assertRaisesRegex(ValueError, "replace the input program"):
                audition.render(wav_named_program, wav_named_program)
            self.assertEqual(wav_named_program.read_bytes(), original)

    def test_output_preflight_rejects_manifest_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            program = write_keygroup(root)
            external = root / "external.json"
            external.write_text("keep\n")
            (root / "audition.json").symlink_to(external)
            with self.assertRaisesRegex(ValueError, "manifest.*symbolic link"):
                audition.render(program, root / "audition.wav")
            self.assertFalse((root / "audition.wav").exists())
            self.assertEqual(external.read_text(), "keep\n")


if __name__ == "__main__":
    unittest.main()
