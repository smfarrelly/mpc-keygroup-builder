import unittest

from mpc_keygroup_builder.midi_writer import MidiNote, MidiTrack, render_standard_midi, variable_length


class MidiWriterTests(unittest.TestCase):
    def test_variable_length_boundaries(self):
        self.assertEqual(variable_length(0), b"\x00")
        self.assertEqual(variable_length(127), b"\x7f")
        self.assertEqual(variable_length(128), b"\x81\x00")
        with self.assertRaisesRegex(ValueError, "negative"):
            variable_length(-1)

    def test_rejects_invalid_note_data(self):
        track = MidiTrack("Bad", (MidiNote(0, 120, 128, 100, 1),))
        with self.assertRaisesRegex(ValueError, "outside"):
            render_standard_midi((track,), tempo=90, ppq=480, end_tick=480)


if __name__ == "__main__":
    unittest.main()
