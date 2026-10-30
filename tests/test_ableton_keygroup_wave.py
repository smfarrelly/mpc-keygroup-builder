import copy
import gzip
import json
import tempfile
import unittest
from unittest.mock import patch
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
    def test_reports_coexisting_unsupported_settings_without_accepting_loss(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preset = self.fixture(root, "test", "Voice")
            report = ableton_keygroup_wave.ableton.inspect(preset)
            report['zones'][0].update(detune=11, samplestart=7, panorama=-0.2)
            with patch.object(ableton_keygroup_wave.ableton, 'inspect', return_value=report):
                with self.assertRaises(ValueError) as caught:
                    ableton_keygroup_wave.preflight(
                        {'path': str(preset.relative_to(root))}, root,
                        allow_loop_loss=True, allow_endpoint_loss=True, allow_keyrange_loss=True,
                    )
            message = str(caught.exception)
            for field in ('detune=11', 'samplestart=7', 'panorama=-0.2'):
                self.assertIn('zone 1 uses unsupported ' + field, message)

    def test_large_unsupported_setting_report_is_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preset = self.fixture(root, "test", "Voice")
            report = ableton_keygroup_wave.ableton.inspect(preset)
            zone = report['zones'][0]
            report['zones'] = []
            for index in range(6):
                item = copy.deepcopy(zone)
                sample = f'Zone{index}.wav'
                (root / 'test' / 'WAV' / sample).write_bytes((root / 'test' / 'WAV' / 'Voice C1.wav').read_bytes())
                item['sample']['relative_path'] = 'WAV/' + sample
                item.update(detune=11, samplestart=7, panorama=0.2)
                report['zones'].append(item)
            with patch.object(ableton_keygroup_wave.ableton, 'inspect', return_value=report):
                with self.assertRaises(ValueError) as caught:
                    ableton_keygroup_wave.preflight({'path': str(preset.relative_to(root))}, root)
            self.assertEqual(str(caught.exception).count('uses unsupported'), 12)
            self.assertIn('6 additional unsupported settings', str(caught.exception))

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

    def test_can_focus_a_wave_on_one_pack(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entries = []
            for pack in ("alpha_from_mars", "beta_from_mars"):
                preset = self.fixture(root, pack, f"Keys {pack}")
                entries.append({
                    "path": preset.relative_to(root).as_posix(), "name": preset.stem,
                    "pack": pack, "target": "keygroup", "priority": "P1",
                    "score": 80, "duplicate_of": None,
                })
            backlog = root / "backlog.json"
            backlog.write_text(json.dumps({"entries": entries}))
            output = root / "focused-plan"
            report = ableton_keygroup_wave.plan(
                backlog, root, output, count=1, max_per_pack=1,
                include_pack="beta_from_mars", exclude_names=("Keys alpha_from_mars",),
            )
            self.assertEqual(report["include_pack"], "beta_from_mars")
            self.assertEqual(report["excluded_names"], ["Keys alpha_from_mars"])
            self.assertEqual(report["programs"][0]["collection"], "Beta")

    def test_assigns_browsable_instrument_categories(self):
        self.assertEqual(ableton_keygroup_wave._category("Presets/01. Guitars/Nylon Guitar.adg"), "Guitars")
        self.assertEqual(ableton_keygroup_wave._category("Presets/02. Strings/Cello.adg"), "Strings")
        self.assertEqual(
            ableton_keygroup_wave._category("Presets/04. Brass & Woodwind/Clarinet.adg"),
            "Brass & Woodwinds",
        )
        self.assertEqual(ableton_keygroup_wave._category("Presets/06. Perc/Timpani.adg"), "Percussion")
        self.assertEqual(ableton_keygroup_wave._category("Presets/07. Percussion/Bongos.adg"), "Percussion")
        self.assertEqual(ableton_keygroup_wave._category("Presets/05. Vocal/Choir.adg"), "Vocals")
        self.assertEqual(ableton_keygroup_wave._category("Presets/08. FX/Dive.adg"), "FX")
        self.assertEqual(
            ableton_keygroup_wave._category("Presets/02. Keys & Pads/Glass.adg"),
            "Keys & Pads",
        )
        self.assertEqual(ableton_keygroup_wave._category("Presets/04. Chords/Stab.adg"), "Chords")
        self.assertEqual(
            ableton_keygroup_wave._category("Presets/05. Percussive/Hit.adg"),
            "Percussive",
        )

    def test_unknown_or_path_like_pack_is_actionable_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backlog = root / 'backlog.json'
            backlog.write_text(json.dumps({'entries': [{'pack': 'known_from_mars'}]}))
            for pack, message in [('typo', 'known_from_mars'), ('../outside', 'not a path')]:
                with self.assertRaisesRegex(ValueError, message):
                    ableton_keygroup_wave.plan(backlog, root, root / 'output', count=1, include_pack=pack)
                self.assertFalse((root / 'output').exists())

    def test_colliding_output_names_are_refused_before_plan_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entries = []
            for pack in ('alpha', 'beta'):
                preset = self.fixture(root, pack, 'Same Keys')
                entries.append({'path': str(preset.relative_to(root)), 'name': 'Same Keys',
                                'pack': pack, 'target': 'keygroup', 'priority': 'P1'})
            backlog = root / 'backlog.json'
            backlog.write_text(json.dumps({'entries': entries}))
            with self.assertRaisesRegex(ValueError, 'collide'):
                ableton_keygroup_wave.plan(backlog, root, root / 'output', count=2)
            self.assertFalse((root / 'output').exists())

    def test_keyrange_loss_does_not_admit_invalid_midi_ranges(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preset = self.fixture(root, 'range_from_mars', 'Invalid')
            raw = gzip.decompress(preset.read_bytes()).replace(
                b'<KeyRange><Min Value="0"/>', b'<KeyRange><Min Value="128"/>')
            preset.write_bytes(gzip.compress(raw))
            with self.assertRaisesRegex(ValueError, 'invalid source key ranges'):
                ableton_keygroup_wave.preflight({'path': str(preset.relative_to(root))}, root, allow_keyrange_loss=True)

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

    def test_shortened_sample_end_requires_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preset = self.fixture(root, "short_from_mars", "Short")
            raw = gzip.decompress(preset.read_bytes()).replace(
                b"</MultiSamplePart>", b'<SampleEnd Value="10"/></MultiSamplePart>',
            )
            with gzip.open(preset, "wb") as stream:
                stream.write(raw)
            entry = {"path": preset.relative_to(root).as_posix(), "name": "Short", "pack": "short_from_mars"}
            with self.assertRaisesRegex(ValueError, "sampleend=10 differs from WAV end=19"):
                ableton_keygroup_wave.preflight(entry, root)
            result = ableton_keygroup_wave.preflight(entry, root, allow_endpoint_loss=True)
            self.assertEqual(result["fidelity"], "review-required")
            self.assertIn("comparison uses WAV end=19", result["warnings"][0])

    def test_source_key_range_loss_requires_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preset = self.fixture(root, "range_from_mars", "Ranged")
            raw = gzip.decompress(preset.read_bytes()).replace(
                b'<KeyRange><Min Value="0"/>', b'<KeyRange><Min Value="12"/>',
            )
            with gzip.open(preset, "wb") as stream:
                stream.write(raw)
            entry = {"path": preset.relative_to(root).as_posix(), "name": "Ranged", "pack": "range_from_mars"}
            with self.assertRaisesRegex(ValueError, "key range"):
                ableton_keygroup_wave.preflight(entry, root)
            result = ableton_keygroup_wave.preflight(entry, root, allow_keyrange_loss=True)
            self.assertEqual(result["fidelity"], "review-required")
            self.assertTrue(any("replaced by builder range" in warning for warning in result["warnings"]))


if __name__ == "__main__":
    unittest.main()
