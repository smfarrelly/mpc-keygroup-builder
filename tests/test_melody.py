import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder.melody import generate_idea, load_recipe, render_midi
from mpc_keygroup_builder.midi_groove import parse_midi


class MelodyIdeaTests(unittest.TestCase):
    def _recipe(self, root: Path) -> Path:
        path = root / "melody.toml"
        path.write_text(
            'schema_version=1\nid="hook"\nname="Hook"\nkey="D"\nscale="dorian"\n'
            'bars=2\nbeats_per_bar=4\nsteps_per_beat=4\nmotif_steps=16\n'
            'rhythm=[0,3,6,10,14]\ncontour=[0,2,4,3,1]\nstart_degree=1\n'
            'note_range=[60,84]\nvariation=0.8\nrest_probability=0.0\n'
            'octave_probability=0.3\nvelocity=95\nhumanize_velocity=5\ngate=0.7\nchannel=4\n',
            encoding="utf-8",
        )
        return path

    def test_motif_repeats_then_varies_deterministically(self):
        with tempfile.TemporaryDirectory() as directory:
            recipe = load_recipe(self._recipe(Path(directory)))
            first = generate_idea(recipe, seed=23, tempo=91)
            second = generate_idea(recipe, seed=23, tempo=91)
            other = generate_idea(recipe, seed=24, tempo=91)
            self.assertEqual(first, second)
            self.assertNotEqual(first.events, other.events)
            first_pass = [event for event in first.events if event.repetition == 0]
            self.assertEqual([event.step for event in first_pass], [0, 3, 6, 10, 14])
            self.assertTrue(all(event.variation == "repeat" for event in first_pass))
            self.assertTrue(any(event.variation != "repeat" for event in first.events))
            self.assertTrue(all(60 <= event.midi_note <= 84 for event in first.events))
            octave_events = [event for event in first.events if "octave" in event.variation]
            self.assertTrue(octave_events)

    def test_midi_is_format_one_and_uses_configured_channel(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recipe = load_recipe(self._recipe(root))
            idea = generate_idea(recipe, seed=7, tempo=100)
            path = root / "melody.mid"
            path.write_bytes(render_midi(idea, recipe))
            source, events = parse_midi(path)
            self.assertEqual((source.midi_format, source.tracks, source.ppq), (1, 2, 480))
            self.assertEqual({event.channel for event in events}, {4})
            self.assertEqual(len(events), len(idea.events))

    def test_schema_rejects_misaligned_motif_and_contour(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._recipe(Path(directory))
            text = path.read_text(encoding="utf-8")
            path.write_text(text.replace("motif_steps=16", "motif_steps=15"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "divide"):
                load_recipe(path)
            path.write_text(text.replace("contour=[0,2,4,3,1]", "contour=[0,2]"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "one scale offset"):
                load_recipe(path)


if __name__ == "__main__":
    unittest.main()
