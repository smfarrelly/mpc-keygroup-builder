"""Conservative recipe-input freshness for newly generated workstation waves."""

import hashlib
import json
from pathlib import Path

from .bundle_verify import sha256, verify_bundle
from .recipe_audit import DIRECTORIES


def snapshot(root: Path) -> dict[str, str]:
    root = root.expanduser()
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f'recipe root must be a regular directory: {root}')
    entries = {}
    for directory in sorted(DIRECTORIES.values()):
        folder = root / directory
        if folder.is_symlink():
            raise ValueError(f'recipe directory cannot be a symlink: {folder}')
        if not folder.exists():
            continue
        if not folder.is_dir():
            raise ValueError(f'recipe category must be a directory: {folder}')
        for path in sorted(folder.glob('*.toml')):
            if path.is_symlink() or not path.is_file():
                raise ValueError(f'recipe must be a regular non-symlink file: {path}')
            before = path.stat()
            digest = sha256(path)
            after = path.stat()
            if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
                raise ValueError(f'recipe changed while hashing: {path}')
            entries[path.relative_to(root).as_posix()] = digest
    return entries


def fingerprint(files: dict[str, str]) -> str:
    return hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def receipt(files: dict[str, str]) -> dict:
    return {'format': 1, 'kind': 'mpc-wave-recipe-inputs', 'scope': 'all-top-level-category-toml',
            'files': files, 'sha256': fingerprint(files)}


def check_bundle(bundle: Path, recipe_root: Path) -> dict:
    integrity = verify_bundle(bundle)
    path = bundle / 'recipe-inputs.json'
    if not path.exists():
        return {'status': 'warn', 'integrity': integrity, 'freshness': 'unknown',
                'warnings': ['This bundle has no build-time recipe receipt. Rebuild into a new folder; do not retrofit freshness evidence.']}
    raw = json.loads(path.read_text(encoding='utf-8'))
    # Compare with the sealed recipe copies, not paths supplied by the receipt.
    sealed = snapshot(bundle / 'Recipes')
    if raw != receipt(sealed):
        raise ValueError('recipe receipt is unsupported or inconsistent with bundled recipe copies')
    current = snapshot(recipe_root)
    added = sorted(current.keys() - sealed.keys())
    removed = sorted(sealed.keys() - current.keys())
    changed = sorted(name for name in current.keys() & sealed.keys() if current[name] != sealed[name])
    stale = bool(added or removed or changed)
    return {'status': 'warn' if stale else 'pass', 'integrity': integrity,
            'freshness': 'stale' if stale else 'current', 'added': added, 'removed': removed,
            'changed': changed, 'recorded_sha256': fingerprint(sealed), 'current_sha256': fingerprint(current),
            'warnings': ['Recipe inputs differ; rebuild into a new folder before treating this as current.'] if stale else [],
            'boundary': 'Exact bytes of all top-level TOML files in supported recipe categories, including unselected families. Not audio, code-version, CLI-option, or hardware freshness.'}
