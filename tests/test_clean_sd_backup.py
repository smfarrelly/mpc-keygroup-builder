import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "clean_sd_backup.py"
SPEC = importlib.util.spec_from_file_location("clean_sd_backup", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class CleanupTests(unittest.TestCase):
    def test_only_identical_redundant_files_are_removed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            samples = root / "Samples" / "Samples From Mars"
            redundant = samples / "Instruments"
            (samples / "Kit").mkdir(parents=True)
            (redundant / "Kit").mkdir(parents=True)
            (samples / "Kit" / "same.wav").write_bytes(b"same")
            (redundant / "Kit" / "same.wav").write_bytes(b"same")
            (redundant / "Kit" / "unique.wav").write_bytes(b"unique")
            report = MODULE.Report(root=str(root), execute=True)

            MODULE.remove_redundant_instruments(root, True, report)

            self.assertFalse((redundant / "Kit" / "same.wav").exists())
            self.assertTrue((redundant / "Kit" / "unique.wav").exists())
            self.assertEqual(report.duplicate_files, 1)
            self.assertEqual(report.unique_files_retained, 1)

    def test_root_program_and_data_move_as_bundle(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "Testing keygroup.xpm").write_bytes(b"program")
            data = root / "Testing keygroup_[ProgramData]"
            data.mkdir()
            (data / "sample.wav").write_bytes(b"sample")
            report = MODULE.Report(root=str(root), execute=True)

            MODULE.move_root_test_programs(root, True, report)

            destination = root / "Programs" / "Keygroups" / "Testing"
            self.assertTrue((destination / "Testing keygroup.xpm").is_file())
            self.assertTrue(
                (destination / "Testing keygroup_[ProgramData]" / "sample.wav").is_file()
            )
            self.assertEqual(report.program_bundles, 1)


if __name__ == "__main__":
    unittest.main()
