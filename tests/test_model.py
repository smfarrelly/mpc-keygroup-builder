import gzip
import json
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import model


class ProgramModelTests(unittest.TestCase):
    def test_loads_inherited_six_bank_manifest(self):
        root = Path(__file__).parents[1]
        program = model.from_drum_manifest(root / "inventory/fg-vinyl-shots-six-bank.toml")
        self.assertEqual(program.name, "FG Vinyl Shots 03 Six Bank")
        self.assertEqual(program.kind, "drum")
        self.assertEqual(len(program.zones), 96)
        self.assertEqual(program.zones[0].role, "percussion.bongo")
        self.assertEqual(program.zones[64].role, "clap.primary")
        self.assertEqual(program.validate(), {"errors": [], "warnings": []})

    def test_loads_inherited_eight_bank_manifest(self):
        root = Path(__file__).parents[1]
        program = model.from_drum_manifest(root / "inventory/fg-vinyl-shots-eight-bank.toml")
        self.assertEqual(program.name, "FG Vinyl Shots 04 Eight Bank")
        self.assertEqual(program.kind, "drum")
        self.assertEqual(len(program.zones), 128)
        self.assertEqual(program.zones[96].role, "kick.primary")
        self.assertEqual(program.zones[104].role, "snare.primary")
        self.assertEqual(program.zones[112].role, "hihat.closed")
        self.assertEqual(program.zones[120].role, "hihat.open")
        self.assertEqual(program.zones[112].mute_group, 1)
        self.assertEqual(program.zones[120].mute_group, 1)
        self.assertEqual(program.validate(), {"errors": [], "warnings": []})

    def test_loads_legacy_xml_drum_program(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Kit.xpm"
            settings = {"ProgramPads": {"pads": {"value0": 0xFF0000}}}
            path.write_text(
                '<?xml version="1.0"?><MPCVObject><Program type="Drum">'
                '<ProgramName>Kit</ProgramName><ProgramPads>' + json.dumps(settings) + '</ProgramPads>'
                '<PadNoteMap><PadNote number="1"><Note>36</Note></PadNote></PadNoteMap>'
                '<Instruments><Instrument number="1"><Mono>True</Mono><Polyphony>1</Polyphony>'
                '<MuteGroup>0</MuteGroup><OneShot>True</OneShot><Layers><Layer>'
                '<VelStart>0</VelStart><VelEnd>127</VelEnd><RootNote>36</RootNote>'
                '<SampleFile>BD Warm.wav</SampleFile><SliceStart>0</SliceStart><SliceEnd>99</SliceEnd>'
                '</Layer></Layers></Instrument></Instruments></Program></MPCVObject>',
                encoding="utf-8",
            )
            program = model.from_xpm(path)
            self.assertEqual(program.kind, "drum")
            self.assertEqual(program.zones[0].pad, 1)
            self.assertEqual(program.zones[0].midi_note, 36)
            self.assertEqual(program.zones[0].role, "kick.primary")
            self.assertEqual(program.zones[0].color, 0xFF0000)
            self.assertEqual(program.zones[0].layers[0].sample_end, 99)

    def test_loads_compressed_keygroup_without_universal_record(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Keys.xpm"
            layer = {
                "active": True,
                "sampleFile": "Piano C3.wav",
                "velocityStart": 0,
                "velocityEnd": 127,
                "rootNote": 60,
                "sliceInfo": {"Start": 0, "End": 999},
            }
            instrument = {"lowNote": 48, "highNote": 72, "layersv": [layer], "polyphony": 8}
            data = {
                "data": {
                    "name": "Keys",
                    "type": 1,
                    "keygroup": {"numKeygroups": 1},
                    "drum": {"instruments": [{"layersv": [layer]}, instrument]},
                    "programPads": {"pads": {}},
                }
            }
            payload = b"ACVS\n3.9.1.2\nSerialisableProgramData\njson\nLinux\n" + json.dumps(data).encode()
            path.write_bytes(gzip.compress(payload, mtime=0))
            program = model.from_xpm(path)
            self.assertEqual(program.kind, "keygroup")
            self.assertEqual(len(program.zones), 1)
            self.assertEqual((program.zones[0].low_note, program.zones[0].high_note), (48, 72))
            self.assertEqual(program.zones[0].layers[0].root_note, 60)
            self.assertEqual(program.validate(), {"errors": [], "warnings": []})

    def test_validation_detects_duplicate_pads_and_bad_velocity(self):
        bad_layer = model.SampleLayer("Bad.wav", velocity_start=100, velocity_end=20)
        bad = model.ProgramModel(
            1,
            "Bad",
            "drum",
            (
                model.Zone(1, "kick.primary", (bad_layer,), pad=1),
                model.Zone(2, "snare.primary", (bad_layer,), pad=1),
            ),
            "fixture",
        )
        report = bad.validate()
        self.assertTrue(any("unique" in value for value in report["errors"]))
        self.assertTrue(any("velocity" in value for value in report["errors"]))


if __name__ == "__main__":
    unittest.main()
