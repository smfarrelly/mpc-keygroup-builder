"""Read-only checks of explicitly selected local projects, bundles and programs."""

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from .bundle_verify import verify_bundle
from .capture import verify_capture
from .model import from_xpm


def sample_status(program: Path, reference: str, root: Path) -> dict:
    """Resolve only bounded local references; never search a whole drive."""
    raw = Path(reference)
    if raw.is_absolute() or '\\' in reference or ':' in reference or '\0' in reference:
        return {'reference': reference, 'status': 'external', 'path': None}
    names = [raw] if raw.suffix else [raw, raw.with_suffix('.wav')]
    candidates = [base / name for base in (program.parent, program.with_name(program.stem + '_[ProgramData]')) for name in names]
    bounded = []
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.is_relative_to(root):
            bounded.append(resolved)
    if not bounded:
        return {'reference': reference, 'status': 'external', 'path': None}
    for candidate in bounded:
        if candidate.is_file():
            return {'reference': reference, 'status': 'found', 'path': str(candidate)}
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
    samples = [sample_status(path, name, root) for name in sorted({layer.sample for zone in model.zones for layer in zone.layers})]
    errors = list(validation['errors'])
    warnings = list(validation['warnings'])
    if not samples:
        errors.append('no populated sample layers found')
    if any(item['status'] == 'missing' for item in samples):
        errors.append('local sample references are missing within the checked lookup locations')
    if any(item['status'] == 'external' for item in samples):
        warnings.append('external or nonportable references were not accessed; their availability is unknown')
    return {'status': 'fail' if errors else 'warn' if warnings else 'pass',
            'errors': errors, 'warnings': warnings, 'samples': samples,
            'sample_root': str(root), 'name': model.name}


def check(*, archives=(), bundles=(), programs=(), sample_root: Path | None = None) -> dict:
    if not any((archives, bundles, programs)):
        raise ValueError('choose at least one --archive, --bundle, or --program; no drives are scanned automatically')
    if sample_root is not None and not programs:
        raise ValueError('--sample-root requires at least one --program')
    rows = []
    for kind, paths, inspector in (
        ('archive', archives, verify_capture), ('bundle', bundles, verify_bundle),
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
            except (OSError, ValueError, ET.ParseError, KeyError, TypeError, AttributeError) as error:
                row.update(status='fail', error=str(error))
            rows.append(row)
    return {'format': 1, 'kind': 'mpc-local-readiness', 'checks': rows,
            'status': 'fail' if any(row['status'] == 'fail' for row in rows) else 'warn' if any(row['status'] == 'warn' for row in rows) else 'pass',
            'hardware_status': 'not-evaluated',
            'boundary': 'Read-only checks of selected local inputs, not hardware acceptance, audio decoding, plugin licensing, or proof that generated outputs match current recipes. Sample lookup checks program-relative and companion ProgramData paths only; no basename search or reference repair.'}


def show(archives, bundles, programs, sample_root, as_json) -> int:
    report = check(archives=archives, bundles=bundles, programs=programs,
                   sample_root=sample_root.expanduser() if sample_root else None)
    if as_json:
        print(json.dumps(report, indent=2))
    else:
        for row in report['checks']:
            print(f"{row['status'].upper()}: {row['kind']} {row['path']}")
            if 'error' in row:
                print('  ' + row['error'])
            for message in row.get('detail', {}).get('errors', []) + row.get('detail', {}).get('warnings', []):
                print('  ' + message)
            for sample in row.get('detail', {}).get('samples', []):
                if sample['status'] != 'found':
                    print(f"  {sample['status']}: {sample['reference']}")
        print(report['boundary'])
    return 1 if report['status'] in {'fail', 'warn'} else 0
