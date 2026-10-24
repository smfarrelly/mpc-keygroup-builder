"""Exercise published commands from an installed wheel, outside the checkout.

Usage: python scripts/smoke_idea_workflow.py --bin-dir /path/to/venv/bin
Only disposable synthetic project bytes are written, inside TemporaryDirectory.
"""

import argparse
import csv
import json
import os
from pathlib import Path
import subprocess
import sysconfig
import tempfile


def smoke(bin_dir: Path) -> int:
    bin_dir = bin_dir.resolve()
    count = 0
    with tempfile.TemporaryDirectory(prefix='mpc-installed-ideas-') as temporary:
        root = Path(temporary)
        env = dict(os.environ)
        env.pop('PYTHONPATH', None)
        env.pop('MPC_DEBUG', None)
        env['PATH'] = str(bin_dir) + os.pathsep + env.get('PATH', '')

        def run(tool, *args, expected=0):
            nonlocal count
            executable = bin_dir / (tool + ('.exe' if os.name == 'nt' else ''))
            result = subprocess.run([str(executable), *map(str, args)], cwd=root, env=env,
                                    capture_output=True, text=True, timeout=60)
            count += 1
            if result.returncode != expected:
                raise RuntimeError(f'{tool}: expected {expected}, got {result.returncode}\n{result.stdout}\n{result.stderr}')
            return result

        commands = json.loads(run('mpc-tools', 'commands', '--json').stdout)
        for command in ['mpc-tools', *(row['command'] for row in commands)]:
            run(command, '-h')
            run(command, '--version')
        run('mpc-tools', 'start', '--json')
        source = root / 'source'
        source.mkdir()
        (source / 'Idea.xpj').write_bytes(b'synthetic project, not MPC playback data')
        (source / 'Idea_[ProjectData]').mkdir()
        archive = root / 'library' / 'take-01'
        args = [source, '--project', 'Idea.xpj', '--output', archive]
        run('mpc-project-capture', *args, '--dry-run', '--json')
        if archive.exists():
            raise RuntimeError('preflight unexpectedly wrote an archive')
        run('mpc-project-capture', *args, '--note', 'Keep this version')
        run('mpc-tools', 'check', '--archive', archive, '--json')
        run('mpc-idea-archive', 'list', archive.parent, '--query', 'keep', '--json')
        experiment = root / 'experiment'
        run('mpc-idea-archive', 'restore', archive, '--output', experiment)
        original = (experiment / 'Idea.xpj').read_bytes()
        result = run('mpc-idea-archive', 'restore', archive, '--output', experiment, expected=2)
        if 'Traceback' in result.stderr or 'NEXT:' not in result.stderr:
            raise RuntimeError('existing destination did not produce an actionable error')
        if (experiment / 'Idea.xpj').read_bytes() != original:
            raise RuntimeError('existing experiment changed after refused restore')
        (experiment / 'Idea.xpj').write_bytes(b'changed variation')
        run('mpc-tools', 'check', '--archive', experiment, expected=1)
        variation = root / 'library' / 'take-02'
        run('mpc-project-capture', experiment, '--project', 'Idea.xpj', '--output', variation)
        comparison = json.loads(run('mpc-project-capture', '--compare', archive, variation, '--json').stdout)
        if comparison['changed'] != ['Idea.xpj']:
            raise RuntimeError('variation comparison did not report changed project')
        failed_output = root / 'should-not-exist'
        run('mpc-idea-archive', 'restore', experiment, '--output', failed_output, expected=2)
        if failed_output.exists():
            raise RuntimeError('invalid archive restore published output')
        run('mpc-project-capture', '--verify', archive)
        run('mpc-tools', 'home', '--archive-library', archive.parent,
            '--output', root / 'home.html')
        instruments = root / 'instruments'
        (instruments / 'Collection').mkdir(parents=True)
        (instruments / 'Collection' / 'Kit.xpm').write_text('<MPCVObject><Program type="Drum"><ProgramName>Kit</ProgramName><Instruments><Instrument number="1"><Layers><Layer><SampleFile>kick.wav</SampleFile></Layer></Layers></Instrument></Instruments></Program></MPCVObject>')
        (instruments / 'Collection' / 'kick.wav').write_bytes(b'synthetic-path-check-only')
        ledger = root / 'ledger.csv'
        with ledger.open('w', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['path', 'program_type', 'hardware_status', 'favorite', 'scratchpad_role', 'notes'])
            writer.writerow(['Programs/Collection/Kit.xpm', 'Drum', 'untested', 'yes', 'drums', 'Synthetic fixture'])
        reconciled = json.loads(run('mpc-tools', 'reconcile', '--ledger', ledger,
                                    '--library-root', instruments, '--verify-samples', '--json').stdout)
        if reconciled['rows'][0]['match_status'] != 'candidate' or reconciled['hardware_status'] != 'not-evaluated':
            raise RuntimeError('reconciliation did not preserve evidence boundaries')
        run('mpc-tools', 'home', '--ledger', ledger, '--library-root', instruments,
            '--verify-samples', '--output', root / 'favorite-home.html')
        package_copy = root / 'package-copy'
        run('mpc-package-deploy', archive, package_copy)
        if package_copy.exists():
            raise RuntimeError('package dry run unexpectedly wrote output')
        run('mpc-package-deploy', archive, package_copy, '--apply', '--probe-mib', '0')
        run('mpc-project-capture', '--verify', package_copy)
        run('mpc-package-deploy', archive, package_copy, '--apply', '--probe-mib', '0')
    print(f'PASS: {count} installed command checks; capture/restore/recovery exercised with synthetic data only.')
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bin-dir', type=Path, default=Path(sysconfig.get_path('scripts')),
                        help='installed command directory; defaults to this Python interpreter\'s script directory')
    raise SystemExit(smoke(parser.parse_args().bin_dir))
