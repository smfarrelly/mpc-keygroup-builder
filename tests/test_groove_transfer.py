from copy import deepcopy
import unittest

from mpc_keygroup_builder.groove_transfer import transfer
from mpc_keygroup_builder.sequence_morph import evolve


def hit(time, pitch, velocity=0.8, length=120, muted=False):
    return {"type": 3, "time": time, "channel": 0, "muted": muted,
            "note": {"note": pitch, "velocity": velocity, "length": length}}


def clip(*events):
    return {"startPulses": 0, "endPulses": 7680, "eventList": {"events": list(events)},
            "timeSignatureList": {"timeSignatures": [{"barStart": 0, "beatLength": 960,
                                                      "beatsPerBar": 4}]}}


class GrooveTransferTests(unittest.TestCase):
    def test_timing_moves_whole_chord_partway_and_preserves_cc_and_unmatched_notes(self):
        cc = {"type": 9, "time": 960, "value": 0.6}
        target = clip(hit(800, 60), hit(800, 64), cc, hit(2100, 67), hit(3800, 71))
        guide = clip(hit(960, 36), hit(2200, 38, muted=True), hit(3840, 36))
        before = deepcopy(guide)
        self.assertEqual(transfer(target, guide, "lock", 50), 1)
        self.assertEqual([e["time"] for e in target["eventList"]["events"]], [880, 880, 960, 2100, 3800])
        self.assertEqual(guide, before)
        self.assertEqual(cc, target["eventList"]["events"][2])

    def test_retrigger_gate_limits_movement_both_ways(self):
        target = clip(hit(500, 60, length=300), hit(850, 60, length=250), hit(1150, 60))
        transfer(target, clip(hit(600, 36), hit(750, 36), hit(1100, 36)), "lock", 100)
        events = target["eventList"]["events"]
        self.assertEqual([e["time"] for e in events], [550, 850, 1100])
        for first, second in zip(events, events[1:]):
            self.assertLessEqual(first["time"] + first["note"]["length"], second["time"])

    def test_velocity_keeps_chord_balance_and_resolves_ties_to_earlier_hit(self):
        guide = clip(hit(800, 36, 0.6), hit(1000, 38, 1.0))
        for style, peak in (("accent", 0.6), ("duck", 0.44)):
            target = clip(hit(900, 60, 0.8), hit(900, 67, 0.4), hit(3200, 36))
            self.assertEqual(transfer(target, guide, style, 100), 1)
            for event, value in zip(target["eventList"]["events"], [peak, peak / 2, 0.8]):
                self.assertAlmostEqual(event["note"]["velocity"], value)
        target = clip(hit(800, 64, 0.2), hit(800, 68, muted=True))
        before = deepcopy(target)
        self.assertEqual(transfer(target, guide, "accent", 100), 0)
        self.assertEqual(target, before)

    def test_default_targets_exclude_guide_and_source_survives(self):
        data = {"currentSequence": 0, "tracks": [{"name": n, "program": {"type": 0}}
                for n in ["Drums", "Keys"]], "sequences": [{"key": 0, "value": {"name": "Jam",
                "trackClipMaps": [[{"key": "Drums", "value": clip(hit(960, 36))},
                                   {"key": "Keys", "value": clip(hit(800, 60))}]]}}]}
        original = deepcopy(data["sequences"][0])
        report = evolve(data, None, [], "lock", [0, 100], 37, "Drums")
        self.assertEqual(report, [("Lock 0%", {"Keys": 0}), ("Lock 100%", {"Keys": 1})])
        self.assertEqual(data["sequences"][0], original)
        for seq in data["sequences"][1:]:
            self.assertEqual(seq["value"]["trackClipMaps"][0][0], original["value"]["trackClipMaps"][0][0])
        with self.assertRaisesRegex(ValueError, "different"):
            evolve(data, None, ["Drums"], "lock", [100], 37, "Drums")
        target = clip(hit(1, 60))
        target["endPulses"] = 100
        with self.assertRaisesRegex(ValueError, "playback ranges"):
            transfer(target, clip(hit(0, 36)), "duck", 100)
