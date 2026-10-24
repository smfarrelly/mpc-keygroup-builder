"""Publish a completed sibling directory without replacing any destination.

Do not fall back to check-then-rename on POSIX: ordinary rename can replace an
empty directory created between the check and the rename. Unsupported systems
fail closed. This is publication safety, not a power-loss durability guarantee.
"""

import ctypes
import errno
import os
from pathlib import Path
import sys


def _native_publish(source: Path, destination: Path) -> None:
    if sys.platform == 'win32':
        # Python documents that Windows rename refuses an existing destination.
        os.rename(source, destination)
        return
    library = ctypes.CDLL(None, use_errno=True)
    if sys.platform.startswith('linux'):
        function = getattr(library, 'renameat2', None)
        args = (-100, os.fsencode(source), -100, os.fsencode(destination), 1)
        signature = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
    elif sys.platform == 'darwin':
        function = getattr(library, 'renamex_np', None)
        args = (os.fsencode(source), os.fsencode(destination), 0x4)
        signature = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint)
    else:
        function = None
    if function is None:
        raise OSError(errno.ENOTSUP, 'exclusive directory publication is unavailable; use a supported local filesystem', str(destination))
    function.argtypes = signature
    function.restype = ctypes.c_int
    if function(*args) != 0:
        code = ctypes.get_errno()
        message = os.strerror(code)
        if code in {errno.ENOSYS, errno.EINVAL, errno.ENOTSUP}:
            message = 'filesystem does not support exclusive directory publication; use a supported local filesystem'
        raise OSError(code, message, str(destination))


def publish_directory(source: Path, destination: Path) -> None:
    """Move a verified staging directory into a new sibling name, or refuse."""
    if source.is_symlink() or not source.is_dir():
        raise ValueError('publication source must be a regular staging directory')
    if '\0' in str(destination):
        raise ValueError('publication destination contains a null byte')
    source = source.absolute()
    destination = destination.absolute()
    if source.parent.resolve() != destination.parent.resolve():
        raise ValueError('publication requires sibling staging and destination directories')
    if source.name == destination.name:
        raise ValueError('publication requires a new destination name')
    _native_publish(source, destination)
