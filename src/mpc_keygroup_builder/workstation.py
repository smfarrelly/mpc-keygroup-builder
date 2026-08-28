"""Combine semantic drums, harmony, bass, and melody into one idea bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path

from .device import load_device
from .harmony import (
    HarmonyIdea,
    HarmonyRecipe,
    generate_idea as generate_harmony,
    load_recipe as load_harmony,
)
from .ideas import (
    DrumIdea,
    PatternRecipe,
    apply_layout,
    generate_idea as generate_drums,
    load_recipe as load_drums,
)
from .layout import arrange, load_preset
from .melody import (
    MelodyIdea,
    MelodyRecipe,
    generate_idea as generate_melody,
    load_recipe as load_melody,
)
from .midi_writer import MidiNote, MidiTrack, render_standard_midi
from .model import ProgramModel, from_xpm
from .roles import load_role_overrides


@dataclass(frozen=True)
class WorkstationRecipe:
    schema_version: int
    id: str
    name: str
    source_path: str
    drum_recipe_path: str
    harmony_recipe_path: str
    melody_recipe_path: str
    programs: dict[str, str]


@dataclass(frozen=True)
class WorkstationIdea:
    schema_version: int
    recipe: str
    name: str
    seed: int
    component_seeds: dict[str, int]
    tempo: float
    bars: int
    beats_per_bar: int
    ppq: int
    drum_program: str
    drum_program_file: str
    drum_program_sha256: str
    layout: str | None
    suggested_programs: dict[str, str]
    drums: DrumIdea
    harmony: HarmonyIdea
    melody: MelodyIdea

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class LoadedWorkstationRecipe:
    recipe: WorkstationRecipe
    drums: PatternRecipe
    harmony: HarmonyRecipe
    melody: MelodyRecipe


def _resolve(source: Path, value: object, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"workstation recipe requires {label}")
    path = (source.parent / value).resolve()
    if not path.is_file():
        raise ValueError(f"workstation {label} does not exist: {path}")
    return path


def load_recipe(path: Path) -> LoadedWorkstationRecipe:
    path = path.resolve()
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    required = ("schema_version", "id", "name", "drums", "harmony", "melody", "programs")
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"workstation recipe is missing: {', '.join(missing)}")
    if data["schema_version"] != 1:
        raise ValueError("workstation recipe requires schema_version=1")
    programs = data["programs"]
    required_programs = ("drums", "bass", "chords", "melody")
    if not isinstance(programs, dict) or any(
        not isinstance(programs.get(role), str) or not programs[role].strip()
        for role in required_programs
    ):
        raise ValueError("workstation programs must name drums, bass, chords, and melody")
    drum_path = _resolve(path, data["drums"], "drums")
    harmony_path = _resolve(path, data["harmony"], "harmony")
    melody_path = _resolve(path, data["melody"], "melody")
    recipe = WorkstationRecipe(
        1,
        str(data["id"]),
        str(data["name"]),
        str(path),
        str(drum_path),
        str(harmony_path),
        str(melody_path),
        {role: programs[role] for role in required_programs},
    )
    loaded = LoadedWorkstationRecipe(
        recipe,
        load_drums(drum_path),
        load_harmony(harmony_path),
        load_melody(melody_path),
    )
    if (loaded.harmony.key, loaded.harmony.scale) != (loaded.melody.key, loaded.melody.scale):
        raise ValueError("workstation harmony and melody must use the same key and scale")
    if (loaded.harmony.bars, loaded.harmony.beats_per_bar) != (
        loaded.melody.bars,
        loaded.melody.beats_per_bar,
    ):
        raise ValueError("workstation harmony and melody must use the same length and meter")
    if loaded.harmony.bars % loaded.drums.bars:
        raise ValueError("workstation drum recipe length must divide the harmony length")
    if loaded.harmony.beats_per_bar != 4:
        raise ValueError("semantic drum recipes currently require four beats per bar")
    return loaded


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generate_idea(
    loaded: LoadedWorkstationRecipe,
    program: ProgramModel,
    *,
    program_path: Path,
    seed: int,
    tempo: float,
    density: float = 1.0,
    layout: str | None = None,
    ppq: int = 480,
) -> WorkstationIdea:
    component_seeds = {"drums": seed, "harmony": seed + 1, "melody": seed + 2}
    harmony = generate_harmony(loaded.harmony, seed=component_seeds["harmony"], tempo=tempo, ppq=ppq)
    melody = generate_melody(loaded.melody, seed=component_seeds["melody"], tempo=tempo, ppq=ppq)
    drums = generate_drums(
        loaded.drums,
        program,
        seed=component_seeds["drums"],
        tempo=tempo,
        density=density,
        layout=layout,
        ppq=ppq,
    )
    return WorkstationIdea(
        1,
        loaded.recipe.id,
        loaded.recipe.name,
        seed,
        component_seeds,
        tempo,
        harmony.bars,
        harmony.beats_per_bar,
        ppq,
        program.name,
        str(program_path.resolve()),
        _sha256(program_path),
        layout,
        dict(loaded.recipe.programs),
        drums,
        harmony,
        melody,
    )


def _note(event, note_attribute: str = "midi_note", channel: int = 1, tick_offset: int = 0) -> MidiNote:
    return MidiNote(
        event.tick + tick_offset,
        event.duration_ticks,
        getattr(event, note_attribute),
        event.velocity,
        channel,
    )


def render_midi(
    idea: WorkstationIdea,
    loaded: LoadedWorkstationRecipe,
    *,
    midi_format: int = 1,
) -> bytes:
    drum_notes = []
    repetitions = idea.bars // idea.drums.bars
    pattern_ticks = idea.drums.bars * 4 * idea.ppq
    for repetition in range(repetitions):
        drum_notes.extend(
            _note(event, channel=loaded.drums.channel, tick_offset=repetition * pattern_ticks)
            for event in idea.drums.events
        )
    chord_notes = tuple(
        _note(event, channel=loaded.harmony.chord_channel)
        for event in idea.harmony.events
        if event.part == "chords"
    )
    bass_notes = tuple(
        _note(event, channel=loaded.harmony.bass_channel)
        for event in idea.harmony.events
        if event.part == "bass"
    )
    melody_notes = tuple(
        _note(event, channel=loaded.melody.channel) for event in idea.melody.events
    )
    tracks = (
        MidiTrack("Drums", tuple(drum_notes)),
        MidiTrack("Bass", bass_notes),
        MidiTrack("Chords", chord_notes),
        MidiTrack("Melody", melody_notes),
    )
    return render_standard_midi(
        tracks,
        tempo=idea.tempo,
        ppq=idea.ppq,
        end_tick=idea.bars * idea.beats_per_bar * idea.ppq,
        midi_format=midi_format,
        beats_per_bar=idea.beats_per_bar,
    )


def render_markdown(idea: WorkstationIdea, loaded: LoadedWorkstationRecipe) -> str:
    counts = {
        "drums": len(idea.drums.events) * (idea.bars // idea.drums.bars),
        "bass": sum(event.part == "bass" for event in idea.harmony.events),
        "chords": sum(event.part == "chords" for event in idea.harmony.events),
        "melody": len(idea.melody.events),
    }
    programs = idea.suggested_programs
    return f"""# {idea.name} — seed {idea.seed}

Software generation: **PASS**  
MPC hardware import/listening: **DEFERRED**

- Tempo: {idea.tempo:g} BPM
- Length: {idea.bars} bars
- Key: {idea.harmony.key} {idea.harmony.scale}
- Drum program used for note mapping: `{idea.drum_program}`
- Drum program file: `{idea.drum_program_file}`
- Drum program SHA-256: `{idea.drum_program_sha256}`
- Layout: `{idea.layout or 'source'}`

## MPC track assignment

1. Drums — channel {loaded.drums.channel} — `{programs['drums']}` — {counts['drums']} notes
2. Bass — channel {loaded.harmony.bass_channel} — `{programs['bass']}` — {counts['bass']} notes
3. Chords — channel {loaded.harmony.chord_channel} — `{programs['chords']}` — {counts['chords']} notes
4. Melody — channel {loaded.melody.channel} — `{programs['melody']}` — {counts['melody']} notes

Import the sibling `.mid` as a new sequence and assign each named MIDI track to
the suggested program. The JSON sibling is the reproducibility and debugging
record; it is not required by the MPC.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipe", type=Path)
    parser.add_argument("--program", type=Path, required=True)
    parser.add_argument("--preset", type=Path)
    parser.add_argument("--device", type=Path)
    parser.add_argument("--roles", type=Path)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--tempo", type=float, default=90.0)
    parser.add_argument("--density", type=float, default=1.0)
    parser.add_argument("--midi-format", type=int, choices=(0, 1), default=1)
    parser.add_argument("--output-prefix", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if bool(args.preset) != bool(args.device):
        parser.error("--preset and --device must be supplied together")
    loaded = load_recipe(args.recipe.expanduser().resolve())
    program_path = args.program.expanduser().resolve()
    overrides = load_role_overrides(args.roles.expanduser().resolve()) if args.roles else None
    program = from_xpm(program_path, overrides)
    layout_id = None
    if args.preset:
        preset = load_preset(args.preset.expanduser().resolve())
        plan = arrange(program, preset, load_device(args.device.expanduser().resolve()))
        program = apply_layout(program, plan)
        layout_id = preset.id
    idea = generate_idea(
        loaded,
        program,
        program_path=program_path,
        seed=args.seed,
        tempo=args.tempo,
        density=args.density,
        layout=layout_id,
    )
    prefix = args.output_prefix.expanduser().resolve()
    paths = (prefix.with_suffix(".mid"), prefix.with_suffix(".json"), prefix.with_suffix(".md"))
    if not args.force and any(path.exists() for path in paths):
        parser.error("output exists; pass --force to replace all bundle files")
    prefix.parent.mkdir(parents=True, exist_ok=True)
    paths[0].write_bytes(render_midi(idea, loaded, midi_format=args.midi_format))
    paths[1].write_text(json.dumps(idea.to_dict(), indent=2) + "\n", encoding="utf-8")
    paths[2].write_text(render_markdown(idea, loaded), encoding="utf-8")
    for path in paths:
        print(f"Wrote: {path}")
    print(f"Tracks: Drums, Bass, Chords, Melody; seed={idea.seed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
