import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import layout, model
from mpc_keygroup_builder.device import load_device


class LayoutTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).parents[1]
        self.device = load_device(self.root / "devices/mpc-key-37.toml")
        self.program = model.ProgramModel(
            1,
            "Kit",
            "drum",
            (
                model.Zone(1, "kick.primary", (model.SampleLayer("Kick.wav"),), pad=1),
                model.Zone(2, "snare.primary", (model.SampleLayer("Snare.wav"),), pad=2),
                model.Zone(3, "hihat.closed", (model.SampleLayer("CH.wav"),), pad=3),
                model.Zone(4, "hihat.open", (model.SampleLayer("OH.wav"),), pad=4),
                model.Zone(5, "fx.vocal", (model.SampleLayer("Vox.wav"),), pad=5),
            ),
            "fixture",
        )

    def test_classic_and_handed_presets_move_semantic_roles(self):
        classic = layout.arrange(
            self.program,
            layout.load_preset(self.root / "layouts/classic-mpc.toml"),
            self.device,
        )
        right = layout.arrange(
            self.program,
            layout.load_preset(self.root / "layouts/right-handed-performance.toml"),
            self.device,
        )
        left = layout.arrange(
            self.program,
            layout.load_preset(self.root / "layouts/left-handed-performance.toml"),
            self.device,
        )
        self.assertEqual(classic.assignments[0].role, "kick.primary")
        self.assertEqual(right.assignments[0].role, "kick.primary")
        self.assertEqual(left.assignments[0].role, "hihat.open")
        self.assertEqual(left.assignments[3].role, "kick.primary")

    def test_full_library_preserves_source_slots(self):
        plan = layout.arrange(
            self.program,
            layout.load_preset(self.root / "layouts/full-library.toml"),
            self.device,
        )
        self.assertEqual([item.slot for item in plan.assignments], [1, 2, 3, 4, 5])
        self.assertEqual([item.source_index for item in plan.assignments], [1, 2, 3, 4, 5])
        self.assertIn("## Bank A", layout.render_markdown(plan, self.device))

    def test_locked_pad_is_not_moved(self):
        locked_program = model.ProgramModel(
            1,
            "Locked",
            "drum",
            (model.Zone(1, "kick.primary", (model.SampleLayer("Kick.wav"),), pad=16, locked=True),),
            "fixture",
        )
        plan = layout.arrange(
            locked_program,
            layout.load_preset(self.root / "layouts/right-handed-performance.toml"),
            self.device,
        )
        self.assertEqual(plan.assignments[0].label, "A16")
        self.assertTrue(plan.assignments[0].locked)

    def test_rejects_more_roles_than_physical_pads(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.toml"
            roles = ",".join('"fx"' for _ in range(17))
            path.write_text(
                f'schema_version=1\nid="bad"\nname="Bad"\nstrategy="role-first"\nrole_order=[{roles}]\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "one physical pad bank"):
                layout.arrange(self.program, layout.load_preset(path), self.device)


if __name__ == "__main__":
    unittest.main()
