import json
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import capture


class CaptureTests(unittest.TestCase):
    def make_pair(self, root: Path, stem: str, content: bytes) -> None:
        (root / f"{stem}.xpj").write_bytes(content)
        data = root / f"{stem}_[ProjectData]"
        data.mkdir()
        (data / "Programs.db").write_bytes(content[::-1])

    def test_copies_and_verifies_two_projects_and_data_folders(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "sd", root / "capture"
            source.mkdir()
            self.make_pair(source, "Key37_Routing_Baseline", b"baseline")
            self.make_pair(source, "Key37_Routing_Changed", b"changed")

            manifest = capture.capture_projects(source, output)

            self.assertEqual((output / "Key37_Routing_Baseline.xpj").read_bytes(), b"baseline")
            self.assertEqual((output / "Key37_Routing_Changed.xpj").read_bytes(), b"changed")
            self.assertEqual(len(manifest["files"]), 4)
            written = json.loads((output / "capture-manifest.json").read_text())
            self.assertEqual(written["changed_setting"], "Key Ranges: Drum Split")
            self.assertTrue(all(len(item["sha256"]) == 64 for item in written["files"]))

    def test_refuses_missing_project_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "sd"
            source.mkdir()
            (source / "Key37_Routing_Baseline.xpj").write_bytes(b"baseline")
            self.make_pair(source, "Key37_Routing_Changed", b"changed")
            with self.assertRaisesRegex(ValueError, "ProjectData"):
                capture.capture_projects(source, root / "capture")

    def test_refuses_nonempty_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "sd", root / "capture"
            source.mkdir()
            self.make_pair(source, "Key37_Routing_Baseline", b"baseline")
            self.make_pair(source, "Key37_Routing_Changed", b"changed")
            output.mkdir()
            (output / "keep.txt").write_text("preserve")
            with self.assertRaises(FileExistsError):
                capture.capture_projects(source, output)
            self.assertEqual((output / "keep.txt").read_text(), "preserve")

    def test_refuses_nested_symlink_before_creating_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output, outside = root / "sd", root / "capture", root / "outside"
            source.mkdir()
            outside.mkdir()
            (outside / "private.db").write_bytes(b"outside")
            self.make_pair(source, "Key37_Routing_Baseline", b"baseline")
            self.make_pair(source, "Key37_Routing_Changed", b"changed")
            data = source / "Key37_Routing_Changed_[ProjectData]"
            (data / "external").symlink_to(outside, target_is_directory=True)

            with self.assertRaisesRegex(ValueError, "symbolic links"):
                capture.capture_projects(source, output)

            self.assertFalse(output.exists())
            self.assertEqual((outside / "private.db").read_bytes(), b"outside")


if __name__ == "__main__":
    unittest.main()
