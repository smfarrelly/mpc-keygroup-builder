import json
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import drum_map


class DrumMapTests(unittest.TestCase):
    def test_labels_banks_and_renders_formats(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Kit.xpm"
            settings = {"ProgramPads": {"Universal": {"value0": False}, "Type": {"value0": 2}, "pads": {"value0": 0xFF0000, "value16": 0x00FF00}}}
            path.write_text(
                '<?xml version="1.0"?><MPCVObject><Program type="Drum"><ProgramName>Kit</ProgramName>'
                '<ProgramPads>' + json.dumps(settings) + '</ProgramPads><Instruments>'
                '<Instrument number="1"><Mono>True</Mono><Polyphony>1</Polyphony><MuteGroup>0</MuteGroup>'
                '<OneShot>True</OneShot><Layers><Layer><SampleFile>BD.wav</SampleFile></Layer></Layers></Instrument>'
                '<Instrument number="17"><Mono>True</Mono><Polyphony>1</Polyphony><MuteGroup>0</MuteGroup>'
                '<OneShot>True</OneShot><Layers><Layer><SampleFile>Tom.wav</SampleFile></Layer></Layers></Instrument>'
                '</Instruments></Program></MPCVObject>', encoding="utf-8"
            )
            report = drum_map.build_map(path)
            self.assertEqual([pad["label"] for pad in report["pads"]], ["A01", "B01"])
            self.assertEqual(report["pads"][0]["color"], "#FF0000")
            markdown = drum_map.render_markdown(report, {"B"})
            self.assertNotIn("Bank A", markdown)
            self.assertIn("Bank B", markdown)
            self.assertIn("Tom.wav", markdown)
            self.assertIn("label,bank,pad", drum_map.render_csv(report))


if __name__ == "__main__":
    unittest.main()
