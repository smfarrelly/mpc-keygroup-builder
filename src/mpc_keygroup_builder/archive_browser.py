"""Render a private, offline archive index; never embed executable archive data."""

from datetime import datetime, timezone
from html import escape
from pathlib import Path
import shlex


def render(report: dict) -> str:
    cards = []
    for row in report['matches']:
        path = row['path']
        verified = row['status'] == 'verified'
        command = shlex.join(['mpc-idea-archive', 'inspect', path])
        cards.append(
            '<article><h2>' + escape(Path(path).name) + '</h2>'
            '<p class="badge">' + ('Verified at generation' if verified else 'Needs attention') + '</p>'
            '<p class="path">' + escape(path) + '</p>'
            '<p>' + escape(str(row.get('note', row.get('error', '')))) + '</p>'
            '<p>Projects: ' + escape(', '.join(str(item) for item in row.get('projects', []))) + '</p>'
            '<p>Payload: ' + escape(str(row.get('bytes', 'unknown'))) + ' bytes · Files: ' + escape(str(row.get('files', 'unknown'))) + '</p>'
            '<p class="path">Content SHA-256: ' + escape(str(row.get('content_sha256', 'unavailable'))) + '</p>'
            '<details><summary>Recheck this archive</summary><pre>' + escape(command) + '</pre>'
            '<p>Run this command in your terminal. This page cannot re-read or restore files.</p></details></article>'
        )
    issues = ''.join('<li>' + escape(str(item['path']) + ': ' + str(item['error'])) + '</li>' for item in report['scan_errors'])
    issues += ''.join('<li>Skipped directory symlink: ' + escape(path) + '</li>' for path in report['skipped_symlinks'])
    timestamp = datetime.now(timezone.utc).isoformat()
    return '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'; form-action 'none'">
<title>My MPC ideas — local archive index</title>
<style>
:root{color-scheme:dark;font-family:system-ui,sans-serif;background:#111815;color:#eef7f1}
body{margin:0}main{max-width:1000px;margin:auto;padding:32px 20px}h1{font-size:2.5rem}
p,li{line-height:1.6}header p{max-width:78ch;color:#c2d3c8}.notice{border-left:4px solid #e5bd77;padding:12px 20px;background:#24251f}
input{display:block;width:100%;box-sizing:border-box;padding:14px;margin:10px 0 20px;background:#1b2721;color:inherit;border:1px solid #81b794;border-radius:8px;font:inherit}
article{border:1px solid #42594b;border-radius:12px;padding:20px;margin:16px 0;background:#18221c}article h2{margin-top:0}
.badge{color:#e5bd77;font-weight:700}.path,pre{overflow-wrap:anywhere;white-space:pre-wrap;font-size:.9rem;color:#b1cfbc}
summary{cursor:pointer;padding:10px 0}input:focus,summary:focus{outline:3px solid #b3efc8;outline-offset:3px}[hidden]{display:none!important}
</style></head><body><main><header><p>PRIVATE LOCAL REPORT · NO UPLOADS</p><h1>Pick up an idea.</h1>
<p>Search the project names, notes, and paths below. Verification is a point-in-time software check, not a listening pass or proof of external sample/plugin availability.</p></header>
<div class="notice"><p>Generated ''' + escape(timestamp) + '''. This is a saved report, not a live connection to your disk. Recheck before restoring or transferring.</p>
<p>Scanned ''' + str(report['archives_scanned']) + ''' archives · ''' + str(report['invalid_archives']) + ''' invalid across the full scan. Initial query: ''' + escape(report['query'] or '(none)') + '''.</p></div>
<label for="search">Filter the displayed archive cards</label><input id="search" type="search" placeholder="Try a project name or listening note">
<p id="count" role="status" aria-live="polite">''' + str(len(cards)) + ''' archive cards</p><div id="cards">''' + ''.join(cards) + '''</div>
<section><h2>Scan notices</h2><ul>''' + (issues or '<li>No scan errors or skipped directory symlinks.</li>') + '''</ul></section>
<section><h2>Try a variation safely</h2><p>Use <code>mpc-idea-archive restore ARCHIVE --output NEW-FOLDER --dry-run</code> in a terminal, replacing the placeholders with quoted paths. Review the plan, then remove <code>--dry-run</code>. Restore requires a new destination and never edits the archive. After editing the restored project, capture it into a new archive.</p>
<p>Keep this HTML private: it includes local paths and personal notes. It contains no audio or XPJ data. No JavaScript is required to read the cards; JavaScript only filters them.</p></section></main>
<script>
const search=document.getElementById('search');
const cards=Array.from(document.querySelectorAll('article'));
search.addEventListener('input',()=>{
 const needle=search.value.toLocaleLowerCase();let visible=0;
 cards.forEach(card=>{const match=card.textContent.toLocaleLowerCase().includes(needle);card.hidden=!match;if(match)visible++;});
 document.getElementById('count').textContent=visible+' of '+cards.length+' archive cards';
});
</script></body></html>'''


def write(report: dict, output: Path, library: Path) -> Path:
    output = output.expanduser()
    if output.is_symlink() or output.exists():
        raise FileExistsError(f'choose a new browser report filename: {output}')
    output = output.resolve()
    if output.is_relative_to(library.expanduser().resolve()):
        raise ValueError('browser report must be outside the archive library to keep archives unchanged')
    rendered = render(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive create prevents clobbering a report created after preflight.
    with output.open('x', encoding='utf-8') as stream:
        stream.write(rendered)
    return output
