"""Build six deterministic, redistributable MPC composition evidence bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from dataclasses import asdict, dataclass, replace
from importlib import resources
from pathlib import Path

from . import arrangement, portable_demo, workstation
from .model import ProgramModel
from .model import from_xpm
from .roles import role_matches


RECIPE_FILES = (
    "drums/dusty-pocket.toml",
    "harmony/dusty-dorian.toml",
    "melody/dusty-answer.toml",
    "workstation/dusty-scratchpad.toml",
    "drums/sparse-weird.toml",
    "harmony/ambient-minor.toml",
    "melody/ambient-drift.toml",
    "workstation/ambient-scratchpad.toml",
    "drums/electro-grid.toml",
    "harmony/electro-minor.toml",
    "melody/electro-hook.toml",
    "workstation/electro-scratchpad.toml",
    "drums/funk-machine.toml",
    "harmony/funk-minor.toml",
    "melody/funk-call.toml",
    "workstation/funk-scratchpad.toml",
    "drums/house-foundation.toml",
    "harmony/house-minor.toml",
    "melody/house-spark.toml",
    "workstation/house-scratchpad.toml",
    "drums/texture-collage.toml",
    "harmony/strange-mixolydian.toml",
    "melody/odd-signal.toml",
    "workstation/weird-scratchpad.toml",
)


@dataclass(frozen=True)
class CompositionSpec:
    id: str
    recipe: str
    seed: int
    arrangement_seed: int
    tempo: float
    density: float
    mutation: float
    role_aliases: dict[str, str]


COMPOSITIONS = (
    CompositionSpec("dusty", "workstation/dusty-scratchpad.toml", 37, 1037, 92.0, 1.0, 0.20, {}),
    CompositionSpec("ambient", "workstation/ambient-scratchpad.toml", 83, 1083, 78.0, 0.82, 0.28, {"fx": "cymbal"}),
    CompositionSpec("electro", "workstation/electro-scratchpad.toml", 149, 1149, 118.0, 1.0, 0.18, {}),
    CompositionSpec("funk", "workstation/funk-scratchpad.toml", 211, 1211, 104.0, 1.0, 0.22, {}),
    CompositionSpec("house", "workstation/house-scratchpad.toml", 277, 1277, 124.0, 1.0, 0.16, {}),
    CompositionSpec("weird", "workstation/weird-scratchpad.toml", 331, 1331, 86.0, 0.90, 0.35, {"fx": "cymbal"}),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_recipes(destination: Path, recipe_root: Path | None) -> None:
    packaged = resources.files("mpc_keygroup_builder.data.showcase_recipes")
    for relative in RECIPE_FILES:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if recipe_root is None:
            target.write_text(packaged.joinpath(relative).read_text(encoding="utf-8"), encoding="utf-8")
        else:
            source = recipe_root / relative
            if not source.is_file():
                raise FileNotFoundError(f"showcase recipe is missing: {source}")
            shutil.copy2(source, target)


def _adapt_roles(program: ProgramModel, aliases: dict[str, str]) -> ProgramModel:
    zones = list(program.zones)
    for requested, available in aliases.items():
        if any(role_matches(zone.role, requested) for zone in zones):
            continue
        index = next(
            (number for number, zone in enumerate(zones) if role_matches(zone.role, available)),
            None,
        )
        if index is None:
            raise ValueError(f"showcase fixture has no role for alias {requested}={available}")
        zones[index] = replace(zones[index], role=requested)
    return replace(program, zones=tuple(zones))


def _composition_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(str(path.relative_to(root)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(_sha256(path)))
    return digest.hexdigest()


def _write_composition(
    staging: Path,
    recipes: Path,
    program_path: Path,
    source_program: ProgramModel,
    spec: CompositionSpec,
) -> dict:
    destination = staging / "Compositions" / spec.id
    sequences = destination / "Sequences"
    sequences.mkdir(parents=True)
    loaded = workstation.load_recipe(recipes / spec.recipe)
    program = _adapt_roles(source_program, spec.role_aliases)
    idea = workstation.generate_idea(
        loaded,
        program,
        program_path=program_path,
        seed=spec.seed,
        tempo=spec.tempo,
        density=spec.density,
    )
    idea = replace(idea, drum_program_file="Instrument/FG Portable Cross Kit.xpm")
    (destination / "idea.mid").write_bytes(workstation.render_midi(idea, loaded))
    (destination / "idea.json").write_text(
        json.dumps(idea.to_dict(), indent=2) + "\n", encoding="utf-8"
    )
    (destination / "README.md").write_text(
        workstation.render_markdown(idea, loaded), encoding="utf-8"
    )
    arranged = arrangement.arrange_idea(
        idea,
        loaded,
        arrangement_seed=spec.arrangement_seed,
        mutation=spec.mutation,
    )
    (destination / "arrangement.json").write_text(
        json.dumps(arranged.to_dict(), indent=2) + "\n", encoding="utf-8"
    )
    (destination / "ARRANGEMENT.md").write_text(
        arrangement.render_markdown(arranged), encoding="utf-8"
    )
    for section in arranged.sections:
        (sequences / f"{section.id}.mid").write_bytes(
            arrangement.render_section(section, arranged)
        )
    return {
        **asdict(spec),
        "name": idea.name,
        "key": idea.harmony.key,
        "scale": idea.harmony.scale,
        "bars": idea.bars,
        "tracks": ["Drums", "Bass", "Chords", "Melody"],
        "sections": [section.id for section in arranged.sections],
        "event_counts": {
            section.id: len(section.events) for section in arranged.sections
        },
        "suggested_programs": idea.suggested_programs,
        "hardware_status": "deferred",
        "digest": _composition_digest(destination),
    }


def _readme(compositions: list[dict]) -> str:
    lines = [
        "# MPC six-composition showcase",
        "",
        "Software generation and deterministic reproduction: **PASS**  ",
        "MPC import, sound selection, listening, and musical completion: **DEFERRED**",
        "",
        "This redistributable bundle demonstrates six contrasting four-part ideas",
        "using generated CC0 Drum audio. Each idea includes a complete MIDI file,",
        "five traceable arrangement sections, editable recipes, and JSON evidence.",
        "For fixtures that address a cymbal semantically as an FX hit, the alias is",
        "recorded explicitly in `showcase.json`.",
        "",
        "## Compositions",
        "",
    ]
    for item in compositions:
        lines.append(
            f"- **{item['name']}** (`Compositions/{item['id']}`) — "
            f"{item['tempo']:g} BPM, {item['key']} {item['scale']}, seed {item['seed']}; "
            f"digest `{item['digest']}`."
        )
    lines.extend(
        (
            "",
            "Start with `HARDWARE_CHECKLIST.md` when an MPC is available. The",
            "suggested program names reflect the maintained Scratchpad palette, but",
            "the MIDI files can be assigned to any suitable local sounds.",
            "",
        )
    )
    return "\n".join(lines)


def _hardware_checklist(compositions: list[dict]) -> str:
    lines = [
        "# Six-composition showcase — MPC checklist",
        "",
        "The bundle is software-verified. Every box below remains hardware-pending.",
        "",
        "## Shared instrument",
        "",
        "MPC browser path after copying the bundle: `Instrument/FG Portable Cross Kit.xpm`",
        "",
        "- [ ] Load the Drum Program and confirm all 16 Bank A pads sound.",
        "- [ ] Confirm colors and samples persist after save/reload.",
    ]
    for item in compositions:
        lines.extend(
            (
                "",
                f"## {item['name']}",
                "",
                f"Full idea: `Compositions/{item['id']}/idea.mid`",
                f"Sections: `Compositions/{item['id']}/Sequences/`",
                "",
                "- [ ] Import `idea.mid` and confirm four named musical tracks.",
                "- [ ] Assign the shared synthetic Drum Program to Drums.",
                "- [ ] Assign the suggested Bass, Chords, and Melody sounds or substitutes.",
                "- [ ] Import Main, Main B, Breakdown, Build, and Outro sequences.",
                "- [ ] Record listening notes and whether this deserves further development.",
                "",
                "Verdict: [ ] pass  [ ] warn  [ ] fail",
                "Notes:",
            )
        )
    return "\n".join(lines).rstrip() + "\n"


def build_showcase(
    output: Path,
    recipe_root: Path | None = None,
    families: tuple[str, ...] | None = None,
    seed_overrides: dict[str, int] | None = None,
) -> dict:
    output = output.expanduser().resolve()
    recipe_root = recipe_root.expanduser().resolve() if recipe_root else None
    if output.exists():
        raise FileExistsError(f"showcase output already exists: {output}")
    available = {spec.id: spec for spec in COMPOSITIONS}
    selected_ids = list(available) if families is None else list(families)
    if not selected_ids or len(selected_ids) != len(set(selected_ids)):
        raise ValueError("showcase families must be non-empty and unique")
    unknown = sorted(set(selected_ids) - set(available))
    if unknown:
        raise ValueError(f"unknown showcase family: {', '.join(unknown)}")
    overrides = seed_overrides or {}
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in overrides.values()):
        raise ValueError("showcase seed overrides must be integers")
    unknown_overrides = sorted(set(overrides) - set(selected_ids))
    if unknown_overrides:
        raise ValueError(
            "seed override requires the family to be selected: " + ", ".join(unknown_overrides)
        )
    specs = [
        replace(
            available[family],
            seed=overrides.get(family, available[family].seed),
            arrangement_seed=overrides.get(family, available[family].seed) + 1000,
        )
        if family in overrides else available[family]
        for family in selected_ids
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        recipes = staging / "Recipes"
        _copy_recipes(recipes, recipe_root)
        fixture = staging / ".fixture-source"
        portable_demo.build_demo(fixture)
        instrument = staging / "Instrument"
        shutil.copytree(fixture / "Cross Kit", instrument)
        shutil.rmtree(fixture)
        program_path = instrument / "FG Portable Cross Kit.xpm"
        program = from_xpm(program_path)
        compositions = [
            _write_composition(staging, recipes, program_path, program, spec)
            for spec in specs
        ]
        report = {
            "schema_version": 1,
            "kind": "mpc-composition-showcase",
            "license": "CC0-1.0 generated audio; repository source remains MIT",
            "software_status": "pass",
            "hardware_status": "deferred",
            "composition_count": len(compositions),
            "compositions": compositions,
        }
        (staging / "showcase.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        (staging / "README.md").write_text(_readme(compositions), encoding="utf-8")
        (staging / "HARDWARE_CHECKLIST.md").write_text(
            _hardware_checklist(compositions), encoding="utf-8"
        )
        (staging / "LICENSE-GENERATED-AUDIO.txt").write_text(
            "Generated WAV audio in Instrument/ is dedicated to the public domain under CC0 1.0.\n"
            "The software source remains licensed under the repository MIT License.\n",
            encoding="utf-8",
        )
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--recipe-root", type=Path,
        help="optional recipes directory; installed defaults are included",
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--family", action="append", choices=[spec.id for spec in COMPOSITIONS],
        help="build one family; repeat to select several (default: all)",
    )
    selection.add_argument("--all", action="store_true", help="build all six families")
    parser.add_argument(
        "--seed", action="append", default=[], metavar="FAMILY=INTEGER",
        help="override a selected family's idea seed; arrangement seed follows at +1000",
    )
    args = parser.parse_args(argv or sys.argv[1:])
    overrides = {}
    for value in args.seed:
        family, separator, seed = value.partition("=")
        if not separator or family not in {spec.id for spec in COMPOSITIONS}:
            raise ValueError(f"seed must use FAMILY=INTEGER: {value!r}")
        if family in overrides:
            raise ValueError(f"duplicate seed override: {family}")
        try:
            overrides[family] = int(seed)
        except ValueError as error:
            raise ValueError(f"seed must use FAMILY=INTEGER: {value!r}") from error
    families = tuple(args.family) if args.family else None
    report = build_showcase(args.output, args.recipe_root, families, overrides)
    print(f"Built {report['composition_count']} compositions -> {args.output.expanduser().resolve()}")
    print("Software status: pass; MPC hardware status: deferred")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
