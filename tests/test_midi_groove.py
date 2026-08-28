import struct
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder.device import load_device
from mpc_keygroup_builder.ideas import DrumEvent, DrumIdea, render_midi
from mpc_keygroup_builder.midi_groove import (
    analyse_program_groove,
    ergonomic_slot_order,
    load_groove,
    parse_midi,
)
from mpc_keygroup_builder.model import ProgramModel, SampleLayer, Zone


class MidiGrooveTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).parents[1]
        self.device = load_device(self.root / "devices/mpc-key-37.toml")

    def _idea(self) -> DrumIdea:
        events = []
        for index, (note, velocity) in enumerate(
            [(36, 100), (36, 110), (36, 120), (36, 90), (38, 80), (99, 70)]
        ):
            events.append(
                DrumEvent(
                    index,
                    index * 120,
                    60,
                    "fixture",
                    1,
                    "A01",
                    note,
                    velocity,
                    "Fixture.wav",
                )
            )
        return DrumIdea(1, "fixture", "Kit", None, 1, 90, 1, 1, 16, 0.5, 10, 480, tuple(events))

    def _program(self) -> ProgramModel:
        return ProgramModel(
            1,
            "Kit",
            "drum",
            (
                Zone(1, "kick.primary", (SampleLayer("Kick.wav"),), pad=1, midi_note=36),
                Zone(
                    2,
                    "snare.primary",
                    (SampleLayer("Snare.wav"),),
                    pad=16,
                    midi_note=38,
                    locked=True,
                ),
                Zone(3, "hihat.closed", (SampleLayer("Hat.wav"),), pad=2, midi_note=42),
            ),
            "fixture",
            pad_note_map={1: 36, 16: 38, 2: 42},
        )

    def test_parses_format_one_and_aggregates_note_usage(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "groove.mid"
            path.write_bytes(render_midi(self._idea()))
            source, events = parse_midi(path)
            self.assertEqual(source.midi_format, 1)
            self.assertEqual(source.tracks, 2)
            self.assertEqual(source.ppq, 480)
            self.assertEqual(len(events), 6)
            self.assertEqual(events[0].channel, 10)
            self.assertEqual(events[-1].note, 99)

            groove = load_groove([path])
            report = analyse_program_groove(self._program(), self.device, groove)
            self.assertEqual(report["note_events"], 6)
            self.assertEqual(report["mapped_events"], 5)
            self.assertEqual(report["unmapped_events"], 1)
            self.assertEqual(report["zones"]["1"]["hits"], 4)
            self.assertEqual(report["zones"]["1"]["average_velocity"], 105.0)
            self.assertEqual(report["zones"]["1"]["intensity"], 1.0)
            self.assertEqual(report["unmapped_notes"], [{"midi_note": 99, "hits": 1}])
            combined = analyse_program_groove(
                self._program(), self.device, load_groove([path, path])
            )
            self.assertEqual(len(combined["sources"]), 2)
            self.assertEqual(combined["note_events"], 12)
            self.assertEqual(combined["mapped_events"], 10)
            self.assertEqual(len(combined["sources"][0]["sha256"]), 64)

    def test_parses_running_status_in_format_zero(self):
        track = b"\x00\x90\x24\x64\x0a\x26\x5a\x00\xff\x2f\x00"
        midi = (
            b"MThd"
            + struct.pack(">IHHH", 6, 0, 1, 96)
            + b"MTrk"
            + struct.pack(">I", len(track))
            + track
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "running.mid"
            path.write_bytes(midi)
            source, events = parse_midi(path)
            self.assertEqual(source.midi_format, 0)
            self.assertEqual([(event.tick, event.note) for event in events], [(0, 36), (10, 38)])

    def test_suggestions_are_deterministic_handed_and_preserve_locks(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "groove.mid"
            path.write_bytes(render_midi(self._idea()))
            report = analyse_program_groove(
                self._program(), self.device, load_groove([path])
            )
            right = report["suggestions"]["right"]
            left = report["suggestions"]["left"]
            right_by_zone = {
                item["source_zone"]: item["slot"] for item in right["assignments"]
            }
            left_by_zone = {
                item["source_zone"]: item["slot"] for item in left["assignments"]
            }
            self.assertEqual(right_by_zone[2], 16)
            self.assertEqual(left_by_zone[2], 16)
            self.assertEqual(right_by_zone[1], 4)
            self.assertEqual(left_by_zone[1], 1)
            self.assertGreaterEqual(right["reach_improvement_percent"], 0)
            self.assertEqual(ergonomic_slot_order(self.device, "right")[0], 4)
            self.assertEqual(ergonomic_slot_order(self.device, "left")[0], 1)

    def test_missing_pad_note_map_is_reported_without_guessing(self):
        program = ProgramModel(
            1,
            "Manifest Kit",
            "drum",
            (Zone(1, "kick.primary", (SampleLayer("Kick.wav"),), pad=1),),
            "fixture",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "groove.mid"
            path.write_bytes(render_midi(self._idea()))
            report = analyse_program_groove(program, self.device, load_groove([path]))
            self.assertEqual(report["mapped_events"], 0)
            self.assertEqual(report["unmapped_events"], 6)
            self.assertEqual(report["active_zones"], 0)
            self.assertEqual(report["suggestions"]["right"]["moved_assignments"], 0)

    def test_rejects_truncated_or_unsupported_midi(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.mid"
            path.write_bytes(b"MThd\0\0\0\6\0\2\0\1\1\xe0")
            with self.assertRaisesRegex(ValueError, "unsupported MIDI format"):
                parse_midi(path)


if __name__ == "__main__":
    unittest.main()
