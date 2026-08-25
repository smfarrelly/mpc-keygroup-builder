#!/usr/bin/env python3
"""Build a lean, self-contained MPC SD image from candidate XPMs."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path


AUDIO_SUFFIXES = {".wav", ".aif", ".aiff"}


def audio_index(root: Path) -> tuple[dict[str, list[Path]], dict[str, list[Path]]]:
    by_name: dict[str, list[Path]] = {}
    by_stem: dict[str, list[Path]] = {}
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in AUDIO_SUFFIXES:
            by_name.setdefault(path.name.casefold(), []).append(path)
            by_stem.setdefault(path.stem.casefold(), []).append(path)
    return by_name, by_stem


def resolve(reference: str, indexes: tuple[dict[str, list[Path]], dict[str, list[Path]]]) -> Path:
    by_name, by_stem = indexes
    name = Path(reference).name
    matches = by_name.get(name.casefold(), []) or by_stem.get(Path(name).stem.casefold(), [])
    if len(matches) != 1:
        raise ValueError(f"expected one sample for {reference!r}, found {len(matches)}")
    return matches[0]


def xml_references(path: Path) -> list[str]:
    root = ET.parse(path).getroot()
    values = []
    for layer in root.iter("Layer"):
        reference = (layer.findtext("SampleFile") or layer.findtext("SampleName") or "").strip()
        if reference:
            values.append(reference)
    return list(dict.fromkeys(values))


def copy_keygroup(source: Path, destination: Path) -> int:
    data_source = source.with_name(f"{source.stem}_[ProgramData]")
    data_destination = destination.with_name(f"{destination.stem}_[ProgramData]")
    if not data_source.is_dir():
        raise ValueError(f"missing ProgramData: {data_source}")
    shutil.copy2(source, destination)
    shutil.copytree(data_source, data_destination, copy_function=shutil.copy2)
    return sum(1 for path in data_destination.iterdir() if path.is_file())


def copy_drum(source: Path, destination: Path) -> int:
    indexes = audio_index(source.parent)
    references = xml_references(source)
    shutil.copy2(source, destination)
    for reference in references:
        sample = resolve(reference, indexes)
        target = destination.parent / sample.name
        if target.exists() and target.read_bytes() != sample.read_bytes():
            raise ValueError(f"conflicting destination sample: {target.name}")
        if not target.exists():
            shutil.copy2(sample, target)
    return len(references)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--card-root", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    card_root = args.card_root.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if output.exists():
        parser.error(f"output already exists: {output}")
    with args.ledger.expanduser().open(encoding="utf-8", newline="") as stream:
        candidates = [
            row for row in csv.DictReader(stream) if row["scratchpad_role"].startswith("candidate:")
        ]
    if not candidates:
        parser.error("ledger contains no Scratchpad candidates")
    for relative in (
        "Exports",
        "Programs/Clips/FG Vinyl Candidates",
        "Projects/Ideas",
        "Projects/Jams",
        "Projects/Songs",
        "Samples/MIDI Grooves",
        "Samples/My Samples",
        "Samples/Recordings",
    ):
        (output / relative).mkdir(parents=True, exist_ok=True)
    records = []
    for row in candidates:
        source = card_root / row["path"]
        role = row["scratchpad_role"].split(":", 1)[1].replace("/", "-").title()
        with source.open("rb") as stream:
            is_keygroup = stream.read(2) == b"\x1f\x8b"
        if is_keygroup:
            destination_dir = output / "Programs" / "Keygroups" / "FG Scratchpad Candidates" / role
        else:
            destination_dir = (
                output / "Programs" / "Drum Programs" / "FG Vinyl Candidates" / source.stem
            )
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination = destination_dir / source.name
        samples = (
            copy_keygroup(source, destination)
            if is_keygroup
            else copy_drum(source, destination)
        )
        records.append(
            {
                "role": role,
                "program": source.name,
                "type": "Keygroup" if is_keygroup else "Drum",
                "samples": samples,
                "source": row["path"],
            }
        )
    manifest = {
        "purpose": "Lean FG Vinyl Scratchpad v0.1 MPC SD image for hardware candidate testing",
        "programs": records,
    }
    (output / "CANDIDATES.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (output / "README.txt").write_text(
        "FG Vinyl Scratchpad v0.1 lean SD image\n\n"
        "Copy the CONTENTS of this folder to a blank MPC SD card.\n"
        "These programs pass local structural and semantic checks but remain hardware-untested.\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
