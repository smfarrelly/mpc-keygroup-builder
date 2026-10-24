"""Optional software-only wave reproducibility matrix using synthetic audio.

The full matrix generates each of 810 scenarios twice, verifies both bundles,
and compares their checksums. Temporary generated waves are removed per case.
No user samples, SD devices, hardware status ledgers, or existing outputs change.
"""

import argparse
import itertools
import json
from pathlib import Path
import shutil
import tempfile
import time

from mpc_keygroup_builder.freshness import check_bundle
from mpc_keygroup_builder.workstation_wave import build_wave


FAMILIES = ('dusty', 'ambient', 'electro', 'funk', 'house', 'weird')


def scenarios(full=False):
    if full:
        return list(itertools.product(FAMILIES, (0, 1, 37, 127, 2147483647),
                                      (0.0, 0.5, 1.0), (0.0, 0.5, 1.0), (20.0, 120.0, 300.0)))
    return [(family, 37, 0.5, 0.5, 120.0) for family in FAMILIES]


def run(recipe_root, output, full=False):
    recipe_root = recipe_root.expanduser().resolve()
    output = output.expanduser()
    if output.is_symlink() or output.exists():
        raise FileExistsError(f'choose a new matrix report: {output}')
    output = output.resolve()
    if output.is_relative_to(recipe_root):
        raise ValueError('matrix report must be outside the recipe tree')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        stream.write('{}\n')
    start = time.monotonic()
    report = {'format': 1, 'kind': 'mpc-release-matrix', 'complete': False,
              'planned_cases': len(scenarios(full)), 'cases': [],
              'boundary': 'Synthetic software generation/reproducibility only. No MPC listening, browser runtime, or external audio acceptance.'}
    try:
        for family, seed, density, mutation, tempo in scenarios(full):
            case = dict(family=family, seed=seed, density=density, mutation=mutation, tempo=tempo)
            try:
                if shutil.disk_usage(tempfile.gettempdir()).free < 256 * 1024 * 1024:
                    raise OSError('less than 256 MiB temporary free space; stopping matrix')
                with tempfile.TemporaryDirectory(prefix='mpc-release-matrix-') as directory:
                    root = Path(directory)
                    fingerprints = []
                    for folder in ('first', 'second'):
                        destination = root / folder / 'wave'
                        result = build_wave(recipe_root, destination, families=(family,),
                                            seeds_per_family=1, seed_start=seed, density=density,
                                            mutation=mutation, tempo=tempo)
                        if result['software_status'] != 'pass' or result['hardware_status'] != 'deferred':
                            raise ValueError('unexpected software/hardware status boundary')
                        verified = check_bundle(destination, recipe_root)
                        if verified['freshness'] != 'current':
                            raise ValueError('newly generated bundle is not recipe-current')
                        fingerprints.append((destination / 'checksums.json').read_bytes())
                    if fingerprints[0] != fingerprints[1]:
                        raise ValueError('identical inputs produced different bundle checksums')
                case['status'] = 'pass'
            except Exception as error:
                case.update(status='fail', error=f'{type(error).__name__}: {error}')
            report['cases'].append(case)
            if len(report['cases']) % 25 == 0:
                print(f"Checked {len(report['cases'])}/{report['planned_cases']}; failures={sum(c['status']=='fail' for c in report['cases'])}", flush=True)
                output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
            if case.get('error', '').startswith('OSError: less than'):
                break
        report['complete'] = len(report['cases']) == report['planned_cases']
    finally:
        report['elapsed_seconds'] = round(time.monotonic() - start, 3)
        report['passed'] = sum(case['status'] == 'pass' for case in report['cases'])
        report['failed'] = len(report['cases']) - report['passed']
        output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f"Matrix complete={report['complete']}; pass={report['passed']}; fail={report['failed']}; seconds={report['elapsed_seconds']}")
    return 0 if report['complete'] and not report['failed'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recipe_root', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--full', action='store_true', help='810 cases; two generated/verified bundles per case; can take several minutes')
    args = parser.parse_args()
    raise SystemExit(run(args.recipe_root, args.output, args.full))
