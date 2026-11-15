from copy import deepcopy
import unittest

from mpc_keygroup_builder.sequence_morph import evolve, morph_clip


def hit(tick, pitch, velocity=0.8, duration=120):
    return {"type": 3, "time": tick, "channel": 0, "muted": False,
            "note": {"note": pitch, "length": duration, "velocity": velocity, "probability": 100}}


def clip():
    return {"startPulses": 0, "endPulses": 3840, "loop": True, "loopStartPulses": 0,
            "loopEndPulses": 3840, "timeSignatureList": {"timeSignatures": [
                {"barStart": 0, "beatLength": 960, "beatsPerBar": 4}]},
            "eventList": {"events": [hit(0, 60), hit(0, 64), {"type": 9, "time": 180},
                                     hit(960, 62, 0.4), hit(1920, 60, 1, 1900)]}}


class SequenceMorphTests(unittest.TestCase):
    def test_answer_adds_quiet_whole_chord_and_respects_long_note(self):
        c = clip()
        original = deepcopy(c["eventList"]["events"])
        self.assertEqual(morph_clip(c, "answer", 100, 1, "Keys", 0), 2)
        events = c["eventList"]["events"]
        self.assertTrue(all(e in events for e in original))
        chord = [e["note"] for e in events if e["time"] == 480]
        self.assertEqual([n["note"] for n in chord], [60, 64])
        self.assertAlmostEqual(chord[0]["velocity"], 0.52)
        self.assertEqual(max(e["time"] for e in events), 1920)

    def test_space_preserves_anchors_controls_and_mutes(self):
        c = clip()
        saved = deepcopy(c["eventList"]["events"])
        self.assertEqual(morph_clip(c, "space", 100, 1, "Keys", 0), 1)
        self.assertEqual(c["eventList"]["events"], [saved[i] for i in [0, 1, 2, 4]])
        c = clip()
        c["eventList"]["events"][3]["muted"] = True
        self.assertEqual(morph_clip(c, "space", 100, 1, "Keys", 0), 0)

    def test_repeatable_nested_variations_and_original_slots(self):
        row = {"key": "Keys", "value": clip()}
        source = {"name": "Jam", "trackClipMaps": [[row, {"key": "Drums", "value": clip()}]]}
        data = {"tracks": [{"name": n, "program": {"type": t}} for n, t in [("Keys", 1), ("Drums", 0)]],
                "sequences": [{"key": 2, "value": source}], "currentSequence": 2}
        before = deepcopy(data)
        evolve(data, None, ["Keys"], "answer", [0, 50, 100], 12)
        self.assertEqual([s["key"] for s in data["sequences"]], [2, 0, 1, 3])
        self.assertEqual(before["sequences"][0], data["sequences"][0])
        def rows(i):
            return data["sequences"][i]["value"]["trackClipMaps"][0]
        self.assertEqual(rows(0), rows(1))
        self.assertEqual(rows(0)[1], rows(3)[1])
        full = rows(3)[0]["value"]["eventList"]["events"]
        self.assertTrue(all(e in full for e in rows(2)[0]["value"]["eventList"]["events"]))
        again = deepcopy(before)
        evolve(again, "Jam", ["Keys"], "answer", [0, 50, 100], 12)
        self.assertEqual(data, again)

    def test_native_copy_is_independent_and_rejects_overwrite_or_missing_media(self):
        import gzip
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from mpc_keygroup_builder.sequence_morph import build
        from mpc_keygroup_builder.xpj import load

        with TemporaryDirectory() as directory:
            root = Path(directory)
            src = root / "Jam.xpj"
            companion = root / "Jam_[ProjectData]"
            companion.mkdir()
            wav = companion / "hit.wav"
            wav.write_bytes(b"original")
            doc = {"data": {"currentSequence": 0, "samples": [{"path": "hit.wav"}],
                            "tracks": [{"name": "Kit", "program": {"type": 0}}],
                            "sequences": [{"key": 0, "value": {"name": "Jam", "trackClipMaps": [
                                [{"key": "Kit", "value": clip()}]]}}]}}
            src.write_bytes(gzip.compress(("ACVS\n3\nproject\njson\nMPC\n" + json.dumps(doc)).encode()))
            output = root / "Variations"
            build(src, output, None, [], "answer", [100], 37)
            self.assertEqual(load(src).document, doc)
            self.assertEqual(len(load(output / src.name).data["sequences"]), 2)
            (output / companion.name / wav.name).write_bytes(b"edited")
            self.assertEqual(wav.read_bytes(), b"original")
            with self.assertRaisesRegex(ValueError, "new output"):
                build(src, output, None, [], "space", [100], 37)
            wav.unlink()
            with self.assertRaisesRegex(ValueError, "hit.wav"):
                build(src, root / "Missing", None, [], "space", [100], 37)
            self.assertFalse((root / "Missing").exists())
