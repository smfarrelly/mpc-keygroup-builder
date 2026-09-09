import json
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import capture_core


class CaptureCoreTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[Path, Path]:
        audit = root / "audit.json"
        audit.write_text(json.dumps({"captures": [{
            "name": "Synth", "path": "synth.syx", "sha256": "abc",
            "enabled_count": 10, "matched_control_count": 9,
            "controls": [
                {"control": "top-encoder-1", "label": "Cutoff", "channel": 9,
                 "number": 20, "channel_source": "encoded", "learned_targets": ["Synth (Cutoff)"]},
                *[
                    {"control": f"fader-{index}", "label": f"Track {index}", "channel": 16,
                     "number": index + 4, "channel_source": "encoded",
                     "learned_targets": [f"Track {index} (Volume)"] if index < 8 else []}
                    for index in range(1, 9)
                ],
            ],
        }]}))
        recipe = root / "recipe.toml"
        recipe.write_text('''schema_version=1
id="synth-core"
name="Synth Core"
capture_name="Synth"
description="Compact synth"
friction_removed="avoids a menu"
preserve_mix_faders=true
[[controls]]
endpoint="top-encoder-1"
expected_label="Cutoff"
expected_target="Synth (Cutoff)"
role="tone"
reason="main gesture"
''')
        return audit, recipe

    def test_preserves_plugin_evidence_and_isolated_mix_faders(self):
        with tempfile.TemporaryDirectory() as directory:
            audit_path, recipe_path = self.fixture(Path(directory))
            report = capture_core.analyze(
                capture_core.load_audit(audit_path),
                [capture_core.load_recipe(recipe_path)],
            )
            self.assertEqual(report["summary"]["errors"], 0)
            self.assertEqual(report["summary"]["plugin_controls"], 1)
            self.assertEqual(report["summary"]["persistent_mix_faders"], 8)
            self.assertEqual(report["cores"][0]["selected_controls"][0]["cc"], 20)
            self.assertIn("fader-8", report["warnings"][0])

    def test_detects_label_target_and_channel_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit_path, recipe_path = self.fixture(root)
            audit = capture_core.load_audit(audit_path)
            audit["captures"][0]["controls"][0]["label"] = "Changed"
            audit["captures"][0]["controls"][0]["learned_targets"] = []
            for row in audit["captures"][0]["controls"]:
                if str(row.get("control")).startswith("fader-"):
                    row["channel"] = 9
            report = capture_core.analyze(audit, [capture_core.load_recipe(recipe_path)])
            self.assertGreaterEqual(report["summary"]["errors"], 3)

    def test_writes_transactional_bundle_and_protects_unknown_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit_path, recipe_path = self.fixture(root)
            report = capture_core.analyze(
                capture_core.load_audit(audit_path), [capture_core.load_recipe(recipe_path)]
            )
            output = root / "output"
            capture_core.write_report(report, output)
            self.assertTrue((output / "captured-controls.csv").is_file())
            self.assertTrue((output / "HARDWARE_CHECKLIST.md").is_file())
            companion = (output / "CORE_COMPANION.html").read_text()
            self.assertIn("Persistent MPC mix faders", companion)
            self.assertIn("Synth Core", companion)
            self.assertNotIn("http://", companion)
            self.assertNotIn("https://", companion)
            with self.assertRaises(FileExistsError):
                capture_core.write_report(report, output)
            capture_core.write_report(report, output, force=True)
            unknown = root / "unknown"
            unknown.mkdir()
            (unknown / "keep").write_text("mine")
            with self.assertRaisesRegex(ValueError, "unrecognized"):
                capture_core.write_report(report, unknown, force=True)
            self.assertTrue((unknown / "keep").is_file())
            link = root / "output-link"
            link.symlink_to(output, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symbolic-link"):
                capture_core.write_report(report, link, force=True)
            nested_input = output / "recipe.toml"
            nested_input.write_text("keep")
            with self.assertRaisesRegex(ValueError, "must not contain input"):
                capture_core.write_report(
                    report, output, force=True, protected_paths=(nested_input,)
                )
            self.assertEqual(nested_input.read_text(), "keep")

    def test_recipe_rejects_more_than_eight_controls(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recipe.toml"
            controls = "\n".join(
                f'[[controls]]\nendpoint="top-{index}"\nexpected_label="L"\nexpected_target="T"\nrole="r"\nreason="x"'
                for index in range(9)
            )
            path.write_text(
                'schema_version=1\nid="x"\nname="x"\ncapture_name="x"\n'
                'description="x"\nfriction_removed="x"\npreserve_mix_faders=true\n' + controls
            )
            with self.assertRaisesRegex(ValueError, "1..8"):
                capture_core.load_recipe(path)


if __name__ == "__main__":
    unittest.main()
