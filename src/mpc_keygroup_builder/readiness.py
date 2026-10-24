"""Read-only checks of explicitly selected local projects, bundles and programs."""

import json
import os
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path

from .bundle_verify import verify_bundle
from .capture import verify_capture
from .model import from_xpm
from .freshness import check_bundle


def _case_matches(path: Path, root: Path, cache: dict) -> tuple[list[Path], bool]:
    """Walk only the named components, preserving FAT-style case collisions."""
    path = Path(os.path.normpath(path))
    if not path.is_relative_to(root):
        return [], True
    choices = [root]
    external = False
    for component in path.relative_to(root).parts:
        next_choices = []
        for parent in choices:
            if not parent.is_dir():
                continue
            if parent not in cache:
                names = {}
                for child in parent.iterdir():
                    names.setdefault(child.name.casefold(), []).append(child)
                cache[parent] = names
            for child in cache[parent].get(component.casefold(), []):
                if child.is_symlink():
                    external = True
                else:
                    next_choices.append(child)
        choices = next_choices
        if len(choices) > 20:
            raise ValueError('sample path has too many case-colliding components; resolve the collisions first')
    return [path for path in choices if path.is_file()], external


def sample_status(program: Path, reference: str, root: Path, *, directory_cache=None) -> dict:
    """Resolve only bounded local references; never search a whole drive."""
    raw = Path(reference)
    if raw.is_absolute() or '\\' in reference or ':' in reference or '\0' in reference:
        return {'reference': reference, 'status': 'external', 'path': None}
    if not raw.parts:
        return {'reference': reference, 'status': 'missing', 'path': None}
    # SampleName values can contain dots; append rather than replace their tail.
    names = [raw] if raw.suffix.casefold() in {'.wav', '.aif', '.aiff', '.mp3', '.flac'} else [raw, raw.with_name(raw.name + '.wav')]
    candidates = [base / name for base in (program.parent, program.with_name(program.stem + '_[ProgramData]')) for name in names]
    bounded = []
    external = False
    cache = directory_cache if directory_cache is not None else {}
    for candidate in candidates:
        normalized = Path(os.path.normpath(candidate))
        if normalized.is_relative_to(root):
            bounded.append(normalized)
        else:
            external = True
    if not bounded:
        return {'reference': reference, 'status': 'external', 'path': None}
    matches = set()
    for candidate in bounded:
        found, skipped = _case_matches(candidate, root, cache)
        matches.update(found)
        external |= skipped
    if len(matches) > 1:
        return {'reference': reference, 'status': 'ambiguous', 'path': None,
                'candidates': sorted(str(path) for path in matches)}
    if matches:
        candidate = matches.pop()
        return {'reference': reference, 'status': 'found', 'path': str(candidate),
                'resolution': 'exact' if candidate in bounded else 'case-insensitive'}
    if external:
        return {'reference': reference, 'status': 'external', 'path': None}
    return {'reference': reference, 'status': 'missing', 'path': None}


def inspect_program(path: Path, root: Path | None) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'program must be a regular non-symlink file: {path}')
    path = path.resolve()
    root = root.resolve() if root else path.parent
    if not root.is_dir() or not path.is_relative_to(root):
        raise ValueError('sample root must be a directory containing the program')
    model = from_xpm(path)
    validation = model.validate()
    directory_cache = {}
    samples = [sample_status(path, name, root, directory_cache=directory_cache) for name in sorted({layer.sample for zone in model.zones for layer in zone.layers})]
    errors = list(validation['errors'])
    warnings = list(validation['warnings'])
    if not samples:
        errors.append('no populated sample layers found')
    if any(item['status'] == 'missing' for item in samples):
        errors.append('local sample references are missing within the checked lookup locations')
    if any(item['status'] == 'ambiguous' for item in samples):
        errors.append('multiple local files match a sample reference; no file was silently selected')
    if any(item['status'] == 'external' for item in samples):
        warnings.append('external or nonportable references were not accessed; their availability is unknown')
    return {'status': 'fail' if errors else 'warn' if warnings else 'pass',
            'errors': errors, 'warnings': warnings, 'samples': samples,
            'sample_root': str(root), 'name': model.name}


def check(*, archives=(), bundles=(), programs=(), sample_root: Path | None = None, recipe_root: Path | None = None) -> dict:
    if not any((archives, bundles, programs)):
        raise ValueError('choose at least one --archive, --bundle, or --program; no drives are scanned automatically')
    if sample_root is not None and not programs:
        raise ValueError('--sample-root requires at least one --program')
    if recipe_root is not None and not bundles:
        raise ValueError('--recipe-root requires at least one --bundle')
    rows = []
    for kind, paths, inspector in (
        ('archive', archives, verify_capture),
        ('bundle', bundles, lambda path: check_bundle(path, recipe_root) if recipe_root is not None else verify_bundle(path)),
        ('program', programs, lambda path: inspect_program(path, sample_root)),
    ):
        for requested in paths:
            path = requested.expanduser()
            row = {'kind': kind, 'path': str(path.absolute())}
            try:
                if path.is_symlink():
                    raise ValueError('top-level symbolic links are not accepted')
                detail = inspector(path)
                row.update(status=detail.get('status', 'pass'), detail=detail)
                if row['status'] == 'verified':
                    row['status'] = 'pass'
            except (OSError, ValueError, ET.ParseError, KeyError, TypeError, AttributeError, EOFError, zlib.error) as error:
                row.update(status='fail', error=str(error))
            rows.append(row)
    return {'format': 1, 'kind': 'mpc-local-readiness', 'checks': rows,
            'status': 'fail' if any(row['status'] == 'fail' for row in rows) else 'warn' if any(row['status'] == 'warn' for row in rows) else 'pass',
            'hardware_status': 'not-evaluated',
            'boundary': 'Read-only checks of selected local inputs, not hardware acceptance, audio decoding, plugin licensing, or proof that generated outputs match current recipes. Sample lookup checks program-relative and companion ProgramData paths only, including unique case-insensitive paths; collisions are not silently selected. No basename search or reference repair.'}


def show(archives, bundles, programs, sample_root, as_json, recipe_root=None) -> int:
    report = check(archives=archives, bundles=bundles, programs=programs,
                   sample_root=sample_root.expanduser() if sample_root else None,
                   recipe_root=recipe_root.expanduser() if recipe_root else None)
    if as_json:
        print(json.dumps(report, indent=2))
    else:
        for row in report['checks']:
            print(f"{row['status'].upper()}: {row['kind']} {row['path']}")
            if 'error' in row:
                print('  ' + row['error'])
            detail = row.get('detail', {})
            if 'freshness' in detail:
                print('  Recipe freshness: ' + detail['freshness'])
                for category in ('added', 'removed', 'changed'):
                    for name in detail.get(category, []):
                        print(f'  {category}: {name}')
            for message in row.get('detail', {}).get('errors', []) + row.get('detail', {}).get('warnings', []):
                print('  ' + message)
            for sample in row.get('detail', {}).get('samples', []):
                if sample['status'] != 'found':
                    print(f"  {sample['status']}: {sample['reference']}")
        print(report['boundary'])
    return 1 if report['status'] in {'fail', 'warn'} else 0
