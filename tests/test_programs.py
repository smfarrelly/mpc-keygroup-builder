import gzip
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from mpc_keygroup_builder import programs


class ProgramTests(unittest.TestCase):
    def write_drum(self, path: Path) -> None:
        pads = {f"value{index}": 0 for index in range(128)}
        payload = json.dumps(
            {
                "ProgramPads": {
                    "Universal": {"value0": True},
                    "Type": {"value0": 1},
                    "pads": pads,
                }
            }
        )
        path.write_text(
            '<?xml version="1.0"?><MPCVObject><Program type="Drum">'
            f"<ProgramName>Kit</ProgramName><ProgramPads>{payload}</ProgramPads><Instruments>"
            '<Instrument number="1"><Layers><Layer><SampleFile>BD 808.wav</SampleFile></Layer></Layers></Instrument>'
            '<Instrument number="2"><Layers><Layer><SampleFile>Snare Vinyl.wav</SampleFile></Layer></Layers></Instrument>'
            '<Instrument number="49"><Layers><Layer><SampleFile>Closed Hat.wav</SampleFile></Layer></Layers></Instrument>'
            "</Instruments><PadNoteMap>"
            '<PadNote number="1"><Note>36</Note></PadNote>'
            '<PadNote number="2"><Note>38</Note></PadNote>'
            '<PadNote number="3"><Note>42</Note></PadNote>'
            "</PadNoteMap></Program></MPCVObject>", encoding="utf-8"
        )

    def write_serialized_program(self, path: Path, program_type: int) -> None:
        pads = {f"value{index}": 0 for index in range(128)}
        data = {
            "data": {
                "version": 6,
                "name": "Kit",
                "type": program_type,
                "programPads": {
                    "Universal": {"value0": True},
                    "Type": {"value0": 1},
                    "pads": pads,
                },
            }
        }
        if program_type == 0:
            data["data"]["drum"] = {
                "instruments": [
                    {"layersv": [{"sampleFile": "BD 808.wav", "sampleName": "BD 808"}]},
                    {"layersv": [{"sampleFile": "SD 606.wav", "sampleName": "SD 606"}]},
                ]
            }
        payload = b"ACVS\n3.9.1.2\nSerialisableProgramData\njson\nLinux\n" + json.dumps(data).encode()
        path.write_bytes(gzip.compress(payload, mtime=0))

    def test_classifies_common_drum_names(self):
        self.assertEqual(programs.classify_sample("BD 808 Long.wav"), "kick")
        self.assertEqual(programs.classify_sample("SD 606 Dirty.wav"), "snare")
        self.assertEqual(programs.classify_sample("HH 808 Tube CH.wav"), "closed_hat")
        self.assertEqual(programs.classify_sample("Crash Clean.wav"), "cymbal")
        self.assertEqual(programs.classify_sample("Rim 808.wav"), "rim")
        self.assertEqual(programs.classify_sample("Clap 909.wav"), "clap")

    def test_exact_filename_override(self):
        self.assertEqual(
            programs.classify_sample(
                "Clap 808 Skip Bell.wav", {"clap 808 skip bell.wav": "percussion"}
            ),
            "percussion",
        )

    def test_rgb888_matches_mpc_resaved_values(self):
        self.assertEqual(programs.rgb888("#ff0000"), 0xFF0000)
        self.assertEqual(programs.rgb888("#11ff00"), 0x11FF00)
        self.assertEqual(programs.rgb888("#0022ff"), 0x0022FF)

    def test_default_palette_matches_hardware_reference(self):
        palette = programs.load_palette()
        self.assertEqual(palette["kick"], 0xFF0000)
        self.assertEqual(palette["snare"], 0x0022FF)
        self.assertEqual(palette["closed_hat"], 0xE6FF00)
        self.assertEqual(palette["open_hat"], 0x00F7FF)
        self.assertEqual(palette["tom"], 0x11FF00)
        self.assertEqual(palette["cymbal"], 0xFF8800)

    def test_detect_and_colorize_drum(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "Kit.xpm", root / "Colored.xpm"
            self.write_drum(source)
            self.assertEqual(programs.detect_program_type(source), "drum")
            counts = programs.colorize_drum_program(source, output, programs.load_palette())
            self.assertEqual(counts, {"kick": 1, "snare": 1, "closed_hat": 1})
            node = ET.parse(output).getroot().find("Program/ProgramPads")
            settings = json.loads(node.text)["ProgramPads"]
            pads = settings["pads"]
            self.assertFalse(settings["Universal"]["value0"])
            self.assertEqual(settings["Type"]["value0"], 2)
            self.assertEqual(pads["value0"], programs.rgb888("#ff0000"))
            self.assertEqual(pads["value1"], programs.rgb888("#0022ff"))
            self.assertEqual(pads["value48"], programs.rgb888("#e6ff00"))

    def test_colorize_can_give_test_copy_a_distinct_name(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "Kit.xpm", root / "Colored.xpm"
            self.write_drum(source)
            programs.colorize_drum_program(
                source, output, programs.load_palette(), name="Kit COLOR TEST"
            )
            self.assertEqual(
                ET.parse(output).getroot().findtext("Program/ProgramName"),
                "Kit COLOR TEST",
            )

    def test_detects_and_colorizes_mpc_resaved_drum_program(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "Kit.xpm", root / "Colored.xpm"
            self.write_serialized_program(source, 0)
            self.assertEqual(programs.detect_program_type(source), "drum")
            counts = programs.colorize_drum_program(
                source, output, programs.load_palette(), name="Colored Kit"
            )
            self.assertEqual(counts, {"kick": 1, "snare": 1})
            raw = gzip.decompress(output.read_bytes())
            data = json.loads(raw[raw.find(b"{"):])["data"]
            self.assertEqual(data["name"], "Colored Kit")
            self.assertFalse(data["programPads"]["Universal"]["value0"])
            self.assertEqual(data["programPads"]["Type"]["value0"], 2)
            self.assertEqual(data["programPads"]["pads"]["value0"], 0xFF0000)
            self.assertEqual(data["programPads"]["pads"]["value1"], 0x0022FF)

    def test_detects_mpc_resaved_keygroup_program(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "Keys.xpm"
            self.write_serialized_program(source, 1)
            self.assertEqual(programs.detect_program_type(source), "keygroup")

    def test_explicit_type_rejects_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "Kit.xpm"
            self.write_drum(source)
            with self.assertRaisesRegex(ValueError, "requested keygroup"):
                programs.resolve_program_type(source, "keygroup")


if __name__ == "__main__":
    unittest.main()
