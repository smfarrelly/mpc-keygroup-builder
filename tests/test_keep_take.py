import gzip
import json
from pathlib import Path
import tempfile
import unittest

from mpc_keygroup_builder import keep_take as studio, xpj


class KeepTakeTests(unittest.TestCase):
    def setUp(self):
        self.events = [
            [0, 176, 64, 125],
            [0, 144, 60, 87],
            [0, 128, 60, 0],
            [42, 144, 64, 77],
            [54, 128, 64, 3],
            [81, 176, 64, 0],
        ]
        self.take = dict(
            format="keep-that-take/1",
            name="Idea",
            seconds=8,
            layers=[dict(track="Wurli", events=self.events)],
        )
        self.instruments = {"Wurli": {"drum": False}}

    def test_export_retains_midi_order_and_embeds_sounding_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p = root / "Demo.xpj"
            doc = {
                "data": {
                    "samples": [{"path": "keys.wav"}],
                    "sequences": [
                        {
                            "value": {
                                "trackClipMaps": [
                                    [
                                        {
                                            "key": "Wurli",
                                            "value": {
                                                "eventList": {
                                                    "events": [{"type": 3, "note": {}}]
                                                }
                                            },
                                        }
                                    ]
                                ]
                            }
                        }
                    ],
                }
            }
            p.write_bytes(
                gzip.compress(
                    ("ACVS\n3.0\nProject\nJSON\nLinux\n" + json.dumps(doc)).encode()
                )
            )
            companion = root / "Demo_[ProjectData]"
            companion.mkdir()
            (companion / "keys.wav").write_bytes(b"test sample")
            out = studio.export(self.take, p, root / "out", self.instruments)
            seq = xpj.load(out / "Idea.xpj").data["sequences"][0]["value"]
            events = seq["trackClipMaps"][0][0]["value"]["eventList"]["events"]
            self.assertEqual(
                [(e["time"], e["note"]["length"], e["note"]["note"]) for e in events],
                [(0, 81, 60), (42, 39, 64)],
            )
            midi = (out / "Idea.mid").read_bytes()
            self.assertIn(bytes([0, 176, 64, 125, 0, 144, 60, 87, 0, 128, 60, 0]), midi)
            self.assertEqual(
                (out / "Idea_[ProjectData]/keys.wav").read_bytes(), b"test sample"
            )
            self.assertEqual(json.loads((out / "take.json").read_text()), self.take)
            self.assertNotEqual(
                studio.export(self.take, p, root / "out", self.instruments), out
            )
            self.assertEqual(xpj.load(p).document, doc)

    def test_validation_rejects_open_notes_and_unknown_auditions(self):
        self.take["layers"][0]["events"] = [[0, 144, 60, 100]]
        with self.assertRaisesRegex(ValueError, "release"):
            studio.validate(self.take, self.instruments)
        self.take["layers"][0].update(events=self.events, audition="other")
        with self.assertRaisesRegex(ValueError, "audition"):
            studio.validate(self.take, self.instruments)
