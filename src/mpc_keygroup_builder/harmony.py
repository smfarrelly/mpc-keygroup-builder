"""Generate deterministic, range-safe chord and bass MIDI ideas."""

from __future__ import annotations

import argparse
import itertools
import json
import random
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path

from .midi_writer import MidiNote, MidiTrack, render_standard_midi


NOTE_NAMES = {
    "C": 0,
    "C#": 1,
    "DB": 1,
    "D": 2,
    "D#": 3,
    "EB": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "GB": 6,
    "G": 7,
    "G#": 8,
    "AB": 8,
    "A": 9,
    "A#": 10,
    "BB": 10,
    "B": 11,
}
SCALES = {
    "major": (0, 2, 4, 5, 7, 9, 11),
    "minor": (0, 2, 3, 5, 7, 8, 10),
    "dorian": (0, 2, 3, 5, 7, 9, 10),
    "mixolydian": (0, 2, 4, 5, 7, 9, 10),
}


@dataclass(frozen=True)
class HarmonyRecipe:
    schema_version: int
    id: str
    name: str
    key: str
    scale: str
    bars: int
    beats_per_bar: int
    progression: tuple[int, ...]
    chord_beats: tuple[float, ...]
    chord_notes: int
    chord_range: tuple[int, int]
    bass_range: tuple[int, int]
    bass_pattern: tuple[int, ...]
    bass_steps_per_beat: int
    chord_velocity: int
    bass_velocity: int
    gate: float
    humanize_velocity: int
    chord_channel: int
    bass_channel: int


@dataclass(frozen=True)
class HarmonicEvent:
    part: str
    chord_index: int
    degree: int
    tick: int
    duration_ticks: int
    midi_note: int
    velocity: int


@dataclass(frozen=True)
class ChordDecision:
    chord_index: int
    degree: int
    start_beat: float
    duration_beats: float
    notes: tuple[int, ...]


@dataclass(frozen=True)
class HarmonyIdea:
    schema_version: int
    recipe: str
    seed: int
    tempo: float
    key: str
    scale: str
    bars: int
    beats_per_bar: int
    ppq: int
    chord_range: tuple[int, int]
    bass_range: tuple[int, int]
    decisions: tuple[ChordDecision, ...]
    events: tuple[HarmonicEvent, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def _integer_range(value: object, label: str) -> tuple[int, int]:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not all(isinstance(item, int) for item in value)
    ):
        raise ValueError(f"{label} must contain two MIDI integers")
    low, high = value
    if not 0 <= low <= high <= 127:
        raise ValueError(f"{label} must satisfy 0 <= low <= high <= 127")
    return low, high


def load_recipe(path: Path) -> HarmonyRecipe:
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    required = (
        "schema_version",
        "id",
        "name",
        "key",
        "scale",
        "bars",
        "progression",
        "chord_range",
        "bass_range",
    )
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"harmony recipe is missing: {', '.join(missing)}")
    if data["schema_version"] != 1:
        raise ValueError("harmony recipe requires schema_version=1")
    key = data["key"].strip().upper() if isinstance(data["key"], str) else ""
    if key not in NOTE_NAMES:
        raise ValueError("recipe key must be a note name such as C, F#, or Bb")
    scale = data["scale"].strip().lower() if isinstance(data["scale"], str) else ""
    if scale not in SCALES:
        raise ValueError(f"recipe scale must be one of: {', '.join(SCALES)}")
    bars = data["bars"]
    beats_per_bar = data.get("beats_per_bar", 4)
    progression = data["progression"]
    chord_beats = data.get("chord_beats")
    chord_notes = data.get("chord_notes", 3)
    if not isinstance(bars, int) or not 1 <= bars <= 64:
        raise ValueError("recipe bars must be 1..64")
    if not isinstance(beats_per_bar, int) or not 2 <= beats_per_bar <= 8:
        raise ValueError("recipe beats_per_bar must be 2..8")
    if not isinstance(progression, list) or not progression or not all(
        isinstance(degree, int) and 1 <= degree <= 7 for degree in progression
    ):
        raise ValueError("recipe progression must contain scale degrees 1..7")
    if chord_beats is None:
        duration = bars * beats_per_bar / len(progression)
        chord_beats = [duration] * len(progression)
    if not isinstance(chord_beats, list) or len(chord_beats) != len(progression) or not all(
        isinstance(value, (int, float)) and value > 0 for value in chord_beats
    ):
        raise ValueError("recipe chord_beats must contain one positive duration per chord")
    if abs(sum(chord_beats) - bars * beats_per_bar) > 1e-6:
        raise ValueError("recipe chord_beats must fill exactly bars * beats_per_bar")
    if chord_notes not in (3, 4):
        raise ValueError("recipe chord_notes must be 3 or 4")
    bass_pattern = data.get("bass_pattern", [0])
    bass_steps = data.get("bass_steps_per_beat", 1)
    if not isinstance(bass_pattern, list) or not bass_pattern or not all(
        isinstance(interval, int) and -24 <= interval <= 24 for interval in bass_pattern
    ):
        raise ValueError("recipe bass_pattern must contain semitone offsets from -24..24")
    if not isinstance(bass_steps, int) or bass_steps not in (1, 2, 4):
        raise ValueError("recipe bass_steps_per_beat must be 1, 2, or 4")
    chord_velocity = data.get("chord_velocity", 88)
    bass_velocity = data.get("bass_velocity", 104)
    gate = data.get("gate", 0.85)
    humanize = data.get("humanize_velocity", 0)
    chord_channel = data.get("chord_channel", 1)
    bass_channel = data.get("bass_channel", 2)
    for label, value in (("chord_velocity", chord_velocity), ("bass_velocity", bass_velocity)):
        if not isinstance(value, int) or not 1 <= value <= 127:
            raise ValueError(f"recipe {label} must be 1..127")
    if not isinstance(gate, (int, float)) or not 0 < gate <= 1:
        raise ValueError("recipe gate must be greater than zero and at most one")
    if not isinstance(humanize, int) or not 0 <= humanize <= 32:
        raise ValueError("recipe humanize_velocity must be 0..32")
    for label, value in (("chord_channel", chord_channel), ("bass_channel", bass_channel)):
        if not isinstance(value, int) or not 1 <= value <= 16:
            raise ValueError(f"recipe {label} must be 1..16")
    return HarmonyRecipe(
        1,
        str(data["id"]),
        str(data["name"]),
        key,
        scale,
        bars,
        beats_per_bar,
        tuple(progression),
        tuple(float(value) for value in chord_beats),
        chord_notes,
        _integer_range(data["chord_range"], "chord_range"),
        _integer_range(data["bass_range"], "bass_range"),
        tuple(bass_pattern),
        bass_steps,
        chord_velocity,
        bass_velocity,
        float(gate),
        humanize,
        chord_channel,
        bass_channel,
    )


def _diatonic_pitches(tonic: int, scale: tuple[int, ...], degree: int, count: int) -> tuple[int, ...]:
    index = degree - 1
    root = tonic + scale[index]
    result = []
    for chord_tone in range(count):
        scale_index = index + chord_tone * 2
        octave, position = divmod(scale_index, 7)
        result.append((tonic + scale[position] + octave * 12 - root) % 12)
    return tuple(result)


def _voicings(pitch_classes: tuple[int, ...], low: int, high: int) -> tuple[tuple[int, ...], ...]:
    choices = [tuple(note for note in range(low, high + 1) if note % 12 == pitch) for pitch in pitch_classes]
    if any(not choice for choice in choices):
        return ()
    voicings = {
        tuple(sorted(notes))
        for notes in itertools.product(*choices)
        if len(set(notes)) == len(notes) and max(notes) - min(notes) <= 24
    }
    return tuple(sorted(voicings))


def _choose_voicing(
    pitch_classes: tuple[int, ...],
    note_range: tuple[int, int],
    previous: tuple[int, ...] | None,
) -> tuple[int, ...]:
    low, high = note_range
    candidates = _voicings(pitch_classes, low, high)
    if not candidates:
        raise ValueError(f"chord cannot fit {len(pitch_classes)} distinct notes in range {low}:{high}")
    center = (low + high) / 2
    if previous is None:
        return min(candidates, key=lambda notes: (abs(sum(notes) / len(notes) - center), max(notes) - min(notes), notes))
    return min(
        candidates,
        key=lambda notes: (
            sum(abs(a - b) for a, b in zip(notes, previous)),
            abs(sum(notes) / len(notes) - center),
            max(notes) - min(notes),
            notes,
        ),
    )


def _fit_pitch(pitch: int, note_range: tuple[int, int], target: float) -> int:
    low, high = note_range
    candidates = [note for note in range(low, high + 1) if note % 12 == pitch % 12]
    if not candidates:
        raise ValueError(f"pitch class {pitch % 12} cannot fit range {low}:{high}")
    return min(candidates, key=lambda note: (abs(note - target), note))


def generate_idea(
    recipe: HarmonyRecipe,
    *,
    seed: int,
    tempo: float,
    ppq: int = 480,
) -> HarmonyIdea:
    if not 20 <= tempo <= 300:
        raise ValueError("tempo must be 20..300 BPM")
    if ppq < 24 or ppq % 4:
        raise ValueError("PPQ must be at least 24 and divisible by four")
    rng = random.Random(seed)
    tonic = NOTE_NAMES[recipe.key]
    scale = SCALES[recipe.scale]
    events: list[HarmonicEvent] = []
    decisions: list[ChordDecision] = []
    start_beat = 0.0
    previous: tuple[int, ...] | None = None
    for chord_index, (degree, duration_beats) in enumerate(
        zip(recipe.progression, recipe.chord_beats)
    ):
        intervals = _diatonic_pitches(tonic, scale, degree, recipe.chord_notes)
        root_pitch = (tonic + scale[degree - 1]) % 12
        pitch_classes = tuple((root_pitch + interval) % 12 for interval in intervals)
        notes = _choose_voicing(pitch_classes, recipe.chord_range, previous)
        previous = notes
        tick = round(start_beat * ppq)
        duration = max(1, round(duration_beats * ppq * recipe.gate))
        decisions.append(ChordDecision(chord_index, degree, start_beat, duration_beats, notes))
        chord_velocity = max(
            1,
            min(127, recipe.chord_velocity + rng.randint(-recipe.humanize_velocity, recipe.humanize_velocity)),
        )
        for note in notes:
            events.append(HarmonicEvent("chords", chord_index, degree, tick, duration, note, chord_velocity))

        bass_count = max(1, round(duration_beats * recipe.bass_steps_per_beat))
        bass_step_beats = duration_beats / bass_count
        bass_target = (recipe.bass_range[0] + recipe.bass_range[1]) / 2
        for step in range(bass_count):
            offset = recipe.bass_pattern[step % len(recipe.bass_pattern)]
            note = _fit_pitch(root_pitch + offset, recipe.bass_range, bass_target)
            bass_tick = round((start_beat + step * bass_step_beats) * ppq)
            bass_duration = max(1, round(bass_step_beats * ppq * recipe.gate))
            velocity = max(
                1,
                min(127, recipe.bass_velocity + rng.randint(-recipe.humanize_velocity, recipe.humanize_velocity)),
            )
            events.append(HarmonicEvent("bass", chord_index, degree, bass_tick, bass_duration, note, velocity))
        start_beat += duration_beats
    events.sort(key=lambda event: (event.tick, event.part, event.midi_note))
    return HarmonyIdea(
        1,
        recipe.id,
        seed,
        tempo,
        recipe.key,
        recipe.scale,
        recipe.bars,
        recipe.beats_per_bar,
        ppq,
        recipe.chord_range,
        recipe.bass_range,
        tuple(decisions),
        tuple(events),
    )


def render_midi(idea: HarmonyIdea, recipe: HarmonyRecipe, *, midi_format: int = 1) -> bytes:
    tracks = []
    for part, channel in (("chords", recipe.chord_channel), ("bass", recipe.bass_channel)):
        notes = tuple(
            MidiNote(event.tick, event.duration_ticks, event.midi_note, event.velocity, channel)
            for event in idea.events
            if event.part == part
        )
        tracks.append(MidiTrack(part.title(), notes))
    return render_standard_midi(
        tuple(tracks),
        tempo=idea.tempo,
        ppq=idea.ppq,
        end_tick=idea.bars * idea.beats_per_bar * idea.ppq,
        midi_format=midi_format,
        beats_per_bar=idea.beats_per_bar,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipe", type=Path)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--tempo", type=float, default=90.0)
    parser.add_argument("--midi-format", type=int, choices=(0, 1), default=1)
    parser.add_argument("--output-prefix", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    recipe = load_recipe(args.recipe.expanduser().resolve())
    idea = generate_idea(recipe, seed=args.seed, tempo=args.tempo)
    prefix = args.output_prefix.expanduser().resolve()
    json_path = prefix.with_suffix(".json")
    midi_path = prefix.with_suffix(".mid")
    if not args.force and (json_path.exists() or midi_path.exists()):
        parser.error("output exists; pass --force to replace both files")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(idea.to_dict(), indent=2) + "\n", encoding="utf-8")
    midi_path.write_bytes(render_midi(idea, recipe, midi_format=args.midi_format))
    chord_count = len(idea.decisions)
    bass_count = sum(event.part == "bass" for event in idea.events)
    print(f"Wrote: {json_path}")
    print(f"Wrote: {midi_path}")
    print(f"Chords: {chord_count}; bass notes: {bass_count}; seed={idea.seed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
