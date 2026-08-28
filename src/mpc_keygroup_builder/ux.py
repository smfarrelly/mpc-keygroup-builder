"""Friendly front door for discovering and checking the MPC instrument tools."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

from .entrypoints import COMMANDS, invoke, version
from .portable_demo import build_demo
from .web_demo import build_web_demo


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
    demo = subparsers.add_parser("demo", help="build the complete redistributable workflow fixture")
    demo.add_argument("--output", type=Path, required=True, help="new directory for the generated demo")
    browser = subparsers.add_parser("web-demo", help="write a standalone browser-only Program Designer demo")
    browser.add_argument("--output", type=Path, required=True, help="HTML file to create")
    browser.add_argument("--force", action="store_true", help="replace an existing demo HTML file")
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
    if args.command == "demo":
        report = build_demo(args.output.expanduser(), None)
        print(f"PASS: {report['cross_kit_program']}")
        print(f"Next: open {args.output.resolve() / 'HARDWARE_CHECKLIST.md'}")
        return 0
    output = args.output.expanduser().resolve()
    build_web_demo(output, force=args.force)
    print(f"Wrote browser demo: {output}")
    return 0
