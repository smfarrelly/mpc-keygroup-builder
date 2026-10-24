"""Build a private local landing page from explicitly selected evidence."""

from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import shlex

from .idea_archive import list_archives
from .library import query
from .readiness import check
from .start import WORKFLOWS


def collect(*, archive_library=None, ledger=None, program_root=None, bundles=(), recipe_root=None):
    if program_root is not None and ledger is None:
        raise ValueError('--program-root requires --ledger')
    if recipe_root is not None and not bundles:
        raise ValueError('--recipe-root requires --bundle')
    report = {'format': 1, 'kind': 'mpc-local-home', 'generated_at': datetime.now(timezone.utc).isoformat(),
              'archives': None, 'favorites': None, 'readiness': None, 'status': 'pass'}
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
    if report['favorites'] is not None:
        favorites = ''.join(card(row['path'], paragraph(row['scratchpad_role']) + paragraph(row['notes']) + paragraph('Historical hardware status: ' + row['hardware_status']) + paragraph('Local availability: ' + row['local_status']) + paragraph(row['local_path'] or 'Select --program-root to resolve an absolute local path.')) for row in report['favorites']) or '<p>No confirmed favorites in the selected ledger.</p>'
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
</style></head><body><main><a href="#workflows">Skip to workflows</a><h1>Start making music.</h1>
<p class="notice">Private local report. Nothing uploads or executes. This page cannot inspect your disks, launch programs, or restore files. Generated ''' + escape(report['generated_at']) + '''. Availability and verification are point-in-time evidence, not live status or hardware acceptance.</p>
<nav aria-label="Page sections"><a href="#workflows">Choose a task</a><a href="#favorites">Favorite sounds</a><a href="#archives">Saved ideas</a><a href="#readiness">Readiness</a></nav>
<section id="workflows"><h2>Choose one task</h2><p>Replace example paths before running commands in a terminal. Quoting examples target POSIX shells.</p>''' + workflows + '''</section>
<section id="favorites"><h2>Favorite sounds</h2><p>Finding an XPM does not prove its samples load. Use mpc-tools check --program with the explicit library root before transferring.</p>''' + favorites + '''</section>
<section id="archives"><h2>Saved ideas</h2>''' + archives + '''</section>
<section id="readiness"><h2>Readiness</h2>''' + readiness + '''</section>
<footer><p>Regenerate into a new filename after changes. Keep this report private: it contains personal notes and local paths. No audio or XPJ payload is embedded.</p></footer></main></body></html>'''


def build(output: Path, **inputs):
    output = output.expanduser()
    if output.is_symlink() or output.exists():
        raise FileExistsError(f'choose a new landing-page filename: {output}')
    output = output.resolve()
    roots = [inputs.get(key) for key in ('archive_library', 'program_root', 'recipe_root')]
    roots += list(inputs.get('bundles', ()))
    for root in roots:
        if root is not None and output.is_relative_to(root.expanduser().resolve()):
            raise ValueError('landing page must be outside input libraries, recipe trees and bundles')
    report = collect(**inputs)
    html = render(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        stream.write(html)
    return report
