import json
import tempfile
import unittest
import wave
import xml.etree.ElementTree as ET
from pathlib import Path

from mpc_keygroup_builder.kit_wave import build_wave, load_wave


class KitWaveTests(unittest.TestCase):
    def _wav(self, path: Path, frames: int = 128) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(44100)
            stream.writeframes(b"\x00\x10" * frames)

    def _template(self, path: Path) -> None:
        pads = {f"value{index}": 0 for index in range(128)}
        root = ET.Element("MPCVObject")
        program = ET.SubElement(root, "Program", type="Drum")
        ET.SubElement(program, "ProgramName").text = "Template"
        ET.SubElement(program, "ProgramPads").text = json.dumps(
            {
                "ProgramPads": {
                    "Universal": {"value0": True},
                    "Type": {"value0": 1},
                    "pads": pads,
                }
            }
        )
        instruments = ET.SubElement(program, "Instruments")
        for number in range(1, 129):
            instrument = ET.SubElement(instruments, "Instrument", number=str(number))
            ET.SubElement(instrument, "Mono").text = "False"
            ET.SubElement(instrument, "Polyphony").text = "4"
            ET.SubElement(instrument, "MuteGroup").text = "0"
            ET.SubElement(instrument, "OneShot").text = "False"
            layers = ET.SubElement(instrument, "Layers")
            layer = ET.SubElement(layers, "Layer", number="1")
            ET.SubElement(layer, "Active").text = "False"
            ET.SubElement(layer, "SampleName")
            ET.SubElement(layer, "SampleFile")
            ET.SubElement(layer, "VelStart").text = "0"
            ET.SubElement(layer, "VelEnd").text = "127"
        ET.ElementTree(root).write(path, encoding="UTF-8", xml_declaration=True)

    def _source(self, root: Path, name: str, role: str) -> dict:
        relative = f"Audio/{name}.wav"
        self._wav(root / relative)
        return {
            "path": f"Programs/{name}.xpm",
            "name": name,
            "collection": "Synthetic",
            "program_type": "drum",
            "index_status": "pass",
            "hardware_status": "pass",
            "favorite": "",
            "zones": [{"index": 1, "role": role, "samples": [f"{name}.wav"]}],
            "audio_facets": {
                "samples": [
                    {
                        "sample": f"{name}.wav",
                        "path": relative,
                        "duration_seconds": 0.2,
                        "rms_dbfs": -18.0,
                        "peak_dbfs": -2.0,
                        "crest_db": 16.0,
                        "attack_milliseconds": 2.0,
                        "onset_to_body_db": 4.0,
                        "descriptors": {
                            "duration": "short",
                            "loudness": "moderate",
                            "transient": "sharp",
                        },
                    }
                ]
            },
        }

    def test_builds_atomic_audited_wave_and_checklist(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recipe_root = root / "recipes"
            (recipe_root / "kits").mkdir(parents=True)
            (recipe_root / "kit-waves").mkdir()
            recipe = recipe_root / "kits/demo.toml"
            recipe.write_text(
                'schema_version=1\nid="demo"\nname="Demo Kit"\nseed=7\n'
                'require_hardware_pass=true\n'
                '[[pads]]\npad=1\nrole="kick"\n'
                '[[pads]]\npad=2\nrole="snare"\n'
                '[[pads]]\npad=7\nrole="hihat.closed"\nmute_group=1\n'
                '[[pads]]\npad=8\nrole="hihat.open"\nmute_group=1\n',
                encoding="utf-8",
            )
            wave_path = recipe_root / "kit-waves/demo.toml"
            wave_path.write_text(
                'schema_version=1\nid="wave"\nname="Demo Wave"\n'
                '[[kits]]\nid="demo"\nrecipe="../kits/demo.toml"\n',
                encoding="utf-8",
            )
            catalog = {
                "schema_version": 1,
                "program_root": str(root),
                "audio_facets_enabled": True,
                "programs": [
                    self._source(root, "BD Demo", "kick.primary"),
                    self._source(root, "SD Demo", "snare.primary"),
                    self._source(root, "CH Demo", "hihat.closed"),
                    self._source(root, "OH Demo", "hihat.open"),
                ],
            }
            template = root / "template.xpm"
            self._template(template)
            output = root / "output"
            report = build_wave(
                load_wave(wave_path),
                catalog,
                catalog_path=root / "catalog.json",
                template=template,
                output=output,
            )
            self.assertEqual(report["kits"][0]["software_verdict"], "pass")
            self.assertEqual(report["pairwise_overlap"], [])
            self.assertEqual(len(report["kits"][0]["selection_signature"]), 64)
            self.assertTrue((output / "demo/Program/Demo Kit.xpm").is_file())
            acceptance = json.loads(
                (output / "demo/software-acceptance.json").read_text(encoding="utf-8")
            )
            self.assertEqual(acceptance["simulation"]["verdict"], "pass")
            self.assertEqual(acceptance["drum_audit"]["verdict"], "pass")
            self.assertNotIn(".staging-", json.dumps(acceptance))
            self.assertNotIn(
                ".staging-",
                (output / "demo/staging-checksums.json").read_text(encoding="utf-8"),
            )
            self.assertIn("Full MPC path", (output / "HARDWARE_CHECKLIST.md").read_text())
            with self.assertRaises(FileExistsError):
                build_wave(
                    load_wave(wave_path),
                    catalog,
                    catalog_path=root / "catalog.json",
                    template=template,
                    output=output,
                )

    def test_wave_rejects_duplicate_recipe_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "kits").mkdir()
            (root / "kit-waves").mkdir()
            (root / "kits/one.toml").write_text("schema_version=1\n", encoding="utf-8")
            path = root / "kit-waves/wave.toml"
            path.write_text(
                'schema_version=1\nid="wave"\nname="Wave"\n'
                '[[kits]]\nid="one"\nrecipe="../kits/one.toml"\n'
                '[[kits]]\nid="two"\nrecipe="../kits/one.toml"\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate wave recipe path"):
                load_wave(path)


if __name__ == "__main__":
    unittest.main()
