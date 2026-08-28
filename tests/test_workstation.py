import json
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder.midi_groove import parse_midi
from mpc_keygroup_builder.model import from_xpm
from mpc_keygroup_builder.workstation import (
    generate_idea,
    load_recipe,
    render_markdown,
    render_midi,
)


class WorkstationIdeaTests(unittest.TestCase):
    def _program(self, root: Path) -> Path:
        path = root / "Kit.xpm"
        instruments = []
        pad_notes = []
        for number, (note, sample) in enumerate(
            ((36, "BD Warm.wav"), (38, "SD Dust.wav"), (42, "CH Tight.wav"), (46, "OH Air.wav")),
            1,
        ):
            pad_notes.append(f'<PadNote number="{number}"><Note>{note}</Note></PadNote>')
            instruments.append(
                f'<Instrument number="{number}"><Layers><Layer><VelStart>0</VelStart>'
                f'<VelEnd>127</VelEnd><RootNote>{note}</RootNote><SampleFile>{sample}</SampleFile>'
                '<SliceStart>0</SliceStart><SliceEnd>99</SliceEnd></Layer></Layers></Instrument>'
            )
        path.write_text(
            '<?xml version="1.0"?><MPCVObject><Program type="Drum"><ProgramName>Kit</ProgramName>'
            '<ProgramPads>{"ProgramPads":{"pads":{}}}</ProgramPads><PadNoteMap>'
            + "".join(pad_notes)
            + '</PadNoteMap><Instruments>'
            + "".join(instruments)
            + '</Instruments></Program></MPCVObject>',
            encoding="utf-8",
        )
        return path

    def test_combines_four_named_tracks_and_repeats_short_drums(self):
        root = Path(__file__).parents[1]
        loaded = load_recipe(root / "recipes/workstation/dusty-scratchpad.toml")
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            program_path = self._program(temp)
            program = from_xpm(program_path)
            first = generate_idea(loaded, program, program_path=program_path, seed=81, tempo=93)
            second = generate_idea(loaded, program, program_path=program_path, seed=81, tempo=93)
            self.assertEqual(first, second)
            self.assertEqual(first.component_seeds, {"drums": 81, "harmony": 82, "melody": 83})
            midi_path = temp / "bundle.mid"
            midi_path.write_bytes(render_midi(first, loaded))
            source, events = parse_midi(midi_path)
            self.assertEqual((source.midi_format, source.tracks, source.ppq), (1, 5, 480))
            self.assertEqual({event.channel for event in events}, {1, 2, 3, 10})
            expected_drums = len(first.drums.events) * 2
            self.assertEqual(sum(event.channel == 10 for event in events), expected_drums)
            self.assertTrue(any(event.tick >= 2 * 4 * 480 for event in events if event.channel == 10))

    def test_evidence_and_hardware_boundary_are_explicit(self):
        root = Path(__file__).parents[1]
        loaded = load_recipe(root / "recipes/workstation/dusty-scratchpad.toml")
        with tempfile.TemporaryDirectory() as directory:
            program_path = self._program(Path(directory))
            idea = generate_idea(
                loaded, from_xpm(program_path), program_path=program_path, seed=1, tempo=90
            )
            payload = json.loads(json.dumps(idea.to_dict()))
            self.assertEqual(payload["suggested_programs"]["bass"], "Mirage Pluck Bass")
            self.assertEqual(len(payload["drum_program_sha256"]), 64)
            markdown = render_markdown(idea, loaded)
            self.assertIn("Software generation: **PASS**", markdown)
            self.assertIn("MPC hardware import/listening: **DEFERRED**", markdown)
            for track in ("1. Drums", "2. Bass", "3. Chords", "4. Melody"):
                self.assertIn(track, markdown)

    def test_repository_workstation_recipes_are_structurally_compatible(self):
        root = Path(__file__).parents[1]
        loaded = [load_recipe(path) for path in sorted((root / "recipes/workstation").glob("*.toml"))]
        self.assertEqual(len(loaded), 3)
        self.assertEqual({item.recipe.id for item in loaded}, {
            "ambient-scratchpad", "dusty-scratchpad", "electro-scratchpad"
        })


if __name__ == "__main__":
    unittest.main()
