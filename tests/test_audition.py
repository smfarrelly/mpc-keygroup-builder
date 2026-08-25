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


if __name__ == "__main__":
    unittest.main()
