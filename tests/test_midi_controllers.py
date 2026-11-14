import unittest
from mpc_keygroup_builder.midi_writer import MidiControlChange, MidiNote, MidiTrack, render_standard_midi


class ControllerMidiTests(unittest.TestCase):
    def test_controller_clock_and_same_tick_note_order_in_both_formats(self):
        controls = (MidiControlChange(128, 20, 103, 8), MidiControlChange(240, 20, 0, 8))
        track = MidiTrack("Bass", (MidiNote(128, 48, 40, 85, 2),), controls)
        for fmt in (0, 1):
            midi = render_standard_midi((track,), tempo=96, ppq=480, end_tick=1920, midi_format=fmt)
            self.assertIn(bytes.fromhex("8100 B71467 00 912855 30 812800 40 B71400"), midi)

    def test_reject_bad_messages(self):
        for args in ((-1, 20, 60, 8), (1920, 20, 60, 8), (0, 128, 60, 8), (0, 1, -1, 8), (0, 1, 1, 17)):
            track = MidiTrack("Bad", (), (MidiControlChange(*args),))
            with self.subTest(args=args), self.assertRaises(ValueError):
                render_standard_midi((track,), tempo=96, ppq=480, end_tick=1920)
