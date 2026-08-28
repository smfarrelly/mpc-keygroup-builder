"""Select deterministic cross-library Drum kit samples from an enriched catalog."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from .roles import role_matches


@dataclass(frozen=True)
class KitSlot:
    pad: int
    role: str
    prefer_duration: str | None
    prefer_loudness: str | None
    prefer_transient: str | None
    mute_group: int


@dataclass(frozen=True)
class KitRecipe:
    schema_version: int
    id: str
    name: str
    seed: int
    require_hardware_pass: bool
    slots: tuple[KitSlot, ...]


@dataclass(frozen=True)
class KitSelection:
    pad: int
    requested_role: str
    selected_role: str
    sample: str
    source_path: str
    source_sample: str
    source_program: str
    source_program_name: str
    collection: str
    zone_index: int
    hardware_status: str
    favorite: str
    descriptors: dict[str, str]
    measurements: dict[str, float | None]
    preference_matches: tuple[str, ...]
    mute_group: int


@dataclass(frozen=True)
class CrossKitPlan:
    schema_version: int
    recipe: str
    name: str
    seed: int
    catalog: str
    program_root: str
    selections: tuple[KitSelection, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def load_recipe(path: Path) -> KitRecipe:
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    required = ("schema_version", "id", "name", "seed", "pads")
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"kit recipe is missing: {', '.join(missing)}")
    if data["schema_version"] != 1:
        raise ValueError("kit recipe requires schema_version=1")
    seed = data["seed"]
    if not isinstance(seed, int):
        raise ValueError("kit recipe seed must be an integer")
    pads = data["pads"]
    if not isinstance(pads, list) or not pads:
        raise ValueError("kit recipe requires [[pads]]")
    slots = []
    valid_descriptors = {
        "prefer_duration": {"short", "medium", "long"},
        "prefer_loudness": {"silent", "quiet", "moderate", "loud"},
        "prefer_transient": {"soft", "defined", "sharp"},
    }
    for index, item in enumerate(pads, 1):
        pad = item.get("pad") if isinstance(item, dict) else None
        role = item.get("role") if isinstance(item, dict) else None
        mute_group = item.get("mute_group", 0) if isinstance(item, dict) else 0
        if not isinstance(pad, int) or not 1 <= pad <= 128:
            raise ValueError(f"pads entry {index}: pad must be 1..128")
        if not isinstance(role, str) or not role.strip():
            raise ValueError(f"pads entry {index}: role is required")
        if not isinstance(mute_group, int) or not 0 <= mute_group <= 32:
            raise ValueError(f"pads entry {index}: mute_group must be 0..32")
        preferences = {}
        for label, allowed in valid_descriptors.items():
            value = item.get(label)
            if value is not None and value not in allowed:
                raise ValueError(f"pads entry {index}: invalid {label}")
            preferences[label] = value
        slots.append(
            KitSlot(
                pad,
                role.strip(),
                preferences["prefer_duration"],
                preferences["prefer_loudness"],
                preferences["prefer_transient"],
                mute_group,
            )
        )
    pad_numbers = [slot.pad for slot in slots]
    if len(pad_numbers) != len(set(pad_numbers)):
        raise ValueError("kit recipe pads must be unique")
    return KitRecipe(
        1,
        str(data["id"]),
        str(data["name"]),
        seed,
        bool(data.get("require_hardware_pass", False)),
        tuple(slots),
    )


def _candidates(catalog: dict[str, Any], slot: KitSlot, require_pass: bool) -> list[dict[str, Any]]:
    candidates = []
    for program in catalog.get("programs", []):
        if program.get("program_type") != "drum" or program.get("index_status") not in {"pass", "warn"}:
            continue
        if require_pass and program.get("hardware_status") != "pass":
            continue
        audio_by_sample = {
            item["sample"]: item
            for item in program.get("audio_facets", {}).get("samples", [])
            if isinstance(item, dict) and item.get("sample") and item.get("path")
        }
        for zone in program.get("zones", []):
            if not role_matches(str(zone.get("role", "")), slot.role):
                continue
            for sample in zone.get("samples", []):
                measurement = audio_by_sample.get(sample)
                if measurement is None:
                    continue
                candidates.append(
                    {
                        "program": program,
                        "zone": zone,
                        "sample": sample,
                        "measurement": measurement,
                    }
                )
    return candidates


def _stable_tie(seed: int, pad: int, candidate: dict[str, Any]) -> str:
    identity = (
        f"{seed}:{pad}:{candidate['program'].get('path')}:{candidate['zone'].get('index')}:"
        f"{candidate['measurement'].get('path')}"
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def select_kit(
    recipe: KitRecipe,
    catalog: dict[str, Any],
    *,
    catalog_path: Path,
    seed: int | None = None,
) -> CrossKitPlan:
    if not catalog.get("audio_facets_enabled"):
        raise ValueError("cross-library selection requires a catalog built with --audio-facets")
    chosen_seed = recipe.seed if seed is None else seed
    used_paths: set[str] = set()
    used_basenames: set[str] = set()
    used_programs: set[str] = set()
    used_collections: set[str] = set()
    selections = []
    warnings = []
    for slot in recipe.slots:
        candidates = []
        for candidate in _candidates(catalog, slot, recipe.require_hardware_pass):
            measurement = candidate["measurement"]
            path = str(measurement["path"])
            basename = PurePosixPath(path).name.casefold()
            if path in used_paths or basename in used_basenames:
                continue
            descriptors = measurement.get("descriptors", {})
            preference_matches = []
            preferences = (
                ("duration", slot.prefer_duration),
                ("loudness", slot.prefer_loudness),
                ("transient", slot.prefer_transient),
            )
            for label, requested in preferences:
                if requested and descriptors.get(label) == requested:
                    preference_matches.append(label)
            program = candidate["program"]
            score = (
                len(preference_matches) * 20
                + (12 if program.get("hardware_status") == "pass" else 0)
                + (8 if program.get("favorite") in {"yes", "provisional"} else 0)
                + (6 if program.get("path") not in used_programs else 0)
                + (4 if program.get("collection") not in used_collections else 0)
            )
            candidates.append(
                (
                    -score,
                    _stable_tie(chosen_seed, slot.pad, candidate),
                    candidate,
                    tuple(preference_matches),
                )
            )
        if not candidates:
            raise ValueError(f"no unique measured candidate for pad {slot.pad} role {slot.role}")
        _, _, candidate, preference_matches = min(candidates)
        program = candidate["program"]
        measurement = candidate["measurement"]
        descriptors = dict(measurement.get("descriptors", {}))
        requested_count = sum(
            value is not None
            for value in (slot.prefer_duration, slot.prefer_loudness, slot.prefer_transient)
        )
        if len(preference_matches) < requested_count:
            warnings.append(
                f"pad {slot.pad}: selected {slot.role} matches {len(preference_matches)}/"
                f"{requested_count} preferred facets"
            )
        path = str(measurement["path"])
        used_paths.add(path)
        used_basenames.add(PurePosixPath(path).name.casefold())
        used_programs.add(str(program.get("path", "")))
        used_collections.add(str(program.get("collection", "")))
        selections.append(
            KitSelection(
                slot.pad,
                slot.role,
                str(candidate["zone"].get("role", "")),
                PurePosixPath(path).name,
                path,
                str(candidate["sample"]),
                str(program.get("path", "")),
                str(program.get("name", "")),
                str(program.get("collection", "")),
                int(candidate["zone"].get("index", 0)),
                str(program.get("hardware_status", "")),
                str(program.get("favorite", "")),
                descriptors,
                {
                    key: float(measurement[key]) if measurement.get(key) is not None else None
                    for key in (
                        "duration_seconds", "rms_dbfs", "peak_dbfs", "crest_db",
                        "attack_milliseconds", "onset_to_body_db",
                    )
                },
                preference_matches,
                slot.mute_group,
            )
        )
    return CrossKitPlan(
        1,
        recipe.id,
        recipe.name,
        chosen_seed,
        str(catalog_path.resolve()),
        str(catalog.get("program_root", "")),
        tuple(selections),
        tuple(warnings),
    )


def render_manifest(plan: CrossKitPlan) -> str:
    lines = [f'name = {json.dumps(plan.name)}', ""]
    for selection in plan.selections:
        lines.extend(
            (
                "[[pads]]",
                f"pad = {selection.pad}",
                f"sample = {json.dumps(selection.sample)}",
                f"mute_group = {selection.mute_group}",
                "",
            )
        )
    return "\n".join(lines)


def render_markdown(plan: CrossKitPlan) -> str:
    lines = [
        f"# {plan.name}", "", f"Seed: `{plan.seed}`", "",
        "Selection is deterministic and descriptor-driven. Licensed audio remains "
        "in its source library unless explicitly staged.",
        "", "## Pads", "",
    ]
    for item in plan.selections:
        facets = ", ".join(f"{key}={value}" for key, value in item.descriptors.items())
        lines.append(
            f"- A{item.pad:02d} `{item.requested_role}` → `{item.sample}` "
            f"from {item.collection}/{item.source_program_name} ({facets})"
        )
    if plan.warnings:
        lines.extend(("", "## Preference fallbacks", ""))
        lines.extend(f"- {warning}" for warning in plan.warnings)
    lines.extend((
        "", "## Build", "", "```bash",
        "uv run mpc-drum-build MANIFEST.toml --template TEMPLATE.xpm --source-root STAGED_AUDIO --output OUTPUT",
        "```", "",
    ))
    return "\n".join(lines)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stage_audio(plan: CrossKitPlan, output: Path) -> dict[str, Any]:
    if output.exists():
        if not output.is_dir():
            raise FileExistsError(f"staging output is not a directory: {output}")
        if any(output.iterdir()):
            raise FileExistsError(f"staging output is not empty: {output}")
    program_root = Path(plan.program_root).resolve()
    copies = []
    output.mkdir(parents=True, exist_ok=True)
    for selection in plan.selections:
        source = (program_root / selection.source_path).resolve()
        try:
            source.relative_to(program_root)
        except ValueError as error:
            raise ValueError(f"source path escapes program root: {selection.source_path}") from error
        if not source.is_file():
            raise FileNotFoundError(f"selected source is missing: {source}")
        destination = output / selection.sample
        if destination.exists():
            raise FileExistsError(f"staging basename collision: {destination.name}")
        source_hash = _sha256(source)
        shutil.copy2(source, destination)
        destination_hash = _sha256(destination)
        if destination_hash != source_hash:
            raise OSError(f"staged checksum mismatch: {destination}")
        copies.append(
            {
                "pad": selection.pad,
                "source": str(source),
                "destination": str(destination.resolve()),
                "sha256": source_hash,
                "bytes": destination.stat().st_size,
            }
        )
    return {
        "schema_version": 1,
        "output": str(output.resolve()),
        "files": len(copies),
        "bytes": sum(item["bytes"] for item in copies),
        "copies": copies,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipe", type=Path)
    parser.add_argument("catalog", type=Path)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--manifest-output", type=Path, required=True)
    parser.add_argument("--report-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--stage-output", type=Path)
    parser.add_argument("--stage-report", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    outputs = [args.manifest_output, args.report_output]
    if args.markdown_output:
        outputs.append(args.markdown_output)
    if bool(args.stage_output) != bool(args.stage_report):
        parser.error("--stage-output and --stage-report must be supplied together")
    if args.stage_report:
        outputs.append(args.stage_report)
    if not args.force and any(path.exists() for path in outputs):
        parser.error("output exists; pass --force to replace all requested files")
    with args.catalog.open(encoding="utf-8") as stream:
        catalog = json.load(stream)
    plan = select_kit(
        load_recipe(args.recipe.expanduser().resolve()),
        catalog,
        catalog_path=args.catalog,
        seed=args.seed,
    )
    for path in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_output.write_text(render_manifest(plan), encoding="utf-8")
    args.report_output.write_text(json.dumps(plan.to_dict(), indent=2) + "\n", encoding="utf-8")
    if args.markdown_output:
        args.markdown_output.write_text(render_markdown(plan), encoding="utf-8")
    if args.stage_output and args.stage_report:
        stage = stage_audio(plan, args.stage_output.expanduser().resolve())
        args.stage_report.write_text(json.dumps(stage, indent=2) + "\n", encoding="utf-8")
    print(f"Selected: {len(plan.selections)} pads from {len(set(x.collection for x in plan.selections))} collections")
    print(f"Warnings: {len(plan.warnings)}; seed={plan.seed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
