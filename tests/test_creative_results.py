import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import creative_results
from mpc_keygroup_builder.workstation_wave import build_wave


class CreativeResultsTests(unittest.TestCase):
    def setUp(self):
        self.repository = Path(__file__).resolve().parents[1]

    def _wave(self, root: Path):
        wave = root / "wave"
        report = build_wave(
            self.repository / "recipes", wave,
            families=("ambient",), seeds_per_family=2, seed_start=91,
        )
        fingerprint, _ = creative_results.expected_rows(report)
        return wave, report, fingerprint

    @staticmethod
    def _export(report, fingerprint, timestamp, statuses, notes=None):
        notes = notes or {}
        return {
            "schema_version": 1, "kind": "mpc-creative-wave-results",
            "fingerprint": fingerprint, "exported_at": timestamp,
            "items": [{
                "id": item["id"], "family": item["family"], "seed": item["seed"],
                "status": statuses.get(item["id"], "pending"), "notes": notes.get(item["id"], ""),
            } for item in report["candidates"]],
        }

    def test_validates_merges_and_packages_only_selected_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wave, report, fingerprint = self._wave(root)
            first_id, second_id = [item["id"] for item in report["candidates"]]
            first = self._export(report, fingerprint, "2026-01-02T10:00:00-08:00", {first_id: "keep"}, {first_id: "promising"})
            second = self._export(report, fingerprint, "2026-01-03T02:00:00Z", {first_id: "pending", second_id: "provisional"}, {first_id: "reload later", second_id: "good contrast"})
            output = root / "shortlist"
            result = creative_results._write_bundle(wave / "wave.json", [second, first], output)
            self.assertEqual(result["summary"]["packaged"], 2)
            self.assertEqual(
                result["source_sessions"],
                ["2026-01-02T18:00:00+00:00", "2026-01-03T02:00:00+00:00"],
            )
            ledger = {item["id"]: item for item in result["ledger"]}
            self.assertEqual(ledger[first_id]["selection_status"], "keep")
            self.assertEqual(ledger[second_id]["selection_status"], "provisional")
            self.assertEqual(ledger[first_id]["notes"], "promising\nreload later")
            for item in report["candidates"]:
                self.assertTrue((output / "Shortlist" / item["paths"]["root"] / "idea.mid").is_file())
            checksums = json.loads((output / "checksums.json").read_text())
            for relative, digest in checksums.items():
                self.assertEqual(hashlib.sha256((output / relative).read_bytes()).hexdigest(), digest)
            with self.assertRaises(FileExistsError):
                creative_results._write_bundle(wave / "wave.json", [], output)

    def test_rejects_stale_incomplete_and_ambiguous_exports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _wave, report, fingerprint = self._wave(root)
            document = self._export(report, fingerprint, "2026-01-01T00:00:00Z", {})
            stale = dict(document, fingerprint="wrong")
            with self.assertRaisesRegex(ValueError, "fingerprint mismatch"):
                creative_results.validate_export(report, stale)
            incomplete = dict(document, items=document["items"][:-1])
            with self.assertRaisesRegex(ValueError, "missing"):
                creative_results.validate_export(report, incomplete)
            duplicate = dict(document, items=document["items"] + [document["items"][0]])
            with self.assertRaisesRegex(ValueError, "duplicate"):
                creative_results.validate_export(report, duplicate)
            naive = dict(document, exported_at="2026-01-01T00:00:00")
            with self.assertRaisesRegex(ValueError, "timezone"):
                creative_results.validate_export(report, naive)


if __name__ == "__main__":
    unittest.main()
