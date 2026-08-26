import gzip
import json
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import xpm


class XpmTests(unittest.TestCase):
    def write_xml(self, path: Path, color: int = 0xFF0000) -> None:
        pads = {"ProgramPads": {"Universal": {"value0": False}, "Type": {"value0": 2}, "pads": {"value0": color}}}
        path.write_text(
            '<?xml version="1.0"?><MPCVObject Version="2.1"><Program type="Drum">'
            '<ProgramName>Kit</ProgramName><ProgramPads>'
            + json.dumps(pads)
            + '</ProgramPads><Instruments><Instrument number="1"><Layers><Layer>'
            '<SampleFile>BD 808.wav</SampleFile></Layer></Layers></Instrument>'
            '</Instruments></Program></MPCVObject>',
            encoding="utf-8",
        )

    def write_serialized(self, path: Path) -> None:
        data = {
            "data": {
                "name": "Bass",
                "type": 1,
                "programPads": {"Universal": {"value0": True}, "Type": {"value0": 1}, "pads": {}},
                "drum": {"instruments": [{"layersv": [{"sampleFile": "Bass C3.wav"}]}]},
            }
        }
        payload = b"ACVS\n3.9.1.2\nSerialisableProgramData\njson\nLinux\n" + json.dumps(data).encode()
        path.write_bytes(gzip.compress(payload, mtime=0))

    def test_inspects_xml_program(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Kit.xpm"
            self.write_xml(path)
            report = xpm.inspect(path)
            self.assertEqual(report["program_type"], "Drum")
            self.assertEqual(report["sample_references"], 1)
            self.assertEqual(report["sample_categories"], {"kick": 1})
            self.assertEqual(report["pad_colors"], {"#FF0000": 1})

    def test_inspects_compressed_keygroup(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Bass.xpm"
            self.write_serialized(path)
            report = xpm.inspect(path)
            self.assertEqual(report["format"], "gzip-json")
            self.assertEqual(report["program_type"], "Keygroup")
            self.assertEqual(report["firmware_or_schema"], "3.9.1.2")

    def test_compares_embedded_program_pad_json(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before, after = root / "Before.xpm", root / "After.xpm"
            self.write_xml(before, 0xFF0000)
            self.write_xml(after, 0x00FF00)
            report = xpm.compare_programs(before, after)
            self.assertEqual(report["change_count"], 1)
            self.assertIn("program_pads", report["changes"][0]["path"])
            self.assertEqual(report["changes"][0]["before"], 0xFF0000)
            self.assertEqual(report["changes"][0]["after"], 0x00FF00)
            self.assertEqual(report["structural_change_count"], 1)


if __name__ == "__main__":
    unittest.main()
