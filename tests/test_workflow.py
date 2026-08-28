import copy
import gzip
import json
import tempfile
import unittest
import wave
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from mpc_keygroup_builder import workflow
from mpc_keygroup_builder.cli import read_xpm


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.library = self.root / "library"
        self.mpc = self.root / "mpc"
        self.source = self.library / "Test From Mars" / "WAV" / "Patch"
        self.source.mkdir(parents=True)
        self.mpc.mkdir()
        template = self.root / "template.xpm"
        self.write_template(template)
        self.settings = workflow.Settings(
            self.library, self.mpc, template, self.root / "artifacts"
        )

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def write_wav(path, frames=8):
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as wav:
            wav.setparams((1, 2, 44100, frames, "NONE", "not compressed"))
            wav.writeframes(b"\0\1" * frames)

    @staticmethod
    def write_template(path):
        layer = {
            "active": True, "mute": False, "sampleName": "old",
            "sampleFile": "old.wav", "rootNote": 60, "velocityStart": 0,
            "velocityEnd": 127, "keyTrackEnable": False, "sampleStart": 0,
            "sampleEnd": 0, "sliceInfo": {"Start": 0, "End": 7},
        }
        instrument = {
            "lowNote": 0, "highNote": 127,
            "layersv": [copy.deepcopy(layer) for _ in range(8)],
        }
        data = {"data": {
            "name": "template",
            "drum": {"instruments": [instrument, copy.deepcopy(instrument)]},
            "keygroup": {"numKeygroups": 1}, "samples": [],
        }}
        with gzip.open(path, "wt") as stream:
            stream.write("ACVS\n3.9.1.2\nSerialisableProgramData\njson\nLinux\n")
            json.dump(data, stream)

    def batch(self, mode="copy", central=None, checked=False):
        item = workflow.Instrument(
            "Patch", "Keys", self.source, None, mode, central, checked
        )
        return workflow.Batch(
            self.root / "test.json", "Test From Mars",
            self.mpc / "Programs" / "Keygroups" / "Test From Mars", (item,),
        )

    def test_copy_lifecycle_resume_and_cleanup(self):
        self.write_wav(self.source / "60 Patch C3.wav")
        self.write_wav(self.source / "64 Patch E3.wav", frames=9)
        batch = self.batch()
        with redirect_stdout(StringIO()):
            self.assertEqual(workflow.inspect_batch(self.settings, batch), 0)
            workflow.build_batch(self.settings, batch, force=False)
            workflow.validate_batch(self.settings, batch, location="artifacts")
            workflow.install_batch(self.settings, batch, execute=False)
        installed, installed_data = workflow.installed_paths(batch, batch.instruments[0])
        self.assertFalse(installed.exists())
        with redirect_stdout(StringIO()):
            workflow.install_batch(self.settings, batch, execute=True)
            workflow.install_batch(self.settings, batch, execute=True)
        self.assertTrue(installed.is_file())
        self.assertEqual(len(workflow.wav_map(installed_data)), 2)
        artifact, artifact_data = workflow.artifact_paths(
            self.settings, batch, batch.instruments[0]
        )
        with redirect_stdout(StringIO()):
            workflow.clean_batch(self.settings, batch, execute=False)
        self.assertTrue(artifact.exists())
        with redirect_stdout(StringIO()):
            workflow.clean_batch(self.settings, batch, execute=True)
        self.assertFalse(artifact.exists())
        self.assertFalse(artifact_data.exists())
        self.assertTrue(installed.exists())

    def test_relocate_resumes_after_directory_move(self):
        self.write_wav(self.source / "60 Patch C3.wav")
        central = self.mpc / "Samples" / "Test" / "Patch"
        central.mkdir(parents=True)
        workflow.copy_file_durable(self.source / "60 Patch C3.wav", central / "60 Patch C3.wav")
        batch = self.batch("relocate", central, True)
        workflow.build_batch(self.settings, batch, force=False)
        _, target_data = workflow.installed_paths(batch, batch.instruments[0])
        target_data.parent.mkdir(parents=True, exist_ok=True)
        central.replace(target_data)
        with redirect_stdout(StringIO()):
            workflow.install_batch(self.settings, batch, execute=True)
        target, _ = workflow.installed_paths(batch, batch.instruments[0])
        self.assertTrue(target.is_file())
        self.assertFalse(central.exists())

    def test_replace_corrupt_removes_only_zero_data(self):
        self.write_wav(self.source / "60 Patch C3.wav")
        central = self.mpc / "Samples" / "Test" / "Patch"
        central.mkdir(parents=True)
        (central / "60 Patch C3.wav").touch()
        batch = self.batch("replace_corrupt", central, True)
        workflow.build_batch(self.settings, batch, force=False)
        with redirect_stdout(StringIO()):
            workflow.install_batch(self.settings, batch, execute=True)
        self.assertFalse(central.exists())

    def test_inspect_rejects_unmapped_wav(self):
        self.write_wav(self.source / "60 Patch C3.wav")
        self.write_wav(self.source / "unknown.wav")
        with redirect_stdout(StringIO()):
            self.assertEqual(workflow.inspect_batch(self.settings, self.batch()), 1)

    def test_manifest_path_escape_is_rejected(self):
        manifest = self.root / "escape.json"
        manifest.write_text(json.dumps({
            "version": 1, "library": "Test", "source_root": "../outside",
            "destination": "Programs/Test",
            "instruments": [{"name": "Patch", "source": "Patch"}],
        }))
        with self.assertRaisesRegex(ValueError, "escapes"):
            workflow.load_batch(manifest, self.settings)


    def test_selection_builds_and_validates_only_chosen_wavs(self):
        self.write_wav(self.source / "60 Patch Clean.wav")
        self.write_wav(self.source / "060 Patch Alt.wav", frames=9)
        item = workflow.Instrument(
            "Patch", "Keys", self.source, None, "copy", None, False,
            ("*Clean.wav",), (),
        )
        batch = workflow.Batch(
            self.root / "selected.json", "Test From Mars",
            self.mpc / "Programs" / "Keygroups" / "Test From Mars", (item,),
        )
        with redirect_stdout(StringIO()) as output:
            self.assertEqual(workflow.inspect_batch(self.settings, batch), 0)
            workflow.build_batch(self.settings, batch, force=False)
            workflow.validate_batch(self.settings, batch, location="artifacts")
            workflow.install_batch(self.settings, batch, execute=True)
        self.assertIn("excluded=1", output.getvalue())
        _, data = workflow.installed_paths(batch, item)
        self.assertEqual(set(workflow.wav_map(data)), {"60 Patch Clean.wav"})

    def test_manifest_selection_rejects_destructive_install_mode(self):
        manifest = self.root / "selection.json"
        manifest.write_text(json.dumps({
            "version": 1,
            "library": "Test",
            "source_root": "Test From Mars/WAV",
            "destination": "Programs/Test",
            "centralized_root": "Samples/Test",
            "instruments": [{
                "name": "Patch",
                "source": "Patch",
                "centralized": "Patch",
                "install": "relocate",
                "sample_selection": {"exclude": ["*Alt.wav"]},
            }],
        }))
        with self.assertRaisesRegex(ValueError, "requires install=copy"):
            workflow.load_batch(manifest, self.settings)

    def test_manifest_root_shift_moves_built_keygroups(self):
        self.write_wav(self.source / "36 Patch C1.wav")
        manifest = self.root / "shifted.json"
        manifest.write_text(json.dumps({
            "version": 1,
            "library": "Test",
            "source_root": "Test From Mars/WAV",
            "destination": "Programs/Test",
            "instruments": [{
                "name": "Patch",
                "category": "Keys",
                "source": "Patch",
                "root_shift": 24,
            }],
        }))
        batch = workflow.load_batch(manifest, self.settings)
        self.assertEqual(batch.instruments[0].root_shift, 24)
        with redirect_stdout(StringIO()):
            workflow.build_batch(self.settings, batch, force=False)
        program, _ = workflow.artifact_paths(self.settings, batch, batch.instruments[0])
        _, payload = read_xpm(program)
        instrument = payload["data"]["drum"]["instruments"][1]
        self.assertEqual(instrument["layersv"][0]["rootNote"], 60)

    def test_manifest_root_target_infers_hardware_proven_octave(self):
        self.write_wav(self.source / "25 Patch C0.wav")
        self.write_wav(self.source / "40 Patch D#1.wav", frames=9)
        manifest = self.root / "targeted.json"
        manifest.write_text(json.dumps({
            "version": 1,
            "library": "Test",
            "source_root": "Test From Mars/WAV",
            "destination": "Programs/Test",
            "instruments": [{
                "name": "Patch",
                "category": "Chromatic Percussion",
                "source": "Patch",
                "root_target": [60, 96],
            }],
        }))
        batch = workflow.load_batch(manifest, self.settings)
        self.assertEqual(batch.instruments[0].root_target, (60, 96))
        with redirect_stdout(StringIO()) as output:
            workflow.build_batch(self.settings, batch, force=False)
            self.assertEqual(workflow.inspect_batch(self.settings, batch), 0)
        self.assertIn("root_shift=+36", output.getvalue())
        program, _ = workflow.artifact_paths(self.settings, batch, batch.instruments[0])
        _, payload = read_xpm(program)
        instruments = payload["data"]["drum"]["instruments"][1:]
        self.assertEqual(
            [instrument["layersv"][0]["rootNote"] for instrument in instruments],
            [61, 76],
        )

    def test_manifest_rejects_invalid_or_conflicting_root_target(self):
        for name, fields in (
            ("invalid", {"root_target": [96, 60]}),
            ("conflict", {"root_target": [60, 96], "root_shift": 0}),
        ):
            with self.subTest(name=name):
                manifest = self.root / f"{name}.json"
                manifest.write_text(json.dumps({
                    "version": 1,
                    "library": "Test",
                    "source_root": "Test From Mars/WAV",
                    "destination": "Programs/Test",
                    "instruments": [{
                        "name": "Patch", "source": "Patch", **fields,
                    }],
                }))
                with self.assertRaisesRegex(ValueError, "root_target"):
                    workflow.load_batch(manifest, self.settings)


if __name__ == "__main__":
    unittest.main()
