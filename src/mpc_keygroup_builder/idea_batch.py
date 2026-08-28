"""Generate and evidence-rank a bounded batch of workstation idea seeds."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .device import load_device
from .ideas import apply_layout
from .layout import arrange, load_preset
from .model import from_xpm
from .roles import load_role_overrides
from .workstation import (
    WorkstationIdea,
    generate_idea,
    load_recipe,
    render_markdown,
    render_midi,
)


@dataclass(frozen=True)
class CandidateSummary:
    seed: int
    stem: str
    event_counts: dict[str, int]
    unique_drum_roles: int
    unique_bass_notes: int
    unique_chord_voicings: int
    unique_melody_notes: int
    melody_variations: int
    velocity_span: int
    evidence_diversity_score: float


@dataclass(frozen=True)
class IdeaBatch:
    schema_version: int
    recipe: str
    tempo: float
    seed_start: int
    count: int
    ranking_policy: str
    candidates: tuple[CandidateSummary, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def summarize(idea: WorkstationIdea) -> CandidateSummary:
    drums = len(idea.drums.events) * (idea.bars // idea.drums.bars)
    bass_events = [event for event in idea.harmony.events if event.part == "bass"]
    chord_events = [event for event in idea.harmony.events if event.part == "chords"]
    chord_voicings = {decision.notes for decision in idea.harmony.decisions}
    melody_variations = sum(event.variation != "repeat" for event in idea.melody.events)
    velocities = (
        [event.velocity for event in idea.drums.events]
        + [event.velocity for event in idea.harmony.events]
        + [event.velocity for event in idea.melody.events]
    )
    velocity_span = max(velocities) - min(velocities) if velocities else 0
    counts = {
        "drums": drums,
        "bass": len(bass_events),
        "chords": len(chord_events),
        "melody": len(idea.melody.events),
    }
    unique_drum_roles = len({event.role for event in idea.drums.events})
    unique_bass_notes = len({event.midi_note for event in bass_events})
    unique_chord_voicings = len(chord_voicings)
    unique_melody_notes = len({event.midi_note for event in idea.melody.events})
    score = round(
        unique_drum_roles * 4
        + unique_bass_notes * 1.5
        + unique_chord_voicings * 2
        + unique_melody_notes * 2
        + melody_variations
        + velocity_span / 10,
        2,
    )
    return CandidateSummary(
        idea.seed,
        f"seed-{idea.seed}",
        counts,
        unique_drum_roles,
        unique_bass_notes,
        unique_chord_voicings,
        unique_melody_notes,
        melody_variations,
        velocity_span,
        score,
    )


def build_batch(ideas: tuple[WorkstationIdea, ...]) -> IdeaBatch:
    if not ideas:
        raise ValueError("idea batch requires at least one candidate")
    recipe = ideas[0].recipe
    tempo = ideas[0].tempo
    if any(idea.recipe != recipe or idea.tempo != tempo for idea in ideas):
        raise ValueError("idea batch candidates must share recipe and tempo")
    summaries = sorted(
        (summarize(idea) for idea in ideas),
        key=lambda item: (-item.evidence_diversity_score, item.seed),
    )
    return IdeaBatch(
        1,
        recipe,
        tempo,
        min(idea.seed for idea in ideas),
        len(ideas),
        "descending measurable event diversity; tie by ascending seed; not a musical-quality score",
        tuple(summaries),
    )


def render_batch_markdown(batch: IdeaBatch) -> str:
    lines = [
        f"# {batch.recipe} seed batch",
        "",
        "Software generation: **PASS**  ",
        "MPC hardware import/listening: **DEFERRED**",
        "",
        f"- Tempo: {batch.tempo:g} BPM",
        f"- Seeds: {batch.seed_start}–{batch.seed_start + batch.count - 1}",
        f"- Ranking: {batch.ranking_policy}",
        "",
        "## Suggested inspection order",
        "",
    ]
    for rank, candidate in enumerate(batch.candidates, 1):
        counts = ", ".join(f"{key}={value}" for key, value in candidate.event_counts.items())
        lines.append(
            f"{rank}. `{candidate.stem}.mid` — diversity "
            f"{candidate.evidence_diversity_score:g}; {counts}; "
            f"melody variations={candidate.melody_variations}"
        )
    lines.extend((
        "",
        "The diversity score only prioritizes candidates that exercise more observable",
        "roles, pitches, voicings, variations, and velocity range. It does not claim",
        "that a higher-ranked seed sounds better. Listening remains the decision gate.",
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
    parser.add_argument("--seed-start", type=int, default=1)
    parser.add_argument("--count", type=int, default=4)
    parser.add_argument("--tempo", type=float, default=90.0)
    parser.add_argument("--density", type=float, default=1.0)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.count <= 128:
        parser.error("--count must be 1..128")
    if bool(args.preset) != bool(args.device):
        parser.error("--preset and --device must be supplied together")
    output = args.output_dir.expanduser().resolve()
    expected_names = {"index.json", "README.md"}
    for seed in range(args.seed_start, args.seed_start + args.count):
        expected_names.update({f"seed-{seed}.mid", f"seed-{seed}.json", f"seed-{seed}.md"})
    if output.exists() and any(output.iterdir()) and not args.force:
        parser.error("output directory is not empty; pass --force to replace known batch files")
    if args.force and output.exists():
        unexpected = [path for path in output.iterdir() if path.name not in expected_names]
        if unexpected:
            parser.error(f"refusing --force with unexpected output: {unexpected[0].name}")
    loaded = load_recipe(args.recipe.expanduser().resolve())
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
    ideas = tuple(
        generate_idea(
            loaded,
            program,
            program_path=program_path,
            seed=seed,
            tempo=args.tempo,
            density=args.density,
            layout=layout_id,
        )
        for seed in range(args.seed_start, args.seed_start + args.count)
    )
    batch = build_batch(ideas)
    output.mkdir(parents=True, exist_ok=True)
    for idea in ideas:
        prefix = output / f"seed-{idea.seed}"
        prefix.with_suffix(".mid").write_bytes(render_midi(idea, loaded))
        prefix.with_suffix(".json").write_text(
            json.dumps(idea.to_dict(), indent=2) + "\n", encoding="utf-8"
        )
        prefix.with_suffix(".md").write_text(render_markdown(idea, loaded), encoding="utf-8")
    (output / "index.json").write_text(
        json.dumps(batch.to_dict(), indent=2) + "\n", encoding="utf-8"
    )
    (output / "README.md").write_text(render_batch_markdown(batch), encoding="utf-8")
    print(f"Wrote: {output}")
    print(f"Candidates: {batch.count}; top seed={batch.candidates[0].seed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
