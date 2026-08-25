import gzip
import json
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import xpj


def write_xpj(path: Path, data: dict, firmware: str = "3.7.0.56") -> Path:
    header = f"ACVS\n{firmware}\nSerialisableProjectData\njson\nLinux\n".encode()
    path.write_bytes(gzip.compress(header + json.dumps({"formatVersion": 2, "data": data}).encode()))
    return path


class XPJTests(unittest.TestCase):
    def test_load_and_summarize_mpc3_project(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = write_xpj(
                Path(temporary) / "Test.xpj",
                {
                    "version": 28,
                    "masterTempo": 120.0,
                    "tracks": [
                        {
                            "name": "Kit",
                            "samples": [{"name": "Kick"}],
                            "program": {"name": "Kit", "type": 0},
                            "outputChannel": 0,
                        },
                        {"name": "Keys", "samples": [], "program": {"name": "Piano", "type": 1}},
                    ],
                    "sequences": [{"key": 0, "value": {"name": "Sequence 01", "bpm": 96.0, "lengthBars": 4}}],
                    "samples": [{"name": "Kick"}],
                },
            )
            project = xpj.load(path)
            summary = xpj.summarize(project)
            self.assertEqual(project.header.firmware, "3.7.0.56")
            self.assertEqual(summary["track_types"], {"Drum": 1, "Keygroup": 1})
            self.assertEqual(summary["sequence_count"], 1)
            self.assertEqual(summary["project_sample_count"], 1)

    def test_detects_mpc2_xml_without_treating_it_as_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "Old.xpj"
            path.write_text('<?xml version="1.0"?><MPCProject/>', encoding="utf-8")
            self.assertEqual(xpj.summarize(xpj.load(path))["generation"], 2)

    def test_rejects_invalid_acvs_header(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "Bad.xpj"
            path.write_bytes(gzip.compress(b"NOPE\n3.7\nObject\njson\nLinux\n{}"))
            with self.assertRaisesRegex(ValueError, "header magic"):
                xpj.load(path)

    def test_compare_reports_json_pointer_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            left = write_xpj(root / "Left.xpj", {"version": 28, "tracks": [{"name": "Old"}]})
            right = write_xpj(root / "Right.xpj", {"version": 28, "tracks": [{"name": "New"}], "masterTempo": 99.0})
            result = xpj.compare(xpj.load(left), xpj.load(right))
            by_path = {change["path"]: change for change in result["changes"]}
            self.assertEqual(by_path["/data/tracks/0/name"]["kind"], "changed")
            self.assertEqual(by_path["/data/masterTempo"]["kind"], "added")

    def test_crlf_header_is_accepted(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "Windows.xpj"
            header = b"ACVS\r\n3.7\r\nSerialisableProjectData\r\njson\r\nWindows\r\n"
            path.write_bytes(gzip.compress(header + b'{"data": {}}'))
            self.assertEqual(xpj.load(path).header.platform, "Windows")


if __name__ == "__main__":
    unittest.main()
