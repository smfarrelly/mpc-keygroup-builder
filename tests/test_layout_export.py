import gzip
import json
import tempfile
import unittest
import wave
import xml.etree.ElementTree as ET
from pathlib import Path

from mpc_keygroup_builder.device import load_device
from mpc_keygroup_builder.layout import LayoutAssignment, LayoutPlan
from mpc_keygroup_builder.layout_export import (
    build_hardware_package,
    export_layout,
    verify_layout_export,
)


class LayoutExportTests(unittest.TestCase):
    def _plan(self) -> LayoutPlan:
        return LayoutPlan(
            "Kit",
            "swap",
            "mpc-key-37",
            (
                LayoutAssignment(1, "A01", 2, "Snare.wav", "snare.primary", 0x22, False),
                LayoutAssignment(2, "A02", 1, "Kick.wav", "kick.primary", 0x11, False),
            ),
            (),
        )

    def _xml_program(self, path: Path) -> None:
        root = ET.Element("MPCVObject", Version="2.1")
        program = ET.SubElement(root, "Program", type="Drum", custom="preserve")
        ET.SubElement(program, "ProgramName").text = "Kit"
        pads = {f"value{index}": index + 0x10 for index in range(128)}
        ET.SubElement(program, "ProgramPads").text = json.dumps(
            {
                "ProgramPads": {
                    "Universal": {"value0": False},
                    "Type": {"value0": 2},
                    "pads": pads,
                }
            }
        )
        ET.SubElement(program, "PadNoteMap").text = "UNCHANGED"
        instruments = ET.SubElement(program, "Instruments", custom="container")
        for number in range(1, 129):
            instrument = ET.SubElement(
                instruments, "Instrument", number=str(number), mystery=f"record-{number}"
            )
            ET.SubElement(instrument, "MuteGroup").text = str(number % 4)
            ET.SubElement(instrument, "OneShot").text = "True"
            layers = ET.SubElement(instrument, "Layers")
            layer = ET.SubElement(layers, "Layer", number="1")
            if number <= 2:
                filename = "Kick.wav" if number == 1 else "Snare.wav"
                ET.SubElement(layer, "SampleFile").text = filename
                ET.SubElement(layer, "SampleName").text = Path(filename).stem
                ET.SubElement(layer, "VelStart").text = "0"
                ET.SubElement(layer, "VelEnd").text = "127"
                ET.SubElement(layer, "SliceStart").text = "0"
                ET.SubElement(layer, "SliceEnd").text = "19"
        ET.ElementTree(root).write(path, encoding="UTF-8", xml_declaration=True)

    def _compressed_program(self, path: Path) -> None:
        instruments = []
        for index in range(128):
            filename = "Kick.wav" if index == 0 else "Snare.wav" if index == 1 else ""
            instruments.append(
                {
                    "mystery": f"record-{index + 1}",
                    "whichMuteGroup": index % 4,
                    "triggerMode": 0,
                    "layersv": [
                        {
                            "active": bool(filename),
                            "sampleFile": filename,
                            "sampleName": Path(filename).stem if filename else "",
                            "velocityStart": 0,
                            "velocityEnd": 127,
                            "sliceInfo": {"Start": 0, "End": 19},
                        }
                    ],
                }
            )
        document = {
            "data": {
                "name": "Kit",
                "type": 0,
                "unknownGlobal": {"keep": True},
                "drum": {"instruments": instruments},
                "programPads": {
                    "Universal": {"value0": False},
                    "Type": {"value0": 2},
                    "pads": {f"value{index}": index + 0x10 for index in range(128)},
                },
                "samples": [],
            }
        }
        prefix = b"ACVS\n3.9.1.2\nSerialisableProgramData\njson\nLinux\n"
        path.write_bytes(gzip.compress(prefix + json.dumps(document).encode(), mtime=0))

    def _write_wav(self, path: Path) -> None:
        with wave.open(str(path), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(44100)
            stream.writeframes(b"\0\0" * 20)

    def test_exports_xml_as_record_and_color_permutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "Source.xpm", root / "Output.xpm"
            self._xml_program(source)
            report = export_layout(source, output, self._plan(), name="Kit Swap")
            program = ET.parse(output).getroot().find("Program")
            first = program.find('./Instruments/Instrument[@number="1"]')
            second = program.find('./Instruments/Instrument[@number="2"]')
            colors = json.loads(program.findtext("ProgramPads"))["ProgramPads"]["pads"]
            self.assertEqual(first.findtext("./Layers/Layer/SampleFile"), "Snare.wav")
            self.assertEqual(first.get("mystery"), "record-2")
            self.assertEqual(second.findtext("./Layers/Layer/SampleFile"), "Kick.wav")
            self.assertEqual(colors["value0"], 0x11)
            self.assertEqual(colors["value1"], 0x10)
            self.assertEqual(program.findtext("PadNoteMap"), "UNCHANGED")
            self.assertTrue(report.record_bijection)
            self.assertTrue(report.global_settings_unchanged)

    def test_exports_compressed_as_record_and_color_permutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "Source.xpm", root / "Output.xpm"
            self._compressed_program(source)
            report = export_layout(source, output, self._plan(), name="Kit Swap")
            raw = gzip.decompress(output.read_bytes())
            document = json.loads(raw[raw.find(b"{") :])
            data = document["data"]
            self.assertEqual(data["drum"]["instruments"][0]["mystery"], "record-2")
            self.assertEqual(data["drum"]["instruments"][1]["mystery"], "record-1")
            self.assertEqual(data["programPads"]["pads"]["value0"], 0x11)
            self.assertEqual(data["programPads"]["pads"]["value1"], 0x10)
            self.assertEqual(data["unknownGlobal"], {"keep": True})
            self.assertEqual(report.source_format, "gzip-json")

    def test_explicit_color_override_is_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "Source.xpm", root / "Output.xpm"
            self._xml_program(source)
            report = export_layout(
                source,
                output,
                self._plan(),
                name="Kit Recolored",
                color_overrides={1: 0xABCDEF},
            )
            colors = json.loads(
                ET.parse(output).getroot().findtext("./Program/ProgramPads")
            )["ProgramPads"]["pads"]
            self.assertEqual(colors["value0"], 0xABCDEF)
            self.assertEqual(report.color_overrides, 1)
            self.assertTrue(report.colors_follow_records)

    def test_compressed_explicit_color_override_is_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "Source.xpm", root / "Output.xpm"
            self._compressed_program(source)
            report = export_layout(
                source,
                output,
                self._plan(),
                name="Kit Recolored",
                color_overrides={1: 0xABCDEF},
            )
            raw = gzip.decompress(output.read_bytes())
            colors = json.loads(raw[raw.find(b"{") :])["data"]["programPads"]["pads"]
            self.assertEqual(colors["value0"], 0xABCDEF)
            self.assertEqual(report.color_overrides, 1)
            self.assertTrue(report.colors_follow_records)

    def test_refuses_in_place_and_existing_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "Source.xpm", root / "Output.xpm"
            self._xml_program(source)
            with self.assertRaisesRegex(ValueError, "in-place"):
                export_layout(source, source, self._plan(), name="No")
            output.write_text("occupied", encoding="utf-8")
            with self.assertRaisesRegex(FileExistsError, "output exists"):
                export_layout(source, output, self._plan(), name="No")

    def test_independent_verifier_detects_instrument_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "Source.xpm", root / "Output.xpm"
            self._xml_program(source)
            export_layout(source, output, self._plan(), name="Kit Swap")
            tree = ET.parse(output)
            instrument = tree.getroot().find('./Program/Instruments/Instrument[@number="1"]')
            instrument.find("MuteGroup").text = "99"
            tree.write(output, encoding="UTF-8", xml_declaration=True)
            with self.assertRaisesRegex(ValueError, "records changed"):
                verify_layout_export(source, output, self._plan())

    def test_builds_self_contained_hardware_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "Source.xpm"
            self._xml_program(source)
            self._write_wav(root / "Kick.wav")
            self._write_wav(root / "Snare.wav")
            preset = root / "preset.toml"
            preset.write_text(
                'schema_version=1\nid="source"\nname="Source"\n'
                'strategy="sequential"\nfill_remaining=true\nprogram_suffix="Full"\n',
                encoding="utf-8",
            )
            device_path = Path(__file__).parents[1] / "devices/mpc-key-37.toml"
            output = root / "package"
            build_hardware_package(
                source,
                [preset],
                load_device(device_path),
                output,
                name_prefix="TEST",
            )
            manifest = json.loads((output / "manifest.json").read_text())
            program = output / manifest["variants"][0]["program"]
            self.assertTrue(program.is_file())
            self.assertTrue((program.parent / "Kick.wav").is_file())
            self.assertEqual(manifest["sample_count"], 2)
            self.assertEqual(manifest["variants"][0]["simulation"]["verdict"], "pass")
            self.assertIn("Hardware acceptance remains manual", (output / "README.md").read_text())


if __name__ == "__main__":
    unittest.main()
