"""Reject licensed MPC artifacts and unexpectedly large files from source control."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


FORBIDDEN_SUFFIXES = {".wav", ".xpm", ".xpj", ".syx", ".aif", ".aiff"}
FORBIDDEN_MARKERS = ("[programdata]", "[projectdata]")


def scan(paths: list[Path], max_bytes: int = 5 * 1024 * 1024) -> list[str]:
    issues = []
    for path in paths:
        lowered = str(path).casefold()
        if path.suffix.casefold() in FORBIDDEN_SUFFIXES:
            issues.append(f"licensed/captured artifact extension: {path}")
        if any(marker in lowered for marker in FORBIDDEN_MARKERS):
            issues.append(f"MPC companion data path: {path}")
        if path.is_file() and path.stat().st_size > max_bytes:
            issues.append(f"file exceeds {max_bytes} bytes: {path}")
    return issues


def tracked_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, check=False, capture_output=True
    )
    if result.returncode:
        detail = os.fsdecode(result.stderr).strip() or "git ls-files failed"
        raise ValueError(f"repository guard requires a Git worktree at {root}: {detail}")
    return [root / os.fsdecode(value) for value in result.stdout.split(b"\0") if value]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--max-bytes", type=int, default=5 * 1024 * 1024)
    args = parser.parse_args()
    issues = scan(tracked_files(args.root.resolve()), args.max_bytes)
    for issue in issues:
        print(f"ERROR: {issue}")
    if not issues:
        print("Repository artifact guard passed.")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
