import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mpc_keygroup_builder import designer, model
from mpc_keygroup_builder.device import load_device


class ProgramDesignerTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).parents[1]
        self.device = load_device(self.root / "devices/mpc-key-37.toml")

    def test_builds_banked_drum_view_with_layers_colors_and_mute_groups(self):
        program = model.ProgramModel(
            1,
            "Layered Kit",
            "drum",
            (
                model.Zone(
                    1,
                    "kick.primary",
                    (
                        model.SampleLayer("BD Soft.wav", 0, 63),
                        model.SampleLayer("BD Hard.wav", 64, 127),
                    ),
                    pad=1,
                    midi_note=36,
                    color=0xFF6030,
                    playback_mode="one-shot",
                ),
                model.Zone(
                    18,
                    "hihat.closed",
                    (model.SampleLayer("CH.wav"),),
                    pad=18,
                    midi_note=42,
                    color=0x45D483,
                    mute_group=2,
                ),
                model.Zone(
                    19,
                    "hihat.open",
                    (model.SampleLayer("OH.wav"),),
                    pad=19,
                    midi_note=46,
                    color=0x7AE8B0,
                    mute_group=2,
                ),
            ),
            "fixture",
            pad_note_map={1: 36, 18: 42, 19: 46},
        )
        data = designer.build_view_data(program, self.device)
        self.assertTrue(data["read_only"])
        self.assertEqual(data["summary"]["populated_banks"], ["A", "B"])
        self.assertEqual(data["banks"]["A"][0]["color_hex"], "#FF6030")
        self.assertEqual(len(data["banks"]["A"][0]["layers"]), 2)
        self.assertEqual(data["banks"]["B"][1]["mute_group"], 2)
        self.assertEqual(data["summary"]["mute_groups"], {"2": ["B02", "B03"]})

    def test_reports_missing_samples_velocity_gaps_and_stacks(self):
        with tempfile.TemporaryDirectory() as directory:
            sample_root = Path(directory)
            (sample_root / "Present.wav").write_bytes(b"present")
            program = model.ProgramModel(
                1,
                "Broken",
                "drum",
                (
                    model.Zone(
                        1,
                        "kick.primary",
                        (
                            model.SampleLayer("Present.wav", 0, 63),
                            model.SampleLayer("Missing.wav", 63, 100),
                        ),
                        pad=1,
                    ),
                ),
                "fixture",
            )
            data = designer.build_view_data(program, self.device, sample_root)
            codes = {issue["code"] for issue in data["issues"]}
            self.assertIn("missing_sample", codes)
            self.assertIn("dead_velocity_range", codes)
            self.assertIn("stacked_velocity_range", codes)
            self.assertEqual(data["banks"]["A"][0]["layers"][0]["sample_status"], "found")
            self.assertEqual(data["banks"]["A"][0]["layers"][1]["sample_status"], "missing")

    def test_keygroup_view_centers_a_37_note_window_on_roots(self):
        program = model.ProgramModel(
            1,
            "Keys",
            "keygroup",
            (
                model.Zone(
                    1,
                    "melodic.instrument",
                    (model.SampleLayer("Keys C4.wav", root_note=60),),
                    low_note=48,
                    high_note=72,
                    polyphony=8,
                ),
            ),
            "fixture",
        )
        data = designer.build_view_data(program, self.device)
        self.assertEqual(data["keyboard"]["keys"], 37)
        self.assertEqual(data["keyboard"]["default_start"], 42)
        self.assertEqual(data["program"]["zones"][0]["low_note"], 48)
        self.assertEqual(data["program"]["zones"][0]["high_note"], 72)

    def test_html_is_self_contained_and_escapes_source_metadata(self):
        program = model.ProgramModel(
            1,
            "Kit </script><script>alert(1)</script>",
            "drum",
            (model.Zone(1, "kick.primary", (model.SampleLayer("Kick.wav"),), pad=1),),
            "fixture",
        )
        rendered = designer.render_html(designer.build_view_data(program, self.device))
        self.assertIn("<!doctype html>", rendered)
        self.assertIn("MPC Program Designer", rendered)
        self.assertIn("const DATA=", rendered)
        self.assertNotIn("Kit </script><script>alert(1)</script>", rendered)
        self.assertNotIn("https://", rendered)

    def test_cli_writes_viewer_without_modifying_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "kit.toml"
            output = root / "kit.html"
            source.write_text(
                'name="Kit"\n[[pads]]\npad=1\nsample="BD Test.wav"\n',
                encoding="utf-8",
            )
            before = source.read_bytes()
            with patch(
                "sys.argv",
                [
                    "mpc-program-designer",
                    str(source),
                    "--device",
                    str(self.root / "devices/mpc-key-37.toml"),
                    "--output",
                    str(output),
                ],
            ):
                self.assertEqual(designer.main(), 0)
            self.assertEqual(source.read_bytes(), before)
            self.assertTrue(output.is_file())
            self.assertIn("Read only", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
