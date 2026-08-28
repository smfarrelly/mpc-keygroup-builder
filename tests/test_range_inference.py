import unittest

from mpc_keygroup_builder.range_inference import (
    infer_octave_shift,
    parse_target,
    validate_target,
)


class RootRangeInferenceTests(unittest.TestCase):
    def test_infers_repeatable_nr2_software_fixture_shift(self):
        source_ranges = {
            "analog tom": (27, 42),
            "chimes": (35, 50),
            "cowbell": (29, 44),
            "tom": (25, 40),
            "tone": (33, 48),
        }
        expected_ranges = {
            "analog tom": (63, 78),
            "chimes": (71, 86),
            "cowbell": (65, 80),
            "tom": (61, 76),
            "tone": (69, 84),
        }
        for name, (low, high) in source_ranges.items():
            with self.subTest(name=name):
                placement = infer_octave_shift(range(low, high + 1), 60, 96)
                self.assertEqual(placement.shift, 36)
                self.assertEqual(
                    (placement.result_low, placement.result_high), expected_ranges[name]
                )
                self.assertTrue(placement.complete)

    def test_preserves_broad_accepted_mapping_when_tied(self):
        placement = infer_octave_shift(range(24, 97), 60, 96)
        self.assertEqual(placement.shift, 0)
        self.assertEqual(placement.roots_in_target, 37)
        self.assertFalse(placement.complete)

    def test_single_low_root_uses_smallest_octave_shift_into_target(self):
        placement = infer_octave_shift([24], 48, 84)
        self.assertEqual(placement.shift, 24)
        self.assertEqual((placement.result_low, placement.result_high), (48, 48))

    def test_pitch_classes_are_preserved(self):
        roots = [25, 29, 36, 40]
        placement = infer_octave_shift(roots, 60, 96)
        self.assertEqual(placement.shift % 12, 0)
        self.assertEqual(
            [(root + placement.shift) % 12 for root in roots],
            [root % 12 for root in roots],
        )

    def test_reports_partial_fit_for_wider_source_than_target(self):
        placement = infer_octave_shift(range(36, 85), 48, 72)
        self.assertEqual(placement.shift, 0)
        self.assertEqual(placement.roots_in_target, 25)
        self.assertEqual(placement.total_roots, 49)
        self.assertFalse(placement.to_dict()["complete"])

    def test_target_parser_and_validation_are_strict(self):
        self.assertEqual(parse_target("60:96"), (60, 96))
        self.assertEqual(validate_target(0, 127), (0, 127))
        for value in ("60", "C3:C6", "96:60", "-1:60", "0:128"):
            with self.subTest(value=value), self.assertRaises((TypeError, ValueError)):
                parse_target(value)

    def test_rejects_missing_or_invalid_roots(self):
        with self.assertRaisesRegex(ValueError, "at least one"):
            infer_octave_shift([], 60, 96)
        with self.assertRaisesRegex(ValueError, "within MIDI"):
            infer_octave_shift([128], 60, 96)
        with self.assertRaisesRegex(TypeError, "integers"):
            infer_octave_shift([60.5], 60, 96)


if __name__ == "__main__":
    unittest.main()
