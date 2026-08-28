"""Build, audit, and document a deterministic wave of cross-library Drum kits."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import tempfile
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .catalog import build_catalog
from .drum_audit import audit_drum_program
from .drum_builder import build_drum_program, load_manifest
from .kit_select import (
    CrossKitPlan,
    load_recipe,
    render_manifest,
    render_markdown,
    select_kit,
    stage_audio,
)
from .model import from_xpm
from .testing import test_program


@dataclass(frozen=True)
class WaveRecipe:
    id: str
    path: Path
    seed: int | None


@dataclass(frozen=True)
class KitWave:
    schema_version: int
    id: str
    name: str
    recipes: tuple[WaveRecipe, ...]


def load_wave(path: Path) -> KitWave:
    path = path.resolve()
    with path.open("rb") as stream:
        raw = tomllib.load(stream)
    if raw.get("schema_version") != 1:
        raise ValueError("kit wave requires schema_version=1")
    if not isinstance(raw.get("id"), str) or not raw["id"]:
        raise ValueError("kit wave requires id")
    if not isinstance(raw.get("name"), str) or not raw["name"]:
        raise ValueError("kit wave requires name")
    entries = raw.get("kits")
    if not isinstance(entries, list) or not entries:
        raise ValueError("kit wave requires [[kits]]")
    recipes = []
    ids: set[str] = set()
    paths: set[Path] = set()
    for index, entry in enumerate(entries, 1):
        recipe_id = entry.get("id") if isinstance(entry, dict) else None
        relative = entry.get("recipe") if isinstance(entry, dict) else None
        seed = entry.get("seed") if isinstance(entry, dict) else None
        if not isinstance(recipe_id, str) or not recipe_id:
            raise ValueError(f"kits entry {index} requires id")
        if recipe_id in ids:
            raise ValueError(f"duplicate wave kit id {recipe_id}")
        if not isinstance(relative, str) or not relative:
            raise ValueError(f"kits entry {index} requires recipe")
        recipe_path = (path.parent / relative).resolve()
        try:
            recipe_path.relative_to(path.parent.parent)
        except ValueError as error:
            raise ValueError(f"kits entry {index} recipe escapes recipes root") from error
        if not recipe_path.is_file():
            raise ValueError(f"kits entry {index} recipe is missing: {recipe_path}")
        if recipe_path in paths:
            raise ValueError(f"duplicate wave recipe path {relative}")
        if seed is not None and not isinstance(seed, int):
            raise ValueError(f"kits entry {index} seed must be an integer")
        ids.add(recipe_id)
        paths.add(recipe_path)
        recipes.append(WaveRecipe(recipe_id, recipe_path, seed))
    return KitWave(1, raw["id"], raw["name"], tuple(recipes))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _final_paths(value: object, staging: Path, output: Path) -> object:
    if isinstance(value, str):
        prefix = str(staging)
        return str(output) + value[len(prefix) :] if value.startswith(prefix) else value
    if isinstance(value, list):
        return [_final_paths(item, staging, output) for item in value]
    if isinstance(value, tuple):
        return tuple(_final_paths(item, staging, output) for item in value)
    if isinstance(value, dict):
        return {key: _final_paths(item, staging, output) for key, item in value.items()}
    return value


def _preflight(
    wave: KitWave,
    catalog: dict[str, Any],
    catalog_path: Path,
) -> tuple[tuple[WaveRecipe, CrossKitPlan], ...]:
    plans = []
    names: set[str] = set()
    signatures: dict[frozenset[str], str] = {}
    for entry in wave.recipes:
        recipe = load_recipe(entry.path)
        if recipe.name in names:
            raise ValueError(f"wave kit names must be unique: {recipe.name}")
        plan = select_kit(recipe, catalog, catalog_path=catalog_path, seed=entry.seed)
        signature = frozenset(selection.source_path for selection in plan.selections)
        if signature in signatures:
            raise ValueError(
                f"wave recipes select the same source set: "
                f"{signatures[signature]} and {entry.id}"
            )
        signatures[signature] = entry.id
        names.add(recipe.name)
        plans.append((entry, plan))
    return tuple(plans)


def _overlap_report(plans: tuple[tuple[WaveRecipe, CrossKitPlan], ...]) -> list[dict[str, Any]]:
    report = []
    for left_index, (left_entry, left_plan) in enumerate(plans):
        left = {selection.source_path for selection in left_plan.selections}
        for right_entry, right_plan in plans[left_index + 1 :]:
            right = {selection.source_path for selection in right_plan.selections}
            shared = left & right
            union = left | right
            report.append(
                {
                    "kit_a": left_entry.id,
                    "kit_b": right_entry.id,
                    "shared_samples": len(shared),
                    "union_samples": len(union),
                    "jaccard": round(len(shared) / len(union), 4) if union else 0.0,
                }
            )
    return report


def _verify_copies(stage_report: dict[str, Any], program_dir: Path) -> list[dict[str, Any]]:
    verified = []
    for copy in stage_report["copies"]:
        destination = program_dir / Path(copy["destination"]).name
        digest = _sha256(destination)
        if digest != copy["sha256"]:
            raise OSError(f"program copy checksum mismatch: {destination}")
        verified.append({"file": destination.name, "sha256": digest, "bytes": copy["bytes"]})
    return verified


def _hardware_checklist(
    wave: KitWave,
    kits: list[dict[str, Any]],
    overlaps: list[dict[str, Any]],
    output: Path,
) -> str:
    lines = [
        f"# {wave.name} — MPC hardware checklist",
        "",
        "Software build, sample checksum, model, semantic simulation, and Drum audit all pass.",
        "Musical usefulness and physical behavior remain hardware decisions.",
        "",
        "## Software distinctness",
        "",
    ]
    if overlaps:
        lines.extend(
            f"- `{item['kit_a']}` vs `{item['kit_b']}`: "
            f"{item['shared_samples']} shared samples; Jaccard {item['jaccard']:.4f}."
            for item in overlaps
        )
    else:
        lines.append("- One-kit wave; no pairwise comparison applies.")
    lines.append("")
    for index, kit in enumerate(kits, 1):
        lines.extend(
            [
                f"## {index}. {kit['name']}",
                "",
                f"Full MPC path: `{output / kit['id'] / 'Program' / (kit['name'] + '.xpm')}`",
                "",
                f"- [ ] Load succeeds; Bank A has {kit['pads']} sounding pads.",
                "- [ ] Pad colors are distinct and semantically useful.",
                "- [ ] Closed/open hats choke audibly on pads A07/A08.",
                "- [ ] Kicks, snares, percussion, and tails feel intentionally different.",
                "- [ ] Save/reload preserves samples, colors, and mute behavior.",
                "- [ ] Record a short pattern and note the strongest musical role.",
                "- Verdict: [ ] pass  [ ] warn  [ ] fail",
                "- Favorite: [ ] yes  [ ] provisional  [ ] no",
                "- Listening notes:",
                "",
            ]
        )
    lines.extend(
        [
            "## Wave decision",
            "",
            "- [ ] Choose a primary cross-library kit.",
            "- [ ] Choose at most two contrasting alternates.",
            "- [ ] Record rejected recipes and the reason; do not delete their provenance.",
            "",
        ]
    )
    return "\n".join(lines)


def build_wave(
    wave: KitWave,
    catalog: dict[str, Any],
    *,
    catalog_path: Path,
    template: Path,
    output: Path,
) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"wave output already exists: {output}")
    if not template.is_file():
        raise FileNotFoundError(f"Drum template is missing: {template}")
    plans = _preflight(wave, catalog, catalog_path)
    overlaps = _overlap_report(plans)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    built = []
    try:
        (staging / "catalog.json").write_text(
            json.dumps(catalog, indent=2) + "\n", encoding="utf-8"
        )
        for entry, plan in plans:
            kit_root = staging / entry.id
            manifest_path = kit_root / "manifest.toml"
            provenance_path = kit_root / "provenance.json"
            selection_path = kit_root / "SELECTION.md"
            audio_root = kit_root / "Staged Audio"
            program_root = kit_root / "Program"
            kit_root.mkdir(parents=True)
            manifest_path.write_text(render_manifest(plan), encoding="utf-8")
            provenance_path.write_text(
                json.dumps(plan.to_dict(), indent=2) + "\n", encoding="utf-8"
            )
            selection_path.write_text(render_markdown(plan), encoding="utf-8")
            stage_report = stage_audio(plan, audio_root)
            (kit_root / "staging-checksums.json").write_text(
                json.dumps(_final_paths(stage_report, staging, output), indent=2) + "\n",
                encoding="utf-8",
            )
            program = build_drum_program(
                load_manifest(manifest_path), template, audio_root, program_root
            )
            model_report = from_xpm(program).validate()
            simulation = asdict(test_program(program, program_root))
            audit = audit_drum_program(program)
            checksums = _verify_copies(stage_report, program_root)
            acceptance = {
                "model": model_report,
                "simulation": simulation,
                "drum_audit": audit,
                "program_audio": checksums,
            }
            if model_report["errors"] or simulation["verdict"] == "fail":
                raise ValueError(f"software acceptance failed for {plan.name}")
            if audit["verdict"] != "pass":
                raise ValueError(f"Drum audit did not pass for {plan.name}")
            (kit_root / "software-acceptance.json").write_text(
                json.dumps(_final_paths(acceptance, staging, output), indent=2) + "\n",
                encoding="utf-8",
            )
            built.append(
                {
                    "id": entry.id,
                    "name": plan.name,
                    "seed": plan.seed,
                    "pads": len(plan.selections),
                    "program": str(output / entry.id / "Program" / program.name),
                    "program_sha256": _sha256(program),
                    "selection_signature": hashlib.sha256(
                        "\n".join(
                            sorted(selection.source_path for selection in plan.selections)
                        ).encode("utf-8")
                    ).hexdigest(),
                    "selection_warnings": list(plan.warnings),
                    "source_programs": sorted(
                        {selection.source_program_name for selection in plan.selections}
                    ),
                    "software_verdict": "pass",
                    "hardware_status": "pending",
                }
            )
        report = {
            "schema_version": 1,
            "wave": wave.id,
            "name": wave.name,
            "catalog": str(catalog_path.resolve()),
            "template": str(template.resolve()),
            "output": str(output.resolve()),
            "kits": built,
            "pairwise_overlap": overlaps,
        }
        (staging / "wave-report.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        with (staging / "wave-index.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=(
                    "id", "name", "seed", "pads", "software_verdict",
                    "hardware_status", "program", "program_sha256",
                ),
            )
            writer.writeheader()
            writer.writerows(
                {key: kit[key] for key in writer.fieldnames}
                for kit in built
            )
        (staging / "HARDWARE_CHECKLIST.md").write_text(
            _hardware_checklist(wave, built, overlaps, output), encoding="utf-8"
        )
        os.replace(staging, output)
        return report
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wave", type=Path)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--catalog", type=Path)
    source.add_argument("--ledger", type=Path)
    parser.add_argument("--program-root", type=Path)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    wave_path = args.wave.expanduser().resolve()
    wave = load_wave(wave_path)
    if args.catalog:
        catalog_path = args.catalog.expanduser().resolve()
        with catalog_path.open(encoding="utf-8") as stream:
            catalog = json.load(stream)
    else:
        if args.program_root is None:
            parser.error("--program-root is required with --ledger")
        catalog_path = args.output.expanduser().resolve() / "catalog.json"
        catalog = build_catalog(
            args.ledger.expanduser().resolve(),
            args.program_root.expanduser().resolve(),
            include_audio=True,
        )
    if not catalog.get("audio_facets_enabled"):
        parser.error("kit wave requires a catalog built with audio facets")
    report = build_wave(
        wave,
        catalog,
        catalog_path=catalog_path,
        template=args.template.expanduser().resolve(),
        output=args.output.expanduser().resolve(),
    )
    print(f"Built: {report['name']}")
    print(f"Kits: {len(report['kits'])}; software acceptance: pass")
    print(f"Hardware checklist: {Path(report['output']) / 'HARDWARE_CHECKLIST.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
