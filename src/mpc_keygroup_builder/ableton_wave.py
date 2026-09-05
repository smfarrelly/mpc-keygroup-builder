"""Plan and build a diverse, preflighted Ableton Drum conversion wave."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import tomllib
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any

from . import ableton, ableton_drum, ableton_fidelity, testing
from .ableton_backlog import display_pack
from .portable_demo import write_drum_template


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "program"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _excluded(paths: list[Path]) -> set[str]:
    result = set()
    for path in paths:
        with path.expanduser().resolve().open("rb") as stream:
            recipe = tomllib.load(stream)
        for item in recipe.get("programs", []):
            if isinstance(item, dict) and isinstance(item.get("preset"), str):
                result.add(item["preset"])
    return result


def infer_pack_root(preset: Path, library_root: Path, report: dict[str, Any]) -> Path:
    references = []
    for zone in report.get("zones", []):
        sample = zone.get("sample") if isinstance(zone, dict) else None
        relative = sample.get("relative_path") if isinstance(sample, dict) else None
        if isinstance(relative, str):
            references.append(relative)
    for pad in report.get("drum_pads", []):
        for zone in pad.get("zones", []) if isinstance(pad, dict) else []:
            sample = zone.get("sample") if isinstance(zone, dict) else None
            relative = sample.get("relative_path") if isinstance(sample, dict) else None
            if isinstance(relative, str):
                references.append(relative)
    if not references:
        raise ValueError(f"no readable Ableton sample paths: {preset}")
    current = preset.parent.resolve()
    boundary = library_root.resolve()
    while True:
        if all((current / relative).is_file() for relative in references):
            return current
        if current == boundary:
            break
        try:
            current.relative_to(boundary)
        except ValueError:
            break
        current = current.parent
    raise FileNotFoundError(f"cannot resolve all Drum Rack samples below {library_root}: {preset}")


def _recipe(name: str, selected: list[dict[str, Any]]) -> str:
    lines = [f"name = {json.dumps(name)}", ""]
    for item in selected:
        lines.extend((
            "[[programs]]", f"id = {json.dumps(item['id'])}",
            f"name = {json.dumps(item['name'])}", f"collection = {json.dumps(item['collection'])}",
            f"preset = {json.dumps(item['path'])}", f"pack_root = {json.dumps(item['pack_root'])}", "",
        ))
    return "\n".join(lines)


def plan_wave(
    backlog_path: Path, source_root: Path, output: Path, *, count: int = 24,
    max_per_pack: int = 2, exclude_recipes: list[Path] | None = None,
) -> dict[str, Any]:
    if count < 1 or max_per_pack < 1:
        raise ValueError("count and max-per-pack must be positive")
    backlog_path, source_root, output = backlog_path.resolve(), source_root.resolve(), output.resolve()
    if output.exists():
        raise FileExistsError(f"Ableton wave output already exists: {output}")
    backlog = json.loads(backlog_path.read_text(encoding="utf-8"))
    excluded = _excluded(exclude_recipes or [])
    groups: dict[str, deque[dict[str, Any]]] = defaultdict(deque)
    for entry in backlog.get("entries", []):
        if not isinstance(entry, dict) or entry.get("target") != "drum" or entry.get("duplicate_of"):
            continue
        if entry.get("priority") not in {"P0", "P1", "P2"} or entry.get("path") in excluded:
            continue
        groups[str(entry.get("pack"))].append(entry)
    selected: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    used_ids: Counter[str] = Counter()
    rounds = 0
    while groups and len(selected) < count and rounds < max_per_pack:
        for pack in sorted(list(groups), key=lambda key: (-int(groups[key][0].get("score", 0)), key)):
            if len(selected) >= count:
                break
            queue = groups[pack]
            accepted = False
            while queue and not accepted:
                entry = queue.popleft()
                preset = source_root / str(entry["path"])
                try:
                    source_report = ableton.inspect(preset)
                    pack_root = infer_pack_root(preset, source_root, source_report)
                    plan = ableton_drum.plan_conversion(preset, pack_root, name=str(entry["name"]))
                except (ValueError, FileNotFoundError, TypeError) as error:
                    rejected.append({"path": str(entry.get("path")), "reason": str(error)})
                    continue
                base = _slug(f"{display_pack(pack)}-{entry['name']}")
                used_ids[base] += 1
                identifier = base if used_ids[base] == 1 else f"{base}-{used_ids[base]}"
                selected.append({
                    "id": identifier, "name": str(entry["name"]), "collection": display_pack(pack),
                    "pack": pack, "path": str(entry["path"]),
                    "pack_root": pack_root.relative_to(source_root).as_posix(),
                    "priority": entry.get("priority"), "score": entry.get("score"),
                    "pads": len(plan.manifest.pads), "samples": len(plan.samples),
                    "translation_warnings": list(plan.warnings),
                    "fidelity": ableton_fidelity.normalize(source_report, source_path=str(entry["path"])),
                })
                accepted = True
                if len(selected) >= count:
                    break
            if not queue:
                groups.pop(pack, None)
        rounds += 1
    if len(selected) < count:
        raise ValueError(f"only {len(selected)} preflightable diverse programs found; requested {count}")
    report = {
        "schema_version": 1, "kind": "mpc-ableton-drum-wave-plan", "name": "Samples From Mars Ableton Drum Wave 02",
        "source_inventory": backlog_path.name, "software_status": "preflight-pass", "hardware_status": "deferred",
        "selection_policy": f"priority P0-P2, unique source, excludes prior recipes, round-robin packs, max {max_per_pack} per pack",
        "summary": {"programs": len(selected), "packs": len({item['pack'] for item in selected}), "rejected_during_preflight": len(rejected)},
        "programs": selected, "rejections": rejected,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        (staging / "ableton-drum-wave-02.toml").write_text(_recipe(report["name"], selected), encoding="utf-8")
        (staging / "wave-plan.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        (staging / "README.md").write_text(
            "# Samples From Mars Ableton Drum Wave 02\n\n"
            f"{len(selected)} programs across {report['summary']['packs']} packs passed source/sample preflight. "
            "Sound, colors, pad ergonomics, choke behavior, and save/reload remain hardware-deferred.\n\n"
            "Build with `mpc-ableton-wave build ableton-drum-wave-02.toml --source-root SOURCE --output OUTPUT`.\n",
            encoding="utf-8",
        )
        os.replace(staging, output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return report


def build_wave(recipe: Path, source_root: Path, output: Path) -> dict[str, Any]:
    recipe, source_root, output = recipe.resolve(), source_root.resolve(), output.resolve()
    if output.exists():
        raise FileExistsError(f"Ableton wave build output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        template = staging / "Support/Generated Drum Template.xpm"
        template.parent.mkdir(parents=True)
        write_drum_template(template)
        report = ableton_drum.build_batch(recipe, source_root, template, staging / "Programs", staging / "Manifests")
        tests = []
        for item in report["programs"]:
            program = Path(str(item["program"]))
            result = testing.test_program(program, program.parent)
            tests.append({"id": item["id"], "verdict": result.verdict, "issues": [vars(issue) for issue in result.issues]})
            item["program"] = program.relative_to(staging).as_posix()
            item["preset"] = Path(str(item["preset"])).relative_to(source_root).as_posix()
        verdicts = Counter(item["verdict"] for item in tests)
        report.update({"kind": "mpc-ableton-drum-wave-build", "software_status": "pass" if not verdicts["fail"] else "fail", "hardware_status": "deferred", "simulation": {"verdicts": dict(sorted(verdicts.items())), "programs": tests}})
        # The underlying batch report and manifest comments are diagnostics; keep the
        # bundle portable by replacing machine-specific roots before publication.
        for path in (staging / "Manifests").glob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                text = text.replace(str(source_root) + "/", "SOURCE_ROOT/")
                text = text.replace(str(staging) + "/", "")
                path.write_text(text, encoding="utf-8")
        (staging / "build-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        checklist = ["# Ableton Drum Wave 02 — MPC checklist", "", "Every program is software-built; hardware status starts deferred.", ""]
        for item in report["programs"]:
            relative = str(item["program"])
            checklist.extend((f"## {item['collection']} / {item['name']}", "", f"Load `{relative}`", "", "- [ ] Pads trigger expected sounds and useful layout.", "- [ ] Velocity layers and choke groups behave as expected.", "- [ ] Colors, save/reload, and musical usefulness checked.", "", "Verdict: [ ] pass  [ ] warn  [ ] fail", "Notes:", ""))
        (staging / "HARDWARE_CHECKLIST.md").write_text("\n".join(checklist), encoding="utf-8")
        checksums = {str(path.relative_to(staging)): _sha256(path) for path in sorted(staging.rglob("*")) if path.is_file() and path.name != "checksums.json"}
        (staging / "checksums.json").write_text(json.dumps(checksums, indent=2) + "\n", encoding="utf-8")
        os.replace(staging, output)
        return report
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan", help="select and preflight a diverse wave")
    plan.add_argument("backlog", type=Path); plan.add_argument("--source-root", type=Path, required=True)
    plan.add_argument("--output", type=Path, required=True); plan.add_argument("--count", type=int, default=24)
    plan.add_argument("--max-per-pack", type=int, default=2); plan.add_argument("--exclude-recipe", type=Path, action="append", default=[])
    build = commands.add_parser("build", help="build a planned wave with a generated structural template")
    build.add_argument("recipe", type=Path); build.add_argument("--source-root", type=Path, required=True); build.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv or sys.argv[1:])
    if args.command == "plan":
        report = plan_wave(args.backlog, args.source_root, args.output, count=args.count, max_per_pack=args.max_per_pack, exclude_recipes=args.exclude_recipe)
        print(f"Wrote: {args.output.resolve()}"); print(f"Programs: {report['summary']['programs']}; packs: {report['summary']['packs']}; hardware: deferred")
    else:
        report = build_wave(args.recipe, args.source_root, args.output)
        print(f"Wrote: {args.output.resolve()}"); print(f"Programs: {len(report['programs'])}; simulation: {report['simulation']['verdicts']}; hardware: deferred")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
