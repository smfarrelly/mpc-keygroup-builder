"""Safely ingest controlled MPC XPJ captures and companion data folders."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_PROJECTS = ("Key37_Routing_Baseline.xpj", "Key37_Routing_Changed.xpj")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalized(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def _find_project(source: Path, filename: str) -> Path:
    matches = [path for path in source.rglob("*") if path.is_file() and path.name.casefold() == filename.casefold()]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {filename!r} below {source}, found {len(matches)}")
    if matches[0].is_symlink():
        raise ValueError(f"capture project cannot be a symbolic link: {matches[0]}")
    return matches[0]


def _find_project_data(project: Path) -> Path:
    stem = _normalized(project.stem)
    matches = []
    for path in project.parent.iterdir():
        normalized = _normalized(path.name)
        if path.is_dir() and normalized.startswith(stem) and "projectdata" in normalized:
            matches.append(path)
    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one ProjectData folder beside {project.name}, found {len(matches)}"
        )
    return matches[0]


def _regular_files(path: Path) -> list[Path]:
    if path.is_symlink():
        raise ValueError(f"capture artifact cannot contain symbolic links: {path}")
    if path.is_file():
        return [path]
    files = []
    for item in sorted(path.rglob("*")):
        if item.is_symlink():
            raise ValueError(f"capture artifact cannot contain symbolic links: {item}")
        if item.is_file():
            files.append(item)
    return files


def _manifest_entries(source: Path, destination: Path, label: str) -> list[dict[str, object]]:
    source_files = _regular_files(source)
    entries = []
    for source_file in source_files:
        relative = Path(source.name) / source_file.relative_to(source) if source.is_dir() else Path(source.name)
        destination_file = destination / relative
        source_hash = sha256(source_file)
        destination_hash = sha256(destination_file)
        if source_hash != destination_hash or source_file.stat().st_size != destination_file.stat().st_size:
            raise OSError(f"capture verification failed: {source_file}")
        entries.append(
            {
                "project": label,
                "source": str(source_file.resolve()),
                "destination": str(relative),
                "bytes": source_file.stat().st_size,
                "sha256": source_hash,
            }
        )
    return entries


def capture_projects(
    source: Path,
    destination: Path,
    project_names: tuple[str, str] = DEFAULT_PROJECTS,
    *,
    changed_setting: str = "Key Ranges: Drum Split",
) -> dict[str, object]:
    source = source.expanduser().resolve()
    destination = destination.expanduser().resolve()
    if not source.is_dir():
        raise ValueError(f"capture source is not a directory: {source}")
    if destination == source or destination.is_relative_to(source):
        raise ValueError("capture destination must be outside the source directory")
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise FileExistsError(f"capture destination must not exist or must be empty: {destination}")

    artifacts = []
    for name in project_names:
        project = _find_project(source, name)
        project_data = _find_project_data(project)
        _regular_files(project)
        _regular_files(project_data)
        artifacts.append((project.stem, project, project_data))

    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent))
    try:
        entries = []
        for label, project, project_data in artifacts:
            shutil.copy2(project, staging / project.name)
            shutil.copytree(project_data, staging / project_data.name, copy_function=shutil.copy2)
            entries.extend(_manifest_entries(project, staging, label))
            entries.extend(_manifest_entries(project_data, staging, label))
        manifest = {
            "format": 1,
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_root": str(source),
            "changed_setting": changed_setting,
            "projects": list(project_names),
            "files": entries,
        }
        (staging / "capture-manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        if destination.exists():
            destination.rmdir()
        os.replace(staging, destination)
        return manifest
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="SD-card folder containing both controlled saves")
    parser.add_argument("--output", type=Path, required=True, help="new or empty local capture folder")
    parser.add_argument("--baseline", default=DEFAULT_PROJECTS[0])
    parser.add_argument("--changed", default=DEFAULT_PROJECTS[1])
    parser.add_argument("--changed-setting", default="Key Ranges: Drum Split")
    args = parser.parse_args()
    manifest = capture_projects(
        args.source,
        args.output,
        (args.baseline, args.changed),
        changed_setting=args.changed_setting,
    )
    print(
        f"Captured and verified {len(manifest['files'])} files in "
        f"{args.output.expanduser().resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
