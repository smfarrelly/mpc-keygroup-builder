"""Generate, score, and package a multi-family wave of workstation ideas."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any

from . import arrangement, portable_demo, workstation
from .creative_review import render_html
from .model import ProgramModel, from_xpm
from .recipe_audit import audit
from .roles import role_matches
from .showcase import COMPOSITIONS


DEFAULTS = {
    item.id: {"tempo": item.tempo, "density": item.density, "mutation": item.mutation}
    for item in COMPOSITIONS
}
TRACKS = ("drums", "bass", "chords", "melody")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _family(identifier: str) -> str:
    return identifier.removesuffix("-scratchpad")


def _copy_recipes(recipe_root: Path, staging: Path, report: dict[str, Any]) -> None:
    for item in report["files"]:
        source = recipe_root / item["path"]
        target = staging / "Recipes" / item["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _adapt_program(program: ProgramModel, loaded: workstation.LoadedWorkstationRecipe) -> ProgramModel:
    zones = list(program.zones)
    requested = {event.role for event in loaded.drums.events}
    for role in sorted(requested):
        if any(role_matches(zone.role, role) for zone in zones):
            continue
        fallback = "cymbal" if role == "fx" else None
        index = next(
            (i for i, zone in enumerate(zones) if fallback and role_matches(zone.role, fallback)),
            None,
        )
        if index is None:
            raise ValueError(f"Drum Program cannot resolve recipe role: {role}")
        zones[index] = replace(zones[index], role=role)
    return replace(program, zones=tuple(zones))


def _structural_digest(idea: workstation.WorkstationIdea) -> str:
    tracks = {
        "drums": [
            (event.tick, event.duration_ticks, event.midi_note, event.role)
            for event in idea.drums.events
        ],
        "harmony": [
            (event.part, event.tick, event.duration_ticks, event.midi_note)
            for event in idea.harmony.events
        ],
        "melody": [
            (event.tick, event.duration_ticks, event.midi_note)
            for event in idea.melody.events
        ],
    }
    return hashlib.sha256(
        json.dumps(tracks, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _score(
    idea: workstation.WorkstationIdea,
    arranged: arrangement.ArrangementIdea,
) -> tuple[dict[str, float], dict[str, Any]]:
    main = arranged.sections[0].events
    drum_events = [event for event in main if event.track == "drums"]
    melody_events = list(idea.melody.events)
    chord_decisions = list(idea.harmony.decisions)
    events_per_bar = len(main) / idea.bars
    sixteenth = max(1, idea.ppq // 4)
    syncopated = sum(
        event.tick % (idea.ppq // 2) == sixteenth for event in drum_events
    )
    syncopation = 100 * syncopated / max(1, len(drum_events))
    melody_notes = [event.midi_note for event in melody_events]
    melody_range = max(melody_notes) - min(melody_notes) if melody_notes else 0
    repeated = sum(event.variation == "repeat" for event in melody_events)
    repetition = 100 * repeated / max(1, len(melody_events))
    movements = []
    for before, after in zip(chord_decisions, chord_decisions[1:]):
        movements.append(sum(abs(a - b) for a, b in zip(before.notes, after.notes)))
    harmonic_movement = sum(movements) / len(movements) if movements else 0.0
    base_count = max(1, len(main))
    contrasts = []
    for section in arranged.sections[1:]:
        changed = len(section.omitted_source_ids) + sum(
            event.action != "source" for event in section.events
        )
        contrasts.append(min(100.0, 100 * changed / base_count))
    arrangement_contrast = sum(contrasts) / len(contrasts) if contrasts else 0.0
    roles = len({event.role for event in drum_events if event.role})
    metrics = {
        "events_per_bar": round(events_per_bar, 2),
        "syncopation_percent": round(syncopation, 2),
        "melody_range_semitones": melody_range,
        "melody_repetition_percent": round(repetition, 2),
        "harmonic_movement_semitones": round(harmonic_movement, 2),
        "arrangement_contrast_percent": round(arrangement_contrast, 2),
        "drum_role_count": roles,
    }
    components = {
        "event_density": min(100.0, events_per_bar / 24 * 100),
        "syncopation": syncopation,
        "melody_range": min(100.0, melody_range / 24 * 100),
        "melody_variation": 100 - repetition,
        "harmonic_movement": min(100.0, harmonic_movement / 12 * 100),
        "arrangement_contrast": arrangement_contrast,
        "drum_role_coverage": min(100.0, roles / 8 * 100),
    }
    score = round(sum(components.values()) / len(components), 2)
    return metrics, {
        "exploration_score": score,
        "components": {key: round(value, 2) for key, value in components.items()},
        "meaning": "observable complexity and variation for review ordering; not musical quality",
    }


def _preview(arranged: arrangement.ArrangementIdea) -> list[dict[str, Any]]:
    return [
        {
            "track": event.track,
            "role": event.role,
            "tick": event.tick,
            "duration": event.duration_ticks,
            "note": event.midi_note,
            "velocity": event.velocity,
        }
        for event in arranged.sections[0].events
    ]


def _candidate_csv(candidates: list[dict[str, Any]]) -> str:
    stream = io.StringIO()
    fields = (
        "rank", "id", "family", "seed", "tempo", "key", "scale",
        "exploration_score", "events_per_bar", "syncopation_percent",
        "melody_range_semitones", "melody_repetition_percent",
        "harmonic_movement_semitones", "arrangement_contrast_percent",
        "drum_role_count", "idea_midi", "sequences", "hardware_status",
    )
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for item in candidates:
        writer.writerow({
            "rank": item["rank"], "id": item["id"], "family": item["family"],
            "seed": item["seed"], "tempo": item["tempo"], "key": item["key"],
            "scale": item["scale"], "exploration_score": item["score"]["exploration_score"],
            **item["metrics"], "idea_midi": item["paths"]["idea_midi"],
            "sequences": item["paths"]["sequences"], "hardware_status": "deferred",
        })
    return stream.getvalue()


def _readme(report: dict[str, Any]) -> str:
    summary = report["summary"]
    return f"""# {report['name']}

Software generation, recipe validation, and duplicate checks: **PASS**

MPC import, listening, and musical selection: **DEFERRED**

This wave contains {summary['candidates']} unique candidates across
{summary['families']} recipe families. Open `review.html` to filter, compare,
shortlist, and annotate them without installing software. Browser results stay
local until explicitly exported as JSON or CSV.

The exploration score averages seven observable dimensions: event density,
syncopation, melody range, melody variation, harmonic movement, arrangement
contrast, and Drum-role coverage. It orders review; it does not predict taste
or certify musical quality.

Start MPC testing with `HARDWARE_CHECKLIST.md`. `candidate-catalog.csv` is the
flat index, `wave.json` is complete evidence, and `checksums.json` verifies the
bundle. Recipes are preserved under `Recipes/`.
"""


def _hardware_checklist(report: dict[str, Any], folder_name: str) -> str:
    lines = [
        f"# {report['name']} — hardware checklist", "",
        "Every result below is pending human testing on MPC hardware.", "",
        f"Copy the complete `{folder_name}` folder to the SD card. MPC browser paths",
        f"then begin at `/{folder_name}/Candidates/`.", "",
    ]
    if report["program"]["portable"]:
        lines.extend((
            f"Load `/{folder_name}/Instrument/FG Portable Cross Kit.xpm` as the Drum Program.",
            "Assign locally installed Keygroups/plugins using each candidate's suggested programs.",
            "",
        ))
    else:
        lines.extend((
            f"Drum Program source: `{report['program']['source']}`.",
            "Deploy that program and its samples separately; this wave never copies licensed audio.",
            "",
        ))
    for item in report["candidates"]:
        base = f"/{folder_name}/{item['paths']['root']}"
        lines.extend((
            f"## Rank {item['rank']} — {item['name']} / seed {item['seed']}", "",
            f"- [ ] Import `{base}/idea.mid` and confirm four named tracks.",
            f"- [ ] Import `{base}/Sequences/main.mid` and one contrasting section.",
            "- [ ] Assign the suggested or equivalent Drum, Bass, Chords, and Melody sounds.",
            "- [ ] Save/reload and confirm timing, routing, and sound assignments persist.",
            "- [ ] Record keep, provisional, or reject in `review.html`.",
            "", "Verdict: [ ] pass  [ ] warn  [ ] fail", "Notes:", "",
        ))
    return "\n".join(lines).rstrip() + "\n"


def _copy_manifest(root: Path) -> str:
    lines = [
        "# Relative files included in this review bundle.",
        "# Copy the containing folder as a unit; do not flatten it.",
    ]
    names = {str(path.relative_to(root)) for path in root.rglob("*") if path.is_file()}
    names.update({"COPY_MANIFEST.txt", "checksums.json"})
    lines.extend(sorted(names))
    return "\n".join(lines) + "\n"


def build_wave(
    recipe_root: Path,
    output: Path,
    *,
    families: tuple[str, ...] | None = None,
    seeds_per_family: int = 4,
    seed_start: int = 1,
    program_path: Path | None = None,
    tempo: float | None = None,
    density: float | None = None,
    mutation: float | None = None,
    locked_tracks: tuple[str, ...] = (),
    name: str = "MPC Creative Wave",
) -> dict[str, Any]:
    recipe_root = recipe_root.expanduser().resolve()
    output = output.expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"creative wave output already exists: {output}")
    if not 1 <= seeds_per_family <= 32:
        raise ValueError("seeds_per_family must be 1..32")
    if seed_start < 0:
        raise ValueError("seed_start must be zero or greater")
    if tempo is not None and not 20 <= tempo <= 300:
        raise ValueError("tempo must be 20..300 BPM")
    if density is not None and not 0 <= density <= 1:
        raise ValueError("density must be 0..1")
    if mutation is not None and not 0 <= mutation <= 1:
        raise ValueError("mutation must be 0..1")
    if len(locked_tracks) != len(set(locked_tracks)) or set(locked_tracks) - set(TRACKS):
        raise ValueError("locked_tracks must be unique drums, bass, chords, or melody values")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be a non-empty string")
    name = name.strip()
    source_audit = audit(recipe_root)
    if source_audit["status"] != "pass":
        raise ValueError(
            f"recipe audit failed with {source_audit['summary']['errors']} errors; "
            "run mpc-recipe-audit for details"
        )
    workstation_rows = [item for item in source_audit["files"] if item["type"] == "workstation"]
    available: dict[str, dict[str, Any]] = {}
    for item in workstation_rows:
        family = _family(item["id"])
        if family in available:
            raise ValueError(f"multiple workstation recipes resolve to family: {family}")
        available[family] = item
    selected = list(available) if families is None else list(families)
    if not selected or len(selected) != len(set(selected)):
        raise ValueError("families must be non-empty and unique")
    unknown = sorted(set(selected) - set(available))
    if unknown:
        raise ValueError("unknown recipe family: " + ", ".join(unknown))
    if len(selected) * seeds_per_family > 128:
        raise ValueError("creative wave is limited to 128 candidates")

    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        _copy_recipes(recipe_root, staging, source_audit)
        portable = program_path is None
        if portable:
            fixture = staging / ".portable-fixture"
            portable_demo.build_demo(fixture)
            shutil.copytree(fixture / "Cross Kit", staging / "Instrument")
            shutil.rmtree(fixture)
            active_program_path = staging / "Instrument/FG Portable Cross Kit.xpm"
            program_reference = "Instrument/FG Portable Cross Kit.xpm"
            (staging / "LICENSE-GENERATED-AUDIO.txt").write_text(
                "Generated WAV audio in Instrument/ is dedicated to the public domain under CC0 1.0.\n"
                "Repository software remains under the MIT License.\n",
                encoding="utf-8",
            )
        else:
            active_program_path = program_path.expanduser().resolve()
            if not active_program_path.is_file():
                raise FileNotFoundError(active_program_path)
            program_reference = str(active_program_path)
        source_program = from_xpm(active_program_path)
        candidates: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []
        fingerprints: dict[str, str] = {}
        for family in selected:
            recipe_relative = available[family]["path"]
            loaded = workstation.load_recipe(staging / "Recipes" / recipe_relative)
            program = _adapt_program(source_program, loaded)
            settings = DEFAULTS.get(family, {"tempo": 90.0, "density": 1.0, "mutation": 0.2})
            family_tempo = float(tempo if tempo is not None else settings["tempo"])
            family_density = float(density if density is not None else settings["density"])
            family_mutation = float(mutation if mutation is not None else settings["mutation"])
            accepted = 0
            seed = seed_start
            attempts = 0
            while accepted < seeds_per_family:
                attempts += 1
                if attempts > seeds_per_family + 128:
                    raise ValueError(f"could not find {seeds_per_family} unique candidates for {family}")
                idea = workstation.generate_idea(
                    loaded, program, program_path=active_program_path, seed=seed,
                    tempo=family_tempo, density=family_density,
                )
                fingerprint = _structural_digest(idea)
                if fingerprint in fingerprints:
                    skipped.append({
                        "family": family, "seed": seed, "reason": "structural-duplicate",
                        "matches": fingerprints[fingerprint], "fingerprint": fingerprint,
                    })
                    seed += 1
                    continue
                candidate_id = f"{family}-seed-{seed}"
                fingerprints[fingerprint] = candidate_id
                portable_idea = replace(idea, drum_program_file=program_reference)
                arranged = arrangement.arrange_idea(
                    portable_idea, loaded, arrangement_seed=seed + 1000,
                    mutation=family_mutation, locked_tracks=locked_tracks,
                )
                root_relative = f"Candidates/{family}/seed-{seed}"
                root = staging / root_relative
                sequences = root / "Sequences"
                sequences.mkdir(parents=True)
                (root / "idea.mid").write_bytes(workstation.render_midi(portable_idea, loaded))
                (root / "idea.json").write_text(
                    json.dumps(portable_idea.to_dict(), indent=2) + "\n", encoding="utf-8"
                )
                (root / "arrangement.json").write_text(
                    json.dumps(arranged.to_dict(), indent=2) + "\n", encoding="utf-8"
                )
                for section in arranged.sections:
                    (sequences / f"{section.id}.mid").write_bytes(
                        arrangement.render_section(section, arranged)
                    )
                metrics, score = _score(portable_idea, arranged)
                candidates.append({
                    "id": candidate_id, "family": family, "seed": seed,
                    "name": portable_idea.name, "tempo": portable_idea.tempo,
                    "key": portable_idea.harmony.key, "scale": portable_idea.harmony.scale,
                    "bars": portable_idea.bars, "structural_fingerprint": fingerprint,
                    "metrics": metrics, "score": score,
                    "suggested_programs": portable_idea.suggested_programs,
                    "paths": {
                        "root": root_relative,
                        "idea_midi": f"{root_relative}/idea.mid",
                        "sequences": f"{root_relative}/Sequences",
                        "evidence": f"{root_relative}/idea.json",
                    },
                    "preview": _preview(arranged), "hardware_status": "deferred",
                })
                accepted += 1
                seed += 1
        candidates.sort(key=lambda item: (-item["score"]["exploration_score"], item["family"], item["seed"]))
        for rank, item in enumerate(candidates, 1):
            item["rank"] = rank
        report = {
            "schema_version": 1, "kind": "mpc-workstation-wave", "name": name,
            "software_status": "pass", "hardware_status": "deferred",
            "ranking_policy": (
                "descending mean of seven normalized observable dimensions; ties by family and seed; "
                "not a musical-quality score"
            ),
            "settings": {
                "families": selected, "seeds_per_family": seeds_per_family,
                "seed_start": seed_start, "tempo_override": tempo,
                "density_override": density, "mutation_override": mutation,
                "locked_tracks": list(locked_tracks),
            },
            "program": {
                "portable": portable, "source": program_reference,
                "sha256": _sha256(active_program_path),
            },
            "recipe_audit": {
                "status": source_audit["status"], "summary": source_audit["summary"],
                "counts": source_audit["counts"],
            },
            "summary": {
                "families": len(selected), "candidates": len(candidates),
                "duplicates_skipped": len(skipped), "hardware_passes": 0,
            },
            "duplicates_skipped": skipped, "candidates": candidates,
        }
        (staging / "wave.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        (staging / "candidate-catalog.csv").write_text(
            _candidate_csv(candidates), encoding="utf-8"
        )
        (staging / "README.md").write_text(_readme(report), encoding="utf-8")
        (staging / "HARDWARE_CHECKLIST.md").write_text(
            _hardware_checklist(report, output.name), encoding="utf-8"
        )
        (staging / "review.html").write_text(render_html(report), encoding="utf-8")
        (staging / "COPY_MANIFEST.txt").write_text(_copy_manifest(staging), encoding="utf-8")
        checksums = {
            str(path.relative_to(staging)): _sha256(path)
            for path in sorted(staging.rglob("*"))
            if path.is_file() and path.name != "checksums.json"
        }
        (staging / "checksums.json").write_text(
            json.dumps(checksums, indent=2) + "\n", encoding="utf-8"
        )
        os.replace(staging, output)
        return report
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipe_root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--name", default="MPC Creative Wave")
    parser.add_argument("--families", default="all", help="all or comma-separated recipe family IDs")
    parser.add_argument("--seeds-per-family", type=int, default=4)
    parser.add_argument("--seed-start", type=int, default=1)
    parser.add_argument("--program", type=Path, help="existing Drum XPM; default is a generated CC0 kit")
    parser.add_argument("--tempo", type=float, help="override family tempos")
    parser.add_argument("--density", type=float, help="override family Drum density (0..1)")
    parser.add_argument("--mutation", type=float, help="override Main B mutation (0..1)")
    parser.add_argument("--lock-track", action="append", choices=TRACKS, default=[])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    families = None if args.families == "all" else tuple(
        value.strip() for value in args.families.split(",") if value.strip()
    )
    report = build_wave(
        args.recipe_root, args.output, families=families,
        seeds_per_family=args.seeds_per_family, seed_start=args.seed_start,
        program_path=args.program, tempo=args.tempo, density=args.density,
        mutation=args.mutation, locked_tracks=tuple(args.lock_track), name=args.name,
    )
    print(f"Wrote: {args.output.expanduser().resolve()}")
    print(
        f"PASS: {report['summary']['candidates']} unique candidates; "
        f"families={report['summary']['families']}; "
        f"duplicates skipped={report['summary']['duplicates_skipped']}"
    )
    print(f"Review: {args.output.expanduser().resolve() / 'review.html'}")
    print("Hardware/listening status: deferred")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
