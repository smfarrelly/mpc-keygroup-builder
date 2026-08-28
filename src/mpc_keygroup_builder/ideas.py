"""Generate deterministic, role-addressed Drum Program ideas and MIDI files."""

from __future__ import annotations

import argparse
import json
import random
import tomllib
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from .device import load_device
from .layout import LayoutPlan, arrange, load_preset
from .model import ProgramModel, Zone, from_xpm
from .midi_writer import MidiNote, MidiTrack, render_standard_midi
from .roles import load_role_overrides, role_matches


@dataclass(frozen=True)
class RoleEvents:
    role: str
    steps: tuple[int, ...]
    velocity: int
    probability: float = 1.0
    humanize_velocity: int = 0
    selection: str = "first"


@dataclass(frozen=True)
class PatternRecipe:
    schema_version: int
    id: str
    name: str
    bars: int
    steps_per_bar: int
    swing: float
    gate: float
    channel: int
    events: tuple[RoleEvents, ...]


@dataclass(frozen=True)
class DrumEvent:
    step: int
    tick: int
    duration_ticks: int
    role: str
    pad: int
    pad_label: str
    midi_note: int
    velocity: int
    sample: str


@dataclass(frozen=True)
class DrumIdea:
    schema_version: int
    recipe: str
    program: str
    layout: str | None
    seed: int
    tempo: float
    density: float
    bars: int
    steps_per_bar: int
    swing: float
    channel: int
    ppq: int
    events: tuple[DrumEvent, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def load_recipe(path: Path) -> PatternRecipe:
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    required = ("schema_version", "id", "name", "bars", "steps_per_bar", "events")
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"drum recipe is missing: {', '.join(missing)}")
    if data["schema_version"] != 1:
        raise ValueError("drum recipe requires schema_version=1")
    bars = data["bars"]
    steps_per_bar = data["steps_per_bar"]
    swing = data.get("swing", 0.5)
    gate = data.get("gate", 0.5)
    channel = data.get("channel", 10)
    if not isinstance(bars, int) or not 1 <= bars <= 64:
        raise ValueError("recipe bars must be 1..64")
    if not isinstance(steps_per_bar, int) or steps_per_bar < 4 or steps_per_bar % 4:
        raise ValueError("recipe steps_per_bar must be a multiple of four")
    if not isinstance(swing, (int, float)) or not 0.5 <= float(swing) <= 0.75:
        raise ValueError("recipe swing must be 0.5..0.75")
    if not isinstance(gate, (int, float)) or not 0 < float(gate) <= 1:
        raise ValueError("recipe gate must be greater than zero and at most one")
    if not isinstance(channel, int) or not 1 <= channel <= 16:
        raise ValueError("recipe channel must be 1..16")
    event_groups = []
    maximum_step = bars * steps_per_bar
    for index, item in enumerate(data["events"], 1):
        if not isinstance(item, dict):
            raise ValueError(f"events entry {index} must be a table")
        role = item.get("role")
        steps = item.get("steps")
        velocity = item.get("velocity", 100)
        probability = item.get("probability", 1.0)
        humanize = item.get("humanize_velocity", 0)
        selection = item.get("selection", "first")
        if not isinstance(role, str) or not role:
            raise ValueError(f"events entry {index} requires a role")
        if not isinstance(steps, list) or not steps or not all(isinstance(step, int) for step in steps):
            raise ValueError(f"events entry {index} steps must be non-empty integers")
        if any(not 0 <= step < maximum_step for step in steps):
            raise ValueError(f"events entry {index} step is outside the pattern")
        if len(steps) != len(set(steps)):
            raise ValueError(f"events entry {index} contains duplicate steps")
        if not isinstance(velocity, int) or not 1 <= velocity <= 127:
            raise ValueError(f"events entry {index} velocity must be 1..127")
        if not isinstance(probability, (int, float)) or not 0 <= float(probability) <= 1:
            raise ValueError(f"events entry {index} probability must be 0..1")
        if not isinstance(humanize, int) or not 0 <= humanize <= 63:
            raise ValueError(f"events entry {index} humanize_velocity must be 0..63")
        if selection not in {"first", "cycle", "random"}:
            raise ValueError(f"events entry {index} has invalid selection")
        event_groups.append(
            RoleEvents(
                role,
                tuple(steps),
                velocity,
                float(probability),
                humanize,
                selection,
            )
        )
    return PatternRecipe(
        1,
        data["id"],
        data["name"],
        bars,
        steps_per_bar,
        float(swing),
        float(gate),
        channel,
        tuple(event_groups),
    )


def apply_layout(program: ProgramModel, plan: LayoutPlan) -> ProgramModel:
    """Resolve source sound identities onto destination pads and MIDI notes."""
    if program.kind != "drum":
        raise ValueError("role-addressed layout requires a Drum Program")
    by_index = {zone.index: zone for zone in program.zones}
    midi_by_pad = program.pad_note_map or {
        zone.pad: zone.midi_note for zone in program.zones if zone.pad is not None
    }
    zones = []
    for assignment in plan.assignments:
        source = by_index[assignment.source_index]
        zones.append(
            replace(
                source,
                index=assignment.slot,
                pad=assignment.slot,
                midi_note=midi_by_pad.get(assignment.slot),
            )
        )
    return ProgramModel(
        program.schema_version,
        program.name,
        program.kind,
        tuple(zones),
        program.source_format,
        program.source_path,
        {**program.provenance, "layout": plan.preset},
        dict(program.pad_note_map),
    )


def _sample(zone: Zone) -> str:
    return zone.layers[0].sample if zone.layers else ""


def _label(pad: int) -> str:
    return f"{chr(ord('A') + (pad - 1) // 16)}{(pad - 1) % 16 + 1:02d}"


def generate_idea(
    recipe: PatternRecipe,
    program: ProgramModel,
    *,
    seed: int,
    tempo: float,
    density: float = 1.0,
    layout: str | None = None,
    ppq: int = 480,
) -> DrumIdea:
    if program.kind != "drum":
        raise ValueError("drum ideas require a Drum Program")
    if not 20 <= tempo <= 300:
        raise ValueError("tempo must be 20..300 BPM")
    if not 0 <= density <= 2:
        raise ValueError("density must be 0..2")
    if ppq < 24 or ppq % 4:
        raise ValueError("PPQ must be at least 24 and divisible by four")
    rng = random.Random(seed)
    step_ticks = ppq * 4 // recipe.steps_per_bar
    events = []
    for group in recipe.events:
        matches = sorted(
            (zone for zone in program.zones if role_matches(zone.role, group.role)),
            key=lambda zone: (_sample(zone).casefold(), zone.index),
        )
        if not matches:
            raise ValueError(f"program has no zone for required role: {group.role}")
        missing_midi = [zone for zone in matches if zone.pad is None or zone.midi_note is None]
        if missing_midi:
            raise ValueError(f"program has no PadNoteMap MIDI note for role: {group.role}")
        probability = min(1.0, group.probability * density)
        occurrence = 0
        for step in group.steps:
            if rng.random() >= probability:
                continue
            if group.selection == "first":
                zone = matches[0]
            elif group.selection == "cycle":
                zone = matches[occurrence % len(matches)]
            else:
                zone = matches[rng.randrange(len(matches))]
            occurrence += 1
            velocity = group.velocity
            if group.humanize_velocity:
                velocity += rng.randint(-group.humanize_velocity, group.humanize_velocity)
            velocity = max(1, min(127, velocity))
            swing_delay = (
                round(step_ticks * (2 * recipe.swing - 1)) if step % 2 else 0
            )
            tick = step * step_ticks + swing_delay
            duration = max(1, round(step_ticks * recipe.gate))
            events.append(
                DrumEvent(
                    step,
                    tick,
                    duration,
                    zone.role,
                    int(zone.pad),
                    _label(int(zone.pad)),
                    int(zone.midi_note),
                    velocity,
                    _sample(zone),
                )
            )
    events.sort(key=lambda item: (item.tick, item.midi_note, item.role))
    return DrumIdea(
        1,
        recipe.id,
        program.name,
        layout,
        seed,
        tempo,
        density,
        recipe.bars,
        recipe.steps_per_bar,
        recipe.swing,
        recipe.channel,
        ppq,
        tuple(events),
    )


def render_midi(idea: DrumIdea, *, midi_format: int = 1) -> bytes:
    end_tick = idea.bars * 4 * idea.ppq
    notes = tuple(
        MidiNote(
            event.tick,
            event.duration_ticks,
            event.midi_note,
            event.velocity,
            idea.channel,
        )
        for event in idea.events
    )
    return render_standard_midi(
        (MidiTrack(f"{idea.recipe} seed {idea.seed}", notes),),
        tempo=idea.tempo,
        ppq=idea.ppq,
        end_tick=end_tick,
        midi_format=midi_format,
    )


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
    parser.add_argument(
        "--midi-format",
        type=int,
        choices=(0, 1),
        default=1,
        help="Standard MIDI file format (default: 1 for MPC standalone compatibility)",
    )
    parser.add_argument("--output-prefix", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if bool(args.preset) != bool(args.device):
        parser.error("--preset and --device must be supplied together")
    overrides = load_role_overrides(args.roles.expanduser().resolve()) if args.roles else None
    program = from_xpm(args.program.expanduser().resolve(), overrides)
    layout_id = None
    if args.preset:
        preset = load_preset(args.preset.expanduser().resolve())
        device = load_device(args.device.expanduser().resolve())
        plan = arrange(program, preset, device)
        program = apply_layout(program, plan)
        layout_id = preset.id
    idea = generate_idea(
        load_recipe(args.recipe.expanduser().resolve()),
        program,
        seed=args.seed,
        tempo=args.tempo,
        density=args.density,
        layout=layout_id,
    )
    prefix = args.output_prefix.expanduser().resolve()
    json_path = prefix.with_suffix(".json")
    midi_path = prefix.with_suffix(".mid")
    if not args.force and (json_path.exists() or midi_path.exists()):
        parser.error("output exists; pass --force to replace both files")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(idea.to_dict(), indent=2) + "\n", encoding="utf-8")
    midi_path.write_bytes(render_midi(idea, midi_format=args.midi_format))
    print(f"Wrote: {json_path}")
    print(f"Wrote: {midi_path}")
    print(f"Events: {len(idea.events)}; seed={idea.seed}; layout={idea.layout or 'source'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
