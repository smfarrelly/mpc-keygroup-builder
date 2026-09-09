import gzip
import json
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import ableton_loop_audit


XML = b'''<Ableton><GroupDevicePreset><Device><InstrumentGroupDevice><Branches>
<InstrumentBranchPreset><Device><OriginalSimpler><MultiSamplePart>
<Name Value="Loop Zone"/><IsActive Value="true"/><RootKey Value="60"/><SampleEnd Value="1000"/>
<SampleRef><FileRef><Name Value="Loop.wav"/></FileRef></SampleRef>
<SustainLoop><Mode Value="1"/><Start Value="100"/><End Value="900"/><Crossfade Value="12"/></SustainLoop>
<ReleaseLoop><Mode Value="3"/><Start Value="0"/><End Value="1000"/><Crossfade Value="0"/></ReleaseLoop>
</MultiSamplePart></OriginalSimpler></Device></InstrumentBranchPreset>
</Branches></InstrumentGroupDevice></Device></GroupDevicePreset></Ableton>'''

DRUM_XML = b'''<Ableton><GroupDevicePreset><Device><DrumGroupDevice><Branches>
<DrumBranchPreset><Name Value="Hat Pad"/><DevicePresets><InstrumentBranchPreset><Device><OriginalSimpler>
<MultiSamplePart><Name Value="Hat"/><IsActive Value="true"/><SampleEnd Value="800"/>
<SampleRef><FileRef><Name Value="Hat.wav"/></FileRef></SampleRef>
<SustainLoop><Mode Value="2"/><Start Value="20"/><End Value="700"/><Crossfade Value="8"/></SustainLoop>
</MultiSamplePart></OriginalSimpler></Device></InstrumentBranchPreset></DevicePresets>
<ZoneSettings><ReceivingNote Value="59"/><SendingNote Value="42"/></ZoneSettings>
</DrumBranchPreset></Branches></DrumGroupDevice></Device></GroupDevicePreset></Ableton>'''


class AbletonLoopAuditTests(unittest.TestCase):
    def test_inventory_keeps_numeric_modes_and_representatives(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preset = root / "Pack/Loop.adg"
            preset.parent.mkdir()
            with gzip.open(preset, "wb") as stream:
                stream.write(XML)
            backlog = root / "backlog.json"
            backlog.write_text(json.dumps({"entries": [{
                "path": "Pack/Loop.adg", "name": "Loop", "pack": "pack_from_mars",
                "target": "keygroup", "priority": "P1", "score": 80, "duplicate_of": None,
            }]}))
            report = ableton_loop_audit.audit(backlog, root)
            self.assertEqual(report["summary"]["nonzero_mode_observations"], 2)
            self.assertEqual(report["summary"]["signature_count"], 2)
            release = next(item for item in report["signatures"] if item["loop_kind"] == "release")
            self.assertEqual(release["mode"], 3)
            self.assertTrue(release["end_matches_sample_end"])
            self.assertFalse(release["crossfade_present"])
            self.assertEqual(release["representatives"][0]["preset"], "Pack/Loop.adg")
            output = root / "report"
            ableton_loop_audit.write_report(report, output)
            self.assertTrue((output / "loop-signatures.csv").is_file())
            self.assertIn("Mode numbers", (output / "ABLETON_LOOP_AUDIT.md").read_text())
            with self.assertRaises(FileExistsError):
                ableton_loop_audit.write_report(report, output)

    def test_isolates_missing_presets_and_rejects_path_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backlog = root / "backlog.json"
            backlog.write_text(json.dumps({"entries": [
                {"path": "missing.adg", "target": "keygroup", "score": 2},
                {"path": "../escape.adg", "target": "keygroup", "score": 1},
            ]}))
            report = ableton_loop_audit.audit(backlog, root)
            self.assertEqual(report["summary"]["issues"], 2)
            self.assertIn("escapes source root", report["issues"][1]["error"])

    def test_drum_target_uses_nested_pad_zones_with_stable_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preset = root / "Pack/Kit.adg"
            preset.parent.mkdir()
            with gzip.open(preset, "wb") as stream:
                stream.write(DRUM_XML)
            backlog = root / "backlog.json"
            backlog.write_text(json.dumps({"entries": [{
                "path": "Pack/Kit.adg", "name": "Kit", "pack": "pack_from_mars",
                "target": "drum", "priority": "P1", "score": 80,
                "duplicate_of": None,
            }]}))

            report = ableton_loop_audit.audit(backlog, root, target="drum")

            self.assertEqual(report["summary"]["loop_observations"], 1)
            representative = report["signatures"][0]["representatives"][0]
            self.assertEqual(representative["zone"], "note-59/zone-1")
            self.assertEqual(representative["pad_name"], "Hat Pad")
            self.assertEqual(representative["receiving_note"], 59)

    def test_validates_bounds(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "backlog.json"
            path.write_text('{"entries": []}')
            with self.assertRaisesRegex(ValueError, "target"):
                ableton_loop_audit.audit(path, path.parent, target="clips")
            with self.assertRaisesRegex(ValueError, "representative-limit"):
                ableton_loop_audit.audit(path, path.parent, representative_limit=0)


if __name__ == "__main__":
    unittest.main()
