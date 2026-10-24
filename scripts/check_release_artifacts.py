"""Inspect wheel/sdist inventories without extracting them before publication."""

import argparse
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import tarfile
import zipfile


FORBIDDEN = {'.wav', '.xpm', '.xpj', '.syx', '.aif', '.aiff'}


def safe_name(name):
    path = PurePosixPath(name.rstrip('/'))
    if not path.parts or path.is_absolute() or '..' in path.parts or '\\' in name or '\0' in name or path.as_posix() != name.rstrip('/'):
        raise ValueError(f'unsafe artifact member: {name}')
    lowered = name.casefold()
    if path.suffix.casefold() in FORBIDDEN or '[projectdata]' in lowered or '[programdata]' in lowered:
        raise ValueError(f'licensed/captured artifact member: {name}')
    if any(part.casefold() in {'work', '.git', '.venv'} or part.casefold().startswith('.env') or part.casefold().endswith('.local.toml') for part in path.parts):
        raise ValueError(f'private/development artifact member: {name}')
    if any(':' in part for part in path.parts):
        raise ValueError(f'nonportable artifact member: {name}')


def inspect(path, version):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError('release asset must be a regular file no larger than 64 MiB')
    names, sizes, metadata = [], [], []
    if path.suffix == '.whl':
        with zipfile.ZipFile(path) as archive:
            if len(archive.infolist()) > 10000:
                raise ValueError('too many wheel members')
            for member in archive.infolist():
                safe_name(member.filename)
                mode = stat.S_IFMT(member.external_attr >> 16)
                if mode not in (0, stat.S_IFREG, stat.S_IFDIR):
                    raise ValueError('wheel contains a link or special file')
                names.append(member.filename.rstrip('/'))
                sizes.append(member.file_size)
                if member.filename.endswith('.dist-info/METADATA'):
                    if member.file_size > 1024 * 1024:
                        raise ValueError('oversized package metadata')
                    metadata.append(archive.read(member))
    elif path.name.endswith('.tar.gz'):
        with tarfile.open(path, 'r:gz') as archive:
            for index, member in enumerate(archive):
                if index >= 10000:
                    raise ValueError('too many source archive members')
                safe_name(member.name)
                if not (member.isfile() or member.isdir()):
                    raise ValueError('source archive contains a link or special file')
                names.append(member.name.rstrip('/'))
                sizes.append(member.size)
                if sum(sizes) > 32 * 1024 * 1024:
                    raise ValueError('uncompressed artifact exceeds 32 MiB')
                if PurePosixPath(member.name).name == 'PKG-INFO':
                    if not member.isfile() or member.size > 1024 * 1024:
                        raise ValueError('oversized package metadata')
                    stream = archive.extractfile(member)
                    metadata.append(stream.read())
    else:
        raise ValueError('expected a wheel or .tar.gz source distribution')
    if len(names) != len(set(name.casefold() for name in names)):
        raise ValueError('duplicate or case-colliding artifact paths')
    if sum(sizes) > 32 * 1024 * 1024:
        raise ValueError('uncompressed artifact exceeds 32 MiB')
    if len(metadata) != 1:
        raise ValueError('expected exactly one package metadata document')
    if not any(PurePosixPath(name).name == 'LICENSE' for name in names):
        raise ValueError('release artifact must include the license text file')
    parsed = BytesParser().parsebytes(metadata[0])
    if parsed['Name'] != 'mpc-keygroup-builder' or parsed['Version'] != version:
        raise ValueError('package name/version does not match the requested release')
    return {'file': path.name, 'version': version, 'members': len(names),
            'uncompressed_bytes': sum(sizes), 'bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifacts', nargs='+', type=Path)
    parser.add_argument('--version', required=True)
    args = parser.parse_args()
    print(json.dumps({'artifacts': [inspect(path, args.version) for path in args.artifacts]}, indent=2))
