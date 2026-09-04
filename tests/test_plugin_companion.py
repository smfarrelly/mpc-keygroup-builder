import json
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import plugin_companion


class PluginCompanionTests(unittest.TestCase):
    def _inputs(self, root: Path) -> tuple[list[Path], Path]:
        synth_root = root / "Synths"
        skins = synth_root / "Vendor - MPC - Test Synth" / "Plugin Skins"
        skins.mkdir(parents=True)
        (skins / "GUI-Popout.json").write_text(
            json.dumps(
                {
                    "controls": [
                        {
                            "componentData": {
                                "name": "Cutoff",
                                "type": "GuiKnob",
                                "data": {"handleName": "Parameter 2"},
                            }
                        },
                        {
                            "componentData": {
                                "name": "Enable",
                                "type": "Button",
                                "data": {"handleName": "Parameter 3"},
                            }
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        profile = root / "profile.toml"
        profile.write_text(
            '''schema_version = 1
id = "test-synth"
plugin = "Test Synth"
name = "Test Synth"
description = "Synthetic companion fixture."
slot = 7
channel = 11
probe = "top-encoder-1"

[[controls]]
control = "top-encoder-1"
ui_parameter = 2
name = "Cutoff"
label = "Cutoff"
role = "tone"
priority = "core"

[[controls]]
control = "upper-button-1"
ui_parameter = 3
name = "Enable"
label = "Enable"
role = "switch"
priority = "secondary"
''',
            encoding="utf-8",
        )
        return [profile], synth_root

    def test_builds_self_contained_interactive_companion(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            profiles, synth_root = self._inputs(root)
            output = root / "site" / "companion.html"
            plugin_companion.build_companion(profiles, synth_root, output)
            rendered = output.read_text(encoding="utf-8")
            self.assertIn("Plugin Mapping Companion", rendered)
            self.assertIn("Test Synth", rendered)
            self.assertIn("localStorage", rendered)
            self.assertIn("Export CSV", rendered)
            self.assertIn("mpc-plugin-mapping-results", rendered)
            self.assertNotIn("https://", rendered)
            self.assertNotIn(str(root), rendered)
            with self.assertRaises(FileExistsError):
                plugin_companion.build_companion(profiles, synth_root, output)

    def test_data_is_deterministic_and_orders_pages_by_slot(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            profiles, synth_root = self._inputs(root)
            from mpc_keygroup_builder import plugin_map, plugin_params

            profile = plugin_map.load_profile(profiles[0])
            catalog = plugin_params.catalog(synth_root)
            first = plugin_companion.companion_data([profile], catalog)
            second = plugin_companion.companion_data([profile], catalog)
            self.assertEqual(first, second)
            self.assertEqual(first["pages"][0]["probe"], "top-encoder-1")
            self.assertEqual(first["pages"][0]["controls"][0]["mpc_parameter"], 4098)
            self.assertEqual(len(first["fingerprint"]), 16)


if __name__ == "__main__":
    unittest.main()
