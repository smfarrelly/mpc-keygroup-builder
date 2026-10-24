"""Capture and verify MPC musical ideas or controlled XPJ comparisons."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
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
        if path.is_dir() and normalized == stem + "projectdata":
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
    project_names: tuple[str, ...] = DEFAULT_PROJECTS,
    *,
    changed_setting: str | None = None,
    note: str = "",
) -> dict[str, object]:
    if not project_names or any(
        not isinstance(name, str) or Path(name).name != name
        or '/' in name or '\\' in name or '\0' in name
        or Path(name).suffix.casefold() != '.xpj'
        for name in project_names
    ):
        raise ValueError("project names must be non-empty .xpj filenames, not paths")
    if len({name.casefold() for name in project_names}) != len(project_names):
        raise ValueError("project names must be distinct")
    if destination.expanduser().is_symlink():
        raise ValueError("capture destination cannot be a symbolic link")
    if changed_setting is None:
        changed_setting = "Key Ranges: Drum Split" if project_names == DEFAULT_PROJECTS else ""
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
            "note": note,
            "capture_kind": "controlled-comparison" if changed_setting else "idea-snapshot",
            "projects": list(project_names),
            "files": entries,
        }
        (staging / "capture-manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        verify_capture(staging)
        if destination.exists():
            destination.rmdir()
        os.replace(staging, destination)
        return manifest
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def verify_capture(directory: Path) -> dict[str, object]:
    """Verify an archived capture without reading its original source paths."""
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError(f"capture must be a regular directory: {directory}")
    directory = directory.resolve()
    actual = {str(path.relative_to(directory)) for path in _regular_files(directory)}
    manifest_path = directory / 'capture-manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if not isinstance(manifest, dict) or manifest.get('format') != 1 or not isinstance(manifest.get('files'), list):
        raise ValueError("unsupported capture manifest; expected format 1 and files list")
    expected = set()
    byte_count = 0
    for entry in manifest['files']:
        if not isinstance(entry, dict):
            raise ValueError("invalid capture file entry")
        name, size, digest = entry.get('destination'), entry.get('bytes'), entry.get('sha256')
        if not isinstance(name, str) or not name or '\\' in name or '\0' in name:
            raise ValueError("invalid capture destination path")
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts or relative.as_posix() != name:
            raise ValueError(f"unsafe capture destination: {name}")
        if name == 'capture-manifest.json' or name in expected:
            raise ValueError(f"duplicate or reserved capture destination: {name}")
        if type(size) is not int or size < 0 or not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise ValueError(f"invalid size or checksum for {name}")
        expected.add(name)
        target = directory / relative
        if not target.is_file():
            raise ValueError(f"missing capture file: {name}")
        if target.stat().st_size != size or sha256(target) != digest:
            raise ValueError(f"capture content changed: {name}")
        byte_count += size
    if not expected:
        raise ValueError("capture manifest contains no files")
    extra = actual - expected - {'capture-manifest.json'}
    if extra:
        raise ValueError(f"unlisted capture files: {', '.join(sorted(extra)[:5])}")
    return {'status': 'verified', 'files': len(expected), 'bytes': byte_count,
            'boundary': 'File integrity only; not project completeness, authenticity, or hardware acceptance.'}


def compare_captures(before: Path, after: Path) -> dict[str, object]:
    """Compare verified inventories by exact relative filename, without writes."""
    inventories = []
    metadata = []
    for directory in (before, after):
        verified = verify_capture(directory)
        manifest = json.loads((directory / 'capture-manifest.json').read_text(encoding='utf-8'))
        inventories.append({entry['destination']: entry for entry in manifest['files']})
        metadata.append({'path': str(directory.resolve()), 'note': manifest.get('note', ''),
                         'projects': manifest.get('projects', []), 'bytes': verified['bytes']})
    left, right = inventories
    common = left.keys() & right.keys()
    changed = sorted(name for name in common if
                     (left[name]['bytes'], left[name]['sha256']) !=
                     (right[name]['bytes'], right[name]['sha256']))
    added, removed = sorted(right.keys() - left.keys()), sorted(left.keys() - right.keys())
    return {
        'format': 1, 'kind': 'mpc-capture-comparison', 'before': metadata[0], 'after': metadata[1],
        'added': added, 'removed': removed, 'changed': changed,
        'unchanged': sorted(common - set(changed)),
        'content_identical': not (added or removed or changed),
        'boundary': 'Exact-path file comparison, not musical or XPJ semantic comparison. Renamed files appear as added/removed; capture notes are metadata, not content changes.',
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, nargs='?', help="folder containing the saved projects")
    parser.add_argument("--output", type=Path, help="new or empty local capture folder")
    parser.add_argument("--baseline")
    parser.add_argument("--changed")
    parser.add_argument("--changed-setting")
    parser.add_argument("--project", action='append', help="capture this .xpj filename; repeat for more projects")
    parser.add_argument("--note", default='', help="musical intention or experiment note stored with the capture")
    read_only = parser.add_mutually_exclusive_group()
    read_only.add_argument("--verify", type=Path, help="verify an existing capture without needing the source card")
    read_only.add_argument("--compare", nargs=2, type=Path, metavar=('BEFORE', 'AFTER'), help="verify and compare two archived takes without changing them")
    parser.add_argument('--json', action='store_true', help='machine-readable output for --verify or --compare')
    args = parser.parse_args()
    if args.verify is not None or args.compare is not None:
        if any((args.source, args.output, args.baseline, args.changed, args.changed_setting, args.project, args.note)):
            parser.error('--verify/--compare cannot be combined with capture arguments')
        report = compare_captures(*args.compare) if args.compare else verify_capture(args.verify)
        if args.json:
            print(json.dumps(report, indent=2))
        elif args.compare:
            for kind in ('added', 'removed', 'changed', 'unchanged'):
                print(f"{kind.capitalize()}: {len(report[kind])}")
                if kind != 'unchanged':
                    for name in report[kind]:
                        print(f"  {name}")
            print(report['boundary'])
        else:
            print(f"Verified {report['files']} files ({report['bytes']} bytes). {report['boundary']}")
        return 0
    if args.json:
        parser.error('--json requires --verify or --compare')
    if args.source is None or args.output is None:
        parser.error('capture requires SOURCE and --output; or use --verify CAPTURE_FOLDER')
    if args.project and (args.baseline or args.changed):
        parser.error('--project cannot be combined with --baseline or --changed')
    names = tuple(args.project) if args.project else (args.baseline or DEFAULT_PROJECTS[0], args.changed or DEFAULT_PROJECTS[1])
    manifest = capture_projects(
        args.source,
        args.output,
        names,
        changed_setting=(args.changed_setting or "") if args.project else args.changed_setting,
        note=args.note,
    )
    print(
        f"Captured and verified {len(manifest['files'])} files in "
        f"{args.output.expanduser().resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
