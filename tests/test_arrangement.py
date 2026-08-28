import json
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import model
from mpc_keygroup_builder.arrangement import arrange_idea, render_markdown, render_section
from mpc_keygroup_builder.midi_groove import parse_midi
from mpc_keygroup_builder.workstation import generate_idea, load_recipe


class ArrangementTests(unittest.TestCase):
    def _program(self) -> model.ProgramModel:
        return model.ProgramModel(
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

    def _base(self, root: Path):
        repository = Path(__file__).parents[1]
        loaded = load_recipe(repository / "recipes/workstation/dusty-scratchpad.toml")
        source = root / "source.xpm"
        source.write_text("deterministic source fingerprint", encoding="utf-8")
        idea = generate_idea(
            loaded, self._program(), program_path=source, seed=12, tempo=94
        )
        return loaded, idea

    def test_sections_are_reproducible_traceable_and_track_lock_aware(self):
        with tempfile.TemporaryDirectory() as directory:
            loaded, base = self._base(Path(directory))
            first = arrange_idea(
                base, loaded, arrangement_seed=500, mutation=0.25,
                locked_tracks=("chords",),
            )
            second = arrange_idea(
                base, loaded, arrangement_seed=500, mutation=0.25,
                locked_tracks=("chords",),
            )
            other = arrange_idea(
                base, loaded, arrangement_seed=501, mutation=0.25,
                locked_tracks=("chords",),
            )
            self.assertEqual(first, second)
            self.assertNotEqual(first.sections[1], other.sections[1])
            self.assertEqual([section.id for section in first.sections], [
                "main", "main-b", "breakdown", "build", "outro"
            ])
            main, main_b, breakdown, build, outro = first.sections
            self.assertEqual(main.events, tuple(event for event in main.events))
            self.assertFalse(main.omitted_source_ids)
            self.assertFalse(main_b.omitted_source_ids)
            eligible = [event for event in main.events if event.track != "chords"]
            changed = [event for event in main_b.events if event.action != "source"]
            self.assertEqual(len(changed), round(len(eligible) * 0.25))
            source_chords = [event for event in main.events if event.track == "chords"]
            for section in first.sections:
                section_chords = [event for event in section.events if event.track == "chords"]
                self.assertEqual(section_chords, source_chords)
            self.assertLess(len(breakdown.events), len(main.events))
            self.assertEqual(len(build.events), len(main.events))
            self.assertLess(len(outro.events), len(main.events))
            source_ids = {event.source_id for event in main.events}
            self.assertTrue(all(
                {event.source_id for event in section.events}.issubset(source_ids)
                for section in first.sections
            ))

    def test_every_section_is_valid_four_track_midi(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            loaded, base = self._base(root)
            arrangement = arrange_idea(base, loaded, arrangement_seed=8, mutation=0.2)
            for section in arrangement.sections:
                path = root / f"{section.id}.mid"
                path.write_bytes(render_section(section, arrangement))
                source, events = parse_midi(path)
                self.assertEqual((source.midi_format, source.tracks, source.ppq), (1, 5, 480))
                self.assertEqual(len(events), len(section.events))
                self.assertTrue(all(1 <= event.velocity <= 127 for event in events))

    def test_evidence_is_serializable_and_documents_hardware_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            loaded, base = self._base(Path(directory))
            arrangement = arrange_idea(base, loaded, arrangement_seed=44)
            payload = json.loads(json.dumps(arrangement.to_dict()))
            self.assertEqual(payload["sections"][0]["name"], "Main")
            self.assertIn("source_id", payload["sections"][1]["events"][0])
            markdown = render_markdown(arrangement)
            self.assertIn("MPC hardware import/listening: **DEFERRED**", markdown)
            self.assertIn("auditable and reversible", markdown)

    def test_rejects_invalid_mutation_and_locks(self):
        with tempfile.TemporaryDirectory() as directory:
            loaded, base = self._base(Path(directory))
            with self.assertRaisesRegex(ValueError, "mutation"):
                arrange_idea(base, loaded, arrangement_seed=1, mutation=1.1)
            with self.assertRaisesRegex(ValueError, "unknown locked"):
                arrange_idea(base, loaded, arrangement_seed=1, locked_tracks=("vocals",))
            with self.assertRaisesRegex(ValueError, "unique"):
                arrange_idea(base, loaded, arrangement_seed=1, locked_tracks=("bass", "bass"))


if __name__ == "__main__":
    unittest.main()
