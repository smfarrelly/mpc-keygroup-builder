import csv
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import candidates


class CandidateTests(unittest.TestCase):
    def write_manifest(self, path: Path) -> None:
        path.write_text(
            'schema_version = 1\nname = "Test Rig"\n'
            '[[candidates]]\nid = "drums"\nledger_path = "Drums.xpm"\n'
            'sd_path = "Programs/Drums.xpm"\nrole = "main drums"\nselected = true\n'
            '[[candidates]]\nid = "bass"\nledger_path = "Bass.xpm"\n'
            'sd_path = "Programs/Bass.xpm"\nrole = "bass"\nselected = true\n'
        )

    def write_ledger(self, path: Path) -> None:
        fields = [
            "path", "hardware_status", "favorite", "scratchpad_role", "notes",
        ]
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerow({"path": "Drums.xpm", "hardware_status": "pass", "favorite": "yes", "scratchpad_role": "main drums", "notes": "Good."})
            writer.writerow({"path": "Bass.xpm", "hardware_status": "untested", "favorite": "provisional", "scratchpad_role": "bass", "notes": "Pending."})

    def test_reports_independent_readiness_gates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, ledger = root / "candidates.toml", root / "status.csv"
            self.write_manifest(manifest)
            self.write_ledger(ledger)
            report = candidates.check_candidates(manifest, ledger)
            self.assertTrue(report["readiness"]["deployed"])
            self.assertFalse(report["readiness"]["hardware"])
            self.assertFalse(report["readiness"]["core"])
            self.assertFalse(report["readiness"]["final"])
            self.assertTrue(any("bass: hardware listening is untested" in issue for issue in report["issues"]))

    def test_rejects_duplicate_manifest_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "candidates.toml"
            self.write_manifest(path)
            path.write_text(path.read_text() + '\n[[candidates]]\nid="bass"\nledger_path="Other.xpm"\nsd_path="Other.xpm"\nrole="lead"\nselected=false\n')
            with self.assertRaisesRegex(ValueError, "duplicates"):
                candidates.load_manifest(path)


if __name__ == "__main__":
    unittest.main()
