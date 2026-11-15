from copy import deepcopy
import unittest

from mpc_keygroup_builder.hook_rehearsal import arrange


def note(tick, pitch, length=120):
    return {"time": tick, "type": 3, "note": {"note": pitch, "length": length, "velocity": .7}}


def take():
    drum = [note(12, 36), note(300, 38), note(14880, 37)]
    chord = [note(4000, 60, 5000), note(4000, 67), note(8000, 62), {"type": 9, "time": 9000}]
    lane = []
    for name, events in (("Break Relay", drum), ("Wurli", chord), ("Pluck Bass", [note(25, 48)])):
        clip = {"startPulses": 0, "endPulses": 15360, "loop": False,
                "eventList": {"events": events}, "timeSignatureList": {"timeSignatures": [
                    {"barStart": 0, "beatsPerBar": 4, "beatLength": 960}]}}
        lane.append({"key": name, "value": clip})
    return {"currentSequence": 2, "sequences": [{"key": 2, "value": {
        "name": "My take", "trackClipMaps": [lane], "lengthBars": 4, "lengthPulses": 15360}}]}


class HookRehearsalTests(unittest.TestCase):
    def test_parts_and_original_survive(self):
        data = take()
        orig = deepcopy(data)
        arrange(data)
        hook, verse, back = [s["value"] for s in data["sequences"]]
        self.assertEqual(hook, dict(orig["sequences"][0]["value"], name="Hook"))
        a, b, c = [s["trackClipMaps"][0] for s in (hook, verse, back)]
        self.assertEqual(a[2], b[2])
        self.assertEqual(a[1:], c[1:])
        self.assertEqual(b[0]["value"]["eventList"]["events"], [note(12, 36), note(14880, 37)])
        self.assertEqual(b[1]["value"]["eventList"]["events"],
                         [note(4000, 60, 3680), note(4000, 67), {"type": 9, "time": 9000}])
        hits = c[0]["value"]["eventList"]["events"]
        self.assertEqual(hits[:-1], a[0]["value"]["eventList"]["events"])
        self.assertEqual((hits[-1]["time"], hits[-1]["note"]["note"]), (15120, 39))

    def test_existing_pickup_and_retry(self):
        data = take()
        data["sequences"][0]["value"]["trackClipMaps"][0][0]["value"]["eventList"]["events"].append(note(15000, 39))
        arrange(data)
        self.assertEqual(data["sequences"][0]["value"]["trackClipMaps"],
                         data["sequences"][2]["value"]["trackClipMaps"])
        with self.assertRaisesRegex(ValueError, "existing"):
            arrange(data)

    def test_rejects_silent_and_short_loop_without_partial_edits(self):
        for silent in (True, False):
            data = take()
            keys = data["sequences"][0]["value"]["trackClipMaps"][0][1]["value"]
            if silent:
                keys["eventList"]["events"].clear()
            else:
                keys.update(loop=True, loopStartPulses=0, loopEndPulses=3840)
            original = deepcopy(data)
            with self.assertRaises(ValueError):
                arrange(data)
            self.assertEqual(data, original)
