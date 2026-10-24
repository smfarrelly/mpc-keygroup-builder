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
from pathlib import Path, PureWindowsPath

from .entrypoints import COMMANDS, invoke, version
from .portable_demo import build_demo, verify_demo
from .scaffold import KINDS, create as create_scaffold
from .web_demo import build_web_demo
from .start import WORKFLOWS, show as show_start
from .readiness import show as show_readiness


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


def _checkpoint_target(root: Path, relative: str) -> Path:
    target = root / relative
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"checkpoint project escapes SD root (possibly through a symlink): {relative}")
    return target


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
            if path.is_dir() and _checkpoint_target(path, baseline_relative).is_file()
        ),
        None,
    )


def _resume(checkpoint_path: Path | None, sd_root: Path | None, as_json: bool, *, offline: bool = False) -> int:
    if offline and sd_root is not None:
        raise ValueError("--offline cannot be combined with --sd-root")
    checkpoint_file = _find_checkpoint(checkpoint_path)
    checkpoint = tomllib.loads(checkpoint_file.read_text(encoding="utf-8"))
    required = ("title", "baseline_relative", "working_relative", "target_relative", "next_action")
    missing = [name for name in required if not isinstance(checkpoint.get(name), str) or not checkpoint[name].strip()]
    if missing:
        raise ValueError(f"checkpoint lacks required fields: {', '.join(missing)}")
    for role in ('baseline', 'working', 'target'):
        relative = checkpoint[f'{role}_relative']
        path = Path(relative)
        if path.is_absolute() or PureWindowsPath(relative).drive or '\\' in relative or '\0' in relative or '..' in path.parts:
            raise ValueError(f"{role}_relative must stay within the SD root: {relative}")
        if path.suffix.casefold() != '.xpj':
            raise ValueError(f"{role}_relative must name an .xpj project: {relative}")
    root = None if offline else _find_sd_root(sd_root, checkpoint["baseline_relative"])
    paths = {}
    for role in ("baseline", "working", "target"):
        relative = checkpoint[f"{role}_relative"]
        absolute = _checkpoint_target(root, relative) if root else None
        paths[role] = {
            "relative": relative,
            "path": str(absolute) if absolute else None,
            "exists": None if offline else bool(absolute and absolute.is_file()),
        }
    read_only = bool(root and os.statvfs(root).f_flag & getattr(os, "ST_RDONLY", 1))
    report = {
        "schema_version": 1,
        "checkpoint": str(checkpoint_file),
        "updated": checkpoint.get("updated"),
        "title": checkpoint["title"],
        "sd_root": str(root) if root else None,
        "sd_status": "not-checked" if offline else "read-only" if read_only else "read-write" if root else "not-found",
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
    print(f"SD: {report['sd_status']} — {root or ('offline mode; storage not inspected' if offline else 'no matching mounted card found')}")
    for role in ("baseline", "working", "target"):
        item = paths[role]
        state = "NOT CHECKED" if offline else "FOUND" if item["exists"] else "MISSING"
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
    start = subparsers.add_parser("start", help="choose one workflow without inspecting drives or running commands")
    start.add_argument("goal", nargs="?", choices=tuple(WORKFLOWS))
    start.add_argument("--json", action="store_true")
    home = subparsers.add_parser("home", help="generate a private local starting page from explicit inputs")
    home.add_argument("--output", required=True, type=Path)
    home.add_argument("--config", type=Path, help="saved local input selection; cannot be combined with input flags")
    home.add_argument("--archive-library", type=Path)
    home.add_argument("--ledger", type=Path)
    home.add_argument("--program-root", type=Path)
    home.add_argument("--bundle", type=Path, action="append", default=[])
    home.add_argument("--recipe-root", type=Path)
    reconcile = subparsers.add_parser("reconcile", help="find local XPM candidates for ledger paths without changing them")
    reconcile.add_argument("--ledger", required=True, type=Path)
    reconcile.add_argument("--library-root", required=True, type=Path, action="append", help="explicit local library; repeat for separate, non-overlapping roots")
    reconcile.add_argument("--favorite", choices=("yes", "no", "provisional"))
    reconcile.add_argument("--verify-samples", action="store_true", help="resolve candidates' sample references within each library; no audio decoding")
    reconcile.add_argument("--json", action="store_true")
    reconcile.add_argument("--output", type=Path, help="write a new private JSON report outside input libraries")
    check = subparsers.add_parser("check", help="read-only readiness checks for explicitly selected local files")
    check.add_argument("--archive", type=Path, action="append", default=[])
    check.add_argument("--bundle", type=Path, action="append", default=[])
    check.add_argument("--program", type=Path, action="append", default=[])
    check.add_argument("--sample-root", type=Path, help="bound sample lookup to this directory; default is each program's parent")
    check.add_argument("--json", action="store_true")
    check.add_argument("--recipe-root", type=Path, help="compare bundle build-time recipe inputs with this current recipe tree")
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
    resume.add_argument("--offline", action="store_true", help="read only the local checkpoint; do not discover or inspect SD storage")
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
    if args.command == "start":
        return show_start(args.goal, args.json)
    if args.command == "home":
        from .home import build, load_config
        if args.config is not None:
            if any((args.archive_library, args.ledger, args.program_root, args.bundle, args.recipe_root)):
                parser.error('--config cannot be combined with home input flags')
            inputs = load_config(args.config)
        else:
            inputs = dict(archive_library=args.archive_library, ledger=args.ledger,
                          program_root=args.program_root, bundles=args.bundle, recipe_root=args.recipe_root)
        report = build(args.output, **inputs)
        print(f"Local starting page: {args.output.expanduser().resolve()}")
        print('Point-in-time report only; no hardware acceptance inferred.')
        return 1 if report['status'] == 'attention' else 0
    if args.command == "reconcile":
        from .reconcile import show
        return show(args.ledger, args.library_root, args.favorite, args.verify_samples, args.json, args.output)
    if args.command == "check":
        return show_readiness(args.archive, args.bundle, args.program, args.sample_root, args.json, args.recipe_root)
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
        return _resume(args.checkpoint, args.sd_root, args.json, offline=args.offline)
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
