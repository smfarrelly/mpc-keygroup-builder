"""Audit creative recipe validity, dependencies, compatibility, IDs, and channels."""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import shutil
import sys
import tempfile
import tomllib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

from . import harmony, ideas, kit_select, melody, workstation


LOADERS: dict[str, Callable[[Path], Any]] = {
    "drum": ideas.load_recipe,
    "harmony": harmony.load_recipe,
    "melody": melody.load_recipe,
    "kit": kit_select.load_recipe,
    "workstation": workstation.load_recipe,
}
DIRECTORIES = {
    "drum": "drums",
    "harmony": "harmony",
    "melody": "melody",
    "kit": "kits",
    "workstation": "workstation",
}
DEPENDENCIES = ("drums", "harmony", "melody")


def _issue(severity: str, code: str, path: str, message: str, next_action: str) -> dict:
    return {
        "severity": severity,
        "code": code,
        "path": path,
        "message": message,
        "next": next_action,
    }


def _details(kind: str, loaded: Any) -> dict:
    if kind == "drum":
        return {
            "bars": loaded.bars,
            "key": "",
            "scale": "",
            "channels": [loaded.channel],
            "roles": [event.role for event in loaded.events],
            "items": sum(len(event.steps) for event in loaded.events),
        }
    if kind == "harmony":
        return {
            "bars": loaded.bars,
            "key": loaded.key,
            "scale": loaded.scale,
            "channels": [loaded.chord_channel, loaded.bass_channel],
            "roles": ["chords", "bass"],
            "items": len(loaded.progression),
        }
    if kind == "melody":
        return {
            "bars": loaded.bars,
            "key": loaded.key,
            "scale": loaded.scale,
            "channels": [loaded.channel],
            "roles": ["melody"],
            "items": len(loaded.rhythm),
        }
    if kind == "kit":
        return {
            "bars": "",
            "key": "",
            "scale": "",
            "channels": [],
            "roles": [slot.role for slot in loaded.slots],
            "items": len(loaded.slots),
        }
    return {
        "bars": loaded.harmony.bars,
        "key": loaded.harmony.key,
        "scale": loaded.harmony.scale,
        "channels": [
            loaded.drums.channel,
            loaded.harmony.chord_channel,
            loaded.harmony.bass_channel,
            loaded.melody.channel,
        ],
        "roles": ["drums", "chords", "bass", "melody"],
        "items": 4,
    }


def _cycles(graph: dict[str, list[str]]) -> list[list[str]]:
    found: set[tuple[str, ...]] = set()
    active: list[str] = []
    finished: set[str] = set()

    def visit(node: str) -> None:
        if node in active:
            start = active.index(node)
            cycle = tuple(active[start:] + [node])
            found.add(cycle)
            return
        if node in finished:
            return
        active.append(node)
        for target in graph.get(node, []):
            visit(target)
        active.pop()
        finished.add(node)

    for node in graph:
        visit(node)
    return [list(cycle) for cycle in sorted(found)]


def audit(recipe_root: Path) -> dict:
    root = recipe_root.expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(root)
    files: list[dict] = []
    issues: list[dict] = []
    identifiers: dict[tuple[str, str], list[str]] = defaultdict(list)
    references: set[str] = set()
    graph: dict[str, list[str]] = {}

    for kind, directory in DIRECTORIES.items():
        folder = root / directory
        for path in sorted(folder.glob("*.toml")) if folder.is_dir() else []:
            relative = str(path.relative_to(root))
            raw: dict[str, Any] = {}
            status = "pass"
            error = ""
            loaded = None
            relation_error = False
            try:
                with path.open("rb") as stream:
                    raw = tomllib.load(stream)
                loaded = LOADERS[kind](path)
            except (OSError, ValueError, tomllib.TOMLDecodeError) as caught:
                status = "fail"
                error = str(caught)
                issues.append(
                    _issue(
                        "error", "invalid-recipe", relative, error,
                        f"Run mpc-schema validate {kind}-recipe {relative} and repair the named field.",
                    )
                )
            identifier = raw.get("id", "") if isinstance(raw, dict) else ""
            name = raw.get("name", "") if isinstance(raw, dict) else ""
            if isinstance(identifier, str) and identifier:
                identifiers[(kind, identifier)].append(relative)
            dependencies = []
            if kind == "workstation" and isinstance(raw, dict):
                for field in DEPENDENCIES:
                    value = raw.get(field)
                    if not isinstance(value, str) or not value:
                        continue
                    target = (path.parent / value).resolve()
                    try:
                        target.relative_to(root)
                    except ValueError:
                        relation_error = True
                        issues.append(
                            _issue(
                                "error", "dependency-escape", relative,
                                f"{field} dependency escapes the recipe root: {value}",
                                "Use a relative path to a file inside this recipe tree.",
                            )
                        )
                        continue
                    target_relative = str(target.relative_to(root))
                    dependencies.append(target_relative)
                    references.add(target_relative)
                graph[relative] = dependencies
            if relation_error:
                status = "fail"
            details = _details(kind, loaded) if loaded is not None else {
                "bars": "", "key": "", "scale": "", "channels": [], "roles": [], "items": 0,
            }
            if kind == "workstation" and loaded is not None:
                duplicates = sorted(
                    channel for channel, count in Counter(details["channels"]).items() if count > 1
                )
                if duplicates:
                    status = "fail"
                    issues.append(
                        _issue(
                            "error", "channel-collision", relative,
                            "workstation reuses MIDI channels: " + ", ".join(map(str, duplicates)),
                            "Assign distinct Drum, Chords, Bass, and Melody channels.",
                        )
                    )
            files.append(
                {
                    "type": kind,
                    "id": identifier,
                    "name": name,
                    "path": relative,
                    "status": status,
                    "error": error,
                    "dependencies": dependencies,
                    **details,
                }
            )

    for (kind, identifier), paths in sorted(identifiers.items()):
        if len(paths) > 1:
            issues.append(
                _issue(
                    "error", "duplicate-id", ", ".join(paths),
                    f"duplicate {kind} recipe id: {identifier}",
                    "Rename one id so every recipe of a given type is unique.",
                )
            )
            for item in files:
                if item["type"] == kind and item["id"] == identifier:
                    item["status"] = "fail"

    if not files:
        issues.append(
            _issue(
                "error", "no-recipes", ".",
                "no recipe TOML files were found in the expected recipe directories",
                "Use a recipe root containing drums/, harmony/, melody/, kits/, or workstation/.",
            )
        )

    component_paths = {
        item["path"] for item in files if item["type"] in {"drum", "harmony", "melody"}
    }
    orphans = sorted(component_paths - references)
    for path in orphans:
        issues.append(
            _issue(
                "warning", "orphan-component", path,
                "component recipe is not referenced by a workstation recipe",
                "Reference it from a workstation or keep it intentionally standalone.",
            )
        )
    cycles = _cycles(graph)
    for cycle in cycles:
        issues.append(
            _issue(
                "error", "dependency-cycle", cycle[0], " -> ".join(cycle),
                "Break the circular recipe reference.",
            )
        )
    errors = sum(issue["severity"] == "error" for issue in issues)
    warnings = sum(issue["severity"] == "warning" for issue in issues)
    counts = Counter(item["type"] for item in files)
    return {
        "schema_version": 1,
        "kind": "mpc-recipe-audit",
        "root": str(root),
        "status": "fail" if errors else "pass",
        "summary": {
            "files": len(files),
            "workstations": counts["workstation"],
            "errors": errors,
            "warnings": warnings,
            "orphans": len(orphans),
        },
        "counts": dict(sorted(counts.items())),
        "files": files,
        "issues": issues,
        "dependency_graph": graph,
        "cycles": cycles,
        "orphans": orphans,
    }


def render_csv(report: dict) -> str:
    fields = ("type", "id", "name", "path", "status", "bars", "key", "scale", "channels", "roles", "items", "dependencies", "error")
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for item in report["files"]:
        writer.writerow(
            {
                **item,
                "channels": ",".join(map(str, item["channels"])),
                "roles": ",".join(item["roles"]),
                "dependencies": ",".join(item["dependencies"]),
            }
        )
    return stream.getvalue()


def render_markdown(report: dict) -> str:
    summary = report["summary"]
    lines = [
        "# Creative recipe audit",
        "",
        f"Status: **{report['status'].upper()}**",
        "",
        f"{summary['files']} files; {summary['workstations']} workstation families; "
        f"{summary['errors']} errors; {summary['warnings']} warnings; "
        f"{summary['orphans']} orphan components.",
        "",
        "## Families",
        "",
    ]
    for item in report["files"]:
        if item["type"] != "workstation":
            continue
        dependencies = ", ".join(item["dependencies"])
        lines.append(
            f"- **{item['name']}** (`{item['id']}`) — {item['key']} {item['scale']}; "
            f"{item['bars']} bars; channels {', '.join(map(str, item['channels']))}; "
            f"{item['status']}; {dependencies}."
        )
    lines.extend(("", "## Issues", ""))
    if report["issues"]:
        for issue in report["issues"]:
            lines.append(
                f"- **{issue['severity']} / {issue['code']}** `{issue['path']}` — "
                f"{issue['message']} Next: {issue['next']}"
            )
    else:
        lines.append("- None.")
    return "\n".join(lines).rstrip() + "\n"


def write_report(report: dict, output: Path) -> Path:
    output = output.expanduser().resolve()
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        (staging / "recipe-catalog.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        (staging / "recipe-catalog.csv").write_text(render_csv(report), encoding="utf-8")
        (staging / "README.md").write_text(render_markdown(report), encoding="utf-8")
        os.replace(staging, output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipe_root", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv or sys.argv[1:])
    report = audit(args.recipe_root)
    if args.output:
        print(f"Wrote: {write_report(report, args.output)}")
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        summary = report["summary"]
        print(
            f"{report['status'].upper()}: {summary['files']} recipes; "
            f"workstations={summary['workstations']}; errors={summary['errors']}; "
            f"warnings={summary['warnings']}; orphans={summary['orphans']}"
        )
        for issue in report["issues"]:
            print(f"{issue['severity'].upper()}: {issue['path']}: {issue['message']}")
            print(f"NEXT: {issue['next']}")
    return 2 if report["summary"]["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
