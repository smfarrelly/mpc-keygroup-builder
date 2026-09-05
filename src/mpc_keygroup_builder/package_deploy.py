"""Transaction-safe deployment for self-contained MPC program packages."""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class FileRecord:
    relative: str
    bytes: int
    sha256: str


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory(root: Path) -> tuple[FileRecord, ...]:
    if not root.is_dir():
        raise NotADirectoryError(f"package directory is missing: {root}")
    records = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"package may not contain symbolic links: {path}")
        if path.is_file():
            records.append(
                FileRecord(
                    relative=path.relative_to(root).as_posix(),
                    bytes=path.stat().st_size,
                    sha256=sha256(path),
                )
            )
    if not records:
        raise ValueError(f"package contains no files: {root}")
    return tuple(records)


def package_sha256(records: tuple[FileRecord, ...]) -> str:
    digest = hashlib.sha256()
    for record in records:
        digest.update(record.relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(record.bytes).encode("ascii"))
        digest.update(b"\0")
        digest.update(record.sha256.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def staging_path(destination: Path) -> Path:
    return destination.parent / f".{destination.name}.mpc-staging"


def _paths_overlap(left: Path, right: Path) -> bool:
    return left == right or left.is_relative_to(right) or right.is_relative_to(left)


def _same_inventory(
    left: tuple[FileRecord, ...], right: tuple[FileRecord, ...]
) -> bool:
    return left == right


def build_plan(source: Path, destination: Path) -> dict[str, object]:
    source = source.expanduser()
    destination = destination.expanduser()
    if source.is_symlink():
        raise ValueError(f"package source may not be a symbolic link: {source}")
    if destination.is_symlink():
        raise ValueError(f"package destination may not be a symbolic link: {destination}")
    source = source.resolve()
    destination = destination.resolve()
    stage = staging_path(destination).resolve()
    if _paths_overlap(source, destination):
        raise ValueError(
            f"package source and destination must not overlap: {source} and {destination}"
        )
    if _paths_overlap(source, stage):
        raise ValueError(
            f"package source and staging path must not overlap: {source} and {stage}"
        )
    source_files = inventory(source)
    if destination.exists():
        action = (
            "unchanged"
            if destination.is_dir()
            and _same_inventory(source_files, inventory(destination))
            else "conflict"
        )
    else:
        action = "create"
    return {
        "format": 1,
        "source": str(source),
        "destination": str(destination),
        "staging": str(staging_path(destination)),
        "action": action,
        "files": len(source_files),
        "bytes": sum(record.bytes for record in source_files),
        "package_sha256": package_sha256(source_files),
        "inventory": [asdict(record) for record in source_files],
    }


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        try:
            os.fsync(descriptor)
        except OSError as error:
            if error.errno not in {errno.EINVAL, errno.ENOTSUP}:
                raise
    finally:
        os.close(descriptor)


def write_probe(parent: Path, size_bytes: int) -> str | None:
    if size_bytes < 0:
        raise ValueError("write probe size may not be negative")
    if size_bytes == 0:
        return None
    if not parent.is_dir():
        raise NotADirectoryError(f"destination parent is missing: {parent}")
    descriptor, name = tempfile.mkstemp(prefix=".mpc-write-probe-", dir=parent)
    path = Path(name)
    expected = hashlib.sha256()
    remaining = size_bytes
    block = bytes(min(CHUNK_SIZE, size_bytes))
    try:
        with os.fdopen(descriptor, "wb") as stream:
            while remaining:
                chunk = block[: min(len(block), remaining)]
                stream.write(chunk)
                expected.update(chunk)
                remaining -= len(chunk)
            stream.flush()
            os.fsync(stream.fileno())
        actual = sha256(path)
        if actual != expected.hexdigest():
            raise OSError(f"destination write probe verification failed: {parent}")
        path.unlink()
        _fsync_directory(parent)
        return actual
    finally:
        path.unlink(missing_ok=True)


def copy_file_verified(source: Path, target: Path, expected_sha256: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{target.name}-", dir=target.parent)
    temporary = Path(name)
    try:
        with source.open("rb") as input_stream, os.fdopen(descriptor, "wb") as output_stream:
            shutil.copyfileobj(input_stream, output_stream, length=CHUNK_SIZE)
            output_stream.flush()
            os.fsync(output_stream.fileno())
        shutil.copystat(source, temporary)
        if sha256(temporary) != expected_sha256:
            raise OSError(f"staged copy verification failed: {source}")
        os.replace(temporary, target)
        _fsync_directory(target.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _records_from_plan(plan: dict[str, object]) -> tuple[FileRecord, ...]:
    values = plan["inventory"]
    if not isinstance(values, list):
        raise TypeError("invalid package plan inventory")
    return tuple(FileRecord(**value) for value in values)


def apply_package(
    plan: dict[str, object], *, resume: bool = False, probe_bytes: int = 64 * CHUNK_SIZE
) -> dict[str, object]:
    if plan["action"] == "unchanged":
        return {**plan, "applied": False, "status": "unchanged"}
    if plan["action"] != "create":
        raise FileExistsError(
            f"destination exists with different content: {plan['destination']}"
        )
    source = Path(str(plan["source"]))
    destination = Path(str(plan["destination"]))
    stage = Path(str(plan["staging"]))
    if destination.exists():
        raise FileExistsError(f"destination appeared after planning: {destination}")
    if stage.exists() and not resume:
        raise FileExistsError(
            f"staging directory already exists; inspect it and rerun with --resume: {stage}"
        )
    if stage.is_symlink():
        raise ValueError(f"staging path may not be a symbolic link: {stage}")
    if stage.exists() and not stage.is_dir():
        raise FileExistsError(f"staging path is not a directory: {stage}")
    write_probe(destination.parent, probe_bytes)
    stage.mkdir(exist_ok=resume)
    records = _records_from_plan(plan)
    for path in stage.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"staging directory may not contain symbolic links: {path}")
    expected_names = {record.relative for record in records}
    existing_names = {
        path.relative_to(stage).as_posix()
        for path in stage.rglob("*")
        if path.is_file()
    }
    extras = sorted(existing_names - expected_names)
    if extras:
        raise ValueError(f"staging directory contains unexpected files: {extras[0]}")
    for record in records:
        source_file = source / record.relative
        target_file = stage / record.relative
        if (
            target_file.is_file()
            and target_file.stat().st_size == record.bytes
            and sha256(target_file) == record.sha256
        ):
            continue
        copy_file_verified(source_file, target_file, record.sha256)
    staged = inventory(stage)
    if not _same_inventory(records, staged):
        raise OSError(f"staged package verification failed: {stage}")
    _fsync_directory(stage)
    os.replace(stage, destination)
    _fsync_directory(destination.parent)
    deployed = inventory(destination)
    if not _same_inventory(records, deployed):
        raise OSError(f"deployed package verification failed: {destination}")
    return {
        **plan,
        "applied": True,
        "status": "deployed",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--probe-mib",
        type=int,
        default=64,
        help="temporary sustained-write probe size before apply; use 0 to skip",
    )
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.resume and not args.apply:
        parser.error("--resume requires --apply")
    plan = build_plan(args.source, args.destination)
    result = plan
    if args.apply:
        result = apply_package(
            plan, resume=args.resume, probe_bytes=args.probe_mib * CHUNK_SIZE
        )
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        f"{str(result.get('status', result['action'])).upper()}: "
        f"files={result['files']} bytes={result['bytes']} "
        f"sha256={result['package_sha256']}"
    )
    if not args.apply:
        print("Dry run only; no files changed.")
    return 2 if result["action"] == "conflict" else 0


if __name__ == "__main__":
    raise SystemExit(main())
