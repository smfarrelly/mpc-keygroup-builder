import copy
import tempfile
import unittest
import wave
import gzip
import json
from pathlib import Path

from mpc_keygroup_builder import cli as builder


class MappingTests(unittest.TestCase):
    def test_note_ranges_cover_midi_without_gaps(self):
        samples = [
            builder.SampleGroup(24, (builder.Sample(24, Path("24.wav"), 10),)),
            builder.SampleGroup(60, (builder.Sample(60, Path("60.wav"), 10),)),
            builder.SampleGroup(120, (builder.Sample(120, Path("120.wav"), 10),)),
        ]
        self.assertEqual(builder.note_ranges(samples), [(0, 42), (43, 90), (91, 127)])

    def test_discovery_reads_frames_and_sorts_notes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for note, frames in ((61, 12), (60, 8)):
                with wave.open(str(root / f"{note} sample.wav"), "wb") as wav:
                    wav.setnchannels(1)
                    wav.setsampwidth(2)
                    wav.setframerate(44100)
                    wav.writeframes(b"\0\0" * frames)
            samples = builder.discover_samples(root)
            self.assertEqual(
                [(group.note, group.layers[0].frames) for group in samples],
                [(60, 8), (61, 12)],
            )

    def test_discovery_accepts_note_immediately_followed_by_name(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_wav(root / "60BreathV_DX100_C3.wav")
            groups = builder.discover_samples(root)
            self.assertEqual(groups[0].note, 60)

    def test_duplicate_notes_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("60 left.wav", "060 right.wav"):
                with wave.open(str(root / name), "wb") as wav:
                    wav.setnchannels(1)
                    wav.setsampwidth(2)
                    wav.setframerate(44100)
                    wav.writeframes(b"\0\0")
            with self.assertRaisesRegex(ValueError, "multiple WAVs map"):
                builder.discover_samples(root)

    def test_adjacent_numeric_typo_uses_trailing_pitch_name(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_wav(root / "073 Square Bass Emulator C#4.wav")
            self.write_wav(root / "073 Square Bass Emulator D4.wav")
            groups = builder.discover_samples(root)
            self.assertEqual([group.note for group in groups], [73, 74])

    def test_repeated_lexical_number_uses_unique_trailing_pitches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_wav(root / "80s Piano Dr Sample 01 C2.wav")
            self.write_wav(root / "80s Piano Dr Sample 02 C#2.wav")
            self.write_wav(root / "80s Piano Dr Sample 03 D2.wav")
            groups = builder.discover_samples(root)
            self.assertEqual([group.note for group in groups], [48, 49, 50])

    def test_note_name_only_filenames_use_trailing_pitch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_wav(root / "Sub Bass Dr Sample C1.wav")
            self.write_wav(root / "Sub Bass Dr Sample C#1.wav")
            groups = builder.discover_samples(root)
            self.assertEqual([group.note for group in groups], [36, 37])

    def test_note_name_only_stereo_pair_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_wav(root / "Wide Pad L C2.wav")
            self.write_wav(root / "Wide Pad R C2.wav")
            with self.assertRaisesRegex(ValueError, "multiple WAVs map"):
                builder.discover_samples(root)

    def test_random_id_suffix_is_not_treated_as_pitch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_wav(root / "027_HalfSub_tri_SH101_D#0-E2E0.wav")
            self.write_wav(root / "028_HalfSub_tri_SH101_E0-JJPH.wav")
            groups = builder.discover_samples(root)
            self.assertEqual([group.note for group in groups], [27, 28])

    def test_pitch_typo_does_not_override_unique_numeric_sequence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_wav(root / "108_BoogieBassPulseMod_ARP2600_C#7.wav")
            self.write_wav(root / "109_BoogieBassPulseMod_ARP2600_C#7.wav")
            groups = builder.discover_samples(root)
            self.assertEqual([group.note for group in groups], [108, 109])

    def test_truncated_wav_names_the_bad_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "60 broken.wav"
            path.touch()
            with self.assertRaisesRegex(ValueError, r"unreadable WAV .*60 broken\.wav"):
                builder.discover_samples(path.parent)


    def write_wav(self, path, frames=8):
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(44100)
            wav.writeframes(b"\0\0" * frames)

    def write_velocity_preset(self, path, zones):
        parts = []
        for filename, low, high in zones:
            parts.append(
                "<MultiSamplePart>"
                f'<VelocityRange><Min Value="{low}"/><Max Value="{high}"/>'
                "</VelocityRange>"
                "<SampleRef><FileRef>"
                f'<Name Value="{filename}"/>'
                "</FileRef></SampleRef>"
                "</MultiSamplePart>"
            )
        with gzip.open(path, "wt") as stream:
            stream.write("<Ableton>" + "".join(parts) + "</Ableton>")

    def test_velocity_preset_groups_layers_and_covers_velocity_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            names = ("60_Test_C3.wav", "60_Test_C3_0001.wav")
            for name in names:
                self.write_wav(root / name)
            preset = root / "Test.adg"
            self.write_velocity_preset(
                preset, [(names[0], 1, 63), (names[1], 64, 127)]
            )
            groups = builder.discover_samples(root, preset)
            self.assertEqual(
                [(layer.velocity_start, layer.velocity_end) for layer in groups[0].layers],
                [(0, 63), (64, 127)],
            )

    def test_single_wav_uses_full_velocity_despite_partial_preset_zone(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            name = "60_Test_C3.wav"
            self.write_wav(root / name)
            preset = root / "Test.adg"
            self.write_velocity_preset(preset, [(name, 67, 127)])
            groups = builder.discover_samples(root, preset)
            layer = groups[0].layers[0]
            self.assertEqual((layer.velocity_start, layer.velocity_end), (0, 127))

    def test_end_to_end_written_program_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            for note in (60, 64):
                with wave.open(str(source / f"{note} sample.wav"), "wb") as wav:
                    wav.setnchannels(1)
                    wav.setsampwidth(2)
                    wav.setframerate(44100)
                    wav.writeframes(b"\0\0" * 8)
            layer = {
                "active": True, "mute": False, "sampleName": "old",
                "sampleFile": "old.wav", "rootNote": 60,
                "velocityStart": 0, "velocityEnd": 127,
                "keyTrackEnable": False, "sampleStart": 0, "sampleEnd": 0,
                "sliceInfo": {"Start": 0, "End": 7},
            }
            instrument = {
                "lowNote": 0, "highNote": 127,
                "layersv": [copy.deepcopy(layer) for _ in range(8)],
            }
            template_data = {"data": {
                "name": "template",
                "drum": {"instruments": [instrument, instrument]},
                "keygroup": {"numKeygroups": 1},
                "samples": [],
            }}
            template = root / "template.xpm"
            header = "ACVS\n3.9.1.2\nSerialisableProgramData\njson\nLinux\n"
            with gzip.open(template, "wt") as stream:
                stream.write(header + json.dumps(template_data))
            samples = builder.discover_samples(source)
            built_header, program = builder.build_program(template, samples, "Test")
            output = root / "Test.xpm"
            builder.write_program(built_header, program, samples, output, force=False)
            self.assertEqual(
                builder.validate_written_program(output),
                {"keygroups": 2, "samples": 2},
            )


    def test_ableton_root_key_maps_filename_without_octave(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            name = "Omni Long-1C.wav"
            self.write_wav(root / name)
            preset = root / "Omni Long.adg"
            with gzip.open(preset, "wt") as stream:
                stream.write(
                    "<Ableton><MultiSamplePart>"
                    '<VelocityRange><Min Value="1"/><Max Value="127"/></VelocityRange>'
                    '<RootKey Value="24"/>'
                    f'<SampleRef><FileRef><Name Value="{name}"/></FileRef></SampleRef>'
                    "</MultiSamplePart></Ableton>"
                )
            groups = builder.discover_samples(root, preset)
            self.assertEqual(groups[0].note, 24)


    def test_ableton_root_key_preserves_velocity_layer_suffix(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            names = ("Patch C.wav", "Patch C_0001.wav")
            for name in names:
                self.write_wav(root / name)
            preset = root / "Patch.adg"
            self.write_velocity_preset(
                preset, [(names[0], 1, 63), (names[1], 64, 127)]
            )
            with gzip.open(preset, "rt") as stream:
                text = stream.read().replace(
                    "<SampleRef>", '<RootKey Value="36"/><SampleRef>'
                )
            with gzip.open(preset, "wt") as stream:
                stream.write(text)
            groups = builder.discover_samples(root, preset)
            self.assertEqual(groups[0].note, 36)
            self.assertEqual(len(groups[0].layers), 2)


    def test_trailing_midi_number_is_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_wav(root / "SFM-MicroMoog1-24.wav")
            groups = builder.discover_samples(root)
            self.assertEqual(groups[0].note, 24)


    def test_pitch_before_random_id_is_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_wav(root / "TB-303_Sub-A0-CJB2.wav")
            groups = builder.discover_samples(root)
            self.assertEqual(groups[0].note, 33)


if __name__ == "__main__":
    unittest.main()
