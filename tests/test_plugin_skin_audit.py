import json
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import plugin_skin_audit


def document(rows):
    return {"controls": [
        {"componentData": {"name": name, "type": kind, "data": {"handleName": f"Parameter {number}"}}}
        for number, name, kind in rows
    ]}


class PluginSkinAuditTests(unittest.TestCase):
    def test_finds_missing_controls_variants_and_binding_conflicts(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin = Path(directory) / "Vendor - MPC - Test"
            skins = plugin / "Plugin Skins"
            skins.mkdir(parents=True)
            (skins / "GUI-Popout.json").write_text(json.dumps(document([(1, "Cutoff", "Knob"), (2, "Resonance", "Knob")])))
            (skins / "GUI.json").write_text(json.dumps(document([(4, "Cutoff", "Knob")])))
            (skins / "TUI.json").write_text(json.dumps(document([(1, "Cutoff", "Dial"), (2, "Reso", "Knob"), (3, "Attack", "Knob")])))
            item = plugin_skin_audit.inspect_plugin(plugin)
            self.assertEqual(item["status"], "warn")
            self.assertEqual(item["selected_skin"], "GUI-Popout.json")
            self.assertEqual(item["union_control_count"], 4)
            self.assertEqual([row["ui_parameter"] for row in item["missing_from_selected"]], [3, 4])
            self.assertEqual(item["binding_conflicts"][0]["name"], "Cutoff")
            bindings = {row["skin"]: row["ui_parameters"] for row in item["binding_conflicts"][0]["skins"]}
            self.assertEqual(bindings["GUI-Popout.json"], [1])
            self.assertEqual(bindings["GUI.json"], [4])
            self.assertEqual({row["ui_parameter"] for row in item["name_variants"]}, {2})
            self.assertEqual({row["ui_parameter"] for row in item["control_type_variants"]}, {1})

    def test_parse_error_fails_and_report_is_transactional(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "Synths"
            skins = root / "Vendor - MPC - Broken" / "Plugin Skins"
            skins.mkdir(parents=True)
            (skins / "GUI-Popout.json").write_text("{")
            report = plugin_skin_audit.audit(root)
            self.assertEqual(report["summary"]["fail"], 1)
            output = Path(directory) / "report"
            plugin_skin_audit.write_report(report, output)
            self.assertTrue((output / "plugin-skin-audit.csv").is_file())
            self.assertIn("Cannot parse", (output / "PLUGIN_SKIN_AUDIT.md").read_text())
            with self.assertRaises(FileExistsError):
                plugin_skin_audit.write_report(report, output)


if __name__ == "__main__":
    unittest.main()
