#!/usr/bin/env python3
"""Conservatively clean a writable copy of an MPC SD-card tree.

The script is a dry run unless ``--execute`` is supplied. It never removes a
file from the redundant Samples From Mars ``Instruments`` tree unless an
identical byte-for-byte counterpart exists one directory level higher.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT_TEST_PROGRAMS = (
    "Testing keygroup",
    "Star Piano TEST",
    "Star Piano C3 RAW",
    "Star Piano C3 STEREO",
)


@dataclass
class Report:
    root: str
    execute: bool
    duplicate_files: int = 0
    duplicate_bytes: int = 0
    unique_files_retained: int = 0
    metadata_files: int = 0
    program_bundles: int = 0
    directories_removed: int = 0


def digest(path: Path) -> bytes:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.digest()


def identical(left: Path, right: Path) -> bool:
    return (
        right.is_file()
        and left.stat().st_size == right.stat().st_size
        and digest(left) == digest(right)
    )


def remove_metadata(root: Path, execute: bool, report: Report) -> None:
    for path in sorted(root.rglob(".DS_Store")):
        report.metadata_files += 1
        if execute:
            path.unlink()


def move_root_test_programs(root: Path, execute: bool, report: Report) -> None:
    destination = root / "Programs" / "Keygroups" / "Testing"
    for name in ROOT_TEST_PROGRAMS:
        program = root / f"{name}.xpm"
        data = root / f"{name}_[ProgramData]"
        existing = [path for path in (program, data) if path.exists()]
        if not existing:
            continue
        if len(existing) != 2:
            raise RuntimeError(f"incomplete root program bundle: {name}")
        conflicts = [destination / path.name for path in existing]
        if any(path.exists() for path in conflicts):
            raise RuntimeError(f"destination already exists for root program: {name}")
        report.program_bundles += 1
        if execute:
            destination.mkdir(parents=True, exist_ok=True)
            for path in existing:
                shutil.move(str(path), destination / path.name)


def remove_redundant_instruments(root: Path, execute: bool, report: Report) -> None:
    samples = root / "Samples" / "Samples From Mars"
    redundant = samples / "Instruments"
    if not redundant.is_dir():
        return

    for path in sorted(item for item in redundant.rglob("*") if item.is_file()):
        counterpart = samples / path.relative_to(redundant)
        if identical(path, counterpart):
            report.duplicate_files += 1
            report.duplicate_bytes += path.stat().st_size
            if execute:
                path.unlink()
        else:
            report.unique_files_retained += 1

    if execute:
        directories = sorted(
            (item for item in redundant.rglob("*") if item.is_dir()),
            key=lambda item: len(item.parts),
            reverse=True,
        )
        for directory in directories + [redundant]:
            try:
                directory.rmdir()
            except OSError:
                continue
            report.directories_removed += 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, help="writable MPC SD-card backup")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    root = args.root.expanduser().resolve()
    if not root.is_dir():
        parser.error(f"backup root does not exist: {root}")

    report = Report(root=str(root), execute=args.execute)
    remove_metadata(root, args.execute, report)
    move_root_test_programs(root, args.execute, report)
    remove_redundant_instruments(root, args.execute, report)

    output = json.dumps(asdict(report), indent=2)
    print(output)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
