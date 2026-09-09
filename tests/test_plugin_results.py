import csv
import tempfile
import tomllib
import unittest
from pathlib import Path

from mpc_keygroup_builder import plugin_results


def companion():
    return {
        "fingerprint": "abc123",
        "pages": [
            {
                "id": "filter",
                "name": "Filter",
                "slot": 7,
                "channel": 11,
                "controls": [
                    {
                        "control": "top-encoder-1",
                        "cc": 20,
                        "plugin": "Test Filter",
                        "name": "Cutoff",
                        "ui_parameter": 1,
                        "mpc_parameter": 4097,
                        "evidence": "hypothesis:+4096",
                        "priority": "core",
                    }
                ],
            }
        ],
    }


def results():
    return {
        "schema_version": 1,
        "kind": "mpc-plugin-mapping-results",
        "fingerprint": "abc123",
        "exported_at": "2026-09-04T12:00:00.000Z",
        "pages": [
            {
                "id": "filter",
                "controls": [
                    {
                        "control": "top-encoder-1",
                        "plugin": "Test Filter",
                        "target": "Cutoff",
                        "status": "pass",
                        "notes": "Smooth sweep.",
                    }
                ],
            }
        ],
    }


class PluginResultTests(unittest.TestCase):
    def test_applies_complete_matching_export(self):
        rows = plugin_results.apply_results(companion(), results())
        self.assertEqual(rows[0]["status"], "pass")
        self.assertEqual(rows[0]["notes"], "Smooth sweep.")
        self.assertEqual(rows[0]["observed_at"], "2026-09-04T12:00:00.000Z")
        self.assertIn("Smooth sweep.", plugin_results.render_csv(rows))
        self.assertIn("1 pass", plugin_results.render_report(rows, "abc123"))

    def test_rejects_stale_fingerprint_and_target_tampering(self):
        stale = results()
        stale["fingerprint"] = "old"
        with self.assertRaisesRegex(ValueError, "fingerprint mismatch"):
            plugin_results.apply_results(companion(), stale)
        tampered = results()
        tampered["pages"][0]["controls"][0]["target"] = "Resonance"
        with self.assertRaisesRegex(ValueError, "target mismatch"):
            plugin_results.apply_results(companion(), tampered)

    def test_rejects_missing_controls_and_invalid_status(self):
        missing = results()
        missing["pages"][0]["controls"] = []
        with self.assertRaisesRegex(ValueError, "missing 1 controls"):
            plugin_results.apply_results(companion(), missing)
        invalid = results()
        invalid["pages"][0]["controls"][0]["status"] = "great"
        with self.assertRaisesRegex(ValueError, "invalid status"):
            plugin_results.apply_results(companion(), invalid)

    def test_repository_pending_ledger_matches_profiles(self):
        root = Path(__file__).parents[1]
        with (root / "inventory/plugin-control-status.csv").open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        expected = 0
        for path in (root / "midi/plugins").glob("*.toml"):
            with path.open("rb") as stream:
                expected += len(tomllib.load(stream)["controls"])
        self.assertEqual(len(rows), expected)
        self.assertEqual(len({(row["profile"], row["control"]) for row in rows}), expected)
        self.assertEqual({row["status"] for row in rows}, {"pending"})
        self.assertEqual(len({row["mapping_fingerprint"] for row in rows}), 1)

    def test_outputs_are_jointly_preflighted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger = root / "ledger.csv"
            report = root / "report-directory"
            report.mkdir()
            with self.assertRaisesRegex(ValueError, "report must be a regular file"):
                plugin_results._output_paths(ledger, report, force=True)
            self.assertFalse(ledger.exists())

            with self.assertRaisesRegex(ValueError, "different paths"):
                plugin_results._output_paths(ledger, ledger, force=True)

    def test_output_symlink_is_rejected_without_touching_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            external = root / "external.csv"
            external.write_text("preserve")
            ledger = root / "ledger.csv"
            ledger.symlink_to(external)
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                plugin_results._output_paths(ledger, None, force=True)
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                plugin_results._write(ledger, "replace", force=True)
            self.assertEqual(external.read_text(), "preserve")


if __name__ == "__main__":
    unittest.main()
