"""Validate creative review exports and package a durable MPC shortlist."""

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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .creative_review import review_data


STATUSES = {"pending", "keep", "provisional", "reject"}
FIELDS = (
    "rank", "id", "family", "seed", "tempo", "key", "scale",
    "exploration_score", "selection_status", "notes", "observed_at",
    "wave_fingerprint", "hardware_status",
)


def _timestamp(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("creative result export requires exported_at")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"invalid exported_at timestamp: {value!r}") from error
    if parsed.tzinfo is None:
        raise ValueError("exported_at timestamp must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat()


def expected_rows(wave: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    companion = review_data(wave)
    rows = [
        {
            "rank": item["rank"], "id": item["id"], "family": item["family"],
            "seed": item["seed"], "tempo": item["tempo"], "key": item["key"],
            "scale": item["scale"],
            "exploration_score": item["score"]["exploration_score"],
            "selection_status": "pending", "notes": "", "observed_at": "",
            "wave_fingerprint": companion["fingerprint"], "hardware_status": "deferred",
        }
        for item in wave["candidates"]
    ]
    return companion["fingerprint"], rows


def validate_export(wave: dict[str, Any], document: dict[str, Any]) -> dict[str, Any]:
    fingerprint, rows = expected_rows(wave)
    if document.get("schema_version") != 1 or document.get("kind") != "mpc-creative-wave-results":
        raise ValueError(
            "creative result export requires schema_version=1 and kind=mpc-creative-wave-results"
        )
    if document.get("fingerprint") != fingerprint:
        raise ValueError(
            f"wave fingerprint mismatch: expected {fingerprint}, "
            f"got {document.get('fingerprint')!r}"
        )
    exported_at = _timestamp(document.get("exported_at"))
    items = document.get("items")
    if not isinstance(items, list):
        raise ValueError("creative result export items must be a list")
    expected = {row["id"]: row for row in rows}
    observed: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ValueError("each creative result item requires an id")
        identifier = item["id"]
        if identifier in observed:
            raise ValueError(f"duplicate creative result candidate: {identifier}")
        reference = expected.get(identifier)
        if reference is None:
            raise ValueError(f"unknown creative result candidate: {identifier}")
        if item.get("family") != reference["family"] or item.get("seed") != reference["seed"]:
            raise ValueError(f"candidate identity mismatch: {identifier}")
        status = item.get("status")
        notes = item.get("notes")
        if status not in STATUSES:
            raise ValueError(f"invalid selection status for {identifier}: {status!r}")
        if not isinstance(notes, str):
            raise ValueError(f"notes must be text for {identifier}")
        observed[identifier] = {
            "status": status, "notes": notes.strip(), "exported_at": exported_at,
        }
    missing = sorted(set(expected) - set(observed))
    if missing:
        raise ValueError(
            f"creative result export is missing {len(missing)} candidates: "
            + ", ".join(missing[:5])
        )
    return {"exported_at": exported_at, "items": observed}


def merge_results(
    wave: dict[str, Any], documents: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    fingerprint, rows = expected_rows(wave)
    validated = sorted(
        (validate_export(wave, document) for document in documents),
        key=lambda item: item["exported_at"],
    )
    by_id = {row["id"]: row for row in rows}
    note_history: dict[str, list[str]] = {row["id"]: [] for row in rows}
    for session in validated:
        for identifier, result in session["items"].items():
            row = by_id[identifier]
            note = result["notes"]
            if note and note not in note_history[identifier]:
                note_history[identifier].append(note)
            if result["status"] != "pending":
                row["selection_status"] = result["status"]
                row["observed_at"] = result["exported_at"]
    for identifier, notes in note_history.items():
        by_id[identifier]["notes"] = "\n".join(notes)
    return fingerprint, rows


def render_csv(rows: list[dict[str, Any]]) -> str:
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_bundle(
    wave_path: Path,
    documents: list[dict[str, Any]],
    output: Path,
) -> dict[str, Any]:
    wave_path = wave_path.expanduser().resolve()
    output = output.expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"creative shortlist output already exists: {output}")
    wave = json.loads(wave_path.read_text(encoding="utf-8"))
    fingerprint, rows = merge_results(wave, documents)
    source_sessions = sorted({
        validate_export(wave, document)["exported_at"] for document in documents
    })
    selected_ids = {
        row["id"] for row in rows if row["selection_status"] in {"keep", "provisional"}
    }
    selected = [item for item in wave["candidates"] if item["id"] in selected_ids]
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        source_root = wave_path.parent
        for directory in ("Recipes", "Instrument"):
            source = source_root / directory
            if source.is_dir():
                shutil.copytree(source, staging / directory)
        license_file = source_root / "LICENSE-GENERATED-AUDIO.txt"
        if license_file.is_file():
            shutil.copy2(license_file, staging / license_file.name)
        for item in selected:
            source = source_root / item["paths"]["root"]
            target = staging / "Shortlist" / item["paths"]["root"]
            shutil.copytree(source, target)
        report = {
            "schema_version": 1, "kind": "mpc-creative-shortlist",
            "wave_fingerprint": fingerprint, "source_wave": wave_path.name,
            "source_sessions": source_sessions,
            "software_status": "pass", "hardware_status": "deferred",
            "summary": {
                "candidates": len(rows), "kept": sum(row["selection_status"] == "keep" for row in rows),
                "provisional": sum(row["selection_status"] == "provisional" for row in rows),
                "rejected": sum(row["selection_status"] == "reject" for row in rows),
                "pending": sum(row["selection_status"] == "pending" for row in rows),
                "packaged": len(selected),
            },
            "program": wave["program"], "selected": selected, "ledger": rows,
        }
        (staging / "shortlist.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        (staging / "review-ledger.csv").write_text(render_csv(rows), encoding="utf-8")
        summary = report["summary"]
        (staging / "README.md").write_text(
            "# MPC creative shortlist\n\n"
            "Selection merge and package validation: **PASS**\n\n"
            "MPC import, listening, and hardware acceptance: **DEFERRED**\n\n"
            f"Wave `{fingerprint}` has {summary['kept']} keep, {summary['provisional']} "
            f"provisional, {summary['rejected']} reject, and {summary['pending']} pending "
            f"verdicts. {summary['packaged']} candidates are copied under `Shortlist/`.\n\n"
            "Selection verdicts prioritize future listening; they never become hardware pass status.\n",
            encoding="utf-8",
        )
        checklist = [
            "# Creative shortlist — MPC checklist", "",
            "All items remain hardware-pending.", "",
        ]
        for item in selected:
            relative = f"Shortlist/{item['paths']['root']}"
            status = next(row["selection_status"] for row in rows if row["id"] == item["id"])
            checklist.extend((
                f"## {item['name']} / seed {item['seed']} ({status})", "",
                f"- [ ] Import `{relative}/idea.mid`.",
                f"- [ ] Compare `{relative}/Sequences/main.mid` and `main-b.mid`.",
                "- [ ] Assign sounds, save/reload, and record a hardware verdict.",
                "", "Hardware: [ ] pass  [ ] warn  [ ] fail", "Notes:", "",
            ))
        if not selected:
            checklist.append("No keep or provisional candidates were exported yet.\n")
        (staging / "HARDWARE_CHECKLIST.md").write_text(
            "\n".join(checklist).rstrip() + "\n", encoding="utf-8"
        )
        names = {
            str(path.relative_to(staging)) for path in staging.rglob("*") if path.is_file()
        }
        names.update({"COPY_MANIFEST.txt", "checksums.json"})
        (staging / "COPY_MANIFEST.txt").write_text(
            "# Copy this folder as a unit; do not flatten it.\n" + "\n".join(sorted(names)) + "\n",
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


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    initialize = commands.add_parser("init", help="write a fully pending durable ledger bundle")
    initialize.add_argument("wave", type=Path)
    initialize.add_argument("--output", type=Path, required=True)
    importing = commands.add_parser("import", help="merge exports and package keep/provisional candidates")
    importing.add_argument("wave", type=Path)
    importing.add_argument("results", type=Path, nargs="+")
    importing.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    documents = [] if args.command == "init" else [
        json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))
        for path in args.results
    ]
    report = _write_bundle(args.wave, documents, args.output)
    summary = report["summary"]
    print(f"Wrote: {args.output.expanduser().resolve()}")
    print(
        f"Selections: keep={summary['kept']} provisional={summary['provisional']} "
        f"reject={summary['rejected']} pending={summary['pending']}"
    )
    print(f"Packaged candidates: {summary['packaged']}; hardware status: deferred")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
