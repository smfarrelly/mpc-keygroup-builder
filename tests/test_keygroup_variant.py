import gzip
import json
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder.keygroup_variant import (
    build_variant_package,
    export_variant,
    inspect_program,
    load_variant,
    verify_variant,
)


class KeygroupVariantTests(unittest.TestCase):
    def _program(self, path: Path, *, kind: int = 1) -> None:
        envelope = {
            "Attack": {"value0": 0.0},
            "Decay": {"value0": 0.66},
            "Sustain": {"value0": 1.0},
            "Release": {"value0": 0.0},
            "MysteryEnvelopeField": {"keep": True},
        }
        document = {
            "data": {
                "name": "Source",
                "type": kind,
                "transpose": 0,
                "unknownGlobal": {"future": [1, 2, 3]},
                "customQLinks": [
                    {"name": "Attack", "controlValue": 0.0, "targetData": [{"parameter": 558}]},
                    {"name": "Cutoff", "controlValue": 1.0, "targetData": [{"parameter": 555}]},
                    {
                        "name": "Filter Attack",
                        "controlValue": 0.0,
                        "targetData": [{"parameter": 563}],
                    },
                ],
                "drum": {
                    "instruments": [
                        {"layersv": []},
                        {
                            "mysteryRecord": "preserve",
                            "lowNote": 0,
                            "highNote": 127,
                            "layersv": [
                                {
                                    "active": True,
                                    "sampleFile": "Tone.wav",
                                    "sampleName": "Tone",
                                    "velocityStart": 0,
                                    "velocityEnd": 127,
                                    "rootNote": 60,
                                    "loop": True,
                                    "loopStart": 10,
                                    "loopEnd": 90,
                                    "unknownLayer": 42,
                                }
                            ],
                        },
                    ]
                },
                "keygroup": {
                    "transpose": 0,
                    "numKeygroups": 1,
                    "unknownKeygroup": "keep",
                    "synthSection": {
                        "ampEnvelope": envelope,
                        "filterEnvelope": json.loads(json.dumps(envelope)),
                        "filterData": {
                            "value0": {
                                "filterCutoff": 1.0,
                                "filterResonance": 0.0,
                                "filterEnvelopeAmount": 0.0,
                                "unknownFilter": False,
                            },
                            "value1": {"preserveSecondFilter": True},
                        },
                        "unknownSynth": {"keep": True},
                    },
                },
                "samples": [
                    {
                        "name": "Tone",
                        "path": "Tone.wav",
                        "metadata": {"rootNote": 60, "mystery": "keep"},
                    }
                ],
            }
        }
        prefix = b"ACVS\n3.9.1.2\nSerialisableProgramData\njson\nLinux\n"
        path.write_bytes(gzip.compress(prefix + json.dumps(document).encode(), mtime=0))

    def _spec(self, path: Path, body: str = "") -> None:
        path.write_text(
            'schema_version = 1\nid = "pad"\nname = "Pad"\n'
            'description = "Slow and dark candidate"\n[parameters]\n'
            + body,
            encoding="utf-8",
        )

    def _data(self, path: Path) -> dict:
        raw = gzip.decompress(path.read_bytes())
        return json.loads(raw[raw.find(b"{") :])["data"]

    def test_exports_self_contained_variant_and_preserves_unknown_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output, spec_path = root / "Source.xpm", root / "Pad.xpm", root / "pad.toml"
            self._program(source)
            source_data = root / "Source_[ProgramData]"
            source_data.mkdir()
            (source_data / "Tone.wav").write_bytes(b"licensed-audio-fixture")
            self._spec(
                spec_path,
                "amp_attack = 0.35\namp_release = 0.55\n"
                "filter_cutoff = 0.72\nfilter_resonance = 0.1\ntranspose = -12\n",
            )
            report = export_variant(source, output, load_variant(spec_path))
            data = self._data(output)
            self.assertEqual(data["name"], "Source Pad")
            self.assertEqual(data["transpose"], -12)
            self.assertEqual(data["keygroup"]["transpose"], -12)
            self.assertEqual(
                data["keygroup"]["synthSection"]["ampEnvelope"]["Attack"]["value0"],
                0.35,
            )
            self.assertEqual(data["customQLinks"][0]["controlValue"], 0.35)
            self.assertEqual(data["customQLinks"][1]["controlValue"], 0.72)
            self.assertEqual(data["unknownGlobal"], {"future": [1, 2, 3]})
            self.assertEqual(
                data["drum"]["instruments"][1]["layersv"][0]["unknownLayer"], 42
            )
            self.assertEqual(
                (root / "Pad_[ProgramData]" / "Tone.wav").read_bytes(),
                b"licensed-audio-fixture",
            )
            self.assertTrue(report.document_preserved_except_allowlist)
            self.assertTrue(report.program_data_checksums_match)
            self.assertEqual(report.sample_layers, 1)
            self.assertEqual(report.program_data_files, 1)

    def test_clean_variant_changes_only_name(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output, spec_path = root / "Source.xpm", root / "Clean.xpm", root / "clean.toml"
            self._program(source)
            self._spec(spec_path)
            report = export_variant(
                source, output, load_variant(spec_path), copy_program_data=False
            )
            self.assertEqual(report.changed_paths, ("data.name",))
            self.assertEqual(self._data(output)["unknownGlobal"], {"future": [1, 2, 3]})

    def test_independent_verifier_detects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output, spec_path = root / "Source.xpm", root / "Pad.xpm", root / "pad.toml"
            self._program(source)
            self._spec(spec_path, "amp_attack = 0.35\n")
            spec = load_variant(spec_path)
            export_variant(source, output, spec, copy_program_data=False)
            data = self._data(output)
            data["unknownGlobal"]["future"] = []
            prefix = b"ACVS\n3.9.1.2\nSerialisableProgramData\njson\nLinux\n"
            output.write_bytes(gzip.compress(prefix + json.dumps({"data": data}).encode(), mtime=0))
            with self.assertRaisesRegex(ValueError, "outside the variant allowlist"):
                verify_variant(source, output, spec, require_program_data=False)

    def test_verifier_detects_program_data_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output, spec_path = root / "Source.xpm", root / "Pad.xpm", root / "pad.toml"
            self._program(source)
            (root / "Source_[ProgramData]").mkdir()
            (root / "Source_[ProgramData]" / "Tone.wav").write_bytes(b"source")
            self._spec(spec_path)
            spec = load_variant(spec_path)
            export_variant(source, output, spec)
            (root / "Pad_[ProgramData]" / "Tone.wav").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "checksums changed"):
                verify_variant(source, output, spec)

    def test_inspect_reports_parameters_and_source_shape(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "Source.xpm"
            self._program(source)
            report = inspect_program(source)
            self.assertEqual(report["name"], "Source")
            self.assertEqual(report["instrument_records"], 2)
            self.assertEqual(report["sample_layers"], 1)
            self.assertEqual(report["parameters"]["filter_cutoff"], 1.0)
            self.assertIn("filter_envelope_amount", report["supported_parameters"])

    def test_applies_every_supported_parameter_family(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output, spec_path = root / "Source.xpm", root / "All.xpm", root / "all.toml"
            self._program(source)
            self._spec(
                spec_path,
                "transpose = 12\namp_attack = 0.1\namp_decay = 0.2\n"
                "amp_sustain = 0.3\namp_release = 0.4\nfilter_attack = 0.5\n"
                "filter_decay = 0.6\nfilter_sustain = 0.7\nfilter_release = 0.8\n"
                "filter_cutoff = 0.9\nfilter_resonance = 0.15\n"
                "filter_envelope_amount = -0.25\n",
            )
            export_variant(
                source, output, load_variant(spec_path), copy_program_data=False
            )
            data = self._data(output)
            synth = data["keygroup"]["synthSection"]
            self.assertEqual(data["transpose"], 12)
            self.assertEqual(synth["ampEnvelope"]["Decay"]["value0"], 0.2)
            self.assertEqual(synth["ampEnvelope"]["Sustain"]["value0"], 0.3)
            self.assertEqual(synth["filterEnvelope"]["Attack"]["value0"], 0.5)
            self.assertEqual(synth["filterEnvelope"]["Decay"]["value0"], 0.6)
            self.assertEqual(synth["filterEnvelope"]["Sustain"]["value0"], 0.7)
            self.assertEqual(synth["filterEnvelope"]["Release"]["value0"], 0.8)
            self.assertEqual(
                synth["filterData"]["value0"]["filterEnvelopeAmount"], -0.25
            )
            self.assertEqual(data["customQLinks"][2]["controlValue"], 0.5)

    def test_bundled_candidate_specs_are_valid_and_unique(self):
        variant_root = Path(__file__).parents[1] / "variants" / "keygroups"
        specs = [load_variant(path) for path in sorted(variant_root.glob("*.toml"))]
        self.assertEqual(
            {spec.id for spec in specs},
            {"clean", "warm", "pad", "pluck", "bass", "lo-fi"},
        )
        self.assertEqual(len({spec.name.casefold() for spec in specs}), len(specs))

    def test_builds_multi_variant_hardware_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "Source.xpm"
            self._program(source)
            (root / "Source_[ProgramData]").mkdir()
            (root / "Source_[ProgramData]" / "Tone.wav").write_bytes(b"source")
            clean, pad = root / "clean.toml", root / "pad.toml"
            self._spec(clean)
            clean.write_text(
                clean.read_text()
                .replace('id = "pad"', 'id = "clean"')
                .replace('name = "Pad"', 'name = "Clean"'),
                encoding="utf-8",
            )
            self._spec(pad, "amp_attack = 0.35\n")
            output = root / "hardware"
            manifest = build_variant_package(
                source, [load_variant(clean), load_variant(pad)], output
            )
            self.assertEqual(manifest["variant_count"], 2)
            self.assertEqual(manifest["preservation_verdict"], "pass")
            self.assertEqual(manifest["semantic_verdict"], "warn")
            self.assertEqual(manifest["semantic_new_issue_count"], 0)
            self.assertEqual(manifest["hardware_verdict"], "pending")
            self.assertTrue((output / "Source Clean.xpm").is_file())
            self.assertTrue((output / "Source Pad_[ProgramData]" / "Tone.wav").is_file())
            saved = json.loads((output / "manifest.json").read_text())
            self.assertEqual(saved["variants"][1]["changed_paths"][0], "data.name")
            self.assertEqual(saved["variants"][1]["semantic"]["playable_notes"], 128)
            self.assertIn("Hardware listening order", (output / "README.md").read_text())

    def test_rejects_unknown_or_out_of_range_parameters(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            unknown, invalid = root / "unknown.toml", root / "invalid.toml"
            self._spec(unknown, "magic = 0.5\n")
            self._spec(invalid, "amp_attack = 1.1\n")
            with self.assertRaisesRegex(ValueError, "unsupported variant parameters"):
                load_variant(unknown)
            with self.assertRaisesRegex(ValueError, "0.0 to 1.0"):
                load_variant(invalid)

    def test_refuses_in_place_existing_missing_data_and_wrong_kind(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output, spec_path = root / "Source.xpm", root / "Output.xpm", root / "v.toml"
            self._program(source)
            self._spec(spec_path)
            spec = load_variant(spec_path)
            with self.assertRaisesRegex(ValueError, "in-place"):
                export_variant(source, source, spec)
            with self.assertRaisesRegex(ValueError, "ProgramData"):
                export_variant(source, output, spec)
            output.write_bytes(b"occupied")
            with self.assertRaisesRegex(FileExistsError, "output exists"):
                export_variant(source, output, spec, copy_program_data=False)
            drum = root / "Drum.xpm"
            self._program(drum, kind=0)
            with self.assertRaisesRegex(ValueError, "not a compressed Keygroup"):
                inspect_program(drum)

    def test_refuses_overlapping_program_data_and_package_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, spec_path = root / "Source.xpm", root / "v.toml"
            self._program(source)
            (root / "Source_[ProgramData]").mkdir()
            (root / "Source_[ProgramData]" / "Tone.wav").write_bytes(b"source")
            self._spec(spec_path)
            spec = load_variant(spec_path)
            with self.assertRaisesRegex(ValueError, "ProgramData paths must not overlap"):
                export_variant(source, root / "Source.XPM", spec, force=True)
            with self.assertRaisesRegex(ValueError, "must not overlap its source"):
                build_variant_package(source, [spec], root, force=True)
            self.assertTrue(source.is_file())
            self.assertTrue((root / "Source_[ProgramData]" / "Tone.wav").is_file())


if __name__ == "__main__":
    unittest.main()
