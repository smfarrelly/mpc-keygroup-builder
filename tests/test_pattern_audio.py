import json
from pathlib import Path
import tempfile
import unittest
import wave

from mpc_keygroup_builder import bundle_verify, drum_session, pattern_audio


class PatternAudioTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.program = self.root / "Kit.xpm"
        self.pattern = self.root / "idea.json"
        self.output = self.root / "preview.wav"
        for name, amplitude in (("low", 1000), ("high", 2000)):
            with wave.open(str(self.root / (name + ".wav")), "wb") as stream:
                stream.setparams((1, 2, 44100, 2000, "NONE", ""))
                stream.writeframes(amplitude.to_bytes(2, "little") * 2000)
        self.program.write_text('''<MPCVObject><Program type="Drum"><ProgramName>Kit</ProgramName>
            <PadNoteMap><PadNote number="1"><Note>36</Note></PadNote><PadNote number="2"><Note>39</Note></PadNote></PadNoteMap>
            <Instruments><Instrument number="1"><OneShot>True</OneShot><MuteGroup>1</MuteGroup><Layers>
            <Layer><SampleFile>low.wav</SampleFile><VelEnd>63</VelEnd></Layer>
            <Layer><SampleFile>high.wav</SampleFile><VelStart>64</VelStart></Layer></Layers></Instrument>
            <Instrument number="2"><OneShot>False</OneShot><MuteGroup>1</MuteGroup><Layers>
            <Layer><SampleFile>low.wav</SampleFile></Layer></Layers></Instrument></Instruments></Program></MPCVObject>''')
        self.idea = {"schema_version": 1, "program": "Kit", "bars": 1, "tempo": 120, "ppq": 480,
                     "events": [{"tick": 0, "pad": 1, "velocity": 90, "midi_note": 36, "sample": "low.wav", "duration_ticks": 1},
                                {"tick": 10, "pad": 2, "velocity": 60, "midi_note": 39, "sample": "low.wav", "duration_ticks": 2}]}

    def render(self, output=None):
        self.pattern.write_text(json.dumps(self.idea))
        return pattern_audio.render_pattern(self.program, self.pattern, output or self.output)

    def test_timing_layer_selection_choke_and_gate(self):
        report = self.render()
        first, second = report["events"]
        self.assertEqual(first["sample"], "high.wav")
        self.assertEqual((first["start_frame"], first["played_frames"]), (0, 459))
        self.assertEqual((second["start_frame"], second["played_frames"]), (459, 92))
        self.assertEqual(report["frames"], 88200)
        with wave.open(str(self.output)) as wav:
            self.assertEqual(wav.getnframes(), 88200)
            signal = wav.readframes(88200)
        self.assertTrue(any(signal[:459 * 2]))
        self.assertFalse(any(signal[551 * 2:]))

    def test_different_mapping_rejected_before_writing(self):
        for key, value in (("sample", "Different.wav"), ("midi_note", 40), ("tick", -1)):
            with self.subTest(key=key):
                old = self.idea["events"][0][key]
                self.idea["events"][0][key] = value
                with self.assertRaises(ValueError):
                    self.render()
                self.assertFalse(self.output.exists())
                self.idea["events"][0][key] = old

    def test_session_creates_linked_midi_audio_and_verified_receipt(self):
        program = self.program.read_text().replace("low.wav", "Kick.wav").replace("high.wav", "Kick Hard.wav")
        self.program.write_text(program)
        (self.root / "low.wav").rename(self.root / "Kick.wav")
        (self.root / "high.wav").rename(self.root / "Kick Hard.wav")
        recipe = self.root / "drums.toml"
        recipe.write_text('schema_version=1\nid="test"\nname="Test & Kit"\nbars=1\nsteps_per_bar=16\n'
                          '[[events]]\nrole="kick"\nsteps=[0,4]\nvelocity=100\n')
        output = self.root / "session"
        result = drum_session.build(self.program, [recipe], output)
        self.assertEqual(result["patterns"][0]["events"], 2)
        self.assertEqual(bundle_verify.verify_bundle(output)["verified_files"], 6)
        html = (output / "index.html").read_text()
        self.assertIn("Test &amp; Kit", html)
        for file in ("listen.wav", "pattern.mid", "pattern.json", "listen.json"):
            relative = "pattern-01/" + file
            self.assertIn(relative, html)
            self.assertTrue((output / relative).is_file())
        with self.assertRaises(FileExistsError):
            drum_session.build(self.program, [recipe], output)
        missing = self.root / "missing.toml"
        missing.write_text(recipe.read_text().replace('role="kick"', 'role="snare"'))
        with self.assertRaisesRegex(ValueError, "required role"):
            drum_session.build(self.program, [recipe, missing], self.root / "incomplete")
        self.assertFalse((self.root / "incomplete").exists())
        self.assertFalse(list(self.root.glob(".drum-session-*")))

    def test_source_files_cannot_be_overwritten(self):
        with self.assertRaisesRegex(ValueError, "output stem"):
            self.render(self.pattern.with_suffix(".wav"))
        source = self.root / "high.wav"
        original = source.read_bytes()
        with self.assertRaisesRegex(ValueError, "replace a sample"):
            self.render(source)
        self.assertEqual(source.read_bytes(), original)
