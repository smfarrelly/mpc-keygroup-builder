"""Parse Standard MIDI grooves and derive deterministic Drum layout usage data."""

from __future__ import annotations

import hashlib
import struct
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .device import DeviceProfile
from .model import ProgramModel, Zone


@dataclass(frozen=True)
class MidiNoteEvent:
    tick: int
    track: int
    channel: int
    note: int
    velocity: int


@dataclass(frozen=True)
class MidiSource:
    path: str
    filename: str
    sha256: str
    midi_format: int
    tracks: int
    ppq: int
    note_events: int


@dataclass(frozen=True)
class MidiGroove:
    schema_version: int
    sources: tuple[MidiSource, ...]
    events: tuple[MidiNoteEvent, ...]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _variable_length(data: bytes, position: int, limit: int) -> tuple[int, int]:
    value = 0
    for _ in range(4):
        if position >= limit:
            raise ValueError("truncated MIDI variable-length value")
        byte = data[position]
        position += 1
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            return value, position
    raise ValueError("MIDI variable-length value exceeds four bytes")


def parse_midi(path: Path) -> tuple[MidiSource, tuple[MidiNoteEvent, ...]]:
    data = path.read_bytes()
    if len(data) < 14 or data[:4] != b"MThd":
        raise ValueError(f"not a Standard MIDI file: {path}")
    header_length = struct.unpack(">I", data[4:8])[0]
    if header_length < 6 or len(data) < 8 + header_length:
        raise ValueError(f"invalid MIDI header: {path}")
    midi_format, track_count, division = struct.unpack(">HHH", data[8:14])
    if midi_format not in (0, 1):
        raise ValueError(f"unsupported MIDI format {midi_format}: {path}")
    if track_count < 1 or (midi_format == 0 and track_count != 1):
        raise ValueError(f"invalid MIDI track count {track_count}: {path}")
    if division & 0x8000 or division == 0:
        raise ValueError(f"SMPTE or zero MIDI time division is unsupported: {path}")
    position = 8 + header_length
    events: list[MidiNoteEvent] = []
    for track_index in range(track_count):
        if position + 8 > len(data) or data[position : position + 4] != b"MTrk":
            raise ValueError(f"missing MIDI track {track_index + 1}: {path}")
        length = struct.unpack(">I", data[position + 4 : position + 8])[0]
        position += 8
        end = position + length
        if end > len(data):
            raise ValueError(f"truncated MIDI track {track_index + 1}: {path}")
        tick = 0
        running_status: int | None = None
        while position < end:
            delta, position = _variable_length(data, position, end)
            tick += delta
            if position >= end:
                raise ValueError(f"truncated MIDI event in track {track_index + 1}: {path}")
            first = data[position]
            if first & 0x80:
                status = first
                position += 1
                if status < 0xF0:
                    running_status = status
            elif running_status is not None:
                status = running_status
            else:
                raise ValueError(f"MIDI running status has no prior status: {path}")
            if status == 0xFF:
                running_status = None
                if position >= end:
                    raise ValueError(f"truncated MIDI meta event: {path}")
                position += 1
                size, position = _variable_length(data, position, end)
                if position + size > end:
                    raise ValueError(f"truncated MIDI meta payload: {path}")
                position += size
                continue
            if status in (0xF0, 0xF7):
                running_status = None
                size, position = _variable_length(data, position, end)
                if position + size > end:
                    raise ValueError(f"truncated MIDI SysEx payload: {path}")
                position += size
                continue
            if status >= 0xF0:
                raise ValueError(f"unsupported MIDI system event 0x{status:02X}: {path}")
            kind = status & 0xF0
            size = 1 if kind in (0xC0, 0xD0) else 2
            if position + size > end:
                raise ValueError(f"truncated MIDI channel event: {path}")
            values = data[position : position + size]
            position += size
            if kind == 0x90 and values[1] > 0:
                events.append(
                    MidiNoteEvent(tick, track_index + 1, (status & 0x0F) + 1, values[0], values[1])
                )
        position = end
    if position != len(data):
        raise ValueError(f"unexpected trailing bytes after MIDI tracks: {path}")
    source = MidiSource(
        str(path.resolve()),
        path.name,
        _sha256(path),
        midi_format,
        track_count,
        division,
        len(events),
    )
    return source, tuple(events)


def load_groove(paths: list[Path]) -> MidiGroove:
    if not paths:
        raise ValueError("at least one MIDI groove is required")
    sources: list[MidiSource] = []
    events: list[MidiNoteEvent] = []
    for path in paths:
        source, parsed = parse_midi(path)
        sources.append(source)
        events.extend(parsed)
    return MidiGroove(1, tuple(sources), tuple(events))


def ergonomic_slot_order(device: DeviceProfile, hand: str) -> tuple[int, ...]:
    if hand not in {"right", "left"}:
        raise ValueError("hand must be right or left")
    ranked = []
    for slot in range(1, device.capacity + 1):
        bank = (slot - 1) // device.pads_per_bank
        position = (slot - 1) % device.pads_per_bank
        row, column = divmod(position, device.pad_columns)
        edge_distance = device.pad_columns - 1 - column if hand == "right" else column
        reach = row + edge_distance
        ranked.append((bank, reach, row, -column if hand == "right" else column, slot))
    return tuple(value[-1] for value in sorted(ranked))


def _midi_note(zone: Zone, program: ProgramModel) -> int | None:
    if zone.midi_note is not None:
        return zone.midi_note
    if zone.pad is not None:
        return program.pad_note_map.get(zone.pad)
    return None


def _suggestion(
    program: ProgramModel,
    device: DeviceProfile,
    zone_usage: dict[int, dict[str, Any]],
    hand: str,
) -> dict[str, Any]:
    zones = [
        zone
        for zone in program.zones
        if zone.pad is not None and 1 <= zone.pad <= device.capacity
    ]
    order = ergonomic_slot_order(device, hand)
    rank = {slot: index for index, slot in enumerate(order)}
    fixed = {int(zone.pad): zone for zone in zones if zone.locked}
    available = [slot for slot in order if slot not in fixed]
    active = sorted(
        (
            zone
            for zone in zones
            if not zone.locked and zone_usage.get(zone.index, {}).get("hits", 0) > 0
        ),
        key=lambda zone: (
            -int(zone_usage[zone.index]["hits"]),
            -float(zone_usage[zone.index]["average_velocity"]),
            zone.index,
        ),
    )
    placed: dict[int, Zone] = dict(fixed)
    for zone, slot in zip(active, available):
        placed[slot] = zone
    placed_indexes = {zone.index for zone in placed.values()}
    remaining = [zone for zone in zones if zone.index not in placed_indexes]
    for zone in tuple(remaining):
        if zone.pad not in placed:
            placed[int(zone.pad)] = zone
            remaining.remove(zone)
    empty = [slot for slot in range(1, device.capacity + 1) if slot not in placed]
    for zone, slot in zip(remaining, empty):
        placed[slot] = zone
    current_cost = sum(
        int(usage["hits"]) * rank[int(zone.pad)]
        for zone in zones
        if (usage := zone_usage.get(zone.index)) and zone.pad in rank
    )
    destination_by_zone = {zone.index: slot for slot, zone in placed.items()}
    suggested_cost = sum(
        int(usage["hits"]) * rank[destination_by_zone[zone.index]]
        for zone in zones
        if (usage := zone_usage.get(zone.index)) and zone.index in destination_by_zone
    )
    improvement = (
        round((current_cost - suggested_cost) / current_cost * 100, 1)
        if current_cost
        else 0.0
    )
    assignments = [
        {"slot": slot, "label": device.label(slot), "source_zone": zone.index}
        for slot, zone in sorted(placed.items())
    ]
    return {
        "hand": hand,
        "name": f"{hand.title()}-hand usage compact",
        "heuristic": "frequent notes toward the lower dominant-hand corner; locked pads fixed",
        "assignments": assignments,
        "moved_assignments": sum(
            slot != zone.pad for slot, zone in placed.items()
        ),
        "current_reach_cost": current_cost,
        "suggested_reach_cost": suggested_cost,
        "reach_improvement_percent": improvement,
    }


def analyse_program_groove(
    program: ProgramModel,
    device: DeviceProfile,
    groove: MidiGroove | None,
) -> dict[str, Any] | None:
    if groove is None or program.kind != "drum":
        return None
    hits = Counter(event.note for event in groove.events)
    velocities: dict[int, list[int]] = defaultdict(list)
    for event in groove.events:
        velocities[event.note].append(event.velocity)
    zone_usage: dict[int, dict[str, Any]] = {}
    mapped_notes: set[int] = set()
    for zone in program.zones:
        note = _midi_note(zone, program)
        if note is None:
            continue
        mapped_notes.add(note)
        note_hits = hits[note]
        if note_hits:
            zone_usage[zone.index] = {
                "midi_note": note,
                "hits": note_hits,
                "average_velocity": round(sum(velocities[note]) / note_hits, 1),
            }
    maximum = max((item["hits"] for item in zone_usage.values()), default=0)
    mapped_events = sum(hits[note] for note in mapped_notes)
    for item in zone_usage.values():
        item["intensity"] = round(item["hits"] / maximum, 4) if maximum else 0.0
        item["share"] = round(item["hits"] / mapped_events, 4) if mapped_events else 0.0
    unmapped = [
        {"midi_note": note, "hits": count}
        for note, count in sorted(hits.items())
        if note not in mapped_notes
    ]
    return {
        "schema_version": 1,
        "sources": [asdict(source) for source in groove.sources],
        "note_events": len(groove.events),
        "mapped_events": mapped_events,
        "unmapped_events": len(groove.events) - mapped_events,
        "active_zones": len(zone_usage),
        "maximum_hits": maximum,
        "zones": {str(index): value for index, value in sorted(zone_usage.items())},
        "unmapped_notes": unmapped,
        "suggestions": {
            hand: _suggestion(program, device, zone_usage, hand)
            for hand in ("right", "left")
        },
    }
