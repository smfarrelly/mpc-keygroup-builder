import tomllib
import unittest
import tempfile
from pathlib import Path

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

    def test_output_stays_outside_scanned_content_and_project(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            synth = root / "Synths"
            synth.mkdir()
            project = root / "Boot.xpj"
            project.write_text("keep\n")
            with self.assertRaisesRegex(ValueError, "outside the scanned"):
                plugin_seed.prepare_output(synth / "profile.toml", synth, project)
            with self.assertRaisesRegex(ValueError, "replace the project"):
                plugin_seed.prepare_output(project, synth, project)
            self.assertEqual(project.read_text(), "keep\n")

    def test_output_refuses_symlinks_and_publishes_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            synth = root / "Synths"
            synth.mkdir()
            external = root / "external.toml"
            external.write_text("keep\n")
            link = root / "profile.toml"
            link.symlink_to(external)
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                plugin_seed.prepare_output(link, synth, None)
            output = plugin_seed.prepare_output(root / "profiles/new.toml", synth, None)
            plugin_seed.write_output(output, "plugin = \"Test\"\n")
            self.assertEqual(output.read_text(), 'plugin = "Test"\n')


if __name__ == "__main__":
    unittest.main()
