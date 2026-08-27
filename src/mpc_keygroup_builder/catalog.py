"""Build and query a metadata-only MPC program catalog."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .model import ProgramModel, from_xpm
from .roles import role_matches


def _location(path: str) -> tuple[str, str]:
    parts = Path(path).parts
    if "Samples From Mars" in parts:
        index = parts.index("Samples From Mars")
        collection = parts[index + 1] if index + 1 < len(parts) - 1 else ""
        category = parts[index + 2] if index + 2 < len(parts) - 1 else ""
        return collection, category
    return (parts[-3] if len(parts) >= 3 else "", parts[-2] if len(parts) >= 2 else "")


def _model_fields(program: ProgramModel) -> dict[str, Any]:
    layers = [layer for zone in program.zones for layer in zone.layers]
    roles = Counter(zone.role for zone in program.zones)
    note_lows = [zone.low_note for zone in program.zones if zone.low_note is not None]
    note_highs = [zone.high_note for zone in program.zones if zone.high_note is not None]
    pads = [zone.pad for zone in program.zones if zone.pad is not None]
    banks = sorted({chr(ord("A") + (pad - 1) // 16) for pad in pads})
    report = program.validate()
    return {
        "name": program.name,
        "program_type": program.kind,
        "source_format": program.source_format,
        "zone_count": len(program.zones),
        "layer_count": len(layers),
        "sample_count": len({layer.sample for layer in layers}),
        "semantic_roles": dict(sorted(roles.items())),
        "note_range": (
            {"low": min(note_lows), "high": max(note_highs)}
            if note_lows and note_highs
            else None
        ),
        "pad_range": {"low": min(pads), "high": max(pads)} if pads else None,
        "populated_banks": banks,
        "model_validation": report,
    }


def _ledger_fields(row: dict[str, str]) -> dict[str, str]:
    return {
        key: row.get(key, "")
        for key in (
            "structural_status",
            "semantic_verdict",
            "hardware_status",
            "favorite",
            "scratchpad_role",
            "notes",
        )
    }


def build_catalog(ledger: Path, program_root: Path) -> dict[str, Any]:
    if not program_root.is_dir():
        raise ValueError(f"program root is not a directory: {program_root}")
    with ledger.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    resolved_root = program_root.resolve()
    programs = []
    for row in rows:
        relative = row.get("path", "")
        collection, category = _location(relative)
        entry: dict[str, Any] = {
            "path": relative,
            "collection": collection,
            "category": category,
            **_ledger_fields(row),
        }
        path = (program_root / relative).resolve()
        try:
            path.relative_to(resolved_root)
        except ValueError:
            entry.update(
                {
                    "index_status": "error",
                    "name": Path(relative).stem,
                    "program_type": row.get("program_type", "").casefold(),
                    "source_format": row.get("format", ""),
                    "index_error": "ledger path escapes the program root",
                }
            )
            programs.append(entry)
            continue
        try:
            is_file = path.is_file()
        except OSError as error:
            entry.update(
                {
                    "index_status": "error",
                    "name": path.stem,
                    "program_type": row.get("program_type", "").casefold(),
                    "source_format": row.get("format", ""),
                    "index_error": f"cannot access program file: {error}",
                }
            )
            programs.append(entry)
            continue
        if not is_file:
            entry.update(
                {
                    "index_status": "missing",
                    "name": Path(relative).stem,
                    "program_type": row.get("program_type", "").casefold(),
                    "source_format": row.get("format", ""),
                    "index_error": "program file is missing",
                }
            )
        else:
            try:
                entry.update(_model_fields(from_xpm(path)))
                validation = entry["model_validation"]
                entry["index_status"] = "warn" if validation["warnings"] else "pass"
                entry["index_error"] = ""
            except Exception as error:
                entry.update(
                    {
                        "index_status": "error",
                        "name": path.stem,
                        "program_type": row.get("program_type", "").casefold(),
                        "source_format": row.get("format", ""),
                        "index_error": str(error),
                    }
                )
        programs.append(entry)
    statuses = Counter(item["index_status"] for item in programs)
    types = Counter(item.get("program_type", "unknown") or "unknown" for item in programs)
    hardware = Counter(item.get("hardware_status", "") or "unset" for item in programs)
    favorites = Counter(item.get("favorite", "") or "unset" for item in programs)
    semantic_roles: Counter[str] = Counter()
    for item in programs:
        semantic_roles.update(item.get("semantic_roles", {}))
    return {
        "schema_version": 1,
        "ledger": str(ledger.resolve()),
        "program_root": str(program_root.resolve()),
        "summary": {
            "programs": len(programs),
            "index_status": dict(sorted(statuses.items())),
            "program_types": dict(sorted(types.items())),
            "hardware_status": dict(sorted(hardware.items())),
            "favorites": dict(sorted(favorites.items())),
            "semantic_roles": dict(sorted(semantic_roles.items())),
        },
        "programs": programs,
    }


def query_catalog(
    catalog: dict[str, Any],
    *,
    program_type: str | None = None,
    role: str | None = None,
    hardware: str | None = None,
    favorite: str | None = None,
    search: str | None = None,
) -> list[dict[str, Any]]:
    programs = list(catalog.get("programs", []))
    if program_type:
        programs = [
            item
            for item in programs
            if str(item.get("program_type", "")).casefold() == program_type.casefold()
        ]
    if hardware:
        programs = [
            item
            for item in programs
            if str(item.get("hardware_status", "")).casefold() == hardware.casefold()
        ]
    if favorite:
        programs = [
            item
            for item in programs
            if str(item.get("favorite", "")).casefold() == favorite.casefold()
        ]
    if role:
        programs = [
            item
            for item in programs
            if any(role_matches(actual, role) for actual in item.get("semantic_roles", {}))
            or role.casefold() in str(item.get("scratchpad_role", "")).casefold()
        ]
    if search:
        needle = search.casefold()
        programs = [
            item
            for item in programs
            if any(
                needle in str(item.get(field, "")).casefold()
                for field in ("path", "name", "collection", "category", "notes")
            )
        ]
    return programs


def _render_query(programs: list[dict[str, Any]], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(programs, indent=2) + "\n"
    return "".join(
        f"{item['path']} | {item.get('program_type', '-')} | "
        f"index={item.get('index_status', '-')} hardware={item.get('hardware_status') or '-'} "
        f"favorite={item.get('favorite') or '-'}\n"
        for item in programs
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("ledger", type=Path)
    build.add_argument("--program-root", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--fail-on-error", action="store_true")
    query = subparsers.add_parser("query")
    query.add_argument("catalog", type=Path)
    query.add_argument("--type", dest="program_type")
    query.add_argument("--role")
    query.add_argument("--hardware")
    query.add_argument("--favorite")
    query.add_argument("--search")
    query.add_argument("--format", choices=("text", "json"), default="text")
    query.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "build":
        catalog = build_catalog(
            args.ledger.expanduser().resolve(), args.program_root.expanduser().resolve()
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
        summary = catalog["summary"]
        print(f"Wrote: {args.output}")
        print(
            f"Programs: {summary['programs']}; "
            + ", ".join(
                f"{key}={value}" for key, value in summary["index_status"].items()
            )
        )
        return 2 if args.fail_on_error and summary["index_status"].get("error", 0) else 0
    with args.catalog.open(encoding="utf-8") as stream:
        catalog = json.load(stream)
    programs = query_catalog(
        catalog,
        program_type=args.program_type,
        role=args.role,
        hardware=args.hardware,
        favorite=args.favorite,
        search=args.search,
    )
    rendered = _render_query(programs, args.format)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
