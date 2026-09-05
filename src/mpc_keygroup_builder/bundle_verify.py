"""Read-only verification for checksum-bearing MPC workflow bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


CHUNK_SIZE = 1024 * 1024


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty relative POSIX path")
    if "\\" in value or "\0" in value:
        raise ValueError(f"unsafe {label}: {value!r}")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or value != path.as_posix()
        or any(part in {"", ".", ".."} for part in path.parts)
        or (path.parts and ":" in path.parts[0])
    ):
        raise ValueError(f"unsafe {label}: {value!r}")
    return path.as_posix()


def _package_sha256(checksums: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for relative, checksum in sorted(checksums.items()):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(checksum.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def verify_bundle(root: Path, *, receipt: str = "checksums.json") -> dict[str, object]:
    """Verify a complete bundle without modifying it or making hardware claims."""
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(root)
    receipt_relative = _relative(receipt, label="checksum receipt path")
    receipt_path = root.joinpath(*PurePosixPath(receipt_relative).parts)
    current = root
    for part in PurePosixPath(receipt_relative).parts:
        current /= part
        if current.is_symlink():
            raise ValueError("bundle checksum receipt may not use symbolic links")
    try:
        receipt_path.resolve().relative_to(root)
    except ValueError as error:
        raise ValueError("bundle checksum receipt escapes the bundle root") from error
    raw = json.loads(receipt_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not raw:
        raise ValueError("bundle checksum receipt must be a non-empty JSON object")

    expected: dict[str, str] = {}
    for raw_relative, raw_checksum in raw.items():
        relative = _relative(raw_relative, label="bundle checksum path")
        if relative == receipt_relative:
            raise ValueError("bundle checksum receipt may not record itself")
        if (
            not isinstance(raw_checksum, str)
            or len(raw_checksum) != 64
            or any(character not in "0123456789abcdef" for character in raw_checksum)
        ):
            raise ValueError(f"invalid SHA-256 for bundle file: {relative}")
        if relative in expected:
            raise ValueError(f"duplicate normalized bundle checksum path: {relative}")
        expected[relative] = raw_checksum

    paths = list(root.rglob("*"))
    symbolic_links = sorted(
        path.relative_to(root).as_posix() for path in paths if path.is_symlink()
    )
    if symbolic_links:
        raise ValueError(f"bundle may not contain symbolic links: {symbolic_links[0]}")
    unsupported = sorted(
        path.relative_to(root).as_posix()
        for path in paths
        if not path.is_dir() and not path.is_file()
    )
    if unsupported:
        raise ValueError(f"bundle contains an unsupported filesystem entry: {unsupported[0]}")
    actual_paths = {
        path.relative_to(root).as_posix(): path
        for path in paths
        if path.is_file() and path != receipt_path
    }
    missing = sorted(set(expected) - set(actual_paths))
    extra = sorted(set(actual_paths) - set(expected))
    if missing:
        raise ValueError(f"bundle files are missing: {missing[0]}")
    if extra:
        raise ValueError(f"bundle has unrecorded files: {extra[0]}")

    total_bytes = 0
    for relative, checksum in expected.items():
        path = actual_paths[relative]
        total_bytes += path.stat().st_size
        if sha256(path) != checksum:
            raise ValueError(f"bundle checksum mismatch: {relative}")
    return {
        "schema_version": 1,
        "kind": "mpc-bundle-verification",
        "software_status": "pass",
        "hardware_status": "not-evaluated",
        "receipt": receipt_relative,
        "verified_files": len(expected),
        "verified_bytes": total_bytes,
        "package_sha256": _package_sha256(expected),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument(
        "--receipt", default="checksums.json",
        help="relative POSIX receipt path inside the bundle (default: checksums.json)",
    )
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args()
    report = verify_bundle(args.bundle, receipt=args.receipt)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(
            f"PASS: files={report['verified_files']} bytes={report['verified_bytes']} "
            f"sha256={report['package_sha256']}"
        )
        print("Hardware status: not-evaluated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
