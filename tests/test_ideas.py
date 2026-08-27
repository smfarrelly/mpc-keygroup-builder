import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import model
from mpc_keygroup_builder.ideas import (
    apply_layout,
    generate_idea,
    load_recipe,
    render_midi,
)
from mpc_keygroup_builder.layout import LayoutAssignment, LayoutPlan


class DrumIdeaTests(unittest.TestCase):
    def _program(self) -> model.ProgramModel:
        return model.ProgramModel(
            1,
            "Kit",
            "drum",
            (
                model.Zone(
                    1,
                    "kick.primary",
                    (model.SampleLayer("Kick.wav"),),
                    pad=1,
                    midi_note=36,
                ),
                model.Zone(
                    2,
                    "snare.primary",
                    (model.SampleLayer("Snare.wav"),),
                    pad=2,
                    midi_note=38,
                ),
                model.Zone(
                    3,
                    "hihat.closed",
                    (model.SampleLayer("Hat A.wav"),),
                    pad=3,
                    midi_note=42,
                ),
                model.Zone(
                    4,
                    "hihat.closed",
                    (model.SampleLayer("Hat B.wav"),),
                    pad=4,
                    midi_note=44,
                ),
            ),
            "fixture",
            pad_note_map={1: 36, 2: 38, 3: 42, 4: 44, 5: 45},
        )

    def _recipe(self, root: Path) -> Path:
        path = root / "recipe.toml"
        path.write_text(
            'schema_version=1\nid="test"\nname="Test"\nbars=1\n'
            'steps_per_bar=16\nswing=0.6\ngate=0.5\nchannel=10\n'
            '[[events]]\nrole="kick"\nsteps=[0,8]\nvelocity=110\n'
            '[[events]]\nrole="hihat.closed"\nsteps=[1,3,5,7]\n'
            'velocity=80\nprobability=0.75\nhumanize_velocity=4\nselection="random"\n',
            encoding="utf-8",
        )
        return path

    def test_generation_is_seed_reproducible_and_renders_standard_midi(self):
        with tempfile.TemporaryDirectory() as directory:
            recipe = load_recipe(self._recipe(Path(directory)))
            first = generate_idea(recipe, self._program(), seed=27, tempo=92)
            second = generate_idea(recipe, self._program(), seed=27, tempo=92)
            other = generate_idea(recipe, self._program(), seed=28, tempo=92)
            self.assertEqual(first, second)
            self.assertNotEqual(first.events, other.events)
            midi = render_midi(first)
            self.assertEqual(midi[:4], b"MThd")
            self.assertIn(b"MTrk", midi)
            self.assertTrue(all(event.tick >= event.step * 120 for event in first.events))

    def test_same_role_pattern_resolves_through_changed_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            recipe = load_recipe(self._recipe(Path(directory)))
            source = self._program()
            plan = LayoutPlan(
                "Kit",
                "swap",
                "mpc-key-37",
                (
                    LayoutAssignment(1, "A01", 2, "Snare.wav", "snare.primary", None, False),
                    LayoutAssignment(2, "A02", 1, "Kick.wav", "kick.primary", None, False),
                    LayoutAssignment(3, "A03", 3, "Hat A.wav", "hihat.closed", None, False),
                    LayoutAssignment(4, "A04", 4, "Hat B.wav", "hihat.closed", None, False),
                ),
                (),
            )
            original = generate_idea(recipe, source, seed=27, tempo=92)
            changed = generate_idea(
                recipe,
                apply_layout(source, plan),
                seed=27,
                tempo=92,
                layout="swap",
            )
            original_kicks = [event for event in original.events if event.role == "kick.primary"]
            changed_kicks = [event for event in changed.events if event.role == "kick.primary"]
            self.assertEqual([event.step for event in original_kicks], [event.step for event in changed_kicks])
            self.assertEqual({event.midi_note for event in original_kicks}, {36})
            self.assertEqual({event.midi_note for event in changed_kicks}, {38})
            self.assertEqual({event.pad_label for event in changed_kicks}, {"A02"})

    def test_missing_role_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "recipe.toml"
            path.write_text(
                'schema_version=1\nid="bad"\nname="Bad"\nbars=1\nsteps_per_bar=16\n'
                '[[events]]\nrole="tom"\nsteps=[0]\nvelocity=100\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "required role: tom"):
                generate_idea(load_recipe(path), self._program(), seed=1, tempo=90)


if __name__ == "__main__":
    unittest.main()
