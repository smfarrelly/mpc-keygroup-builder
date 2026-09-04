import json
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import plugin_params


class PluginParameterTests(unittest.TestCase):
    def _plugin(self, root: Path) -> Path:
        plugin = root / "AIR Music Technology - MPC - Test Synth"
        skins = plugin / "Plugin Skins"
        presets = plugin / "Presets"
        skins.mkdir(parents=True)
        presets.mkdir()
        (presets / "Init.xpl").write_text("<pluginstate/>")
        (skins / "GUI-Popout.json").write_text(
            json.dumps(
                {
                    "pageData": {
                        "controls": [
                            {"componentData": {"name": "Filter Cutoff", "type": "GuiKnob", "data": {"handleName": "Parameter 22"}}},
                            {"componentData": {"name": "Filter background", "type": "Image", "data": {"handleName": "Parameter 23"}}},
                            {"componentData": {"name": "Macro 1", "type": "Knob"}, "map": [{"key": "Data", "value": "Parameter 8"}]},
                        ]
                    }
                }
            )
        )
        (skins / "Q-Links.json").write_text(
            json.dumps({"Screen Mode Q-Links": {"map": [{"Tab": 2, "SubTab": 1, "Q-Links": {"Q-Link 1": 22, "Q-Link 2": -1}}]}})
        )
        return plugin

    def test_extracts_controls_and_qlink_locations(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin = self._plugin(Path(directory))
            report = plugin_params.inspect_plugin(plugin)
            self.assertEqual(report["plugin"], "Test Synth")
            self.assertEqual(report["preset_count"], 1)
            self.assertEqual(report["control_count"], 2)
            controls = {item["name"]: item for item in report["controls"]}
            self.assertEqual(controls["Filter Cutoff"]["ui_parameter"], 22)
            self.assertEqual(controls["Filter Cutoff"]["mpc_parameter"], 4118)
            self.assertEqual(controls["Filter Cutoff"]["mpc_parameter_basis"], "hypothesis:+4096")
            self.assertIn("Screen Mode T2/S1 Q-Link 1", controls["Filter Cutoff"]["q_links"])
            self.assertNotIn("Filter background", controls)

    def test_catalog_filter_and_search(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._plugin(root)
            report = plugin_params.catalog(root, plugin_filter="test")
            rows = plugin_params.filtered(report, "cutoff", True, 10)
            self.assertEqual([row["name"] for row in rows], ["Filter Cutoff"])
            self.assertIn("MPC plugin parameter catalog", plugin_params.render_markdown(report, rows))
            self.assertIn("Filter Cutoff", plugin_params.render_csv(rows))


if __name__ == "__main__":
    unittest.main()
