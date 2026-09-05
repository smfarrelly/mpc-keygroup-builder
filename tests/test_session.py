import csv
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import session


class SessionTests(unittest.TestCase):
    def test_combines_rig_and_candidate_next_actions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "candidates.toml"
            manifest.write_text('schema_version=1\n[[candidates]]\nid="bass"\nledger_path="Bass.xpm"\nsd_path="Bass.xpm"\nrole="bass"\nselected=true\n')
            ledger = root / "status.csv"
            fields = ["path", "hardware_status", "favorite", "scratchpad_role", "notes"]
            with ledger.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerow({"path": "Bass.xpm", "hardware_status": "untested", "favorite": "provisional", "scratchpad_role": "bass", "notes": ""})
            profile = root / "rig.toml"
            profile.write_text('schema_version=1\nname="Rig"\n[[tracks]]\nindex=1\nname="Bass"\nrole="bass"\ntype="keygroup"\nprogram="Bass"\n')
            report = session.build_report(manifest, ledger, profile, routing_report=root / "missing.json")
            self.assertTrue(any("hardware listening" in item for item in report["next_actions"]))
            self.assertIn("controlled routing capture is not available", report["next_actions"])

    def test_optional_evidence_distinguishes_missing_from_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertIsNone(session._read_optional(root / "missing.json"))

            report = root / "report.json"
            report.write_text('{"format": 1}')
            self.assertEqual(session._read_optional(report), {"format": 1})

            report.write_text("[]")
            with self.assertRaisesRegex(ValueError, "JSON object"):
                session._read_optional(report)

            evidence_dir = root / "evidence"
            evidence_dir.mkdir()
            with self.assertRaisesRegex(ValueError, "not a regular file"):
                session._read_optional(evidence_dir)

    def test_optional_evidence_refuses_symbolic_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            external = root / "external.json"
            external.write_text('{"private": true}')
            linked = root / "routing.json"
            linked.symlink_to(external)
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                session._read_optional(linked)
            self.assertEqual(external.read_text(), '{"private": true}')


if __name__ == "__main__":
    unittest.main()
