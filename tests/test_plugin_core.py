import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import plugin_core, plugin_map


def profile() -> dict:
    rows = []
    for index, (role, priority, endpoint) in enumerate((
        ("tone", "core", "fader-1"),
        ("tone", "core", "fader-2"),
        ("movement", "core", "top-encoder-1"),
        ("texture", "core", "middle-encoder-1"),
        ("global", "secondary", "bottom-encoder-1"),
        ("switch", "core", "upper-button-1"),
    )):
        rows.append({
            "control": endpoint, "ui_parameter": index, "name": f"Control {index}",
            "label": f"Control {index}", "role": role, "priority": priority,
            "color": "white",
        })
    return {
        "schema_version": 1, "id": "full", "plugin": "Test", "name": "Full",
        "description": "Full page", "slot": 2, "channel": 9,
        "probe": "fader-1", "controls": rows,
    }


class PluginCoreTests(unittest.TestCase):
    def test_selects_core_first_with_role_diversity_and_avoids_faders(self):
        core, report = plugin_core.core_profile(profile(), limit=4)
        self.assertEqual(report["selected_controls"], 4)
        self.assertEqual(report["selected_roles"], ["movement", "switch", "texture", "tone"])
        self.assertFalse(any(row["control"].startswith("fader-") for row in core["controls"]))
        self.assertEqual(len({row["control"] for row in core["controls"]}), 4)
        self.assertEqual(core["probe"], core["controls"][0]["control"])

    def test_faders_are_opt_in_and_limit_is_bounded(self):
        core, _ = plugin_core.core_profile(profile(), limit=6, allow_faders=True)
        self.assertTrue(any(row["control"].startswith("fader-") for row in core["controls"]))
        with self.assertRaisesRegex(ValueError, "limit"):
            plugin_core.core_profile(profile(), limit=41)

    def test_builds_reloadable_profiles_and_protects_unrecognized_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "profile.toml"
            from mpc_keygroup_builder import plugin_seed
            source.write_text(plugin_seed.render_toml(profile()))
            output = root / "output"
            receipt = plugin_core.build([source], output, limit=4)
            self.assertEqual(receipt["hardware_status"], "pending")
            generated = next((output / "profiles").glob("*.toml"))
            parsed = plugin_map.load_profile(generated)
            self.assertEqual(len(parsed["controls"]), 4)
            with self.assertRaises(FileExistsError):
                plugin_core.build([source], output)
            plugin_core.build([source], output, limit=4, force=True)
            unsafe = root / "unsafe"
            unsafe.mkdir()
            (unsafe / "keep").write_text("mine")
            with self.assertRaisesRegex(ValueError, "unrecognized"):
                plugin_core.build([source], unsafe, force=True)
            self.assertTrue((unsafe / "keep").is_file())


if __name__ == "__main__":
    unittest.main()
