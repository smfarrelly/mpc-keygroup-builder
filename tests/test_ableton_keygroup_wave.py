import gzip
import json
import tempfile
import unittest
import wave
from pathlib import Path

from mpc_keygroup_builder import ableton_keygroup_wave, workflow


def xml(sample: str, *, warped: bool = False) -> bytes:
    return f'''<Ableton><GroupDevicePreset><Device><InstrumentGroupDevice>
    <UserName Value="Test Instrument"/><Branches><InstrumentBranchPreset><Device><OriginalSimpler>
    <MultiSamplePart><Name Value="Zone"/><IsActive Value="true"/><RootKey Value="36"/>
    <KeyRange><Min Value="0"/><Max Value="127"/></KeyRange>
    <VelocityRange><Min Value="1"/><Max Value="127"/></VelocityRange>
    <SampleRef><FileRef><RelativePath><RelativePathElement Dir="WAV"/></RelativePath><Name Value="{sample}"/></FileRef></SampleRef>
    <SampleWarpProperties><IsWarped Value="{'true' if warped else 'false'}"/></SampleWarpProperties>
    </MultiSamplePart></OriginalSimpler></Device></InstrumentBranchPreset></Branches>
    </InstrumentGroupDevice></Device></GroupDevicePreset></Ableton>'''.encode()


class AbletonKeygroupWaveTests(unittest.TestCase):
    @staticmethod
    def fixture(root: Path, pack: str, name: str, *, warped: bool = False) -> Path:
        directory = root / pack
        samples = directory / "WAV"
        samples.mkdir(parents=True)
        sample = f"{name} C1.wav"
        with wave.open(str(samples / sample), "wb") as stream:
            stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(44100)
            stream.writeframes(b"\0\0" * 20)
        preset = directory / f"{name}.adg"
        with gzip.open(preset, "wb") as stream:
            stream.write(xml(sample, warped=warped))
        return preset

    def test_preflight_proves_current_builder_topology(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preset = self.fixture(root, "vinyl_from_mars", "Soft Bass")
            entry = {"path": preset.relative_to(root).as_posix(), "name": "Soft Bass", "pack": "vinyl_from_mars"}
            result = ableton_keygroup_wave.preflight(entry, root)
            self.assertEqual(result["roots"], [36])
            self.assertEqual(result["sample_directory"], "vinyl_from_mars/WAV")
            self.assertEqual(result["category"], "Bass")
            self.assertEqual(result["fidelity"], "direct")

    def test_plans_diverse_transactional_workflow_batch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entries = []
            for index, pack in enumerate(("alpha_from_mars", "beta_from_mars"), 1):
                preset = self.fixture(root, pack, f"Keys {index}")
                entries.append({
                    "path": preset.relative_to(root).as_posix(), "name": f"Keys {index}",
                    "pack": pack, "target": "keygroup", "priority": "P1", "score": 80, "duplicate_of": None,
                })
            backlog = root / "backlog.json"
            backlog.write_text(json.dumps({"entries": entries}))
            output = root / "plan"
            report = ableton_keygroup_wave.plan(backlog, root, output, count=2, max_per_pack=1)
            self.assertEqual(report["summary"]["programs"], 2)
            batch = json.loads((output / "keygroup-batch.json").read_text())
            settings = workflow.Settings(root, root / "media", root / "template.xpm", root / "artifacts")
            loaded = workflow.load_batch(output / "keygroup-batch.json", settings)
            self.assertEqual(len(loaded.instruments), 2)
            self.assertEqual(batch["instruments"][0]["install"], "copy")
            self.assertTrue((output / "HARDWARE_CHECKLIST.md").is_file())
            self.assertTrue((output / "README.md").is_file())
            with self.assertRaises(FileExistsError):
                ableton_keygroup_wave.plan(backlog, root, output, count=2, max_per_pack=1)

    def test_rejects_warp_and_insufficient_compatible_count(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preset = self.fixture(root, "bad_from_mars", "Warped", warped=True)
            entry = {"path": preset.relative_to(root).as_posix(), "name": "Warped", "pack": "bad_from_mars"}
            with self.assertRaisesRegex(ValueError, "uses warp"):
                ableton_keygroup_wave.preflight(entry, root)
            backlog = root / "backlog.json"
            backlog.write_text(json.dumps({"entries": [{**entry, "target": "keygroup", "duplicate_of": None}]}))
            with self.assertRaisesRegex(ValueError, "only 0 compatible"):
                ableton_keygroup_wave.plan(backlog, root, root / "output", count=1)

    def test_loop_loss_requires_explicit_opt_in_and_stays_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preset = self.fixture(root, "loop_from_mars", "Looped")
            raw = gzip.decompress(preset.read_bytes()).replace(
                b"</MultiSamplePart>",
                b'<SustainLoop><Mode Value="1"/><Start Value="2"/><End Value="18"/></SustainLoop></MultiSamplePart>',
            )
            with gzip.open(preset, "wb") as stream:
                stream.write(raw)
            entry = {"path": preset.relative_to(root).as_posix(), "name": "Looped", "pack": "loop_from_mars"}
            with self.assertRaisesRegex(ValueError, "unsupported sustain_loop"):
                ableton_keygroup_wave.preflight(entry, root)
            result = ableton_keygroup_wave.preflight(entry, root, allow_loop_loss=True)
            self.assertEqual(result["fidelity"], "review-required")
            self.assertIn("omitted from the comparison build", result["warnings"][0])


if __name__ == "__main__":
    unittest.main()
