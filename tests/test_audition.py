import gzip
import json
import tempfile
import unittest
import wave
from unittest.mock import patch
from pathlib import Path

from mpc_keygroup_builder import audition, program_io
from tests.test_testing_framework import write_keygroup


class AuditionTests(unittest.TestCase):
    def test_rejected_containers_do_not_create_output_directory(self):
        header = b'ACVS\n3.9.1.2\nSerialisableProgramData\njson\nLinux\n'
        cases = [
            (gzip.compress(b'{}'), 'header'),
            (gzip.compress(header + b'{"data":{"type":0}}'), 'compressed Drum'),
            (gzip.compress(header + b'{"data":{},"data":{}}'), 'duplicate'),
            (gzip.compress(header + b'{"data":{"type":1,"drum":{"instruments":[null]}}}'), 'objects'),
            (b'<!DOCTYPE x [<!ENTITY y "text">]><MPCVObject/>', 'document types'),
            (b'<MPCVObject><Program type="Keygroup"/></MPCVObject>', 'Drum programs only'),
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            program = root/'Bad.xpm'
            for payload, message in cases:
                with self.subTest(message=message):
                    program.write_bytes(payload)
                    with self.assertRaisesRegex(ValueError, message):
                        audition.render(program, root/'preview'/'test.wav')
                    self.assertFalse((root/'preview').exists())

    def test_source_and_expansion_limits_apply_before_audio_lookup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            program = root/'Large.xpm'
            for payload, setting, message in [
                (b'x'*101, 'MAX_SOURCE_BYTES', 'source bytes'),
                (gzip.compress(b'x'*101), 'MAX_EXPANDED_BYTES', 'expanded bytes'),
            ]:
                with self.subTest(setting=setting), patch.object(program_io, setting, 100):
                    program.write_bytes(payload)
                    with self.assertRaisesRegex(ValueError, message):
                        audition.render(program, root/'preview'/'test.wav')
                    self.assertFalse((root/'preview').exists())

    def test_trim_bounds_are_inclusive_and_reject_invalid_offsets(self):
        samples = [0.1, 0.2, 0.3, 0.4]
        self.assertEqual(audition.trim_sample(samples, "1", "2"), ([0.2, 0.3], 1, 2))
        self.assertEqual(audition.trim_sample(samples, 0, 0), ([0.1], 0, 0))
        self.assertEqual(audition.trim_sample(samples, None, None), (samples, 0, 3))
        for start, end in [(-1, 2), (2, 1), (0, 4), (True, 2), (1.5, 2), (0, "bad")]:
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                audition.trim_sample(samples, start, end)
        with self.assertRaises(ValueError):
            audition.trim_sample([], None, None)

    def test_keygroup_slices_before_resampling_and_records_bounds(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            program = write_keygroup(root)
            data = audition._json_program(program)
            layer = data['drum']['instruments'][1]['layersv'][0]
            layer.update(sampleStart=0, sampleEnd=0, sliceInfo={'Start': 7, 'End': 12})
            with gzip.open(program, 'wt') as stream:
                stream.write('ACVS\n3.9.1.2\nSerialisableProgramData\njson\nLinux\n')
                json.dump({'data': data}, stream)
            with patch.object(audition, 'KEYGROUP_NOTES', (60,)), \
                 patch.object(audition, 'read_pcm_mono', return_value=(list(range(32)), 44100)), \
                 patch.object(audition, 'resample', side_effect=lambda samples, rate, pitch: samples) as resample, \
                 patch.object(audition, 'shape', side_effect=lambda samples, velocity: samples):
                events, audio = audition.keygroup_events(program)
            self.assertEqual(audio, [list(range(7, 13))])
            self.assertEqual(resample.call_args.args[0], list(range(7, 13)))
            self.assertEqual((events[0].sample_start, events[0].sample_end), (7, 12))

    def test_drum_uses_slice_bounds_before_pitch_preview(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'sample.wav').touch()
            program = root / 'Drum.xpm'
            program.write_text('<MPCVObject><Program><Instrument number="1"><Layer>'
                              '<SampleFile>sample.wav</SampleFile><SliceStart>2</SliceStart>'
                              '<SliceEnd>4</SliceEnd><SampleStart>0</SampleStart>'
                              '<SampleEnd>0</SampleEnd></Layer></Instrument></Program></MPCVObject>')
            with patch.object(audition, 'read_pcm_mono', return_value=(list(range(10)), 44100)), \
                 patch.object(audition, 'resample', side_effect=lambda samples, rate, pitch: samples), \
                 patch.object(audition, 'shape', side_effect=lambda samples, velocity: samples):
                events, audio = audition.drum_events(program)
            self.assertEqual(audio, [[2, 3, 4]])
            self.assertEqual((events[0].sample_start, events[0].sample_end), (2, 4))

    def test_invalid_bounds_do_not_publish_preview(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            program = write_keygroup(root, sample_end=99999)
            with self.assertRaisesRegex(ValueError, 'sample bounds'):
                audition.render(program, root / 'preview.wav')
            self.assertFalse((root / 'preview.wav').exists())
            self.assertFalse((root / 'preview.json').exists())

    def test_keygroup_render_writes_audio_and_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            program = write_keygroup(root)
            output = root / "audition.wav"
            manifest = audition.render(program, output)
            self.assertTrue(output.is_file())
            self.assertTrue(output.with_suffix(".json").is_file())
            self.assertEqual(len(manifest["events"]), len(audition.KEYGROUP_NOTES))
            with wave.open(str(output), "rb") as stream:
                self.assertEqual(stream.getframerate(), audition.OUTPUT_RATE)
                self.assertGreater(stream.getnframes(), 0)

    def test_output_requires_wav_and_cannot_replace_program(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            program = write_keygroup(root)
            original = program.read_bytes()
            with self.assertRaisesRegex(ValueError, r"\.wav extension"):
                audition.render(program, root / "audition.json")
            wav_named_program = program.with_suffix(".wav")
            program.rename(wav_named_program)
            with self.assertRaisesRegex(ValueError, "replace the input program"):
                audition.render(wav_named_program, wav_named_program)
            self.assertEqual(wav_named_program.read_bytes(), original)

    def test_output_preflight_rejects_manifest_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            program = write_keygroup(root)
            external = root / "external.json"
            external.write_text("keep\n")
            (root / "audition.json").symlink_to(external)
            with self.assertRaisesRegex(ValueError, "manifest.*symbolic link"):
                audition.render(program, root / "audition.wav")
            self.assertFalse((root / "audition.wav").exists())
            self.assertEqual(external.read_text(), "keep\n")


if __name__ == "__main__":
    unittest.main()
