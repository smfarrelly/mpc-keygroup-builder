import gzip
import json
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import drum_audit


class DrumAuditTests(unittest.TestCase):
    def write_xml(self, path: Path, open_group: int = 1) -> None:
        path.write_text(
            '<?xml version="1.0"?><MPCVObject><Program type="Drum"><Instruments>'
            '<Instrument number="1"><Mono>True</Mono><Polyphony>1</Polyphony>'
            '<MuteGroup>1</MuteGroup><OneShot>True</OneShot><Layers><Layer>'
            '<SampleFile>CH 808.wav</SampleFile></Layer></Layers></Instrument>'
            '<Instrument number="2"><Mono>True</Mono><Polyphony>1</Polyphony>'
            f'<MuteGroup>{open_group}</MuteGroup><OneShot>True</OneShot><Layers><Layer>'
            '<SampleFile>OH 808.wav</SampleFile></Layer></Layers></Instrument>'
            '</Instruments></Program></MPCVObject>',
            encoding="utf-8",
        )

    def write_serialized(self, path: Path) -> None:
        instruments = [
            {
                "monophonic": True,
                "polyphony": 1,
                "whichMuteGroup": 2,
                "triggerMode": 0,
                "layersv": [{"sampleFile": "Closed Hat.wav"}],
            },
            {
                "monophonic": True,
                "polyphony": 1,
                "whichMuteGroup": 2,
                "triggerMode": 0,
                "layersv": [{"sampleFile": "Open Hat.wav"}],
            },
        ]
        document = {"data": {"type": 0, "drum": {"instruments": instruments}}}
        payload = b"ACVS\n3.9.1.2\nSerialisableProgramData\njson\nLinux\n" + json.dumps(document).encode()
        path.write_bytes(gzip.compress(payload, mtime=0))

    def test_passes_xml_with_paired_hat_group(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Kit.xpm"
            self.write_xml(path)
            report = drum_audit.audit_drum_program(path)
            self.assertEqual(report["verdict"], "pass")
            self.assertEqual(report["categories"], {"closed_hat": 1, "open_hat": 1})
            self.assertEqual(report["mute_groups"], {"1": [1, 2]})
            self.assertEqual(report["pads"][0]["playback_mode"], "one-shot")

    def test_warns_for_unpaired_hat_group(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Kit.xpm"
            self.write_xml(path, open_group=0)
            report = drum_audit.audit_drum_program(path)
            self.assertEqual(report["verdict"], "warn")
            self.assertTrue(any("has no mute group" in issue for issue in report["issues"]))
            self.assertTrue(any("missing open_hat" in issue for issue in report["issues"]))

    def test_reads_mpc_resaved_drum_program(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Kit.xpm"
            self.write_serialized(path)
            report = drum_audit.audit_drum_program(path)
            self.assertEqual(report["verdict"], "pass")
            self.assertEqual(report["format"], "gzip-json")
            self.assertEqual(report["pads"][1]["playback_mode"], "trigger-mode-0")


if __name__ == "__main__":
    unittest.main()
