import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mpc_keygroup_builder import designer, model
from mpc_keygroup_builder.device import DeviceProfile, load_device
from mpc_keygroup_builder.ideas import DrumEvent, DrumIdea, render_midi
from mpc_keygroup_builder.midi_groove import load_groove


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
        self.assertIn("const BUNDLE=", rendered)
        self.assertIn('id="program-select"', rendered)
        self.assertIn('id="comparison-panel"', rendered)
        self.assertIn('id="editor-panel"', rendered)
        self.assertIn('id="edit-toggle"', rendered)
        self.assertIn('id="groove-toggle"', rendered)
        self.assertIn('id="apply-ergonomic"', rendered)
        self.assertIn("Draft only · source unchanged", rendered)
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
            self.assertIn("source unchanged", output.read_text(encoding="utf-8"))

    def test_bundle_renders_each_program_and_device_with_pairwise_comparisons(self):
        first = model.ProgramModel(
            1,
            "Kit",
            "drum",
            (model.Zone(1, "kick.primary", (model.SampleLayer("Kick.wav"),), pad=1),),
            "fixture",
        )
        second = model.ProgramModel(
            1,
            "Kit",
            "drum",
            (
                model.Zone(1, "snare.primary", (model.SampleLayer("Snare.wav"),), pad=1),
                model.Zone(2, "hihat.closed", (model.SampleLayer("Hat.wav"),), pad=2),
            ),
            "fixture",
        )
        key_61 = DeviceProfile(
            1, "mpc-key-61", "Akai MPC Key 61", 61, 4, 4, tuple("ABCDEFGH")
        )
        layout = designer.load_preset(self.root / "layouts/right-handed-performance.toml")
        bundle = designer.build_view_bundle(
            [(first, None), (second, None)], [self.device, key_61], [layout]
        )
        self.assertEqual(bundle["schema_version"], 3)
        self.assertEqual([item["id"] for item in bundle["programs"]], ["kit", "kit-2"])
        self.assertEqual(set(bundle["views"]["kit"]), {"mpc-key-37", "mpc-key-61"})
        self.assertEqual(bundle["layouts"][0]["id"], "right-handed-performance")
        comparison = bundle["comparisons"]["mpc-key-37"]["kit"]["kit-2"]
        self.assertEqual(comparison["summary"]["changed_locations"], 2)
        self.assertEqual(comparison["summary"]["right_only"], 1)
        self.assertEqual(comparison["summary"]["zone_delta"], 1)
        self.assertIn("role", comparison["locations"][0]["changed_fields"])

    def test_cli_bundles_compare_source_and_repeated_devices_as_json(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first.toml"
            second = root / "second.toml"
            device = root / "alternate.toml"
            output = root / "comparison.json"
            first.write_text('name="First"\n[[pads]]\npad=1\nsample="Kick.wav"\n')
            second.write_text('name="Second"\n[[pads]]\npad=1\nsample="Snare.wav"\n')
            device.write_text(
                'schema_version=1\nid="alternate"\nname="Alternate"\nkeys=25\n'
                'pad_rows=4\npad_columns=4\nbanks=["A","B"]\n'
            )
            before = (first.read_bytes(), second.read_bytes())
            with patch(
                "sys.argv",
                [
                    "mpc-program-designer",
                    str(first),
                    "--compare",
                    str(second),
                    "--device",
                    str(self.root / "devices/mpc-key-37.toml"),
                    "--device",
                    str(device),
                    "--layout",
                    str(self.root / "layouts/right-handed-performance.toml"),
                    "--format",
                    "json",
                    "--output",
                    str(output),
                ],
            ):
                self.assertEqual(designer.main(), 0)
            payload = json.loads(output.read_text())
            self.assertEqual(payload["schema_version"], 3)
            self.assertEqual(len(payload["programs"]), 2)
            self.assertEqual(len(payload["devices"]), 2)
            self.assertEqual(payload["layouts"][0]["id"], "right-handed-performance")
            self.assertEqual((first.read_bytes(), second.read_bytes()), before)

    def test_bundle_maps_optional_groove_into_heat_and_suggestions(self):
        program = model.ProgramModel(
            1,
            "Groove Kit",
            "drum",
            (
                model.Zone(
                    1,
                    "kick.primary",
                    (model.SampleLayer("Kick.wav"),),
                    pad=1,
                    midi_note=36,
                ),
                model.Zone(
                    2,
                    "snare.primary",
                    (model.SampleLayer("Snare.wav"),),
                    pad=2,
                    midi_note=38,
                ),
            ),
            "fixture",
            pad_note_map={1: 36, 2: 38},
        )
        events = (
            DrumEvent(0, 0, 60, "kick.primary", 1, "A01", 36, 110, "Kick.wav"),
            DrumEvent(1, 120, 60, "kick.primary", 1, "A01", 36, 100, "Kick.wav"),
            DrumEvent(2, 240, 60, "snare.primary", 2, "A02", 38, 90, "Snare.wav"),
        )
        idea = DrumIdea(1, "fixture", "Groove Kit", None, 1, 90, 1, 1, 16, 0.5, 10, 480, events)
        with tempfile.TemporaryDirectory() as directory:
            midi = Path(directory) / "groove.mid"
            midi.write_bytes(render_midi(idea))
            bundle = designer.build_view_bundle(
                [(program, None)], [self.device], groove=load_groove([midi])
            )
        view = bundle["views"]["groove-kit"]["mpc-key-37"]
        self.assertEqual(view["groove"]["mapped_events"], 3)
        self.assertEqual(view["banks"]["A"][0]["groove"]["hits"], 2)
        self.assertEqual(
            set(view["groove"]["suggestions"]), {"right", "left"}
        )


if __name__ == "__main__":
    unittest.main()
