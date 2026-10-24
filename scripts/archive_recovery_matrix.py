"""Exercise capture → variation → comparison with synthetic recovery faults.

Default: seven quick cases. --full: 840 cases spanning file counts, sizes,
project counts and filename styles. No user projects, audio, or SD paths are read.
"""

import argparse
from itertools import product
import json
from pathlib import Path
import shutil
import tempfile
import time
from unittest.mock import patch

from mpc_keygroup_builder import capture, idea_archive


FAULTS = ('healthy', 'capture-interrupt', 'restore-interrupt', 'source-mutates',
          'empty-destination', 'occupied-destination', 'archive-tampered')
STYLES = ('plain', 'spaces', 'unicode', 'punctuation')


def expect(error_type, action):
    try:
        action()
    except error_type:
        return
    raise AssertionError(f'expected {error_type.__name__}; operation unexpectedly succeeded')


def snapshot(root):
    return {path.relative_to(root).as_posix(): capture.sha256(path)
            for path in root.rglob('*') if path.is_file()}


def exercise(root, files, size, projects, style, fault):
    source = root / 'source'
    source.mkdir()
    labels = {'plain': 'Idea', 'spaces': 'Late Night Idea',
              'unicode': 'Idée 音楽', 'punctuation': "Idea [A] 'take'"}
    names = []
    payload = bytes((n % 251 for n in range(size)))
    for number in range(projects):
        name = f'{labels[style]} {number}'
        names.append(name + '.xpj')
        (source / names[-1]).write_bytes(b'Synthetic XPJ fixture, not an MPC project.')
        data = source / (name + '_[ProjectData]')
        data.mkdir()
        for index in range(files):
            parent = data / f'group {index % 8}'
            parent.mkdir(exist_ok=True)
            (parent / f'part {index:04}.bin').write_bytes(payload)
    names = tuple(names)
    before = snapshot(source)
    archive = root / 'library' / 'take-one'
    experiment = root / 'experiment'
    options = dict(project_names=names, note='Synthetic recovery fixture')
    estimate = capture.capture_projects(source, archive, dry_run=True, **options)
    if archive.parent.exists() or estimate['bytes'] != sum(path.stat().st_size for path in source.rglob('*') if path.is_file()):
        raise AssertionError('preflight wrote output or miscounted bytes')
    if fault == 'capture-interrupt':
        copy = capture.shutil.copy2
        calls = 0
        def interrupt(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == max(1, len(before) // 2):
                raise KeyboardInterrupt('synthetic interrupt')
            return copy(*args, **kwargs)
        with patch.object(capture.shutil, 'copy2', side_effect=interrupt):
            expect(KeyboardInterrupt, lambda: capture.capture_projects(source, archive, **options))
        if archive.exists() or list(archive.parent.glob('.take-one-*')):
            raise AssertionError('interrupted capture published output or left owned staging')
    elif fault == 'source-mutates':
        copy = capture.shutil.copy2
        changed = False
        def mutate(src, dst, *args, **kwargs):
            nonlocal changed
            result = copy(src, dst, *args, **kwargs)
            if not changed:
                Path(src).write_bytes(b'simulated concurrent save')
                changed = True
            return result
        with patch.object(capture.shutil, 'copy2', side_effect=mutate):
            expect(OSError, lambda: capture.capture_projects(source, archive, **options))
        # The mutation was injected deliberately; do not restore or conceal it.
        if archive.exists() or list(archive.parent.glob('.take-one-*')):
            raise AssertionError('mutating source was published')
        return {'source_change_detected': True, 'payload_files': len(before)}
    elif fault in ('empty-destination', 'occupied-destination'):
        publish = capture.publish_directory
        def conflict(stage, destination):
            destination.mkdir()
            if fault == 'occupied-destination':
                (destination / 'keep.txt').write_text('someone else owns this')
            return publish(stage, destination)
        with patch.object(capture, 'publish_directory', side_effect=conflict):
            expect(FileExistsError, lambda: capture.capture_projects(source, archive, **options))
        if fault == 'empty-destination' and list(archive.iterdir()):
            raise AssertionError('empty concurrent destination was overwritten')
        if fault == 'occupied-destination' and (archive / 'keep.txt').read_text() != 'someone else owns this':
            raise AssertionError('concurrent destination content was changed')
        if list(archive.parent.glob('.take-one-*')):
            raise AssertionError('failed publication left owned staging')
    else:
        capture.capture_projects(source, archive, **options)
        fingerprint = capture.verify_capture(archive)['content_sha256']
        if fault == 'archive-tampered':
            (archive / names[0]).write_bytes(b'tampered')
            expect(ValueError, lambda: idea_archive.restore_archive(archive, experiment))
            if experiment.exists():
                raise AssertionError('tampered archive restored')
        elif fault == 'restore-interrupt':
            copytree = idea_archive.shutil.copytree
            def interrupt(src, dst, *args, **kwargs):
                result = copytree(src, dst, *args, **kwargs)
                if Path(src) == archive:
                    raise KeyboardInterrupt('synthetic interrupt after copying')
                return result
            with patch.object(idea_archive.shutil, 'copytree', side_effect=interrupt):
                expect(KeyboardInterrupt, lambda: idea_archive.restore_archive(archive, experiment))
            if experiment.exists() or list(root.glob('.experiment.restore-*')):
                raise AssertionError('interrupted restore published or left owned staging')
            if capture.verify_capture(archive)['content_sha256'] != fingerprint:
                raise AssertionError('restore changed the archive')
        else:
            idea_archive.restore_archive(archive, experiment)
            (experiment / names[0]).write_bytes(b'a deliberate variation')
            variant = root / 'library' / 'take-two'
            capture.capture_projects(experiment, variant, **options)
            comparison = capture.compare_captures(archive, variant)
            if comparison['changed'] != [names[0]] or comparison['added'] or comparison['removed']:
                raise AssertionError('variation comparison did not isolate the project change')
            if capture.verify_capture(archive)['content_sha256'] != fingerprint:
                raise AssertionError('variation changed the original archive')
    if snapshot(source) != before:
        raise AssertionError('operation changed source bytes')
    return {'payload_files': len(before), 'payload_bytes': estimate['bytes']}


def run(output, full=False):
    if output.exists() or output.is_symlink():
        raise FileExistsError('choose a new recovery matrix report filename')
    cases = list(product((0, 1, 16, 128, 1024), (0, 32, 4096), (1, 2), STYLES, FAULTS)) if full else [(2, 32, 1, 'plain', fault) for fault in FAULTS]
    report = {'format': 1, 'kind': 'mpc-archive-recovery-matrix', 'complete': False,
              'planned_cases': len(cases), 'cases': [],
              'boundary': 'Synthetic file workflow and failure-recovery checks, not MPC project playback, SD acceptance, or power-loss durability.'}
    output.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    def save():
        report['passed'] = sum(row['status'] == 'pass' for row in report['cases'])
        report['failed'] = len(report['cases']) - report['passed']
        report['elapsed_seconds'] = round(time.monotonic() - started, 3)
        output.write_text(json.dumps(report, indent=2) + '\n')
    save()
    for files, size, projects, style, fault in cases:
        if shutil.disk_usage(tempfile.gettempdir()).free < 256 * 1024 * 1024:
            report['stopped_reason'] = 'less than 256 MiB temporary free space'
            break
        row = dict(files_per_project=files, bytes_per_file=size, projects=projects, style=style, fault=fault)
        try:
            with tempfile.TemporaryDirectory(prefix='mpc-recovery-matrix-') as temporary:
                row['evidence'] = exercise(Path(temporary), files, size, projects, style, fault)
            row['status'] = 'pass'
        except Exception as error:
            row.update(status='fail', error=f'{type(error).__name__}: {error}')
        report['cases'].append(row)
        if len(report['cases']) % 20 == 0:
            save()
            print(f"Checked {len(report['cases'])}/{len(cases)}; failures={report['failed']}", flush=True)
    report['complete'] = len(report['cases']) == len(cases)
    save()
    print(f"Complete={report['complete']}; pass={report['passed']}; fail={report['failed']}; seconds={report['elapsed_seconds']}")
    return 0 if report['complete'] and not report['failed'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--full', action='store_true')
    args = parser.parse_args()
    raise SystemExit(run(args.output, args.full))
