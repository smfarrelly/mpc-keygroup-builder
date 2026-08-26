import gzip
import json
import tempfile
import unittest
import wave
from pathlib import Path

from mpc_keygroup_builder import testing


def write_wav(path: Path, frames: int = 32) -> None:
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(44100)
        stream.writeframes(b"\0\0" * frames)


def write_keygroup(root: Path, *, velocity_end: int = 127, sample_end: int = 31) -> Path:
    program = root / "Test.xpm"
    data = root / "Test_[ProgramData]"
    data.mkdir()
    write_wav(data / "sample.wav")
    layer = {
        "active": True,
        "sampleFile": "sample.wav",
        "rootNote": 60,
        "velocityStart": 0,
        "velocityEnd": velocity_end,
        "sampleEnd": 0,
        "sliceInfo": {"End": sample_end},
        "loop": False,
    }
    payload = {
        "data": {
            "keygroup": {"numKeygroups": 1},
            "drum": {
                "instruments": [
                    {"lowNote": 60, "highNote": 60, "layersv": [layer]},
                    {"lowNote": 0, "highNote": 127, "layersv": [layer]},
                ]
            },
            "samples": [{"path": "sample.wav", "metadata": {"rootNote": 60}}],
        }
    }
    text = "ACVS\n3.9.1.2\nSerialisableProgramData\njson\nLinux\n" + json.dumps(payload)
    with gzip.open(program, "wt", encoding="utf-8") as stream:
        stream.write(text)
    return program


class TestingFrameworkTests(unittest.TestCase):
    def test_complete_matrix_warns_about_extreme_sample_extrapolation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = testing.test_program(write_keygroup(root), root)
            self.assertEqual(result.verdict, "warn")
            self.assertEqual(result.playable_notes, 128)
            self.assertEqual(result.dead_trigger_cells, 0)
            self.assertIn("extreme_key_extrapolation", {issue.code for issue in result.issues})

    def test_velocity_gap_fails_simulation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = testing.test_program(write_keygroup(root, velocity_end=64), root)
            self.assertEqual(result.verdict, "fail")
            self.assertIn("dead_note_velocity_cells", {issue.code for issue in result.issues})

    def test_invalid_sample_endpoint_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = testing.test_program(write_keygroup(root, sample_end=32), root)
            self.assertIn("invalid_sample_end", {issue.code for issue in result.issues})

    def test_testing_folder_is_not_production_scope(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            testing_root = root / "Programs" / "Keygroups" / "Testing"
            testing_root.mkdir(parents=True)
            result = testing.test_program(write_keygroup(testing_root, velocity_end=64), root)
            self.assertEqual(result.scope, "testing")
            self.assertEqual(result.verdict, "fail")


if __name__ == "__main__":
    unittest.main()
