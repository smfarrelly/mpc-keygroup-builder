"""Small dependency-free Standard MIDI file writer shared by idea generators."""

from __future__ import annotations

import struct
from dataclasses import dataclass


@dataclass(frozen=True)
class MidiNote:
    tick: int
    duration_ticks: int
    note: int
    velocity: int
    channel: int


@dataclass(frozen=True)
class MidiTrack:
    name: str
    notes: tuple[MidiNote, ...]


def variable_length(value: int) -> bytes:
    if value < 0:
        raise ValueError("MIDI delta time cannot be negative")
    buffer = value & 0x7F
    result = bytearray([buffer])
    while value >> 7:
        value >>= 7
        buffer = (value & 0x7F) | 0x80
        result.insert(0, buffer)
    return bytes(result)


def _track_chunk(timeline: list[tuple[int, int, bytes]]) -> bytes:
    timeline.sort(key=lambda item: (item[0], item[1], item[2]))
    track = bytearray()
    previous = 0
    for tick, _, message in timeline:
        if tick < previous:
            raise ValueError("MIDI timeline is not monotonic")
        track.extend(variable_length(tick - previous))
        track.extend(message)
        previous = tick
    return b"MTrk" + struct.pack(">I", len(track)) + bytes(track)


def render_standard_midi(
    tracks: tuple[MidiTrack, ...],
    *,
    tempo: float,
    ppq: int,
    end_tick: int,
    midi_format: int = 1,
    beats_per_bar: int = 4,
) -> bytes:
    """Render named note tracks with a tempo/time-signature conductor track."""
    if midi_format not in (0, 1):
        raise ValueError("MIDI format must be 0 or 1")
    if not tracks:
        raise ValueError("at least one MIDI note track is required")
    if not 20 <= tempo <= 300:
        raise ValueError("tempo must be 20..300 BPM")
    if ppq < 24 or ppq % 4:
        raise ValueError("PPQ must be at least 24 and divisible by four")
    if end_tick < 1:
        raise ValueError("MIDI end tick must be positive")
    if beats_per_bar not in (2, 3, 4, 5, 6, 7, 8):
        raise ValueError("beats per bar must be 2..8")

    tempo_microseconds = round(60_000_000 / tempo)
    conductor = [
        (0, 0, b"\xff\x03\x09Conductor"),
        (0, 1, b"\xff\x51\x03" + tempo_microseconds.to_bytes(3, "big")),
        (0, 2, bytes([0xFF, 0x58, 0x04, beats_per_bar, 2, 24, 8])),
        (end_tick, 9, b"\xff\x2f\x00"),
    ]
    rendered_tracks: list[list[tuple[int, int, bytes]]] = []
    for midi_track in tracks:
        name = midi_track.name.encode("utf-8")[:127]
        timeline = [(0, 0, b"\xff\x03" + variable_length(len(name)) + name)]
        for note in midi_track.notes:
            if note.tick < 0 or note.duration_ticks < 1:
                raise ValueError("MIDI notes require non-negative ticks and positive duration")
            if not 0 <= note.note <= 127 or not 1 <= note.velocity <= 127:
                raise ValueError("MIDI note/velocity is outside 0..127")
            if not 1 <= note.channel <= 16:
                raise ValueError("MIDI channel must be 1..16")
            channel = note.channel - 1
            timeline.append((note.tick, 2, bytes([0x90 | channel, note.note, note.velocity])))
            timeline.append(
                (
                    note.tick + note.duration_ticks,
                    1,
                    bytes([0x80 | channel, note.note, 0]),
                )
            )
        timeline.append((end_tick, 9, b"\xff\x2f\x00"))
        rendered_tracks.append(timeline)

    if midi_format == 0:
        merged = conductor[1:-1]
        for timeline in rendered_tracks:
            merged.extend(timeline[:-1])
        merged.append((end_tick, 9, b"\xff\x2f\x00"))
        header = b"MThd" + struct.pack(">IHHH", 6, 0, 1, ppq)
        return header + _track_chunk(merged)

    header = b"MThd" + struct.pack(">IHHH", 6, 1, len(tracks) + 1, ppq)
    return header + _track_chunk(conductor) + b"".join(
        _track_chunk(timeline) for timeline in rendered_tracks
    )
