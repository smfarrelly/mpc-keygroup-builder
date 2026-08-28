import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path

from mpc_keygroup_builder.device import load_device
from mpc_keygroup_builder.drum_builder import load_manifest
from mpc_keygroup_builder.layout_draft import (
    color_overrides,
    draft_to_plan,
    file_sha256,
    load_draft,
    model_fingerprint,
    render_manifest,
    validate_draft,
)
from mpc_keygroup_builder.layout_export import export_layout
from mpc_keygroup_builder.model import from_xpm


class LayoutDraftTests(unittest.TestCase):
    def _source(self, path: Path) -> None:
        root = ET.Element("MPCVObject", Version="2.1")
        program = ET.SubElement(root, "Program", type="Drum", custom="preserve")
        ET.SubElement(program, "ProgramName").text = "Draft Kit"
        ET.SubElement(program, "ProgramPads").text = json.dumps(
            {
                "ProgramPads": {
                    "Universal": {"value0": False},
                    "pads": {"value0": 0x112233, "value1": 0x445566},
                }
            }
        )
        instruments = ET.SubElement(program, "Instruments")
        for number in range(1, 129):
            instrument = ET.SubElement(
                instruments, "Instrument", number=str(number), identity=f"record-{number}"
            )
            ET.SubElement(instrument, "OneShot").text = "True"
            ET.SubElement(instrument, "MuteGroup").text = "1" if number in (1, 2) else "0"
            layers = ET.SubElement(instrument, "Layers")
            for layer_number in range(1, 5):
                layer = ET.SubElement(layers, "Layer", number=str(layer_number))
                if number == 1 and layer_number in (1, 2):
                    ET.SubElement(layer, "SampleFile").text = f"Kick {layer_number}.wav"
                    ET.SubElement(layer, "VelStart").text = "0" if layer_number == 1 else "64"
                    ET.SubElement(layer, "VelEnd").text = "63" if layer_number == 1 else "127"
                elif number == 2 and layer_number == 1:
                    ET.SubElement(layer, "SampleFile").text = "Snare.wav"
                    ET.SubElement(layer, "VelStart").text = "0"
                    ET.SubElement(layer, "VelEnd").text = "127"
        ET.ElementTree(root).write(path, encoding="UTF-8", xml_declaration=True)

    def _draft_data(self, source: Path, *, recolor: bool = True) -> dict:
        program = from_xpm(source)
        device = load_device(Path(__file__).parents[1] / "devices/mpc-key-37.toml")
        assignments = []
        destinations = {1: 2, 2: 1}
        for zone in program.zones:
            slot = destinations[zone.index]
            assignments.append(
                {
                    "slot": slot,
                    "label": device.label(slot),
                    "source_zone": zone.index,
                    "source_pad": zone.pad,
                    "role": zone.role,
                    "source_color": zone.color,
                    "color": 0xABCDEF if recolor and zone.index == 1 else zone.color,
                    "source_locked": zone.locked,
                    "locked": zone.index == 2,
                    "playback_mode": zone.playback_mode,
                    "mute_group": zone.mute_group,
                    "layers": [asdict(layer) for layer in zone.layers],
                }
            )
        return {
            "schema_version": 1,
            "kind": "mpc-layout-draft",
            "program": program.name,
            "device": device.id,
            "source_path": str(source),
            "source_format": program.source_format,
            "source_sha256": file_sha256(source),
            "source_model_sha256": model_fingerprint(program),
            "assignments": assignments,
        }

    def _load(self, root: Path, data: dict):
        path = root / "draft.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path, load_draft(path)

    def test_validates_and_renders_builder_compatible_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "Source.xpm"
            self._source(source)
            draft_path, draft = self._load(root, self._draft_data(source))
            program = from_xpm(source)
            device = load_device(Path(__file__).parents[1] / "devices/mpc-key-37.toml")
            report = validate_draft(draft, draft_path, source, program, device)
            self.assertEqual(report.moved_assignments, 2)
            self.assertEqual(report.color_changes, 1)
            self.assertEqual(report.lock_changes, 1)
            manifest_path = root / "result.toml"
            manifest_path.write_text(render_manifest(draft, "Draft Result"), encoding="utf-8")
            manifest = load_manifest(manifest_path)
            self.assertEqual([pad.pad for pad in manifest.pads], [1, 2])
            self.assertEqual(manifest.pads[0].sample, "Snare.wav")
            self.assertEqual(len(manifest.pads[1].layers), 2)
            self.assertEqual(manifest.pads[1].layers[1].velocity_start, 64)

    def test_exports_only_record_placement_name_and_declared_color(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "Source.xpm", root / "Output.xpm"
            self._source(source)
            draft_path, draft = self._load(root, self._draft_data(source))
            program = from_xpm(source)
            device = load_device(Path(__file__).parents[1] / "devices/mpc-key-37.toml")
            validate_draft(draft, draft_path, source, program, device)
            report = export_layout(
                source,
                output,
                draft_to_plan(draft, program, device),
                name="Draft Result",
                color_overrides=color_overrides(draft),
            )
            rendered = ET.parse(output).getroot().find("Program")
            first = rendered.find('./Instruments/Instrument[@number="1"]')
            second = rendered.find('./Instruments/Instrument[@number="2"]')
            colors = json.loads(rendered.findtext("ProgramPads"))["ProgramPads"]["pads"]
            self.assertEqual(first.get("identity"), "record-2")
            self.assertEqual(second.get("identity"), "record-1")
            self.assertEqual(colors["value0"], 0x445566)
            self.assertEqual(colors["value1"], 0xABCDEF)
            self.assertEqual(report.color_overrides, 1)
            self.assertTrue(report.colors_follow_records)
            self.assertTrue(report.global_settings_unchanged)

    def test_rejects_changed_source_and_tampered_assignment_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "Source.xpm"
            self._source(source)
            data = self._draft_data(source)
            source.write_bytes(source.read_bytes() + b"\n")
            draft_path, draft = self._load(root, data)
            program = from_xpm(source)
            device = load_device(Path(__file__).parents[1] / "devices/mpc-key-37.toml")
            with self.assertRaisesRegex(ValueError, "source SHA-256"):
                validate_draft(draft, draft_path, source, program, device)

            self._source(source)
            data = self._draft_data(source)
            data["assignments"][0]["role"] = "tampered.role"
            draft_path, draft = self._load(root, data)
            with self.assertRaisesRegex(ValueError, "role does not match"):
                validate_draft(draft, draft_path, source, from_xpm(source), device)

    def test_rejects_incomplete_color_contract_and_unrepresentable_manifest_layers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "Source.xpm"
            self._source(source)
            data = self._draft_data(source)
            del data["assignments"][0]["source_color"]
            path = root / "draft.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing source_color"):
                load_draft(path)

            data = self._draft_data(source)
            data["assignments"][0]["layers"] = [
                {**data["assignments"][0]["layers"][0], "velocity_end": 31}
            ]
            _, draft = self._load(root, data)
            with self.assertRaisesRegex(ValueError, "velocity gaps or overlaps"):
                render_manifest(draft, "Cannot Render")


if __name__ == "__main__":
    unittest.main()
