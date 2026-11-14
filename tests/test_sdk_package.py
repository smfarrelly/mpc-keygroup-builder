import json
from pathlib import Path
import struct
import tempfile
import unittest

from mpc_keygroup_builder import sdk_package


def elf32():
    header = bytearray(88)
    header[:7] = b"\x7fELF\x01\x01\x01"
    struct.pack_into("<HHI", header, 16, 3, 40, 1)
    struct.pack_into("<I", header, 28, 52)
    struct.pack_into("<I", header, 36, 0x05000400)
    struct.pack_into("<HHH", header, 40, 52, 32, 1)
    struct.pack_into("<8I", header, 52, 1, 0, 0, 0, 88, 88, 5, 4)
    return header


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "MPC SDK Examples - VST - Stereo Delay"
        self.root.mkdir()
        self.binary = self.root / "delay.so"
        self.binary.write_bytes(elf32())
        self.manifest = {"name": "Stereo Delay", "manufacturer": "MPC SDK Examples",
                         "format": "vst2", "uid": "MxSd", "file": "delay.so",
                         "kind": "effect", "numInputs": 2, "numOutputs": 2}
        self.dump = Path(__file__).parent / "fixtures/sdk/stereo-delay.json"

    def inspect(self, **kwargs):
        (self.root / "plugin.json").write_text(json.dumps(self.manifest))
        return sdk_package.inspect(self.root, **kwargs)

    def test_read_only_package_and_dump_check(self):
        before = self.binary.read_bytes()
        result = self.inspect(dump=self.dump)
        self.assertEqual(result["hardware_status"], "untested")
        self.assertEqual(result["uid"], 1299731300)
        self.assertEqual(result["binary"]["bytes"], len(before))
        self.assertEqual(result["install_relative_path"], f"VST2 Plugins/{self.root.name}")
        self.assertEqual(self.binary.read_bytes(), before)

    def test_binary_selection_does_not_fall_back_across_targets(self):
        self.manifest["file64"] = "delay.so"
        with self.assertRaisesRegex(ValueError, "no file32"):
            self.inspect()
        with self.assertRaisesRegex(ValueError, "arm64"):
            self.inspect(target="arm64")

    def test_signed_uid_and_punctuation_handling(self):
        self.assertEqual(sdk_package.manifest_uid("0xFAFA1111"), 0xfafa1111)
        self.assertEqual(sdk_package.manifest_uid("1299731300"), 1299731300)
        self.manifest["uid"] = "FAKE"
        with self.assertRaisesRegex(ValueError, "uidInt"):
            self.inspect(dump=self.dump)
        self.manifest["name"] = "Another Name"
        with self.assertRaisesRegex(ValueError, "folder should be named"):
            self.inspect()

    def test_wrong_abi_truncation_and_missing_segments(self):
        for field, offset, value in [("machine", 18, 62), ("flags", 37, 2),
                                     ("offset", 28, 255), ("segment", 52, 0),
                                     ("filesz", 68, 255)]:
            with self.subTest(field=field):
                image = elf32()
                image[offset] = value
                self.binary.write_bytes(image)
                with self.assertRaises(ValueError):
                    self.inspect()
        self.binary.write_bytes(elf32()[:18])
        with self.assertRaises(ValueError):
            self.inspect()

    def test_nonportable_paths_and_symlinks(self):
        for path in ("../one.so", "C:/temp/one.so", "/tmp/one.so", "VST\\one.so"):
            self.manifest["file"] = path
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.inspect()
        self.manifest["file"] = "link.so"
        try:
            (self.root / "link.so").symlink_to(self.binary)
        except OSError:
            self.skipTest("symlink creation unavailable")
        with self.assertRaisesRegex(ValueError, "symbolic link"):
            self.inspect()
