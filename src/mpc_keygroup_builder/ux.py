"""Friendly front door for discovering and checking the MPC instrument tools."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import tomllib
from collections import defaultdict
from pathlib import Path

from .entrypoints import COMMANDS, invoke, version
from .portable_demo import build_demo, verify_demo
from .scaffold import KINDS, create as create_scaffold
from .web_demo import build_web_demo


def _find_checkpoint(explicit: Path | None) -> Path:
    candidates = [explicit] if explicit else [
        Path.cwd() / "inventory" / "session-checkpoint.toml",
        Path.cwd() / "session-checkpoint.toml",
    ]
    for path in candidates:
        if path is not None and path.expanduser().is_file():
            return path.expanduser().resolve()
    raise FileNotFoundError(
        "session checkpoint not found; run from the project checkout or pass --checkpoint"
    )


def _find_sd_root(explicit: Path | None, baseline_relative: str) -> Path | None:
    if explicit is not None:
        root = explicit.expanduser().resolve()
        if not root.is_dir():
            raise NotADirectoryError(root)
        return root
    media = Path("/media") / os.environ.get("USER", "")
    if not media.is_dir():
        return None
    return next(
        (
            path.resolve()
            for path in media.iterdir()
            if path.is_dir() and (path / baseline_relative).is_file()
        ),
        None,
    )


def _resume(checkpoint_path: Path | None, sd_root: Path | None, as_json: bool) -> int:
    checkpoint_file = _find_checkpoint(checkpoint_path)
    checkpoint = tomllib.loads(checkpoint_file.read_text(encoding="utf-8"))
    required = ("title", "baseline_relative", "working_relative", "target_relative", "next_action")
    missing = [name for name in required if not checkpoint.get(name)]
    if missing:
        raise ValueError(f"checkpoint lacks required fields: {', '.join(missing)}")
    root = _find_sd_root(sd_root, checkpoint["baseline_relative"])
    paths = {}
    for role in ("baseline", "working", "target"):
        relative = checkpoint[f"{role}_relative"]
        absolute = root / relative if root else None
        paths[role] = {
            "relative": relative,
            "path": str(absolute) if absolute else None,
            "exists": bool(absolute and absolute.is_file()),
        }
    read_only = bool(root and os.statvfs(root).f_flag & getattr(os, "ST_RDONLY", 1))
    report = {
        "schema_version": 1,
        "checkpoint": str(checkpoint_file),
        "updated": checkpoint.get("updated"),
        "title": checkpoint["title"],
        "sd_root": str(root) if root else None,
        "sd_status": "read-only" if read_only else "read-write" if root else "not-found",
        "projects": paths,
        "routes": checkpoint.get("routes", []),
        "next_action": checkpoint["next_action"],
        "notes": checkpoint.get("notes", ""),
    }
    if as_json:
        print(json.dumps(report, indent=2))
        return 0
    print(f"RESUME: {report['title']}")
    print(f"Checkpoint: {checkpoint_file} ({report['updated'] or 'date unknown'})")
    print(f"SD: {report['sd_status']} — {root or 'no matching mounted card found'}")
    for role in ("baseline", "working", "target"):
        item = paths[role]
        state = "FOUND" if item["exists"] else "MISSING"
        print(f"{role.title():<8} {state:<7} {item['path'] or item['relative']}")
    routes = "; ".join(
        f"T{row['track']} {row['name']} ch{row['channel']}" for row in report["routes"]
    )
    print(f"Routes: {routes}")
    print(f"NEXT: {report['next_action']}")
    if report["notes"]:
        print(f"NOTE: {report['notes']}")
    return 0


def _commands(category: str | None, as_json: bool) -> int:
    rows = [
        {
            "command": command,
            "category": spec.category,
            "summary": spec.summary,
            "documentation": spec.documentation,
        }
        for command, spec in sorted(COMMANDS.items())
        if command != "mpc-tools" and (category is None or spec.category.casefold() == category.casefold())
    ]
    if as_json:
        print(json.dumps(rows, indent=2))
        return 0
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["category"]].append(row)
    for name in sorted(grouped):
        print(f"\n{name}")
        for row in grouped[name]:
            print(f"  {row['command']:<26} {row['summary']}")
    print("\nRun `mpc-tools help COMMAND` for detailed arguments.")
    return 0


def _doctor(as_json: bool) -> int:
    checks = []

    def add(name: str, status: str, detail: str) -> None:
        checks.append({"name": name, "status": status, "detail": detail})

    supported = sys.version_info >= (3, 12)
    add("Python", "pass" if supported else "fail", sys.version.split()[0] + " (requires 3.12+)")
    add("Package", "pass", version())
    command_path = shutil.which("mpc-tools")
    add(
        "Command PATH",
        "pass" if command_path else "warn",
        command_path or "mpc-tools is running but is not discoverable through PATH",
    )
    try:
        with tempfile.NamedTemporaryFile(prefix=".mpc-write-test-", dir=Path.cwd()):
            pass
        add("Current directory", "pass", f"writable: {Path.cwd()}")
    except OSError as error:
        add("Current directory", "warn", f"not writable: {error}")
    repo = Path.cwd() / "pyproject.toml"
    add(
        "Repository checkout",
        "pass" if repo.is_file() else "info",
        "detected" if repo.is_file() else "not required for installed commands",
    )
    if as_json:
        print(json.dumps({"checks": checks}, indent=2))
    else:
        for item in checks:
            print(f"{item['status'].upper():<5} {item['name']}: {item['detail']}")
    return 2 if any(item["status"] == "fail" for item in checks) else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="Start with `mpc-tools demo --output mpc-demo` or list everything with `mpc-tools commands`.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {version()}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    commands = subparsers.add_parser("commands", help="list tools by workflow category")
    commands.add_argument("--category", help="show one category, such as Build or Creative MIDI")
    commands.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    help_parser = subparsers.add_parser("help", help="show detailed help for one command")
    help_parser.add_argument("tool", choices=sorted(name for name in COMMANDS if name != "mpc-tools"))
    doctor = subparsers.add_parser("doctor", help="check the installation and current directory")
    doctor.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    resume = subparsers.add_parser(
        "resume", help="show the current project checkpoint and exact next action"
    )
    resume.add_argument(
        "--checkpoint",
        type=Path,
        help="checkpoint TOML; defaults to inventory/session-checkpoint.toml",
    )
    resume.add_argument(
        "--sd-root",
        type=Path,
        help="mounted MPC SD-card root; otherwise detect under /media",
    )
    resume.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    demo = subparsers.add_parser("demo", help="build the complete redistributable workflow fixture")
    demo_destination = demo.add_mutually_exclusive_group(required=True)
    demo_destination.add_argument("--output", type=Path, help="new directory for the generated demo")
    demo_destination.add_argument("--verify", type=Path, metavar="DEMO", help="verify an existing demo without changing it")
    browser = subparsers.add_parser("web-demo", help="write a standalone browser-only Program Designer demo")
    browser.add_argument("--output", type=Path, required=True, help="HTML file to create")
    browser.add_argument("--force", action="store_true", help="replace an existing demo HTML file")
    new = subparsers.add_parser("new", help="create a safe starter for a common MPC workflow")
    new.add_argument("kind", choices=KINDS)
    new.add_argument("--name", required=True, help="human-readable instrument or setup name")
    new.add_argument("--output", type=Path, required=True, help="new starter directory")
    new.add_argument(
        "--family",
        choices=("dusty", "ambient", "electro", "funk", "house", "weird"),
        help="workstation recipe family (default for workstations: dusty)",
    )
    args = parser.parse_args()
    if args.command == "commands":
        return _commands(args.category, args.json)
    if args.command == "help":
        try:
            return invoke(args.tool, ["--help"])
        except SystemExit as error:
            return int(error.code or 0)
    if args.command == "doctor":
        return _doctor(args.json)
    if args.command == "resume":
        return _resume(args.checkpoint, args.sd_root, args.json)
    if args.command == "demo":
        if args.verify is not None:
            report = verify_demo(args.verify)
            print(f"PASS: {report['verified_files']} files and the cross-kit simulation verified")
            print(f"Hardware status: {report['hardware_status']}")
            return 0
        report = build_demo(args.output.expanduser(), None)
        print(f"PASS: {args.output.expanduser().resolve() / report['cross_kit_program']}")
        print(f"Next: open {args.output.resolve() / 'HARDWARE_CHECKLIST.md'}")
        return 0
    if args.command == "new":
        if args.kind != "workstation" and args.family is not None:
            parser.error("--family applies only to workstation starters")
        output = create_scaffold(args.kind, args.name, args.output, args.family or "dusty")
        print(f"Created {args.kind} starter: {output}")
        print(f"Next: open {output / 'README.md'}")
        return 0
    output = args.output.expanduser().resolve()
    build_web_demo(output, force=args.force)
    print(f"Wrote browser demo: {output}")
    return 0
