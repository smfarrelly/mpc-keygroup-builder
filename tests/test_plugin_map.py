import json
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import plugin_map, plugin_params


class PluginMapTests(unittest.TestCase):
    def _catalog(self, root: Path) -> dict:
        skins = root / "Vendor - MPC - Test Synth" / "Plugin Skins"
        skins.mkdir(parents=True)
        (skins / "GUI-Popout.json").write_text(
            json.dumps(
                {
                    "controls": [
                        {
                            "componentData": {
                                "name": "Filter Cutoff",
                                "type": "GuiKnob",
                                "data": {"handleName": "Parameter 22"},
                            }
                        },
                        {
                            "componentData": {
                                "name": "Enable",
                                "type": "Button",
                                "data": {"handleName": "Parameter 23"},
                            }
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        return plugin_params.catalog(root)

    def _profile(self, path: Path, *, wrong_name: bool = False) -> dict:
        cutoff = "Wrong Name" if wrong_name else "Filter Cutoff"
        path.write_text(
            f'''schema_version = 1
id = "test-synth-performance"
plugin = "Test Synth"
name = "Test Synth Performance"
description = "Small fixture profile."
slot = 7
channel = 11

[[controls]]
control = "top-encoder-1"
ui_parameter = 22
name = "{cutoff}"
label = "Cutoff"
role = "tone"
priority = "core"

[[controls]]
control = "upper-button-1"
ui_parameter = 23
name = "Enable"
label = "Enable"
role = "switch"
priority = "secondary"
''',
            encoding="utf-8",
        )
        return plugin_map.load_profile(path)

    def test_endpoint_convention(self):
        self.assertEqual(plugin_map.endpoint_cc("top-encoder-1"), 20)
        self.assertEqual(plugin_map.endpoint_cc("lower-button-8"), 67)
        with self.assertRaisesRegex(ValueError, "invalid Launch Control endpoint"):
            plugin_map.endpoint_cc("encoder-9")

    def test_validates_profile_against_discovered_controls(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = plugin_map.validate_profile(
                self._profile(root / "profile.toml"), self._catalog(root / "synths")
            )
            self.assertEqual(result["errors"], [])
            self.assertEqual(result["warnings"], [])
            self.assertEqual(result["controls"][0]["cc"], 20)
            self.assertEqual(result["controls"][0]["mpc_parameter"], 4118)

    def test_rejects_stale_parameter_name(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = plugin_map.validate_profile(
                self._profile(root / "profile.toml", wrong_name=True),
                self._catalog(root / "synths"),
            )
            self.assertIn("not 'Wrong Name'", result["errors"][0])

    def test_compiles_worksheets_atomically(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "nested" / "batch"
            manifest = plugin_map.compile_batch(
                [self._profile(root / "profile.toml")],
                self._catalog(root / "synths"),
                output,
            )
            self.assertEqual(len(manifest["profiles"]), 1)
            self.assertTrue((output / "test-synth-performance" / "CONTROL_LAYOUT.md").is_file())
            self.assertTrue((output / "launch-control-components-all.csv").is_file())
            self.assertTrue((output / "existing-capture-controls.csv").is_file())
            self.assertIn("Filter Cutoff", (output / "mpc-midi-learn-all.csv").read_text())
            with self.assertRaises(FileExistsError):
                plugin_map.compile_batch(
                    [self._profile(root / "profile.toml")],
                    self._catalog(root / "synths"),
                    output,
                )

    def test_repository_profiles_reserve_distinct_slots_and_channels(self):
        root = Path(__file__).parents[1]
        profiles = [plugin_map.load_profile(path) for path in sorted((root / "midi/plugins").glob("*.toml"))]
        self.assertEqual(len(profiles), 5)
        self.assertEqual(len({item["slot"] for item in profiles}), 5)
        self.assertEqual(len({item["channel"] for item in profiles}), 5)


if __name__ == "__main__":
    unittest.main()
