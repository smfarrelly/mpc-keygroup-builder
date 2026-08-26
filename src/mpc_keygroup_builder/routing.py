"""Capture the controlled Key 37 routing experiment and inspect it without merging tools."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from .capture import DEFAULT_PROJECTS, capture_projects


def inspect_capture(destination: Path, inspector_root: Path) -> dict[str, object]:
    inspector_source = inspector_root / "src"
    if not inspector_source.is_dir():
        raise FileNotFoundError(f"XPJ inspector source is missing: {inspector_source}")
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(inspector_source.resolve()), environment.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    outputs = {
        "baseline": destination / "baseline-inspect.json",
        "changed": destination / "changed-inspect.json",
        "comparison": destination / "routing-compare.json",
    }
    baseline, changed = (destination / name for name in DEFAULT_PROJECTS)
    commands = [
        ["inspect", baseline, "--output", outputs["baseline"]],
        ["inspect", changed, "--output", outputs["changed"]],
        ["compare", baseline, changed, "--output", outputs["comparison"]],
    ]
    for arguments in commands:
        subprocess.run(
            [sys.executable, "-m", "mpc_keygroup_builder.xpj", *map(str, arguments)],
            check=True,
            env=environment,
            capture_output=True,
            text=True,
        )
    return {key: json.loads(path.read_text(encoding="utf-8")) for key, path in outputs.items()}


def run_capture(
    source: Path,
    destination: Path,
    inspector_root: Path,
    *,
    changed_setting: str,
) -> dict[str, object]:
    capture = capture_projects(source, destination, changed_setting=changed_setting)
    inspection = inspect_capture(destination, inspector_root)
    report = {
        "format": 1,
        "changed_setting": changed_setting,
        "capture": capture,
        "inspection": inspection,
    }
    (destination / "routing-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--inspector-root", type=Path, default=Path("work/mac-xpj-inspector"),
        help="detached worktree containing the mac/xpj-inspector source",
    )
    parser.add_argument("--changed-setting", required=True)
    args = parser.parse_args()
    report = run_capture(
        args.source.expanduser().resolve(),
        args.output.expanduser().resolve(),
        args.inspector_root.expanduser().resolve(),
        changed_setting=args.changed_setting,
    )
    print(f"Captured, verified, and compared {len(report['capture']['files'])} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
