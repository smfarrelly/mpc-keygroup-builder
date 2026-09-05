import csv
import json
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import ableton_risk


class AbletonRiskTests(unittest.TestCase):
    @staticmethod
    def report() -> dict:
        return {
            "kind": "mpc-ableton-drum-wave-build",
            "programs": [
                {
                    "id": "clean", "name": "Clean", "collection": "808", "program": "Programs/Clean.xpm",
                    "warnings": [
                        "Ableton Rack macros are not serialized",
                        "pad 2 non-default volume=0.25 is not serialized",
                        "pad 1 non-default volume=0.5 is not serialized",
                    ],
                },
                {
                    "id": "acid", "name": "Acid", "collection": "Acid", "program": "Programs/Acid.xpm",
                    "warnings": ["pad 7 non-default samplestart=442 is not serialized"],
                },
                {"id": "plain", "name": "Plain", "collection": "Plain", "program": "Programs/Plain.xpm", "warnings": []},
            ],
        }

    def test_groups_repeated_pad_warnings_and_prioritizes_programs(self):
        result = ableton_risk.analyze(self.report())
        self.assertEqual([item["id"] for item in result["programs"]], ["acid", "clean", "plain"])
        clean = result["programs"][1]
        self.assertEqual(clean["risk_level"], "high")
        gain = next(item for item in clean["risks"] if item["category"] == "gain")
        self.assertEqual(gain["warning_count"], 2)
        self.assertEqual(gain["affected_pads"], [1, 2])
        self.assertEqual(result["summary"]["risk_levels"], {"high": 2, "none": 1})

    def test_reads_wave_build_translation_warnings(self):
        report = self.report()
        report["programs"][0]["translation_warnings"] = report["programs"][0].pop("warnings")
        result = ableton_risk.analyze(report)
        clean = next(item for item in result["programs"] if item["id"] == "clean")
        self.assertEqual(clean["warning_count"], 3)

    def test_actual_converter_warp_diagnostic_is_critical(self):
        result = ableton_risk.classify_warning("pad 6 warp behavior is not serialized")
        self.assertEqual(result["category"], "timing-warp")
        self.assertEqual(result["severity"], "critical")

    def test_writes_transactional_machine_and_human_reviews(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "build-report.json"
            source.write_text(json.dumps(self.report()), encoding="utf-8")
            output = root / "review"
            result = ableton_risk.write_review(source, output)
            self.assertEqual(result["kind"], "mpc-ableton-translation-risk")
            self.assertTrue((output / "translation-risk.json").is_file())
            markdown = (output / "TRANSLATION_REVIEW.md").read_text(encoding="utf-8")
            self.assertIn("pads 1, 2; 2 diagnostic(s)", markdown)
            with (output / "translation-risk.csv").open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(rows[0]["id"], "acid")
            with self.assertRaises(FileExistsError):
                ableton_risk.write_review(source, output)

    def test_rejects_wrong_report_kind_and_malformed_warnings(self):
        with self.assertRaisesRegex(ValueError, "mpc-ableton-drum-wave-build"):
            ableton_risk.analyze({"kind": "other", "programs": []})
        report = self.report()
        report["programs"][0]["warnings"] = [1]
        with self.assertRaisesRegex(ValueError, "warnings"):
            ableton_risk.analyze(report)


if __name__ == "__main__":
    unittest.main()
