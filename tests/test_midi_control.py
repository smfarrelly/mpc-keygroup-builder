import csv
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import midi_control


class MidiControlTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).parents[1]
        self.map_path = self.root / "midi/maps/fg-key37-lcxl3-volcas.toml"
        self.document, self.devices = midi_control.load_map(self.map_path)

    def test_repository_map_matches_device_definitions(self):
        report = midi_control.validate(self.document, self.devices)
        self.assertEqual(report["errors"], [])
        self.assertEqual(set(self.devices), {"volca-bass", "volca-keys", "volca-drum"})
        self.assertTrue(any("project-scoped" in item for item in report["warnings"]))

    def test_bridge_map_inherits_controls_and_overrides_routes(self):
        bridge, devices = midi_control.load_map(
            self.root / "midi/maps/fg-key37-lcxl3-volcas-bridge.toml"
        )
        report = midi_control.validate(bridge, devices)
        self.assertEqual(report["errors"], [])
        self.assertEqual(len(bridge["modes"][0]["controls"]), 48)
        self.assertEqual(bridge["modes"][0]["output"], "usb")
        self.assertEqual([mode["output"] for mode in bridge["modes"][1:]], ["din-1"] * 3)
        self.assertTrue(all("To DIN Out 1" in route["output_port"] for route in bridge["routes"]))
        self.assertIn("hardware-pending", midi_control.render_setup(bridge, devices))

    def test_map_inheritance_cycle_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "one.toml").write_text('schema_version=1\nextends="two.toml"\n', encoding="utf-8")
            (root / "two.toml").write_text('schema_version=1\nextends="one.toml"\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "inheritance cycle"):
                midi_control.load_map(root / "one.toml")

    def test_device_definition_rejects_duplicate_cc(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "device.toml"
            path.write_text(
                'schema_version=1\nid="bad"\nname="Bad"\nkind="synth"\n'
                '[[parameters]]\nid="one"\ncc=40\n'
                '[[parameters]]\nid="two"\ncc=40\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate parameters cc 40"):
                midi_control.load_device(path)

    def test_detects_wrong_cc_duplicate_endpoint_and_passive_merge(self):
        document = dict(self.document)
        document["topology"] = dict(document["topology"], launch_direct_din=True)
        document["modes"] = [dict(document["modes"][1])]
        document["modes"][0]["controls"] = [
            dict(document["modes"][0]["controls"][0], number=99),
            dict(document["modes"][0]["controls"][1], control=document["modes"][0]["controls"][0]["control"]),
        ]
        report = midi_control.validate(document, self.devices)
        self.assertTrue(any("passive MIDI thru" in item for item in report["errors"]))
        self.assertTrue(any("duplicate endpoint" in item for item in report["errors"]))
        self.assertTrue(any("expects cc" in item for item in report["errors"]))

    def test_compile_emits_machine_readable_and_setup_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "compiled"
            midi_control.compile_map(self.document, self.devices, output)
            expected = {
                "launch-control-components.csv",
                "mpc-midi-learn.csv",
                "mpc-track-routes.csv",
                "device-midi-reference.csv",
                "SETUP.md",
                "mapping.json",
            }
            self.assertEqual({path.name for path in output.iterdir()}, expected)
            with (output / "launch-control-components.csv").open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertTrue(any(row["target"] == "volca-keys:cutoff" and row["number"] == "44" for row in rows))
            self.assertTrue(any(row["target"] == "volca-drum:part-6" and row["number"] == "69" for row in rows))
            setup = (output / "SETUP.md").read_text(encoding="utf-8")
            self.assertIn("does not merge", setup)
            self.assertIn("Components worksheet", setup)
            with self.assertRaises(FileExistsError):
                midi_control.compile_map(self.document, self.devices, output)


if __name__ == "__main__":
    unittest.main()
