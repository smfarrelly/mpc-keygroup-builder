import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import entrypoints, rig


class RigTests(unittest.TestCase):
    def test_repository_profiles_are_valid(self):
        root = Path(__file__).parents[1]
        for path in sorted((root / "rigs").glob("*.toml")):
            with self.subTest(path=path.name):
                report = rig.validate(rig.load(path))
                self.assertEqual(report["errors"], [])
                self.assertIn("# ", rig.render_markdown(rig.load(path)))

    def test_detects_channels_indexes_devices_and_controller_collisions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.toml"
            path.write_text(
                'schema_version=1\nname="Bad"\n'
                '[[devices]]\nid="ctl"\nname="Control"\nkind="controller"\nclock="none"\n'
                '[[tracks]]\nindex=1\nname="One"\nrole="bass"\ntype="midi"\n'
                'device="missing"\nmidi_channel=17\n'
                '[[tracks]]\nindex=1\nname="One"\nrole="bass"\ntype="wrong"\n'
                '[[control_groups]]\ncontroller="ctl"\ncontrols="fader-{n}"\ncount=1\n'
                'semantic="volume"\ntarget="track-{n}"\nmessage="learn"\n'
                '[[control_groups]]\ncontroller="ctl"\ncontrols="fader-{n}"\ncount=1\n'
                'semantic="tone"\ntarget="track-{n}"\nmessage="learn"\n'
            )
            report = rig.validate(rig.load(path))
            self.assertTrue(any("indexes" in value for value in report["errors"]))
            self.assertTrue(any("MIDI channel" in value for value in report["errors"]))
            self.assertTrue(any("duplicate controller" in value for value in report["errors"]))

    def test_detects_duplicate_external_route(self):
        document = {
            "schema_version": 1,
            "name": "Collision",
            "devices": [
                {"id": "one", "kind": "synth", "midi_channel": 1, "midi_port": "out", "clock": "receive"},
                {"id": "two", "kind": "synth", "midi_channel": 1, "midi_port": "out", "clock": "receive"},
            ],
            "tracks": [
                {"index": 1, "name": "One", "role": "bass", "type": "midi", "device": "one", "midi_channel": 1},
                {"index": 2, "name": "Two", "role": "lead", "type": "midi", "device": "two", "midi_channel": 1},
            ],
        }
        report = rig.validate(document)
        self.assertTrue(any("already used" in value for value in report["errors"]))

    def test_rejects_non_table_sections_and_non_scalar_identity_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rig.toml"
            cases = (
                (
                    'schema_version=1\nname="Bad"\ndevices="not tables"\n'
                    '[[tracks]]\nindex=1\nname="Track"\nrole="bass"\ntype="midi"\n',
                    "devices must contain table",
                ),
                (
                    'schema_version=1\nname="Bad"\n[[devices]]\nid=["bad"]\n'
                    '[[tracks]]\nindex=1\nname="Track"\nrole="bass"\ntype="midi"\n',
                    "device 1 id must be a nonempty str",
                ),
                (
                    'schema_version=1\nname="Bad"\n[[tracks]]\nindex=1\n'
                    'name=["Track"]\nrole="bass"\ntype="midi"\n',
                    "track 1 name must be a nonempty str",
                ),
            )
            for source, message in cases:
                with self.subTest(message=message):
                    path.write_text(source)
                    with self.assertRaisesRegex(ValueError, message):
                        rig.load(path)

    def test_malformed_profile_is_friendly_through_installed_command(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rig.toml"
            path.write_text(
                'schema_version=1\nname="Bad"\ntracks=["not a table"]\n'
            )
            error = io.StringIO()
            with contextlib.redirect_stderr(error):
                status = entrypoints.invoke("mpc-rig", ["check", str(path)])
            self.assertEqual(status, 2)
            self.assertIn("tracks entry 1 must be a table", error.getvalue())
            self.assertNotIn("Traceback", error.getvalue())

    def test_plan_rejects_control_group_without_count_cleanly(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rig.toml"
            path.write_text(
                'schema_version=1\nname="Bad"\n'
                '[[devices]]\nid="ctl"\nkind="controller"\n'
                '[[tracks]]\nindex=1\nname="Track"\nrole="bass"\ntype="midi"\n'
                '[[control_groups]]\ncontroller="ctl"\ncontrols="fader-{n}"\n'
                'semantic="volume"\ntarget="track-{n}"\n'
            )
            error = io.StringIO()
            with contextlib.redirect_stderr(error):
                status = entrypoints.invoke("mpc-rig", ["plan", str(path)])
            self.assertEqual(status, 2)
            self.assertIn("control group 1 count", error.getvalue())
            self.assertNotIn("Traceback", error.getvalue())


if __name__ == "__main__":
    unittest.main()
