import tomllib
import unittest

from mpc_keygroup_builder import plugin_seed


class PluginSeedTests(unittest.TestCase):
    def test_ranks_roles_and_assigns_distinct_endpoints(self):
        plugin = {
            "plugin": "Test Synth",
            "control_count": 4,
            "controls": [
                {"ui_parameter": 0, "name": "Filter Cutoff", "control_type": "Knob", "usefulness_score": 11, "q_links": ["Q1"]},
                {"ui_parameter": 1, "name": "LFO Rate", "control_type": "Knob", "usefulness_score": 6, "q_links": []},
                {"ui_parameter": 2, "name": "Output Level", "control_type": "Knob", "usefulness_score": 6, "q_links": []},
                {"ui_parameter": 3, "name": "Enable", "control_type": "Button", "usefulness_score": 3, "q_links": []},
            ],
        }
        profile = plugin_seed.seed_profile(plugin, 8, 12)
        by_name = {item["name"]: item for item in profile["controls"]}
        self.assertTrue(by_name["Filter Cutoff"]["control"].startswith("top-encoder"))
        self.assertTrue(by_name["LFO Rate"]["control"].startswith("middle-encoder"))
        self.assertTrue(by_name["Output Level"]["control"].startswith("fader"))
        self.assertEqual(by_name["Enable"]["control"], "upper-button-1")
        self.assertEqual(len({item["control"] for item in profile["controls"]}), 4)
        rendered = plugin_seed.render_toml(profile)
        self.assertIn("Generated draft", rendered)
        self.assertEqual(tomllib.loads(rendered)["plugin"], "Test Synth")

    def test_rejects_capacity_outside_controller_limits(self):
        plugin = {"plugin": "Empty", "control_count": 0, "controls": []}
        with self.assertRaisesRegex(ValueError, "limit must be"):
            plugin_seed.seed_profile(plugin, 1, 1, 49)


if __name__ == "__main__":
    unittest.main()
