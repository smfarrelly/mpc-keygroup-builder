"""Check saved project selection, velocity boundaries and the portable two-track result."""

from pathlib import Path
from tempfile import TemporaryDirectory
import gzip
import json
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from print_take import print_take
from mpc_keygroup_builder.midi_groove import parse_midi


class Printer(unittest.TestCase):
    def test_project_to_variations(self):
        def hit(time, velocity, muted=False):
            return dict(
                type=3,
                time=time,
                channel=0,
                muted=muted,
                note=dict(note=54, velocity=velocity / 127),
            )

        events = [
            hit(0, 126),
            hit(3840, 105),
            hit(4080, 80),
            hit(4320, 48),
            hit(4560, 47),
            hit(4800, 33, True),
        ]
        clip = dict(eventList=dict(events=events))
        seq = dict(
            name="Groove",
            bpm=96,
            timeSignatureTrack=dict(
                timeSignatures=[dict(beatsPerBar=4, beatLength=960)]
            ),
            trackClipMaps=[
                [dict(key="Kit", value=clip), dict(key="Another", value=clip)]
            ],
        )
        data = dict(masterTempoEnabled=False, sequences=[dict(value=seq)])
        with TemporaryDirectory() as tmp:
            f = Path(tmp) / "Jam.xpj"
            out = Path(tmp) / "Printed"
            original = gzip.compress(
                b"ACVS\n3\nProject\nJSON\nMPC\n" + json.dumps(dict(data=data)).encode()
            )
            f.write_bytes(original)
            with self.assertRaisesRegex(ValueError, "--track"):
                print_take(f, out, None, 2, None, 43, strike_note=54)
            self.assertFalse(out.exists())
            print_take(f, out, None, 2, None, 43, strike_note=54, track="Kit")
            self.assertEqual(f.read_bytes(), original)
            _, played = parse_midi(out / "Original.mid")
            self.assertEqual(
                [(e.tick, e.channel, e.note, e.velocity) for e in played],
                [
                    (0, 10, 36, 105),
                    (120, 10, 38, 80),
                    (240, 10, 42, 48),
                    (360, 10, 46, 47),
                ],
            )
            _, canon = parse_midi(out / "Canon.mid")
            self.assertEqual(
                [(e.tick, e.note) for e in canon if e.channel == 1],
                [(360, 74), (480, 65), (600, 69), (720, 72)],
            )
            _, trigger = parse_midi(out / "Play in Shadow Steps.mid")
            self.assertEqual([e.note for e in trigger], [35, 36, 37, 38, 39])
            with self.assertRaises(FileExistsError):
                print_take(f, out, None, 2, None, 43, strike_note=54, track="Kit")


if __name__ == "__main__":
    unittest.main()
