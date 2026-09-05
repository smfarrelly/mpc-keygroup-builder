import gzip
import json
import tempfile
import unittest
import wave
from pathlib import Path

from mpc_keygroup_builder import ableton, ableton_fidelity, ableton_wave
from test_ableton_drum import DRUM_XML


class AbletonFidelityWaveTests(unittest.TestCase):
    @staticmethod
    def fixture(root: Path, pack_name: str) -> Path:
        pack = root / pack_name
        samples = pack / "WAV"
        samples.mkdir(parents=True)
        for name in ("Kick.wav", "Hat.wav"):
            with wave.open(str(samples / name), "wb") as stream:
                stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(44100)
                stream.writeframes(b"\0\0" * 20)
        preset = pack / "Kit.adg"
        with gzip.open(preset, "wb") as stream:
            stream.write(DRUM_XML)
        return preset

    def test_normalizes_feature_fidelity_and_writes_transactional_catalog(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preset = self.fixture(root, "alpha_from_mars")
            model = ableton_fidelity.normalize(ableton.inspect(preset), source_path="alpha/Kit.adg")
            self.assertEqual(model["target"], "drum")
            self.assertEqual(model["fidelity"]["grade"], "C")
            translations = {item["feature"]: item["translation"] for item in model["features"]}
            self.assertEqual(translations["sample references"], "direct")
            self.assertEqual(translations["choke groups"], "direct")
            output = root / "fidelity"
            catalog = ableton_fidelity.build_catalog([preset], output, source_root=root)
            self.assertEqual(catalog["summary"]["presets"], 1)
            self.assertTrue((output / "README.md").is_file())
            with self.assertRaises(FileExistsError):
                ableton_fidelity.build_catalog([preset], output, source_root=root)

    def test_plans_diverse_wave_and_builds_all_programs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = [self.fixture(root, name) for name in ("alpha_from_mars", "beta_from_mars", "gamma_from_mars")]
            entries = [{
                "pack": path.parent.name, "path": path.relative_to(root).as_posix(), "name": f"Kit {index}",
                "target": "drum", "priority": "P1", "score": 80, "duplicate_of": None,
            } for index, path in enumerate(paths, 1)]
            backlog = root / "backlog.json"
            backlog.write_text(json.dumps({"entries": entries}), encoding="utf-8")
            plan_root = root / "plan"
            report = ableton_wave.plan_wave(backlog, root, plan_root, count=2, max_per_pack=1)
            self.assertEqual(report["summary"], {"programs": 2, "packs": 2, "rejected_during_preflight": 0})
            build_root = root / "build"
            built = ableton_wave.build_wave(plan_root / "ableton-drum-wave-02.toml", root, build_root)
            self.assertEqual(len(built["programs"]), 2)
            self.assertNotIn("fail", built["simulation"]["verdicts"])
            self.assertTrue((build_root / "HARDWARE_CHECKLIST.md").is_file())
            self.assertNotIn(str(root), (build_root / "build-report.json").read_text())


if __name__ == "__main__":
    unittest.main()
