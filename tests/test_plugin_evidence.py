import json
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import plugin_evidence


class PluginEvidenceTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[Path, Path, Path]:
        recipe = root / "core.toml"
        recipe.write_text('''schema_version=1
id="synth-core"
name="Synth Core"
capture_name="Synth Capture"
description="Compact"
friction_removed="avoids menus"
preserve_mix_faders=true
[[controls]]
endpoint="top-encoder-1"
expected_label="Cutoff"
expected_target="Synth (Cutoff)"
role="tone"
reason="main gesture"
''')
        targets = root / "targets.toml"
        targets.write_text('''schema_version=1
name="Targets"
[[plugins]]
id="synth"
name="Synth"
aliases=["Test Synth"]
priority="P0"
purpose="perform"
capture_names=["Synth Capture"]
core_recipe="core.toml"
[[plugins]]
id="missing"
name="Missing"
aliases=["Missing"]
priority="P1"
purpose="future"
capture_names=[]
''')
        catalog = root / "catalog.json"
        catalog.write_text(json.dumps({"source_root": "/synths", "plugins": [
            {"plugin": "Test Synth", "control_count": 42},
        ]}))
        audit = root / "audit.json"
        audit.write_text(json.dumps({"project": "boot.xpj", "captures": [{
            "name": "Synth Capture", "enabled_count": 8,
            "controls": [{"learned_targets": ["Synth (Cutoff)"]}],
        }]}))
        return targets, catalog, audit

    def test_classifies_full_and_missing_evidence_without_install_claims(self):
        with tempfile.TemporaryDirectory() as directory:
            targets, catalog, audit = self.fixture(Path(directory))
            report = plugin_evidence.analyze(plugin_evidence.load_targets(targets), catalog, audit)
            by_id = {row["id"]: row for row in report["plugins"]}
            self.assertEqual(by_id["synth"]["status"], "full-evidence-core-ready")
            self.assertEqual(by_id["synth"]["catalog_control_count"], 42)
            self.assertEqual(by_id["missing"]["status"], "evidence-missing")
            self.assertIn("not evidence", report["boundary"])

    def test_invalid_recipe_capture_is_actionable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            targets, catalog, audit = self.fixture(root)
            recipe = root / "core.toml"
            recipe.write_text(recipe.read_text().replace('capture_name="Synth Capture"', 'capture_name="Other"'))
            report = plugin_evidence.analyze(plugin_evidence.load_targets(targets), catalog, audit)
            synth = next(row for row in report["plugins"] if row["id"] == "synth")
            self.assertEqual(synth["status"], "recipe-invalid")
            self.assertIn("repair core recipe", synth["next_action"])

    def test_writes_safe_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            targets, catalog, audit = self.fixture(root)
            report = plugin_evidence.analyze(plugin_evidence.load_targets(targets), catalog, audit)
            output = root / "output"
            plugin_evidence.write_report(report, output, protected_paths=(targets, catalog, audit))
            self.assertTrue((output / "plugin-evidence.csv").is_file())
            with self.assertRaises(FileExistsError):
                plugin_evidence.write_report(report, output)
            plugin_evidence.write_report(report, output, force=True)
            nested = output / "input.json"
            nested.write_text("keep")
            with self.assertRaisesRegex(ValueError, "must not contain"):
                plugin_evidence.write_report(report, output, force=True, protected_paths=(nested,))
            self.assertEqual(nested.read_text(), "keep")

    def test_target_paths_cannot_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            targets, catalog, audit = self.fixture(root)
            targets.write_text(targets.read_text().replace('core_recipe="core.toml"', 'core_recipe="../core.toml"'))
            report = plugin_evidence.analyze(plugin_evidence.load_targets(targets), catalog, audit)
            synth = next(row for row in report["plugins"] if row["id"] == "synth")
            self.assertEqual(synth["status"], "recipe-invalid")
            self.assertIn("escapes", synth["recipe_error"])


if __name__ == "__main__":
    unittest.main()
