import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import controller_capacity, entrypoints, plugin_map


class ControllerCapacityTests(unittest.TestCase):
    def test_combines_reserved_modes_and_profiles(self):
        plan = {
            "name": "Test plan",
            "control_channel": 16,
            "external_channels": [1, 2, 3],
            "modes": [
                {"slot": 1, "name": "External", "channel": 1, "role": "external-device", "source": "plan"}
            ],
        }
        profile = {
            "slot": 2,
            "channel": 11,
            "name": "Plugin",
            "controls": [{"control": "top-encoder-1"}],
        }
        report = controller_capacity.analyze(plan, [profile])
        self.assertEqual(report["errors"], [])
        self.assertEqual([item["slot"] for item in report["modes"]], [1, 2])
        self.assertIn(8, report["spare_channels"])
        self.assertIn("2/15 assigned", controller_capacity.render_markdown(report))

    def test_rejects_slot_and_reserved_channel_collisions(self):
        plan = {
            "name": "Test plan",
            "control_channel": 16,
            "external_channels": [1],
            "modes": [
                {"slot": 1, "name": "Existing", "channel": 1, "role": "external-device", "source": "plan"}
            ],
        }
        profile = {"slot": 1, "channel": 1, "name": "Bad", "controls": []}
        report = controller_capacity.analyze(plan, [profile])
        self.assertTrue(any("slot 1 has" in item for item in report["errors"]))
        self.assertTrue(any("external-device channel" in item for item in report["errors"]))

    def test_cross_checks_capture_channel(self):
        plan = {
            "name": "Test plan",
            "control_channel": 16,
            "external_channels": [],
            "modes": [
                {"slot": 1, "name": "Synth", "channel": 9, "role": "plugin", "source": "captured", "capture_name": "Synth capture"}
            ],
        }
        report = controller_capacity.analyze(plan, [], [{"name": "Synth capture", "primary_channel": 10}])
        self.assertTrue(any("expected channel 9" in item for item in report["errors"]))

    def test_repository_plan_fills_slots_and_leaves_channel_eight(self):
        root = Path(__file__).parents[1]
        plan = controller_capacity.load_plan(root / "midi/controller-capacity.toml")
        profiles = [
            plugin_map.load_profile(path)
            for path in sorted((root / "midi/plugins").glob("*.toml"))
        ]
        report = controller_capacity.analyze(plan, profiles)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["missing_slots"], [])
        self.assertEqual(report["spare_channels"], [8])

    def test_load_rejects_malformed_mode_structure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capacity.toml"
            base = (
                'schema_version=1\nname="Bad"\ncontrol_channel=16\n'
                'external_channels=[]\n'
            )
            cases = (
                (base + 'modes=["bad"]\n', "mode 1 must be a table"),
                (
                    base
                    + '[[modes]]\nslot=true\nname="Mode"\nchannel=1\n'
                    'role="plugin"\nsource="plan"\n',
                    "mode 1 slot must be an integer",
                ),
            )
            for source, message in cases:
                with self.subTest(message=message):
                    path.write_text(source)
                    with self.assertRaisesRegex(ValueError, message):
                        controller_capacity.load_plan(path)

    def test_malformed_mode_is_friendly_through_installed_command(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = root / "capacity.toml"
            plan.write_text(
                'schema_version=1\nname="Bad"\ncontrol_channel=16\n'
                'external_channels=[]\nmodes=["bad"]\n'
            )
            error = io.StringIO()
            with contextlib.redirect_stderr(error):
                status = entrypoints.invoke(
                    "mpc-controller-capacity",
                    [str(plan), str(root / "missing.toml"), "--output", str(root / "out")],
                )
            self.assertEqual(status, 2)
            self.assertIn("capacity mode 1 must be a table", error.getvalue())
            self.assertNotIn("Traceback", error.getvalue())


if __name__ == "__main__":
    unittest.main()
