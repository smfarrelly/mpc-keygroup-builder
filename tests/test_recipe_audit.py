import json
import shutil
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder.recipe_audit import _cycles, audit, write_report


class RecipeAuditTests(unittest.TestCase):
    def setUp(self):
        self.repository = Path(__file__).resolve().parents[1]

    def test_repository_recipes_form_six_clean_families(self):
        report = audit(self.repository / "recipes")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["summary"], {
            "files": 29,
            "workstations": 6,
            "errors": 0,
            "warnings": 0,
            "orphans": 0,
        })
        self.assertEqual(report["counts"], {
            "drum": 6, "harmony": 6, "kit": 5, "melody": 6, "workstation": 6
        })
        self.assertFalse(report["issues"])
        for item in report["files"]:
            self.assertEqual(item["status"], "pass")

    def test_reports_duplicate_missing_orphan_and_channel_problems_together(self):
        with tempfile.TemporaryDirectory() as directory:
            recipes = Path(directory) / "recipes"
            shutil.copytree(self.repository / "recipes", recipes)
            shutil.copy2(
                recipes / "drums/dusty-pocket.toml",
                recipes / "drums/dusty-pocket-copy.toml",
            )
            ambient = recipes / "workstation/ambient-scratchpad.toml"
            ambient.write_text(
                ambient.read_text(encoding="utf-8").replace(
                    "../melody/ambient-drift.toml", "../melody/missing.toml"
                ),
                encoding="utf-8",
            )
            melody_file = recipes / "melody/dusty-answer.toml"
            melody_file.write_text(
                melody_file.read_text(encoding="utf-8").replace("channel = 3", "channel = 2"),
                encoding="utf-8",
            )
            report = audit(recipes)
            codes = {issue["code"] for issue in report["issues"]}
            self.assertEqual(report["status"], "fail")
            self.assertTrue(
                {"invalid-recipe", "duplicate-id", "channel-collision", "orphan-component"}
                .issubset(codes)
            )
            self.assertGreaterEqual(report["summary"]["errors"], 3)
            self.assertGreaterEqual(report["summary"]["warnings"], 2)

    def test_report_bundle_contains_json_csv_markdown_and_refuses_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "audit"
            report = audit(self.repository / "recipes")
            self.assertEqual(write_report(report, output), output.resolve())
            self.assertEqual(
                json.loads((output / "recipe-catalog.json").read_text())["summary"]["files"],
                29,
            )
            self.assertIn("80s Funk Scratchpad", (output / "recipe-catalog.csv").read_text())
            self.assertIn("Status: **PASS**", (output / "README.md").read_text())
            with self.assertRaises(FileExistsError):
                write_report(report, output)

    def test_cycle_detection_is_deterministic(self):
        self.assertEqual(
            _cycles({"a": ["b"], "b": ["c"], "c": ["a"]}),
            [["a", "b", "c", "a"]],
        )

    def test_empty_recipe_root_fails_instead_of_reporting_a_false_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            report = audit(Path(directory))
            self.assertEqual(report["status"], "fail")
            self.assertEqual(report["summary"]["errors"], 1)
            self.assertEqual(report["issues"][0]["code"], "no-recipes")


if __name__ == "__main__":
    unittest.main()
