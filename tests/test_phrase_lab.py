from copy import deepcopy
import unittest

from mpc_keygroup_builder.phrase_lab import MODES, groups, transform


def hit(t, note, vel=0.85, length=120):
    return {
        "type": 3,
        "time": t,
        "muted": False,
        "note": {"note": note, "velocity": vel, "length": length, "probability": 100},
    }


def clip(*events):
    return {
        "startPulses": 0,
        "endPulses": 7680,
        "loop": True,
        "loopStartPulses": 0,
        "loopEndPulses": 7680,
        "eventList": {"events": list(events)},
    }


def fixture():
    keys = clip(
        hit(0, 64),
        hit(0, 67),
        hit(480, 72),
        hit(960, 65),
        hit(2400, 62),
        hit(4000, 70),
        hit(5000, 69),
    )
    keys["eventList"]["events"].extend(
        [{"type": 9, "time": 720, "value": 4}, dict(hit(500, 63), muted=True)]
    )
    drums = clip(hit(0, 36), hit(240, 42, 0.1), hit(900, 36, 1), hit(2000, 42, 0.3))
    bass = clip(hit(300, 40), hit(1800, 43), hit(2100, 40))
    return {
        "name": "take",
        "lengthBars": 2,
        "lengthPulses": 7680,
        "loopEndBar": 2,
        "loopStartPulses": 0,
        "loopEndPulses": 7680,
        "timeSignatureTrack": {
            "timeSignatures": [{"beatsPerBar": 4, "beatLength": 960, "barStart": 0}]
        },
        "seqEventList": {"events": []},
        "trackClipMaps": [
            [
                {"key": n, "value": c}
                for n, c in [("Keys", keys), ("Drums", drums), ("Bass", bass)]
            ]
        ],
    }


def run(mode):
    seq = fixture()
    transform(seq, mode, "Keys", "Drums", "Bass", 58)
    return seq


def played(seq, track=0):
    return groups(seq["trackClipMaps"][0][track]["value"])


class PhraseLabTests(unittest.TestCase):
    def test_all_fourteen_derive_distinct_playable_results_and_preserve_other_data(
        self,
    ):
        original = fixture()
        results = set()
        for mode in MODES:
            with self.subTest(mode=mode):
                s = run(mode)
                self.assertEqual(s, run(mode))
                notes = played(s)
                self.assertTrue(notes)
                results.add(str(notes))
                for t, chord in notes:
                    for e in chord:
                        self.assertLessEqual(t + e["note"]["length"], s["lengthPulses"])
                        self.assertTrue(0 <= e["note"]["note"] <= 127)
                if mode != "fourth":
                    self.assertEqual(
                        s["trackClipMaps"][0][1], original["trackClipMaps"][0][1]
                    )
                    clip_events = s["trackClipMaps"][0][0]["value"]["eventList"][
                        "events"
                    ]
                    self.assertIn({"type": 9, "time": 720, "value": 4}, clip_events)
                    self.assertIn(dict(hit(500, 63), muted=True), clip_events)
        self.assertEqual(len(results), 14)

    def test_drum_gestures_keep_identity_and_ghosts_voice_opening_chord(self):
        self.assertEqual([t for t, _ in played(run("hands"))], [0, 240, 900, 2000])
        self.assertEqual(
            [e["note"]["note"] for e in played(run("hands"))[0][1]], [64, 67]
        )
        self.assertEqual(
            [(t, c[0]["note"]["note"]) for t, c in played(run("ghost"))],
            [(240, 64), (2000, 67)],
        )
        notes = played(run("pressure"))
        self.assertGreater(
            notes[2][1][0]["note"]["note"], notes[1][1][0]["note"]["note"]
        )

    def test_melodic_landmarks_and_time(self):
        original = played(fixture())
        self.assertEqual(played(run("resolve"))[-1][1][0]["note"]["note"], 58)
        self.assertEqual(played(run("mirror"))[1][1][0]["note"]["note"], 56)
        self.assertEqual([t for t, _ in played(run("stretch"))], [0, 960, 1920, 4800])
        gaps = played(run("negative"))
        for t, chord in gaps:
            for onset, source in original:
                self.assertTrue(
                    t >= onset + max(e["note"]["length"] for e in source)
                    or t + max(e["note"]["length"] for e in chord) <= onset
                )
        self.assertGreater(len(played(run("reply"))), len(original))
        self.assertLess(len(played(run("outline"))), len(original))

    def test_partner_exchange_and_fourth_pass(self):
        s = run("trade")
        self.assertEqual(
            [t for t, _ in played(s)], [t for t, _ in played(fixture(), 2)]
        )
        self.assertEqual(
            [t for t, _ in played(s, 2)], [t for t, _ in played(fixture())]
        )
        s = run("hocket")
        self.assertFalse({t for t, _ in played(s)} & {t for t, _ in played(s, 2)})
        s = run("fourth")
        self.assertEqual(s["lengthBars"], 8)
        for repeat in range(3):
            expected = deepcopy(played(fixture()))
            for t, chord in expected:
                for e in chord:
                    e["time"] += repeat * 7680
            actual = [
                (t - repeat * 7680, c)
                for t, c in played(s)
                if repeat * 7680 <= t < (repeat + 1) * 7680
            ]
            self.assertEqual(actual, expected)
        self.assertEqual(played(s)[-1][0], 4 * 7680 - 480)
        broken = fixture()
        broken["trackClipMaps"][0][2]["value"]["startPulses"] = 240
        with self.assertRaisesRegex(ValueError, "full-sequence"):
            transform(broken, "fourth", "Keys", None, None, 60)

    def test_live_bridge_encodes_learn_reset_and_all_four_guide_performances(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from mpc_keygroup_builder.phrase_lab import hands_midi
        from mpc_keygroup_builder.midi_groove import parse_midi

        with TemporaryDirectory() as directory:
            path = Path(directory) / "performance.mid"
            s = fixture()
            path.write_bytes(hands_midi(s, "Keys", "Drums", 120))
            source, events = parse_midi(path)
        self.assertEqual((source.midi_format, source.ppq), (0, 960))
        self.assertEqual(events[0].note, 40)
        self.assertEqual(
            [e.note for e in events if e.note >= 48], [67, 72, 65, 62, 70, 69]
        )
        for i in range(4):
            start = 3840 + i * 7680
            self.assertIn(start - 2, [e.tick for e in events if e.note == 41])
            self.assertEqual(
                [e.tick - start for e in events if e.note == 36 + i],
                [0, 240, 900, 2000],
            )

    def test_fixed_velocity_guide_preserves_drums_and_yields_defined_alternatives(self):
        for mode in ("pressure", "ghost"):
            s = fixture()
            for _, chord in played(s, 1):
                for e in chord:
                    e["note"]["velocity"] = 0.7
            transform(s, mode, "Keys", "Drums", "Bass", 60)
            pitches = [chord[0]["note"]["note"] for _, chord in played(s)]
            self.assertEqual(len(set(pitches)), int(mode == "pressure"))
            self.assertEqual(len(played(s, 1)), 4)
