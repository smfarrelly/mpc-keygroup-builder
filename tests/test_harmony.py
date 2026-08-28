import json
import struct
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder.harmony import generate_idea, load_recipe, render_midi
from mpc_keygroup_builder.midi_groove import parse_midi


class HarmonyIdeaTests(unittest.TestCase):
    def _recipe(self, root: Path, extra: str = "") -> Path:
        path = root / "harmony.toml"
        path.write_text(
            'schema_version=1\nid="test-minor"\nname="Test Minor"\n'
            'key="D"\nscale="minor"\nbars=2\nbeats_per_bar=4\n'
            'progression=[1,6,3,7]\nchord_beats=[2,2,2,2]\n'
            'chord_notes=4\nchord_range=[48,76]\nbass_range=[28,52]\n'
            'bass_pattern=[0,7,12,7]\nbass_steps_per_beat=2\n'
            'chord_velocity=84\nbass_velocity=105\ngate=0.8\n'
            'humanize_velocity=5\nchord_channel=1\nbass_channel=3\n'
            + extra,
            encoding="utf-8",
        )
        return path

    def test_generation_is_reproducible_range_safe_and_voice_led(self):
        with tempfile.TemporaryDirectory() as directory:
            recipe = load_recipe(self._recipe(Path(directory)))
            first = generate_idea(recipe, seed=41, tempo=92)
            second = generate_idea(recipe, seed=41, tempo=92)
            other = generate_idea(recipe, seed=42, tempo=92)
            self.assertEqual(first, second)
            self.assertNotEqual(first.events, other.events)
            self.assertEqual([decision.degree for decision in first.decisions], [1, 6, 3, 7])
            self.assertEqual(sum(decision.duration_beats for decision in first.decisions), 8)
            self.assertTrue(
                all(48 <= event.midi_note <= 76 for event in first.events if event.part == "chords")
            )
            self.assertTrue(
                all(28 <= event.midi_note <= 52 for event in first.events if event.part == "bass")
            )
            self.assertTrue(all(len(decision.notes) == 4 for decision in first.decisions))
            movements = [
                sum(abs(a - b) for a, b in zip(before.notes, after.notes))
                for before, after in zip(first.decisions, first.decisions[1:])
            ]
            self.assertTrue(all(movement <= 24 for movement in movements))

    def test_format_one_has_conductor_chords_and_bass_tracks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recipe = load_recipe(self._recipe(root))
            idea = generate_idea(recipe, seed=9, tempo=88)
            midi_path = root / "idea.mid"
            midi_path.write_bytes(render_midi(idea, recipe))
            source, events = parse_midi(midi_path)
            self.assertEqual((source.midi_format, source.tracks, source.ppq), (1, 3, 480))
            self.assertEqual({event.channel for event in events}, {1, 3})
            self.assertEqual(len(events), len(idea.events))
            legacy = render_midi(idea, recipe, midi_format=0)
            self.assertEqual(struct.unpack(">HHH", legacy[8:14]), (0, 1, 480))

    def test_recipe_default_harmonic_rhythm_fills_pattern(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "defaults.toml"
            path.write_text(
                'schema_version=1\nid="defaults"\nname="Defaults"\nkey="Bb"\n'
                'scale="mixolydian"\nbars=1\nprogression=[1,4]\n'
                'chord_range=[48,72]\nbass_range=[24,47]\n',
                encoding="utf-8",
            )
            recipe = load_recipe(path)
            self.assertEqual(recipe.key, "BB")
            self.assertEqual(recipe.chord_beats, (2.0, 2.0))
            idea = generate_idea(recipe, seed=1, tempo=100)
            self.assertEqual(idea.decisions[-1].start_beat, 2)

    def test_recipe_rejects_timing_and_range_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self._recipe(root)
            text = path.read_text(encoding="utf-8")
            path.write_text(text.replace("chord_beats=[2,2,2,2]", "chord_beats=[1,1,1,1]"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "fill exactly"):
                load_recipe(path)
            path.write_text(text.replace("bass_range=[28,52]", "bass_range=[60,20]"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "0 <= low"):
                load_recipe(path)

    def test_json_evidence_is_serializable(self):
        with tempfile.TemporaryDirectory() as directory:
            recipe = load_recipe(self._recipe(Path(directory)))
            idea = generate_idea(recipe, seed=17, tempo=96)
            payload = json.loads(json.dumps(idea.to_dict()))
            self.assertEqual(payload["seed"], 17)
            self.assertEqual(payload["chord_range"], [48, 76])
            self.assertEqual(payload["decisions"][0]["degree"], 1)


if __name__ == "__main__":
    unittest.main()
