import csv
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import plugin_coverage


def control(number, name, score, *, learned=False):
    return {
        "ui_parameter": number, "mpc_parameter": number + 4096,
        "mpc_parameter_basis": "verified" if learned else "hypothesis:+4096",
        "name": name, "aliases": [], "control_type": "Knob", "q_links": [],
        "learned": learned, "usefulness_score": score,
    }


class PluginCoverageTests(unittest.TestCase):
    def setUp(self):
        self.catalog = {"plugins": [
            {"plugin": "Synth A", "controls": [control(1, "Cutoff", 11), control(2, "Resonance", 10, learned=True), control(3, "Page", 0)]},
            {"plugin": "Effect B", "controls": [control(4, "Mix", 7)]},
        ]}
        self.profile = {
            "id": "synth-a", "plugin": "Synth A", "name": "Synth A", "description": "Test",
            "slot": 1, "channel": 9, "controls": [
                {"control": "top-encoder-1", "ui_parameter": 1, "name": "Cutoff", "role": "tone", "priority": "core"},
                {"control": "top-encoder-2", "ui_parameter": 1, "name": "Cutoff", "role": "tone", "priority": "secondary"},
            ],
        }

    def test_combines_planned_and_learned_coverage_and_finds_omissions(self):
        report = plugin_coverage.analyze([self.profile], self.catalog)
        effect, synth = report["plugins"]
        self.assertEqual(synth["useful_coverage_percent"], 100.0)
        self.assertEqual(synth["planned_controls"], 1)
        self.assertEqual(synth["learned_controls"], 1)
        self.assertEqual(synth["duplicate_targets"][0]["assignments"], 2)
        self.assertEqual(effect["useful_coverage_percent"], 0.0)
        self.assertEqual(effect["omitted_recommended"][0]["name"], "Mix")
        self.assertEqual(report["summary"]["useful_coverage_percent"], 66.7)

    def test_writes_transactional_json_csv_and_markdown(self):
        report = plugin_coverage.analyze([self.profile], self.catalog)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "coverage"
            plugin_coverage.write_report(report, output)
            self.assertTrue((output / "plugin-mapping-coverage.json").is_file())
            self.assertIn("Best useful controls", (output / "PLUGIN_MAPPING_COVERAGE.md").read_text())
            with (output / "plugin-mapping-coverage.csv").open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual([row["plugin"] for row in rows], ["Effect B", "Synth A"])
            with self.assertRaises(FileExistsError):
                plugin_coverage.write_report(report, output)

    def test_rejects_invalid_limit_and_profiles(self):
        with self.assertRaisesRegex(ValueError, "nonnegative"):
            plugin_coverage.analyze([], self.catalog, -1)
        broken = {**self.profile, "controls": [{**self.profile["controls"][0], "name": "Wrong"}]}
        with self.assertRaisesRegex(ValueError, "invalid plugin mapping batch"):
            plugin_coverage.analyze([broken], self.catalog)


if __name__ == "__main__":
    unittest.main()
