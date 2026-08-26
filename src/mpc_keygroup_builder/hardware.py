"""Validate and apply MPC hardware-session results to the program ledger."""

from __future__ import annotations

import argparse
import csv
import json
import os
import stat
import tempfile
import tomllib
from pathlib import Path

from .candidates import load_manifest


REQUIRED_FIELDS = {
    "path",
    "hardware_status",
    "favorite",
    "scratchpad_role",
    "notes",
}
ALLOWED_STATUSES = {"untested", "pass", "warn", "fail"}
ALLOWED_FAVORITES = {"", "yes", "no", "provisional"}
RESULT_FIELDS = {"path", "hardware_status", "favorite", "scratchpad_role", "notes"}


def load_results(path: Path) -> list[dict[str, str]]:
    with path.open("rb") as stream:
        document = tomllib.load(stream)
    values = document.get("results")
    if not isinstance(values, list) or not values:
        raise ValueError("result file must contain at least one [[results]] table")
    results = []
    seen = set()
    for index, value in enumerate(values, 1):
        if not isinstance(value, dict):
            raise ValueError(f"result {index} must be a table")
        unknown = set(value) - RESULT_FIELDS
        if unknown:
            raise ValueError(f"result {index} has unknown fields: {', '.join(sorted(unknown))}")
        missing = RESULT_FIELDS - set(value)
        if missing:
            raise ValueError(
                f"result {index} is missing fields: {', '.join(sorted(missing))}"
            )
        if not all(isinstance(item, str) for item in value.values()):
            raise ValueError(f"result {index} values must be strings")
        if value["path"] in seen:
            raise ValueError(f"duplicate result path: {value['path']}")
        if value["hardware_status"] not in ALLOWED_STATUSES:
            raise ValueError(f"invalid hardware_status for {value['path']}: {value['hardware_status']}")
        if value.get("favorite", "") not in ALLOWED_FAVORITES:
            raise ValueError(f"invalid favorite for {value['path']}: {value['favorite']}")
        if value["hardware_status"] != "untested" and not value["notes"].strip():
            raise ValueError(f"listening notes are required for {value['path']}")
        seen.add(value["path"])
        results.append(value)
    return results


def update_ledger(
    ledger: Path, results: list[dict[str, str]], *, write: bool = False
) -> list[dict[str, object]]:
    raw = ledger.read_bytes()
    line_ending = "\r\n" if b"\r\n" in raw else "\n"
    with ledger.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    missing = REQUIRED_FIELDS - set(fieldnames)
    if missing:
        raise ValueError(f"ledger is missing fields: {', '.join(sorted(missing))}")
    indexes = {row["path"]: index for index, row in enumerate(rows)}
    changes = []
    for result in results:
        path = result["path"]
        if path not in indexes:
            raise ValueError(f"program path is not present in ledger: {path}")
        row = rows[indexes[path]]
        before = {field: row[field] for field in RESULT_FIELDS - {"path"}}
        for field in RESULT_FIELDS - {"path"}:
            if field in result:
                row[field] = result[field]
        after = {field: row[field] for field in RESULT_FIELDS - {"path"}}
        changes.append({"path": path, "before": before, "after": after})

    if write:
        mode = stat.S_IMODE(ledger.stat().st_mode)
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{ledger.name}-", dir=ledger.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator=line_ending)
                writer.writeheader()
                writer.writerows(rows)
            temporary.chmod(mode)
            os.replace(temporary, ledger)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
    return changes


def initialize_results(ledger: Path, manifest: Path, output: Path) -> int:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite hardware-session file: {output}")
    candidates = load_manifest(manifest)["candidates"]
    with ledger.open(newline="", encoding="utf-8") as stream:
        rows = {row["path"]: row for row in csv.DictReader(stream)}
    blocks = [
        "# Edit every result after listening on hardware. Validate with",
        "# mpc-hardware-results before applying with --apply.",
        "",
    ]
    for candidate in candidates:
        row = rows.get(candidate["ledger_path"])
        if row is None:
            raise ValueError(f"candidate is missing from ledger: {candidate['ledger_path']}")
        values = {
            "path": row["path"],
            "hardware_status": row["hardware_status"],
            "favorite": row["favorite"],
            "scratchpad_role": row["scratchpad_role"],
            "notes": row["notes"],
        }
        blocks.append("[[results]]")
        blocks.extend(f"{key} = {json.dumps(value)}" for key, value in values.items())
        blocks.append("")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(blocks), encoding="utf-8")
    return len(candidates)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("results", type=Path, help="TOML file containing [[results]] tables")
    parser.add_argument("--apply", action="store_true", help="write validated changes")
    args = parser.parse_args()
    results = load_results(args.results)
    changes = update_ledger(args.ledger, results, write=args.apply)
    for change in changes:
        after = change["after"]
        print(
            f"{change['path']}: status={after['hardware_status']} "
            f"favorite={after['favorite'] or '-'} role={after['scratchpad_role'] or '-'}"
        )
    print("Applied changes." if args.apply else "Dry run only; pass --apply to update the ledger.")
    return 0


def init_main() -> int:
    parser = argparse.ArgumentParser(description="Initialize an editable MPC hardware-session TOML file")
    parser.add_argument("ledger", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    count = initialize_results(args.ledger, args.manifest, args.output)
    print(f"Wrote {count} hardware-session entries: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
