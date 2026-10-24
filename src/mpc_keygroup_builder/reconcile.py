"""Reconcile ledger paths against explicitly selected local XPM libraries.

Matches are location candidates, never inferred hardware acceptance or identity.
No reference repair, ledger edits, audio copying, or drive discovery occurs.
"""

from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath

from .library import query
from .readiness import check


MAX_ENTRIES = 250_000
MAX_PROGRAMS = 20_000
MAX_CANDIDATES = 20
BOUNDARY = ('Read-only location candidates, not proof of identity with deployed programs. '
            'Historical listening verdicts remain unchanged. Sample checks resolve paths only; '
            'they do not decode audio or prove MPC playback. No drives are discovered or modified.')


def relative_parts(value):
    if not isinstance(value, str) or not value or any(char in value for char in ('\\', ':', '\0')):
        return None
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or not path.parts:
        return None
    return path.parts


def inventory(roots):
    """Bound a deterministic scan; do not follow directory or file symlinks."""
    if not roots:
        raise ValueError('select at least one --library-root; no drives are discovered automatically')
    resolved = []
    for requested in roots:
        root = requested.expanduser()
        if root.is_symlink() or not root.is_dir():
            raise ValueError(f'library root must be an existing non-symlink directory: {root}')
        root = root.resolve()
        if root == Path(root.anchor) or root == Path.home().resolve():
            raise ValueError('choose a specific instrument library, not a filesystem or home root')
        if root not in resolved:
            resolved.append(root)
    resolved.sort(key=str)
    if any(a != b and a.is_relative_to(b) for a in resolved for b in resolved):
        raise ValueError('library roots must not overlap; select each library once')
    programs, errors, skipped = [], [], []
    entries = 0
    def onerror(error):
        errors.append({'path': str(error.filename), 'error': str(error)})
    for root in resolved:
        for folder, dirs, files in os.walk(root, followlinks=False, onerror=onerror):
            parent = Path(folder)
            entries += len(dirs) + len(files)
            if entries > MAX_ENTRIES:
                raise ValueError(f'library scan exceeds {MAX_ENTRIES} entries; select narrower roots')
            for name in list(dirs):
                if (parent / name).is_symlink():
                    skipped.append(str(parent / name))
                    dirs.remove(name)
            dirs.sort()
            for name in sorted(files):
                path = parent / name
                if path.suffix.casefold() != '.xpm':
                    continue
                if path.is_symlink():
                    skipped.append(str(path))
                    continue
                if not path.is_file():
                    continue
                programs.append({'path': str(path), 'root': str(root),
                                 'relative': path.relative_to(root).as_posix()})
                if len(programs) > MAX_PROGRAMS:
                    raise ValueError(f'library scan exceeds {MAX_PROGRAMS} programs; select narrower roots')
    return {'roots': [str(root) for root in resolved], 'programs': programs,
            'entries_scanned': entries, 'scan_errors': errors, 'skipped_symlinks': skipped}


def suffix_length(left, right):
    count = 0
    for a, b in zip(reversed(left), reversed(right)):
        if a.casefold() != b.casefold():
            break
        count += 1
    return count


def reconcile(ledger, roots, *, favorite=None, verify_samples=False):
    ledger = ledger.expanduser()
    if ledger.is_symlink() or not ledger.is_file():
        raise ValueError(f'ledger must be a regular non-symlink file: {ledger}')
    rows = query(ledger, favorite=favorite)
    index = inventory(roots)
    by_name = {}
    for item in index['programs']:
        by_name.setdefault(Path(item['path']).name.casefold(), []).append(item)
    results, cache, matched = [], {}, set()
    for row in rows:
        parts = relative_parts(row['path'])
        result = {**row, 'match_status': 'missing', 'candidates': [], 'candidate_count': 0}
        if parts is None:
            result['match_status'] = 'unsafe-ledger-path'
            results.append(result)
            continue
        choices = []
        for item in by_name.get(parts[-1].casefold(), []):
            local_parts = PurePosixPath(item['relative']).parts
            common = suffix_length(parts, local_parts)
            choices.append({**item, 'matching_components': common,
                            'match_basis': 'exact-relative' if tuple(parts) == tuple(local_parts)
                            else 'path-suffix' if common >= 2 else 'name-only'})
        # Never hide weaker duplicates behind one good-looking suffix match.
        choices.sort(key=lambda item: (-item['matching_components'], item['path']))
        result['candidate_count'] = len(choices)
        if choices:
            result['match_status'] = ('ambiguous' if len(choices) > 1 else
                                      'candidate' if choices[0]['matching_components'] >= 2
                                      or choices[0]['match_basis'] == 'exact-relative' else 'name-only')
        result['candidates_truncated'] = len(choices) > MAX_CANDIDATES
        for item in choices:
            matched.add(item['path'])
        for item in choices[:MAX_CANDIDATES]:
            candidate = {**item, 'sample_status': 'not-checked'}
            if verify_samples:
                key = item['path']
                if key not in cache:
                    cache[key] = check(programs=[Path(key)], sample_root=Path(item['root']))['checks'][0]
                evidence = cache[key]
                detail = evidence.get('detail', {})
                candidate.update(sample_status=evidence['status'], sample_check=evidence,
                                 sample_counts=dict(Counter(sample['status'] for sample in detail.get('samples', []))))
            result['candidates'].append(candidate)
        results.append(result)
    counts = dict(Counter(row['match_status'] for row in results))
    attention = bool(index['scan_errors'] or index['skipped_symlinks']) or any(
        row['match_status'] != 'candidate' or any(
            item['sample_status'] in ('fail', 'warn') for item in row['candidates']) for row in results)
    return {'format': 1, 'kind': 'mpc-library-reconciliation',
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'ledger': str(ledger.absolute()), 'favorite_filter': favorite,
            'roots': index['roots'], 'entries_scanned': index['entries_scanned'],
            'programs_scanned': len(index['programs']), 'rows': results, 'summary': counts,
            'unmatched_programs': [item for item in index['programs'] if item['path'] not in matched],
            'scan_errors': index['scan_errors'], 'skipped_symlinks': index['skipped_symlinks'],
            'status': 'attention' if attention else 'pass', 'hardware_status': 'not-evaluated',
            'boundary': BOUNDARY}


def write_report(output, report):
    output = output.expanduser()
    if output.exists() or output.is_symlink():
        raise FileExistsError(f'choose a new reconciliation report filename: {output}')
    resolved = output.resolve()
    if resolved == Path(report['ledger']).resolve() or any(resolved.is_relative_to(Path(root)) for root in report['roots']):
        raise ValueError('reconciliation report must be outside the ledger and input libraries')
    payload = json.dumps(report, indent=2) + '\n'
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        stream.write(payload)


def show(ledger, roots, favorite, verify_samples, as_json, output):
    report = reconcile(ledger, roots, favorite=favorite, verify_samples=verify_samples)
    if output:
        write_report(output, report)
    if as_json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Scanned {report['programs_scanned']} XPMs; evaluated {len(report['rows'])} ledger rows.")
        for row in report['rows']:
            print(f"{row['match_status'].upper()}: {row['path']}")
            for item in row['candidates']:
                print(f"  {item['match_basis']} / samples={item['sample_status']}: {item['path']}")
            if row.get('candidates_truncated'):
                print(f"  Showing first {MAX_CANDIDATES} of {row['candidate_count']} candidates; narrow the roots.")
        print(report['boundary'])
        for error in report['scan_errors']:
            print(f"SCAN ERROR: {error['path']}: {error['error']}")
        for path in report['skipped_symlinks']:
            print(f'SKIPPED SYMLINK: {path}')
        if output:
            print(f'Report: {output.expanduser().absolute()}')
    return 1 if report['status'] == 'attention' else 0
