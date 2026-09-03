import gzip
import json
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import launch_control


def section(name: str, section_id: int, enabled: dict[int, tuple[int, int, str]]) -> bytes:
    start = 0x10 if section_id == 0 else 0x28
    data = bytearray(launch_control.NOVATION_HEADER)
    data.extend((section_id, 0x7F, 0x20, len(name)))
    data.extend(name.encode("ascii"))
    blocks = [(0x10, 24)] if section_id == 0 else [(0x28, 8), (0x30, 16)]
    for block_start, count in blocks:
        for control_id in range(block_start, block_start + count):
            item = enabled.get(control_id)
            if item is None:
                data.extend((0x40, control_id))
            else:
                channel, number, _ = item
                data.extend((0x49, control_id, 0x02, 0x03, 0x00, channel - 1, 0x00, 0x00, number, 0x7F, 0x00))
        for control_id in range(block_start, block_start + count):
            label = enabled.get(control_id, (0, 0, ""))[2].encode("ascii")
            data.extend((0x60 + len(label), control_id))
            data.extend(label)
    data.append(0xF7)
    return bytes(data)


def project(path: Path) -> Path:
    data = {
        "data": {
            "midiLearnSettings": {
                "controls": [
                    {
                        "mapping": {"channel": 9, "controlType": 5, "data1": 13},
                        "control": {
                            "name": "OPX (Level 1)",
                            "targetData": [{"track": "OPX", "parameter": 4122}],
                        },
                    }
                ]
            }
        }
    }
    header = b"ACVS\n3.9.1.2\nSerialisableProjectData\njson\nLinux\n"
    path.write_bytes(gzip.compress(header + json.dumps(data).encode()))
    return path


class LaunchControlTests(unittest.TestCase):
    def test_inspects_observed_components_shape(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "OPX.syx"
            path.write_bytes(
                section("OPX", 0, {0x10: (9, 13, "OP1 Level")})
                + section("OPX", 3, {
                    0x28: (16, 5, "Track 1 Vol"),
                    0x30: (9, 37, "OP1 On"),
                })
            )
            result = launch_control.inspect(path)
            self.assertEqual(result["name"], "OPX")
            self.assertEqual(result["primary_channel"], 9)
            enabled = [item for item in result["controls"] if item["enabled"]]
            self.assertEqual([(item["control"], item["channel"], item["number"]) for item in enabled], [
                ("top-encoder-1", 9, 13),
                ("fader-1", 16, 5),
                ("upper-button-1", 9, 37),
            ])
            self.assertEqual(enabled[-1]["channel_source"], "inferred-from-encoder-section")

    def test_audit_matches_project_channel_and_number(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            syx = root / "OPX.syx"
            syx.write_bytes(section("OPX", 0, {0x10: (9, 13, "OP1 Level")}))
            result = launch_control.audit(project(root / "Boot.xpj"), [syx])
            self.assertEqual(result["project_midi_learn_count"], 1)
            self.assertEqual(result["captures"][0]["matched_control_count"], 1)
            self.assertEqual(result["captures"][0]["controls"][0]["learned_targets"], ["OPX (Level 1)"])

    def test_rejects_unrecognized_sysex(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.syx"
            path.write_bytes(b"\xf0\x01\x02\xf7")
            with self.assertRaisesRegex(ValueError, "not a recognized"):
                launch_control.inspect(path)


if __name__ == "__main__":
    unittest.main()
