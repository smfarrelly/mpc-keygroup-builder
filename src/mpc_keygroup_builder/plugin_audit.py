"""Inventory MPC standalone plugin content without claiming activation state."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


SHARED_DIRECTORIES = {"air components", "generic"}


def _version(path: Path) -> tuple[str | None, str | None, str | None]:
    marker = path / "version.xml"
    if not marker.is_file():
        return None, None, None
    try:
        root = ET.parse(marker).getroot()
    except ET.ParseError as error:
        return None, None, f"unreadable version.xml: {error}"
    identifier = root.findtext("identifier")
    version = root.findtext("version")
    if not identifier or not version:
        return identifier, version, "version.xml lacks identifier or version"
    return identifier, version, None


def inspect_content(path: Path) -> dict[str, Any]:
    files = sorted(item for item in path.rglob("*") if item.is_file())
    identifier, version, marker_issue = _version(path)
    presets = [
        item
        for item in files
        if item.suffix.casefold() == ".xpl"
        and any(parent.casefold() == "presets" for parent in item.parts)
    ]
    content_files = [
        item for item in files if any(parent.casefold() == "content" for parent in item.parts)
    ]
    warnings = []
    if marker_issue:
        warnings.append(marker_issue)
    if version is None and path.name.casefold() not in SHARED_DIRECTORIES:
        warnings.append("no version.xml marker; content presence does not prove activation")
    evidence = (
        "versioned-content"
        if version is not None
        else "preset-content"
        if presets
        else "assets-only"
    )
    return {
        "name": path.name,
        "role": "shared" if path.name.casefold() in SHARED_DIRECTORIES else "plugin-content",
        "identifier": identifier,
        "version": version,
        "evidence": evidence,
        "file_count": len(files),
        "bytes": sum(item.stat().st_size for item in files),
        "preset_count": len(presets),
        "content_file_count": len(content_files),
        "warnings": warnings,
    }


def audit(root: Path) -> dict[str, Any]:
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(root)
    entries = [inspect_content(path) for path in sorted(root.iterdir()) if path.is_dir()]
    return {
        "schema_version": 1,
        "root": str(root),
        "directory_count": len(entries),
        "plugin_content_count": sum(item["role"] == "plugin-content" for item in entries),
        "total_files": sum(item["file_count"] for item in entries),
        "total_bytes": sum(item["bytes"] for item in entries),
        "total_presets": sum(item["preset_count"] for item in entries),
        "entries": entries,
        "boundary": (
            "Filesystem content can support an installed plugin, but activation, binary "
            "availability, playability, and project persistence require MPC hardware testing."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# MPC plugin content audit",
        "",
        f"Root: `{report['root']}`",
        "",
        f"Directories: {report['directory_count']}; plugin-content directories: "
        f"{report['plugin_content_count']}; files: {report['total_files']}; "
        f"presets: {report['total_presets']}; bytes: {report['total_bytes']}.",
        "",
        "| Name | Evidence | Version | Presets | Content files | Files | Warnings |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for item in report["entries"]:
        warnings = "; ".join(item["warnings"]) or "—"
        lines.append(
            f"| {item['name']} | {item['evidence']} | {item['version'] or '—'} | "
            f"{item['preset_count']} | {item['content_file_count']} | {item['file_count']} | "
            f"{warnings} |"
        )
    lines.extend(["", f"**Boundary:** {report['boundary']}", ""])
    return "\n".join(lines)


def _write_atomic(path: Path, text: str) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="MPC Synths content directory")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    report = audit(args.root)
    text = (
        json.dumps(report, indent=2) + "\n"
        if args.format == "json"
        else render_markdown(report)
    )
    if args.output:
        _write_atomic(args.output, text)
        print(f"Wrote: {args.output}")
    else:
        print(text, end="")
    return 0
