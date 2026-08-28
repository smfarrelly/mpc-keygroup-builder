import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import model
from mpc_keygroup_builder.idea_batch import build_batch, render_batch_markdown, summarize
from mpc_keygroup_builder.workstation import generate_idea, load_recipe


class IdeaBatchTests(unittest.TestCase):
    def _ideas(self, root: Path):
        repository = Path(__file__).parents[1]
        loaded = load_recipe(repository / "recipes/workstation/dusty-scratchpad.toml")
        program = model.ProgramModel(
            1,
            "Kit",
            "drum",
            (
                model.Zone(1, "kick.primary", (model.SampleLayer("BD.wav"),), pad=1, midi_note=36),
                model.Zone(2, "snare.primary", (model.SampleLayer("SD.wav"),), pad=2, midi_note=38),
                model.Zone(3, "hihat.closed", (model.SampleLayer("CH.wav"),), pad=3, midi_note=42),
                model.Zone(4, "hihat.open", (model.SampleLayer("OH.wav"),), pad=4, midi_note=46),
            ),
            "fixture",
            pad_note_map={1: 36, 2: 38, 3: 42, 4: 46},
        )
        source = root / "source.xpm"
        source.write_text("source", encoding="utf-8")
        ideas = tuple(
            generate_idea(loaded, program, program_path=source, seed=seed, tempo=92)
            for seed in (20, 21, 22, 23)
        )
        return ideas

    def test_batch_is_deterministically_ranked_by_evidence_not_quality(self):
        with tempfile.TemporaryDirectory() as directory:
            ideas = self._ideas(Path(directory))
            first = build_batch(ideas)
            second = build_batch(ideas)
            self.assertEqual(first, second)
            self.assertEqual(first.count, 4)
            scores = [candidate.evidence_diversity_score for candidate in first.candidates]
            self.assertEqual(scores, sorted(scores, reverse=True))
            self.assertIn("not a musical-quality score", first.ranking_policy)
            self.assertEqual({candidate.seed for candidate in first.candidates}, {20, 21, 22, 23})
            markdown = render_batch_markdown(first)
            self.assertIn("Listening remains the decision gate", markdown)
            self.assertIn("MPC hardware import/listening: **DEFERRED**", markdown)

    def test_summary_has_all_four_parts_and_measurable_features(self):
        with tempfile.TemporaryDirectory() as directory:
            summary = summarize(self._ideas(Path(directory))[0])
            self.assertEqual(set(summary.event_counts), {"drums", "bass", "chords", "melody"})
            self.assertTrue(all(count > 0 for count in summary.event_counts.values()))
            self.assertGreaterEqual(summary.unique_drum_roles, 4)
            self.assertGreater(summary.unique_melody_notes, 1)
            self.assertGreater(summary.velocity_span, 0)

    def test_rejects_empty_or_mixed_batches(self):
        with self.assertRaisesRegex(ValueError, "at least one"):
            build_batch(())
        with tempfile.TemporaryDirectory() as directory:
            ideas = list(self._ideas(Path(directory)))
            object.__setattr__(ideas[1], "tempo", 93)
            with self.assertRaisesRegex(ValueError, "share recipe and tempo"):
                build_batch(tuple(ideas))


if __name__ == "__main__":
    unittest.main()
