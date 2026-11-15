from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from mpc_keygroup_builder.imprint_bank import build, encode
from mpc_keygroup_builder.midi_writer import MidiNote, MidiTrack, render_standard_midi


class ImprintBankTest(unittest.TestCase):
    def test_timing_relative_strength_filter_and_non_replacing_publication(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "guide.mid"
            notes = tuple(
                MidiNote(t, 5, p, v, 1)
                for t, p, v in [
                    (0, 36, 60),
                    (960, 36, 80),
                    (960, 42, 100),
                    (1203, 42, 50),
                ]
            )
            src.write_bytes(
                render_standard_midi(
                    (MidiTrack("guide", notes),), tempo=100, ppq=240, end_tick=1920
                )
            )
            self.assertEqual(encode(src, 2), bytes([1, 2, 0, 0, 127, 13, 4, 64]))
            self.assertEqual(encode(src, 2, 36), bytes([1, 1, 0, 0, 127]))
            bank = root / "Content"
            build([src], bank, 2, None)
            self.assertEqual((bank / "slot-1.gri").read_bytes(), encode(src, 2))
            with self.assertRaisesRegex(ValueError, "new output"):
                build([src], bank, 1, None)
            with self.assertRaisesRegex(ValueError, "0 attacks"):
                build([src], root / "empty", 3, None)
            self.assertFalse((root / "empty").exists())
