"""Derive traceable Main, variation, breakdown, build, and outro MIDI sections."""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from .device import load_device
from .ideas import apply_layout
from .layout import arrange, load_preset
from .midi_writer import MidiNote, MidiTrack, render_standard_midi
from .model import from_xpm
from .roles import load_role_overrides
from .workstation import (
    LoadedWorkstationRecipe,
    WorkstationIdea,
    generate_idea as generate_workstation,
    load_recipe as load_workstation,
)


TRACK_ORDER = ("drums", "bass", "chords", "melody")


@dataclass(frozen=True)
class ArrangedEvent:
    source_id: str
    track: str
    role: str | None
    tick: int
    duration_ticks: int
    midi_note: int
    velocity: int
    channel: int
    action: str


@dataclass(frozen=True)
class ArrangementSection:
    id: str
    name: str
    purpose: str
    events: tuple[ArrangedEvent, ...]
    omitted_source_ids: tuple[str, ...]


@dataclass(frozen=True)
class ArrangementIdea:
    schema_version: int
    seed: int
    arrangement_seed: int
    mutation: float
    locked_tracks: tuple[str, ...]
    base: WorkstationIdea
    sections: tuple[ArrangementSection, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def _flatten(idea: WorkstationIdea, loaded: LoadedWorkstationRecipe) -> tuple[ArrangedEvent, ...]:
    events = []
    pattern_ticks = idea.drums.bars * 4 * idea.ppq
    repetitions = idea.bars // idea.drums.bars
    for repetition in range(repetitions):
        for index, event in enumerate(idea.drums.events):
            events.append(
                ArrangedEvent(
                    f"drums:{repetition}:{index}",
                    "drums",
                    event.role,
                    event.tick + repetition * pattern_ticks,
                    event.duration_ticks,
                    event.midi_note,
                    event.velocity,
                    loaded.drums.channel,
                    "source",
                )
            )
    for part, channel in (
        ("bass", loaded.harmony.bass_channel),
        ("chords", loaded.harmony.chord_channel),
    ):
        part_events = [event for event in idea.harmony.events if event.part == part]
        for index, event in enumerate(part_events):
            events.append(
                ArrangedEvent(
                    f"{part}:{index}", part, None, event.tick, event.duration_ticks,
                    event.midi_note, event.velocity, channel, "source",
                )
            )
    for index, event in enumerate(idea.melody.events):
        events.append(
            ArrangedEvent(
                f"melody:{index}", "melody", None, event.tick, event.duration_ticks,
                event.midi_note, event.velocity, loaded.melody.channel, "source",
            )
        )
    events.sort(key=lambda event: (event.tick, TRACK_ORDER.index(event.track), event.midi_note))
    return tuple(events)


def _section(
    section_id: str,
    name: str,
    purpose: str,
    base: tuple[ArrangedEvent, ...],
    events: list[ArrangedEvent],
) -> ArrangementSection:
    retained = {event.source_id for event in events}
    return ArrangementSection(
        section_id,
        name,
        purpose,
        tuple(sorted(events, key=lambda event: (event.tick, TRACK_ORDER.index(event.track), event.midi_note))),
        tuple(event.source_id for event in base if event.source_id not in retained),
    )


def arrange_idea(
    idea: WorkstationIdea,
    loaded: LoadedWorkstationRecipe,
    *,
    arrangement_seed: int,
    mutation: float = 0.2,
    locked_tracks: tuple[str, ...] = (),
) -> ArrangementIdea:
    if not 0 <= mutation <= 1:
        raise ValueError("mutation must be 0..1")
    unknown = sorted(set(locked_tracks) - set(TRACK_ORDER))
    if unknown:
        raise ValueError(f"unknown locked track: {', '.join(unknown)}")
    if len(locked_tracks) != len(set(locked_tracks)):
        raise ValueError("locked tracks must be unique")
    locked = set(locked_tracks)
    base = _flatten(idea, loaded)
    main = _section("main", "Main", "unaltered source idea", base, list(base))

    rng = random.Random(arrangement_seed)
    eligible = [index for index, event in enumerate(base) if event.track not in locked]
    mutate_count = round(len(eligible) * mutation)
    if mutation and eligible:
        mutate_count = max(1, mutate_count)
    selected = set(rng.sample(eligible, mutate_count)) if mutate_count else set()
    main_b_events = []
    for index, event in enumerate(base):
        if index not in selected:
            main_b_events.append(event)
            continue
        amount = rng.randint(6, 18)
        direction = rng.choice((-1, 1))
        velocity = max(1, min(127, event.velocity + direction * amount))
        if velocity == event.velocity:
            velocity = max(1, min(127, event.velocity - direction * amount))
        action = "velocity-up" if velocity > event.velocity else "velocity-down"
        main_b_events.append(replace(event, velocity=velocity, action=action))
    main_b = _section(
        "main-b", "Main B", f"{mutation:.0%} seeded velocity mutation", base, main_b_events
    )

    breakdown_events = []
    counters = {track: 0 for track in TRACK_ORDER}
    for event in base:
        counter = counters[event.track]
        counters[event.track] += 1
        keep = event.track in locked or event.track == "chords"
        if event.track == "drums":
            keep = keep or bool(event.role and event.role.startswith(("kick", "snare")))
        elif event.track == "bass":
            keep = keep or event.tick % idea.ppq == 0
        elif event.track == "melody":
            keep = keep or counter % 2 == 0
        if keep:
            breakdown_events.append(
                event if event.track in locked else replace(event, action="breakdown-keep")
            )
    breakdown = _section(
        "breakdown", "Breakdown", "reduced rhythm with sustained harmonic identity",
        base, breakdown_events,
    )

    end_tick = idea.bars * idea.beats_per_bar * idea.ppq
    build_events = []
    for event in base:
        if event.track in locked:
            build_events.append(event)
            continue
        progress = event.tick / max(1, end_tick - 1)
        offset = round(-16 + progress * 28)
        velocity = max(1, min(127, event.velocity + offset))
        build_events.append(replace(event, velocity=velocity, action="build-ramp"))
    build = _section(
        "build", "Build", "velocity ramp while preserving notes and timing", base, build_events
    )

    cutoff = end_tick // 2
    outro_events = [
        event if event.track in locked else replace(event, action="outro-first-half")
        for event in base
        if event.track in locked or event.tick < cutoff
    ]
    outro = _section(
        "outro", "Outro", "first-half reprise followed by deliberate space", base, outro_events
    )
    return ArrangementIdea(
        1, idea.seed, arrangement_seed, mutation, tuple(locked_tracks), idea,
        (main, main_b, breakdown, build, outro),
    )


def render_section(section: ArrangementSection, arrangement: ArrangementIdea) -> bytes:
    tracks = []
    for track in TRACK_ORDER:
        notes = tuple(
            MidiNote(
                event.tick, event.duration_ticks, event.midi_note, event.velocity, event.channel
            )
            for event in section.events
            if event.track == track
        )
        tracks.append(MidiTrack(track.title(), notes))
    idea = arrangement.base
    return render_standard_midi(
        tuple(tracks), tempo=idea.tempo, ppq=idea.ppq,
        end_tick=idea.bars * idea.beats_per_bar * idea.ppq,
        beats_per_bar=idea.beats_per_bar,
    )


def render_markdown(arrangement: ArrangementIdea) -> str:
    lines = [
        f"# {arrangement.base.name} arrangement — seed {arrangement.seed}",
        "",
        "Software generation: **PASS**  ",
        "MPC hardware import/listening: **DEFERRED**",
        "",
        f"- Arrangement seed: {arrangement.arrangement_seed}",
        f"- Main B mutation: {arrangement.mutation:.0%} of unlocked events",
        f"- Locked tracks: {', '.join(arrangement.locked_tracks) or 'none'}",
        "",
        "## Sequence files",
        "",
    ]
    for section in arrangement.sections:
        counts = ", ".join(
            f"{track}={sum(event.track == track for event in section.events)}"
            for track in TRACK_ORDER
        )
        lines.append(
            f"- `{section.id}.mid` — {section.name}: {section.purpose}; {counts}; "
            f"omitted={len(section.omitted_source_ids)}"
        )
    lines.extend((
        "",
        "Each MIDI file is a separate four-track sequence candidate. Import them",
        "individually and assign Drums, Bass, Chords, and Melody to the programs",
        "listed in the sibling JSON's `base.suggested_programs` object.",
        "The JSON retains the complete source idea, stable source IDs, mutations,",
        "and omitted IDs, making every derived section auditable and reversible.",
        "",
    ))
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipe", type=Path)
    parser.add_argument("--program", type=Path, required=True)
    parser.add_argument("--preset", type=Path)
    parser.add_argument("--device", type=Path)
    parser.add_argument("--roles", type=Path)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--arrangement-seed", type=int)
    parser.add_argument("--tempo", type=float, default=90.0)
    parser.add_argument("--density", type=float, default=1.0)
    parser.add_argument("--mutation", type=float, default=0.2)
    parser.add_argument("--lock-track", action="append", choices=TRACK_ORDER, default=[])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    output = args.output_dir.expanduser().resolve()
    expected = [output / "arrangement.json", output / "README.md"] + [
        output / f"{section}.mid" for section in ("main", "main-b", "breakdown", "build", "outro")
    ]
    if output.exists() and any(output.iterdir()) and not args.force:
        parser.error("output directory is not empty; pass --force to replace known arrangement files")
    if args.force and output.exists():
        unexpected = [path for path in output.iterdir() if path not in expected]
        if unexpected:
            parser.error(f"refusing --force with unexpected output: {unexpected[0].name}")
    if bool(args.preset) != bool(args.device):
        parser.error("--preset and --device must be supplied together")
    loaded = load_workstation(args.recipe.expanduser().resolve())
    program_path = args.program.expanduser().resolve()
    overrides = load_role_overrides(args.roles.expanduser().resolve()) if args.roles else None
    program = from_xpm(program_path, overrides)
    layout_id = None
    if args.preset:
        preset = load_preset(args.preset.expanduser().resolve())
        program = apply_layout(
            program,
            arrange(program, preset, load_device(args.device.expanduser().resolve())),
        )
        layout_id = preset.id
    base = generate_workstation(
        loaded, program, program_path=program_path, seed=args.seed,
        tempo=args.tempo, density=args.density, layout=layout_id,
    )
    result = arrange_idea(
        base, loaded,
        arrangement_seed=args.arrangement_seed if args.arrangement_seed is not None else args.seed + 1000,
        mutation=args.mutation,
        locked_tracks=tuple(args.lock_track),
    )
    output.mkdir(parents=True, exist_ok=True)
    (output / "arrangement.json").write_text(
        json.dumps(result.to_dict(), indent=2) + "\n", encoding="utf-8"
    )
    (output / "README.md").write_text(render_markdown(result), encoding="utf-8")
    for section in result.sections:
        (output / f"{section.id}.mid").write_bytes(render_section(section, result))
    print(f"Wrote: {output}")
    print("Sequences: Main, Main B, Breakdown, Build, Outro")
    print(f"Source events: {len(result.sections[0].events)}; mutation={result.mutation:.0%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
