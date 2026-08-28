"""Generate deterministic scale-safe melodies from repeating, varied motifs."""

from __future__ import annotations

import argparse
import json
import random
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path

from .harmony import NOTE_NAMES, SCALES
from .midi_writer import MidiNote, MidiTrack, render_standard_midi


@dataclass(frozen=True)
class MelodyRecipe:
    schema_version: int
    id: str
    name: str
    key: str
    scale: str
    bars: int
    beats_per_bar: int
    steps_per_beat: int
    motif_steps: int
    rhythm: tuple[int, ...]
    contour: tuple[int, ...]
    start_degree: int
    note_range: tuple[int, int]
    variation: float
    rest_probability: float
    octave_probability: float
    velocity: int
    humanize_velocity: int
    gate: float
    channel: int


@dataclass(frozen=True)
class MelodyEvent:
    repetition: int
    motif_event: int
    source_step: int
    step: int
    scale_degree: int
    variation: str
    tick: int
    duration_ticks: int
    midi_note: int
    velocity: int


@dataclass(frozen=True)
class MelodyIdea:
    schema_version: int
    recipe: str
    seed: int
    tempo: float
    key: str
    scale: str
    bars: int
    beats_per_bar: int
    steps_per_beat: int
    motif_steps: int
    note_range: tuple[int, int]
    ppq: int
    events: tuple[MelodyEvent, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def _range(value: object) -> tuple[int, int]:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not all(isinstance(item, int) for item in value)
    ):
        raise ValueError("note_range must contain two MIDI integers")
    low, high = value
    if not 0 <= low <= high <= 127:
        raise ValueError("note_range must satisfy 0 <= low <= high <= 127")
    return low, high


def load_recipe(path: Path) -> MelodyRecipe:
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    required = (
        "schema_version", "id", "name", "key", "scale", "bars",
        "motif_steps", "rhythm", "contour", "note_range",
    )
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"melody recipe is missing: {', '.join(missing)}")
    if data["schema_version"] != 1:
        raise ValueError("melody recipe requires schema_version=1")
    key = data["key"].strip().upper() if isinstance(data["key"], str) else ""
    scale = data["scale"].strip().lower() if isinstance(data["scale"], str) else ""
    if key not in NOTE_NAMES:
        raise ValueError("recipe key must be a note name such as C, F#, or Bb")
    if scale not in SCALES:
        raise ValueError(f"recipe scale must be one of: {', '.join(SCALES)}")
    bars = data["bars"]
    beats_per_bar = data.get("beats_per_bar", 4)
    steps_per_beat = data.get("steps_per_beat", 4)
    motif_steps = data["motif_steps"]
    rhythm = data["rhythm"]
    contour = data["contour"]
    if not isinstance(bars, int) or not 1 <= bars <= 64:
        raise ValueError("recipe bars must be 1..64")
    if not isinstance(beats_per_bar, int) or not 2 <= beats_per_bar <= 8:
        raise ValueError("recipe beats_per_bar must be 2..8")
    if not isinstance(steps_per_beat, int) or steps_per_beat not in (1, 2, 4):
        raise ValueError("recipe steps_per_beat must be 1, 2, or 4")
    total_steps = bars * beats_per_bar * steps_per_beat
    if (
        not isinstance(motif_steps, int) or motif_steps < 1
        or motif_steps > total_steps or total_steps % motif_steps
    ):
        raise ValueError("motif_steps must divide the complete pattern")
    if not isinstance(rhythm, list) or not rhythm or not all(
        isinstance(step, int) and 0 <= step < motif_steps for step in rhythm
    ):
        raise ValueError("rhythm must contain motif step indexes")
    if len(rhythm) != len(set(rhythm)) or rhythm != sorted(rhythm):
        raise ValueError("rhythm steps must be unique and ascending")
    if not isinstance(contour, list) or len(contour) != len(rhythm) or not all(
        isinstance(offset, int) and -14 <= offset <= 14 for offset in contour
    ):
        raise ValueError("contour must contain one scale offset per rhythm event")
    start_degree = data.get("start_degree", 1)
    if not isinstance(start_degree, int) or not 1 <= start_degree <= 7:
        raise ValueError("start_degree must be 1..7")
    variation = data.get("variation", 0.2)
    rest_probability = data.get("rest_probability", 0.0)
    octave_probability = data.get("octave_probability", 0.0)
    for label, value in (
        ("variation", variation), ("rest_probability", rest_probability),
        ("octave_probability", octave_probability),
    ):
        if not isinstance(value, (int, float)) or not 0 <= value <= 1:
            raise ValueError(f"{label} must be 0..1")
    velocity = data.get("velocity", 96)
    humanize = data.get("humanize_velocity", 0)
    gate = data.get("gate", 0.8)
    channel = data.get("channel", 3)
    if not isinstance(velocity, int) or not 1 <= velocity <= 127:
        raise ValueError("velocity must be 1..127")
    if not isinstance(humanize, int) or not 0 <= humanize <= 32:
        raise ValueError("humanize_velocity must be 0..32")
    if not isinstance(gate, (int, float)) or not 0 < gate <= 1:
        raise ValueError("gate must be greater than zero and at most one")
    if not isinstance(channel, int) or not 1 <= channel <= 16:
        raise ValueError("channel must be 1..16")
    return MelodyRecipe(
        1, str(data["id"]), str(data["name"]), key, scale, bars,
        beats_per_bar, steps_per_beat, motif_steps, tuple(rhythm), tuple(contour),
        start_degree, _range(data["note_range"]), float(variation),
        float(rest_probability), float(octave_probability), velocity, humanize,
        float(gate), channel,
    )


def _scale_note(
    tonic: int,
    scale: tuple[int, ...],
    degree_index: int,
    note_range: tuple[int, int],
    target: float,
) -> int:
    _, position = divmod(degree_index, 7)
    pitch = (tonic + scale[position]) % 12
    low, high = note_range
    choices = [note for note in range(low, high + 1) if note % 12 == pitch]
    if not choices:
        raise ValueError(f"scale pitch class {pitch} cannot fit range {low}:{high}")
    return min(choices, key=lambda note: (abs(note - target), note))


def _degree_semitones(scale: tuple[int, ...], degree_index: int) -> int:
    octave, position = divmod(degree_index, 7)
    return octave * 12 + scale[position]


def generate_idea(
    recipe: MelodyRecipe,
    *,
    seed: int,
    tempo: float,
    ppq: int = 480,
) -> MelodyIdea:
    if not 20 <= tempo <= 300:
        raise ValueError("tempo must be 20..300 BPM")
    if ppq < 24 or ppq % recipe.steps_per_beat:
        raise ValueError("PPQ must be at least 24 and divisible by steps_per_beat")
    rng = random.Random(seed)
    total_steps = recipe.bars * recipe.beats_per_bar * recipe.steps_per_beat
    repetitions = total_steps // recipe.motif_steps
    step_ticks = ppq // recipe.steps_per_beat
    tonic = NOTE_NAMES[recipe.key]
    scale = SCALES[recipe.scale]
    previous: int | None = None
    previous_degree: int | None = None
    events = []
    for repetition in range(repetitions):
        for motif_event, (source_step, base_offset) in enumerate(zip(recipe.rhythm, recipe.contour)):
            if repetition and rng.random() < recipe.rest_probability:
                continue
            offset = base_offset
            changes = []
            if repetition and rng.random() < recipe.variation:
                offset += rng.choice((-1, 1))
                changes.append("neighbor")
            octave = 0
            if repetition and rng.random() < recipe.octave_probability:
                octave = rng.choice((-7, 7))
                changes.append("octave")
            degree_index = recipe.start_degree - 1 + offset + octave
            if previous is None or previous_degree is None:
                target = (recipe.note_range[0] + recipe.note_range[1]) / 2
            else:
                target = previous + _degree_semitones(scale, degree_index) - _degree_semitones(
                    scale, previous_degree
                )
            note = _scale_note(tonic, scale, degree_index, recipe.note_range, target)
            previous = note
            previous_degree = degree_index
            step = repetition * recipe.motif_steps + source_step
            velocity = max(
                1, min(127, recipe.velocity + rng.randint(
                    -recipe.humanize_velocity, recipe.humanize_velocity
                )),
            )
            events.append(MelodyEvent(
                repetition, motif_event, source_step, step, degree_index + 1,
                "+".join(changes) or "repeat", step * step_ticks,
                max(1, round(step_ticks * recipe.gate)), note, velocity,
            ))
    return MelodyIdea(
        1, recipe.id, seed, tempo, recipe.key, recipe.scale, recipe.bars,
        recipe.beats_per_bar, recipe.steps_per_beat, recipe.motif_steps,
        recipe.note_range, ppq, tuple(events),
    )


def render_midi(idea: MelodyIdea, recipe: MelodyRecipe, *, midi_format: int = 1) -> bytes:
    notes = tuple(
        MidiNote(event.tick, event.duration_ticks, event.midi_note, event.velocity, recipe.channel)
        for event in idea.events
    )
    return render_standard_midi(
        (MidiTrack("Melody", notes),), tempo=idea.tempo, ppq=idea.ppq,
        end_tick=idea.bars * idea.beats_per_bar * idea.ppq,
        midi_format=midi_format, beats_per_bar=idea.beats_per_bar,
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
    variations = sum(event.variation != "repeat" for event in idea.events)
    print(f"Wrote: {json_path}")
    print(f"Wrote: {midi_path}")
    print(f"Notes: {len(idea.events)}; variations: {variations}; seed={idea.seed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
