#!/usr/bin/env python3
"""Inventory MPC XPM programs and validate their local sample references."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable


AUDIO_SUFFIXES = {".wav", ".aif", ".aiff"}


@dataclass
class ProgramResult:
    path: str
    format: str
    program_type: str
    references: int
    resolved: int
    missing: list[str]
    ambiguous: list[str]
    zero_byte: list[str]
    status: str


@lru_cache(maxsize=None)
def audio_index(root: Path, *, recursive: bool) -> tuple[dict[str, list[Path]], dict[str, list[Path]]]:
    paths = root.rglob("*") if recursive else root.glob("*")
    audio = [path for path in paths if path.is_file() and path.suffix.lower() in AUDIO_SUFFIXES]
    by_name: dict[str, list[Path]] = {}
    by_stem: dict[str, list[Path]] = {}
    for path in audio:
        by_name.setdefault(path.name.casefold(), []).append(path)
        by_stem.setdefault(path.stem.casefold(), []).append(path)
    return by_name, by_stem


def unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def walk_values(value: Any, key: str) -> Iterable[str]:
    if isinstance(value, dict):
        for child_key, child in value.items():
            if child_key == key and isinstance(child, str) and child:
                yield child
            yield from walk_values(child, key)
    elif isinstance(value, list):
        for child in value:
            yield from walk_values(child, key)


def parse_gzip_json(path: Path) -> tuple[str, list[str], Path, bool]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        text = stream.read()
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON payload")
    payload = json.loads(text[start:])
    data = payload.get("data", {})
    if isinstance(data.get("keygroup"), dict) and data["keygroup"].get("numKeygroups", 0):
        program_type = "Keygroup"
    elif isinstance(data.get("drum"), dict):
        program_type = "Drum"
    else:
        program_type = str(data.get("type", "Unknown"))
    references: list[str] = []
    if isinstance(data.get("samples"), list):
        references = unique(
            entry.get("path", "") for entry in data["samples"] if isinstance(entry, dict)
        )
    if not references:
        references = unique(walk_values(data.get("drum", {}), "sampleFile"))
    sample_root = path.with_name(f"{path.stem}_[ProgramData]")
    return program_type, references, sample_root, False


def parse_xml(path: Path) -> tuple[str, list[str], Path, bool]:
    root = ET.parse(path).getroot()
    program = root.find("Program")
    program_type = program.get("type", "Unknown") if program is not None else "Unknown"
    references: list[str] = []
    for layer in root.iter("Layer"):
        sample_file = (layer.findtext("SampleFile") or "").strip()
        sample_name = (layer.findtext("SampleName") or "").strip()
        references.append(sample_file or sample_name)
    if not references:
        references.extend((node.text or "").strip() for node in root.iter("SampleFile"))
        references.extend((node.text or "").strip() for node in root.iter("SampleName"))
    return program_type, unique(references), path.parent, True


def resolve_references(
    references: list[str], sample_root: Path, *, recursive: bool
) -> tuple[int, list[str], list[str], list[str]]:
    if not sample_root.is_dir():
        return 0, references, [], []
    by_name, by_stem = audio_index(sample_root, recursive=recursive)
    resolved = 0
    missing: list[str] = []
    ambiguous: list[str] = []
    zero: list[str] = []
    for reference in references:
        key = Path(reference).name.casefold()
        matches = by_name.get(key, [])
        if not matches:
            matches = by_stem.get(Path(reference).stem.casefold(), [])
        if not matches:
            missing.append(reference)
        elif len(matches) > 1:
            ambiguous.append(reference)
        else:
            resolved += 1
            if matches[0].stat().st_size == 0:
                zero.append(reference)
    return resolved, missing, ambiguous, zero


def audit_program(path: Path, card_root: Path) -> ProgramResult:
    try:
        if path.read_bytes()[:2] == b"\x1f\x8b":
            format_name = "gzip-json"
            program_type, references, sample_root, recursive = parse_gzip_json(path)
        else:
            format_name = "xml"
            program_type, references, sample_root, recursive = parse_xml(path)
        resolved, missing, ambiguous, zero = resolve_references(
            references, sample_root, recursive=recursive
        )
        status = "pass" if references and not (missing or ambiguous or zero) else "fail"
        if not references:
            status = "no-references"
        return ProgramResult(
            path=str(path.relative_to(card_root)),
            format=format_name,
            program_type=program_type,
            references=len(references),
            resolved=resolved,
            missing=missing,
            ambiguous=ambiguous,
            zero_byte=zero,
            status=status,
        )
    except Exception as error:
        return ProgramResult(
            path=str(path.relative_to(card_root)),
            format="unreadable",
            program_type="Unknown",
            references=0,
            resolved=0,
            missing=[str(error)],
            ambiguous=[],
            zero_byte=[],
            status="unreadable",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--csv", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    programs = sorted(root.rglob("*.xpm"))
    results = [audit_program(path, root) for path in programs]
    status = Counter(item.status for item in results)
    formats = Counter(item.format for item in results)
    types = Counter(item.program_type for item in results)
    summary = {
        "root": str(root),
        "programs": len(results),
        "status": dict(sorted(status.items())),
        "formats": dict(sorted(formats.items())),
        "types": dict(sorted(types.items())),
        "missing_references": sum(len(item.missing) for item in results),
        "ambiguous_references": sum(len(item.ambiguous) for item in results),
        "zero_byte_references": sum(len(item.zero_byte) for item in results),
    }
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps({"summary": summary, "programs": [asdict(item) for item in results]}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "status", "program_type", "format", "references", "resolved",
                "missing", "ambiguous", "zero_byte", "path",
            ),
        )
        writer.writeheader()
        for item in results:
            row = asdict(item)
            for field in ("missing", "ambiguous", "zero_byte"):
                row[field] = " | ".join(row[field])
            writer.writerow({field: row[field] for field in writer.fieldnames})
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
