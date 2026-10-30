import csv
import contextlib
import io
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from pathlib import Path

from mpc_keygroup_builder import candidates, entrypoints


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

    def test_duplicate_selected_roles_block_core_and_final(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, ledger = root/'candidates.toml', root/'status.csv'
            self.write_manifest(manifest)
            manifest.write_text(manifest.read_text().replace('role = "bass"', 'role = "main drums"'))
            self.write_ledger(ledger)
            ledger.write_text(ledger.read_text().replace('untested', 'pass').replace('provisional', 'yes'))
            report = candidates.check_candidates(manifest, ledger)
            self.assertTrue(report['readiness']['hardware'])
            self.assertFalse(report['readiness']['core'])
            self.assertFalse(report['readiness']['final'])
            self.assertIn('selected core duplicates roles: main drums', report['issues'])

    def test_sd_paths_cannot_escape_or_use_host_path_syntax(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'candidates.toml'
            self.write_manifest(path)
            original = path.read_text()
            for replacement in ('../Drums.xpm', '/tmp/Drums.xpm', 'C:/Drums.xpm', '.'):
                with self.subTest(path=replacement):
                    path.write_text(original.replace('Programs/Drums.xpm', replacement))
                    with self.assertRaisesRegex(ValueError, 'relative path inside the SD root'):
                        candidates.load_manifest(path)

    def test_external_symlink_is_not_counted_as_sd_deployment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, ledger = root/'candidates.toml', root/'status.csv'
            self.write_manifest(manifest)
            self.write_ledger(ledger)
            sd = root/'sd'
            sd.mkdir()
            try:
                (sd/'Programs').symlink_to(root, target_is_directory=True)
            except OSError:
                self.skipTest('symlinks unavailable')
            with patch.object(candidates, 'test_program') as inspect:
                with self.assertRaisesRegex(ValueError, 'outside the SD root'):
                    candidates.check_candidates(manifest, ledger, sd)
                inspect.assert_not_called()

    def test_ambiguous_and_invalid_ledgers_fail_before_readiness(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, ledger = root/'candidates.toml', root/'status.csv'
            self.write_manifest(manifest)
            self.write_ledger(ledger)
            original = ledger.read_text()
            cases = [
                (original + original.splitlines()[1]+'\n', 'duplicate program path'),
                (original.replace('untested', 'unknown'), 'invalid hardware_status'),
                (original.replace('provisional', 'maybe'), 'invalid favorite'),
                ('path,notes\nDrums.xpm,Good\n', 'missing fields'),
            ]
            for contents, message in cases:
                with self.subTest(message=message):
                    ledger.write_text(contents)
                    with self.assertRaisesRegex(ValueError, message):
                        candidates.check_candidates(manifest, ledger)

    def test_sd_warnings_retain_actionable_details_in_json_and_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, ledger = root/'candidates.toml', root/'status.csv'
            self.write_manifest(manifest)
            self.write_ledger(ledger)
            (root/'Programs').mkdir()
            for name in ('Drums.xpm', 'Bass.xpm'):
                (root/'Programs'/name).touch()
            detail = SimpleNamespace(severity='warning', code='extreme_key_extrapolation', message='notes 0-24 use root 24')
            with patch.object(candidates, 'test_program', return_value=SimpleNamespace(verdict='warn', issues=[detail])):
                report = candidates.check_candidates(manifest, ledger, root)
                self.assertTrue(report['readiness']['deployed'])
                self.assertEqual(report['candidates'][0]['sd_issues'][0]['message'], detail.message)
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    status = entrypoints.invoke('mpc-scratchpad-check', [str(manifest), '--ledger', str(ledger), '--sd-root', str(root)])
                self.assertEqual(status, 0)
                self.assertIn('WARNING extreme_key_extrapolation: notes 0-24 use root 24', output.getvalue())
            unchecked = candidates.check_candidates(manifest, ledger)
            self.assertEqual(unchecked['candidates'][0]['sd_issues'], [])

    def test_reports_independent_readiness_gates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, ledger = root / "candidates.toml", root / "status.csv"
            self.write_manifest(manifest)
            self.write_ledger(ledger)
            report = candidates.check_candidates(manifest, ledger)
            self.assertIsNone(report["readiness"]["deployed"])
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

    def test_rejects_non_string_and_empty_required_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "candidates.toml"
            self.write_manifest(path)
            original = path.read_text()
            for field, replacement in (
                ("id", 'id = ["drums"]'),
                ("ledger_path", 'ledger_path = ""'),
                ("sd_path", 'sd_path = 37'),
                ("role", 'role = "   "'),
            ):
                with self.subTest(field=field):
                    line = next(
                        item for item in original.splitlines() if item.startswith(f"{field} =")
                    )
                    path.write_text(original.replace(line, replacement, 1))
                    with self.assertRaisesRegex(
                        ValueError, rf"candidate 1 {field} must be a nonempty string"
                    ):
                        candidates.load_manifest(path)

    def test_invalid_field_is_friendly_through_installed_command(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "candidates.toml"
            self.write_manifest(path)
            path.write_text(path.read_text().replace('id = "drums"', 'id = ["drums"]'))
            error = io.StringIO()
            with contextlib.redirect_stderr(error):
                status = entrypoints.invoke("mpc-scratchpad-check", [str(path)])
            self.assertEqual(status, 2)
            self.assertIn("candidate 1 id must be a nonempty string", error.getvalue())
            self.assertNotIn("Traceback", error.getvalue())

    def test_rejects_missing_sd_root_instead_of_reporting_every_program_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, ledger = root / "candidates.toml", root / "status.csv"
            self.write_manifest(manifest)
            self.write_ledger(ledger)
            with self.assertRaisesRegex(ValueError, "not a mounted directory"):
                candidates.check_candidates(manifest, ledger, root / "missing-card")

    def test_required_roles_prevent_incomplete_core_from_being_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, ledger = root / "candidates.toml", root / "status.csv"
            self.write_manifest(manifest)
            manifest.write_text(
                manifest.read_text().replace(
                    'name = "Test Rig"',
                    'name = "Test Rig"\nrequired_roles = ["main drums", "bass", "keys"]',
                )
            )
            self.write_ledger(ledger)
            report = candidates.check_candidates(manifest, ledger)
            self.assertFalse(report["readiness"]["core"])
            self.assertIn("selected core is missing roles: keys", report["issues"])


if __name__ == "__main__":
    unittest.main()
