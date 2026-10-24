"""Find, inspect, and restore verified musical-idea snapshots without edits in place."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path

from .capture import read_capture_manifest, verify_capture
from .publication import publish_directory


def inspect_archive(path: Path) -> dict:
    verification = verify_capture(path)
    manifest = read_capture_manifest(path)
    return {'path': str(path.resolve()), **verification,
            'projects': manifest.get('projects', []), 'note': manifest.get('note', ''),
            'captured_at_utc': manifest.get('captured_at_utc'),
            'capture_kind': manifest.get('capture_kind', 'legacy-capture'),
            'changed_setting': manifest.get('changed_setting', '')}


def list_archives(root: Path, *, query: str = '') -> dict:
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f'archive library must be a regular directory: {root}')
    rows, errors, skipped = [], [], []
    def scan_error(error):
        errors.append({'path': str(error.filename), 'error': str(error)})
    for folder, dirs, files in os.walk(root, followlinks=False, onerror=scan_error):
        parent = Path(folder)
        for name in list(dirs):
            if (parent / name).is_symlink():
                skipped.append(str(parent / name))
                dirs.remove(name)
        dirs.sort()
        if 'capture-manifest.json' not in files:
            continue
        # Do not mistake files inside an archive's ProjectData for more archives.
        dirs.clear()
        try:
            row = inspect_archive(parent)
        except (OSError, ValueError) as error:
            row = {'path': str(parent.resolve()), 'status': 'invalid', 'error': str(error)}
        rows.append(row)
    rows.sort(key=lambda row: row['path'])
    needle = query.casefold()
    matches = [row for row in rows if needle in json.dumps(
        [row['path'], row.get('projects', []), row.get('note', '')], ensure_ascii=False).casefold()]
    return {'format': 1, 'kind': 'mpc-idea-archive-index', 'query': query,
            'archives_scanned': len(rows), 'invalid_archives': sum(row['status'] != 'verified' for row in rows),
            'matches': matches, 'scan_errors': errors, 'skipped_symlinks': sorted(skipped),
            'boundary': 'Read-only file-integrity index. No musical quality or hardware acceptance inferred.'}


def restore_archive(source: Path, output: Path, *, dry_run: bool = False) -> dict:
    """Create a verified independent copy for experiments; never overwrite."""
    before = inspect_archive(source)
    source = source.resolve()
    if output.is_symlink() or output.exists():
        raise FileExistsError(f'restore requires a new output directory: {output}')
    output = output.resolve()
    if output == source or output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError('restore output must be separate from the source archive')
    report = {'status': 'planned' if dry_run else 'restored', 'source': str(source),
              'output': str(output), 'files': before['files'], 'bytes': before['bytes'],
              'content_sha256': before['content_sha256'],
              'boundary': 'Independent file copy only. External samples and plugin licenses are not added.'}
    if dry_run:
        return report
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f'.{output.name}.restore-', dir=output.parent))
    try:
        shutil.copytree(source, stage, dirs_exist_ok=True, symlinks=True)
        copied = inspect_archive(stage)
        after = inspect_archive(source)
        if before != after or copied['content_sha256'] != before['content_sha256']:
            raise ValueError('source archive changed during restore; no output published')
        if (stage / 'capture-manifest.json').read_bytes() != (source / 'capture-manifest.json').read_bytes():
            raise ValueError('capture manifest changed during restore')
        if output.is_symlink() or output.exists():
            raise FileExistsError(f'restore destination appeared during copy: {output}')
        publish_directory(stage, output)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    listing = commands.add_parser('list', help='verify archives below a local folder and search notes/project names')
    listing.add_argument('root', type=Path)
    listing.add_argument('--query', default='')
    listing.add_argument('--html', type=Path, help='write a new private offline report outside the archive library')
    inspection = commands.add_parser('inspect', help='verify one archive and show its note and content fingerprint')
    inspection.add_argument('archive', type=Path)
    restore = commands.add_parser('restore', help='copy a verified archive into a new experiment directory')
    restore.add_argument('archive', type=Path)
    restore.add_argument('--output', required=True, type=Path)
    restore.add_argument('--dry-run', action='store_true')
    for command in (listing, inspection, restore):
        command.add_argument('--json', action='store_true')
    args = parser.parse_args()
    if args.command == 'list':
        report = list_archives(args.root, query=args.query)
        if args.html is not None:
            from .archive_browser import write
            report['html_report'] = str(write(report, args.html, args.root))
    elif args.command == 'inspect':
        report = inspect_archive(args.archive)
    else:
        report = restore_archive(args.archive, args.output, dry_run=args.dry_run)
    if args.json:
        print(json.dumps(report, indent=2))
    elif args.command == 'list':
        if 'html_report' in report:
            print('Browser report: ' + report['html_report'])
        print(f"Scanned {report['archives_scanned']} archives; {report['invalid_archives']} invalid; {len(report['matches'])} matches.")
        for row in report['matches']:
            print(f"{row['status'].upper()} {row['path']}")
            print(f"  {row.get('note', row.get('error', ''))}")
        for error in report['scan_errors']:
            print(f"SCAN ERROR {error['path']}: {error['error']}")
        for path in report['skipped_symlinks']:
            print(f'SKIPPED SYMLINK {path}')
    else:
        print(f"{report['status'].upper()}: {report.get('path', report.get('output'))}")
        print(f"Files: {report['files']}; payload bytes: {report['bytes']}; content SHA-256: {report['content_sha256']}")
        if args.command == 'inspect':
            print(f"Note: {report['note']}")
        print(report['boundary'])
    return 1 if args.command == 'list' and (report['invalid_archives'] or report['scan_errors']) else 0


if __name__ == '__main__':
    raise SystemExit(main())
