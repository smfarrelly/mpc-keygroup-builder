"""Build a private local landing page from explicitly selected evidence."""

from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import shlex
import tomllib

from .idea_archive import list_archives
from .library import query
from .readiness import check
from .reconcile import reconcile
from .start import WORKFLOWS


def load_config(path: Path) -> dict:
    """Read a declarative local input selection; paths are relative to the config."""
    path = path.expanduser()
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'home config must be a regular non-symlink file: {path}')
    with path.open('rb') as stream:
        raw = tomllib.load(stream)
    allowed = {'format', 'archive_library', 'ledger', 'program_root', 'bundles', 'recipe_root',
               'library_roots', 'verify_samples'}
    unknown = raw.keys() - allowed
    if unknown:
        raise ValueError('unknown home config fields: ' + ', '.join(sorted(unknown)))
    if type(raw.get('format')) is not int or raw['format'] != 1:
        raise ValueError('home config requires format = 1')
    base = path.absolute().parent
    def configured_path(value):
        if not isinstance(value, str) or not value.strip() or '\0' in value:
            raise ValueError('home config paths must be nonempty strings')
        item = Path(value).expanduser()
        return item if item.is_absolute() else base / item
    result = {key: configured_path(raw[key]) for key in allowed - {'format', 'bundles', 'library_roots', 'verify_samples'} if key in raw}
    for key in ('bundles', 'library_roots'):
        values = raw.get(key, [])
        if not isinstance(values, list):
            raise ValueError(f'home config {key} must be an array of paths')
        result[key] = [configured_path(value) for value in values]
    if 'verify_samples' in raw:
        if type(raw['verify_samples']) is not bool:
            raise ValueError('home config verify_samples must be a boolean')
        result['verify_samples'] = raw['verify_samples']
    return result


def collect(*, archive_library=None, ledger=None, program_root=None, bundles=(), recipe_root=None,
            library_roots=(), verify_samples=False):
    if program_root is not None and ledger is None:
        raise ValueError('--program-root requires --ledger')
    if recipe_root is not None and not bundles:
        raise ValueError('--recipe-root requires --bundle')
    if library_roots and ledger is None:
        raise ValueError('--library-root requires --ledger')
    if verify_samples and program_root is None and not library_roots:
        raise ValueError('--verify-samples requires --program-root or --library-root')
    report = {'format': 1, 'kind': 'mpc-local-home', 'generated_at': datetime.now(timezone.utc).isoformat(),
              'archives': None, 'favorites': None, 'readiness': None, 'reconciliation': None, 'status': 'pass'}
    if archive_library is not None:
        report['archives'] = list_archives(archive_library.expanduser())
        if report['archives']['invalid_archives'] or report['archives']['scan_errors']:
            report['status'] = 'attention'
    if ledger is not None:
        if ledger.expanduser().is_symlink():
            raise ValueError('ledger must not be a symbolic link')
        report['favorites'] = query(ledger.expanduser(), favorite='yes')
        root = program_root.expanduser().resolve() if program_root is not None else None
        if root is not None and not root.is_dir():
            raise ValueError('program root must be an existing directory')
        for row in report['favorites']:
            row['local_status'] = 'not-checked'
            row['local_path'] = ''
            row['sample_status'] = 'not-checked'
            if root is None:
                continue
            relative = Path(row['path'])
            if not relative.parts or relative.is_absolute() or '..' in relative.parts or '\\' in row['path'] or ':' in row['path'] or '\0' in row['path']:
                row['local_status'] = 'unsafe-path'
            else:
                candidate = (root / relative).resolve()
                if not candidate.is_relative_to(root):
                    row['local_status'] = 'outside-root'
                else:
                    row['local_path'] = str(candidate)
                    row['local_status'] = 'found' if candidate.is_file() else 'missing'
            if row['local_status'] != 'found':
                report['status'] = 'attention'
            elif verify_samples:
                evidence = check(programs=[candidate], sample_root=root)['checks'][0]
                row['sample_status'] = evidence['status']
                row['sample_check'] = evidence
                if evidence['status'] != 'pass':
                    report['status'] = 'attention'
    if library_roots:
        report['reconciliation'] = reconcile(ledger, library_roots, favorite='yes', verify_samples=verify_samples)
        if report['reconciliation']['status'] != 'pass':
            report['status'] = 'attention'
    if bundles:
        report['readiness'] = check(bundles=bundles, recipe_root=recipe_root)
        if report['readiness']['status'] != 'pass':
            report['status'] = 'attention'
    return report


def render(report):
    def card(title, text):
        return '<article><h3>' + escape(title) + '</h3>' + text + '</article>'
    def paragraph(value):
        return '<p>' + escape(str(value)) + '</p>'
    def command(args):
        return '<pre>' + escape(shlex.join(args)) + '</pre>'
    workflows = ''.join(card(item['title'], paragraph(item['needs']) + '<pre>' + escape(item['command']) + '</pre>' + paragraph(item['next'])) for item in WORKFLOWS.values())
    favorites = '<p>No ledger selected. No favorites were inferred.</p>'
    reconciliation = report.get('reconciliation')
    local_rows = {row['path']: row for row in reconciliation['rows']} if reconciliation else {}
    if report['favorites'] is not None:
        cards = []
        for row in report['favorites']:
            text = paragraph('Role: ' + (row['scratchpad_role'] or 'not recorded')) + paragraph(row['notes'])
            text += paragraph('Historical hardware status: ' + row['hardware_status'])
            text += '<details><summary>Recorded library / SD navigation path</summary>' + paragraph(row['path']) + paragraph('Historical location only; the card was not inspected by this report.') + '</details>'
            text += paragraph('Recorded-layout local availability: ' + row['local_status'])
            if row['local_path']:
                text += paragraph(row['local_path']) + paragraph('Sample references: ' + row.get('sample_status', 'not-checked'))
                if row.get('sample_check'):
                    text += '<details><summary>Recorded-layout sample evidence</summary><pre>' + escape(json.dumps(row['sample_check'], indent=2)) + '</pre></details>'
            local = local_rows.get(row['path'])
            if local is not None:
                text += paragraph('Local location matching: ' + local['match_status'])
                for item in local['candidates']:
                    text += '<div class="candidate">' + paragraph(item['path'])
                    text += paragraph('Match: ' + item['match_basis'] + '; sample references: ' + item['sample_status'])
                    text += command(['mpc-tools', 'check', '--program', item['path'], '--sample-root', item['root']])
                    if item.get('sample_check'):
                        text += '<details><summary>Candidate sample evidence</summary><pre>' + escape(json.dumps(item['sample_check'], indent=2)) + '</pre></details>'
                    text += '</div>'
                if local.get('candidates_truncated'):
                    text += paragraph(f"Showing {len(local['candidates'])} of {local['candidate_count']} candidates. Narrow the selected roots.")
                if not local['candidates']:
                    text += paragraph('No candidate in the selected local libraries. This does not prove it is missing from other storage.')
            elif not row['local_path']:
                text += paragraph('Select --program-root for the recorded layout, or --library-root to find candidates in a different layout.')
            cards.append(card(Path(row['path']).stem, text))
        favorites = ''.join(cards) or '<p>No confirmed favorites in the selected ledger.</p>'
    overview = paragraph('Report status: ' + report['status'])
    overview += paragraph(f"Confirmed favorites: {len(report['favorites'])}" if report['favorites'] is not None else 'Favorites: not selected')
    if reconciliation:
        overview += paragraph(f"Scanned {reconciliation['programs_scanned']} local programs in explicitly selected libraries.")
        overview += paragraph('Location results: ' + ', '.join(f'{key}: {value}' for key, value in sorted(reconciliation['summary'].items())))
        overview += paragraph(reconciliation['boundary'])
        overview += ''.join(paragraph('Scan error: ' + str(item)) for item in reconciliation['scan_errors'])
        overview += ''.join(paragraph('Skipped symlink: ' + item) for item in reconciliation['skipped_symlinks'])
    overview += paragraph('Next: choose a favorite below, or inspect a saved idea before making an independent experiment copy. No hardware test is required to browse this evidence.')
    archives = '<p>No archive library selected. No disks were searched.</p>'
    if report['archives'] is not None:
        index = report['archives']
        archives = paragraph(f"Scanned {index['archives_scanned']} archives; {index['invalid_archives']} invalid.")
        archives += ''.join(card(Path(row['path']).name, paragraph(row['path']) + paragraph(row['status']) + paragraph(row.get('note', row.get('error', ''))) + command(['mpc-idea-archive', 'inspect', row['path']])) for row in index['matches'])
        archives += ''.join(paragraph('Scan error: ' + str(item)) for item in index['scan_errors'])
        archives += ''.join(paragraph('Skipped symlink: ' + item) for item in index['skipped_symlinks'])
    readiness = '<p>No bundles selected. Integrity and freshness were not checked.</p>'
    if report['readiness'] is not None:
        readiness = ''.join(card(row['path'], paragraph(row['status']) + '<details><summary>Evidence and limitations</summary><pre>' + escape(json.dumps(row, indent=2)) + '</pre></details>') for row in report['readiness']['checks'])
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>MPC — Start making music</title><style>
:root{color-scheme:dark;font-family:system-ui,sans-serif;background:#111815;color:#edf7f0}body{margin:0}main{max-width:1000px;margin:auto;padding:32px 20px}h1{font-size:clamp(2rem,6vw,4rem)}p{line-height:1.6}a{color:#aee6bf}nav{display:flex;gap:20px;flex-wrap:wrap}article{background:#1b2820;border:1px solid #486453;border-radius:12px;padding:20px;margin:16px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;color:#bddbc7}p,h3{overflow-wrap:anywhere}summary{cursor:pointer}a:focus,summary:focus{outline:3px solid #e9c879;outline-offset:4px}.notice{border-left:4px solid #e9c879;padding:12px 20px}section{margin-top:40px}
</style></head><body><main><a href="#favorites">Skip to favorite sounds</a><h1>Start making music.</h1>
<p class="notice">Private local report. Nothing uploads or executes. This page cannot inspect your disks, launch programs, or restore files. Generated ''' + escape(report['generated_at']) + '''. Availability and verification are point-in-time evidence, not live status or hardware acceptance.</p>
<nav aria-label="Page sections"><a href="#overview">At a glance</a><a href="#favorites">Favorite sounds</a><a href="#archives">Saved ideas</a><a href="#workflows">Choose a task</a><a href="#readiness">Readiness</a></nav>
<section id="overview"><h2>At a glance</h2>''' + overview + '''</section>
<section id="favorites"><h2>Favorite sounds</h2><p>Local candidates are not proven identical to your tested SD copies. Sample-reference checks do not decode audio or prove MPC playback. Commands below are examples to run yourself in a POSIX shell.</p>''' + favorites + '''</section>
<section id="archives"><h2>Saved ideas</h2>''' + archives + '''</section>
<section id="workflows"><h2>Choose one task</h2><p>Replace example paths before running commands in a terminal. Quoting examples target POSIX shells.</p>''' + workflows + '''</section>
<section id="readiness"><h2>Readiness</h2>''' + readiness + '''</section>
<footer><p>Regenerate into a new filename after changes. Keep this report private: it contains personal notes and local paths. No audio or XPJ payload is embedded.</p></footer></main></body></html>'''


def build(output: Path, **inputs):
    output = output.expanduser()
    if output.is_symlink() or output.exists():
        raise FileExistsError(f'choose a new landing-page filename: {output}')
    output = output.resolve()
    roots = [inputs.get(key) for key in ('archive_library', 'program_root', 'recipe_root')]
    roots += list(inputs.get('bundles', ()))
    roots += list(inputs.get('library_roots', ()))
    for root in roots:
        if root is not None and output.is_relative_to(root.expanduser().resolve()):
            raise ValueError('landing page must be outside input libraries, recipe trees and bundles')
    report = collect(**inputs)
    html = render(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        stream.write(html)
    return report
