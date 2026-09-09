import csv
import tempfile
import unittest
import tomllib
from pathlib import Path
from unittest import mock

from mpc_keygroup_builder import hardware


FIELDS = (
    "path",
    "program_type",
    "format",
    "structural_status",
    "sample_references",
    "simulation_scope",
    "semantic_verdict",
    "semantic_issues",
    "hardware_status",
    "favorite",
    "scratchpad_role",
    "notes",
)


class HardwareResultTests(unittest.TestCase):
    def write_ledger(self, path: Path) -> None:
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\r\n")
            writer.writeheader()
            writer.writerow(
                {
                    "path": "Programs/Bass.xpm",
                    "program_type": "Keygroup",
                    "hardware_status": "untested",
                    "favorite": "",
                    "scratchpad_role": "candidate:bass",
                    "notes": "Pending.",
                }
            )

    def test_loads_and_applies_valid_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger, session = root / "status.csv", root / "session.toml"
            self.write_ledger(ledger)
            session.write_text(
                '[[results]]\npath = "Programs/Bass.xpm"\n'
                'hardware_status = "pass"\nfavorite = "yes"\n'
                'scratchpad_role = "bass"\nnotes = "Even response across the keybed."\n'
            )
            results = hardware.load_results(session)
            changes = hardware.update_ledger(ledger, results, write=True)
            self.assertEqual(changes[0]["before"]["hardware_status"], "untested")
            with ledger.open(newline="", encoding="utf-8") as stream:
                row = next(csv.DictReader(stream))
            self.assertEqual(row["hardware_status"], "pass")
            self.assertEqual(row["favorite"], "yes")
            self.assertEqual(row["scratchpad_role"], "bass")
            self.assertEqual(row["notes"], "Even response across the keybed.")
            self.assertEqual(ledger.read_bytes().count(b"\r\n"), 2)

    def test_apply_flushes_the_replacement_before_promotion(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "status.csv"
            self.write_ledger(ledger)
            events = []
            real_fsync = hardware.os.fsync
            real_replace = hardware.os.replace
            with mock.patch.object(hardware.os, "fsync", side_effect=lambda fd: (events.append("fsync"), real_fsync(fd))[1]), mock.patch.object(
                hardware.os, "replace", side_effect=lambda source, target: (events.append("replace"), real_replace(source, target))[1]
            ):
                hardware.update_ledger(
                    ledger,
                    [{"path": "Programs/Bass.xpm", "hardware_status": "pass"}],
                    write=True,
                )
            self.assertEqual(events, ["fsync", "replace"])

    def test_dry_run_does_not_change_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "status.csv"
            self.write_ledger(ledger)
            before = ledger.read_bytes()
            hardware.update_ledger(
                ledger,
                [{"path": "Programs/Bass.xpm", "hardware_status": "fail"}],
            )
            self.assertEqual(ledger.read_bytes(), before)

    def test_rejects_invalid_status_and_unknown_program(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger, session = root / "status.csv", root / "session.toml"
            self.write_ledger(ledger)
            session.write_text(
                '[[results]]\npath = "Programs/Bass.xpm"\nhardware_status = "maybe"\n'
                'favorite = ""\nscratchpad_role = "bass"\nnotes = "Test note."\n'
            )
            with self.assertRaisesRegex(ValueError, "invalid hardware_status"):
                hardware.load_results(session)
            with self.assertRaisesRegex(ValueError, "not present"):
                hardware.update_ledger(
                    ledger,
                    [{"path": "Programs/Unknown.xpm", "hardware_status": "pass"}],
                )

    def test_initializes_results_from_candidate_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger, manifest, output = root / "status.csv", root / "candidates.toml", root / "work/results.toml"
            self.write_ledger(ledger)
            manifest.write_text(
                'schema_version = 1\nname = "Test"\n[[candidates]]\nid = "bass"\n'
                'ledger_path = "Programs/Bass.xpm"\nsd_path = "Programs/Bass.xpm"\n'
                'role = "bass"\nselected = true\n'
            )
            self.assertEqual(hardware.initialize_results(ledger, manifest, output), 1)
            with output.open("rb") as stream:
                result = tomllib.load(stream)["results"][0]
            self.assertEqual(result["path"], "Programs/Bass.xpm")
            self.assertEqual(result["hardware_status"], "untested")
            with self.assertRaises(FileExistsError):
                hardware.initialize_results(ledger, manifest, output)

    def test_initialize_refuses_broken_output_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger = root / "status.csv"
            manifest = root / "candidates.toml"
            self.write_ledger(ledger)
            manifest.write_text(
                'schema_version = 1\nname = "Test"\n[[candidates]]\nid = "bass"\n'
                'ledger_path = "Programs/Bass.xpm"\nsd_path = "Programs/Bass.xpm"\n'
                'role = "bass"\nselected = true\n'
            )
            external = root / "outside" / "results.toml"
            output = root / "results-link.toml"
            output.symlink_to(external)

            with self.assertRaisesRegex(ValueError, "output.*symbolic link"):
                hardware.initialize_results(ledger, manifest, output)
            self.assertFalse(external.exists())

    def test_update_rejects_duplicate_ledger_paths_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "status.csv"
            self.write_ledger(ledger)
            original = ledger.read_text()
            ledger.write_text(original + original.splitlines()[-1] + "\n")
            before = ledger.read_bytes()
            with self.assertRaisesRegex(ValueError, "duplicate program path"):
                hardware.update_ledger(
                    ledger,
                    [{"path": "Programs/Bass.xpm", "hardware_status": "pass"}],
                    write=True,
                )
            self.assertEqual(ledger.read_bytes(), before)

    def test_initialize_rejects_malformed_ledger_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger, manifest, output = (
                root / "status.csv",
                root / "candidates.toml",
                root / "results.toml",
            )
            ledger.write_text("path,hardware_status\nPrograms/Bass.xpm,untested\n")
            manifest.write_text(
                'schema_version = 1\n[[candidates]]\nid = "bass"\n'
                'ledger_path = "Programs/Bass.xpm"\nsd_path = "Programs/Bass.xpm"\n'
                'role = "bass"\nselected = true\n'
            )
            with self.assertRaisesRegex(ValueError, "ledger is missing fields"):
                hardware.initialize_results(ledger, manifest, output)
            self.assertFalse(output.exists())

    def test_initialize_cleans_up_after_publication_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger, manifest, output = root / "status.csv", root / "candidates.toml", root / "work/results.toml"
            self.write_ledger(ledger)
            manifest.write_text(
                'schema_version = 1\nname = "Test"\n[[candidates]]\nid = "bass"\n'
                'ledger_path = "Programs/Bass.xpm"\nsd_path = "Programs/Bass.xpm"\n'
                'role = "bass"\nselected = true\n'
            )
            with mock.patch.object(hardware.os, "replace", side_effect=OSError("disk disconnected")):
                with self.assertRaisesRegex(OSError, "disk disconnected"):
                    hardware.initialize_results(ledger, manifest, output)
            self.assertFalse(output.exists())
            self.assertEqual(list(output.parent.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
