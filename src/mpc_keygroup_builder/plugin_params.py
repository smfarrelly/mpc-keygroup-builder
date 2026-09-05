"""Build a searchable parameter catalog from MPC plugin UI metadata."""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable

from . import xpj


PARAMETER = re.compile(r"^Parameter\s+(\d+)$", re.IGNORECASE)
SKIN_PREFERENCE = ("GUI-Popout.json", "GUI.json", "TUI.json")
USEFUL_WORDS = {
    "macro": 12,
    "cutoff": 11,
    "resonance": 10,
    "reso": 10,
    "attack": 8,
    "decay": 8,
    "release": 8,
    "feedback": 8,
    "mix": 7,
    "drive": 7,
    "level": 6,
    "depth": 6,
    "rate": 6,
    "speed": 6,
    "tune": 5,
    "ratio": 5,
    "pan": 4,
    "enable": 3,
}
DECORATIVE_WORDS = (
    " bg",
    "background",
    " label",
    " panel",
    " tab",
    " image",
    "active settings",
    "blank ",
    "bypassed",
)


def _plugin_name(path: Path) -> str:
    marker = " - MPC - "
    return path.name.split(marker, 1)[-1] if marker in path.name else path.name


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _parameter_handles(value: Any) -> Iterable[int]:
    if isinstance(value, dict):
        handle = value.get("handleName")
        if isinstance(handle, str) and (match := PARAMETER.match(handle)):
            yield int(match.group(1))
        for key, child in value.items():
            if key != "componentData":
                yield from _parameter_handles(child)
    elif isinstance(value, list):
        for child in value:
            yield from _parameter_handles(child)


def _components(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        component = value.get("componentData")
        if isinstance(component, dict):
            name = str(component.get("name", "")).strip()
            control_type = str(component.get("type", "")).strip()
            # The binding is direct in some skins and nested under either
            # ``map`` or ``handle remapping`` in others. Do not consume
            # additionalInvalidatingHandles: those are dependencies, not the
            # control's own value.
            handles = set(_parameter_handles(component))
            mappings = list(value.get("map", []))
            remapping = value.get("handle remapping", {})
            if isinstance(remapping, dict):
                mappings.extend(remapping.get("map", []))
            for entry in mappings:
                if not isinstance(entry, dict) or entry.get("key") != "Data":
                    continue
                raw = entry.get("value")
                if isinstance(raw, str) and (match := PARAMETER.match(raw)):
                    handles.add(int(match.group(1)))
            handles = sorted(handles)
            for number in sorted(set(handles)):
                if name and not _decorative(name, control_type):
                    yield {"ui_parameter": number, "name": name, "control_type": control_type}
        for child in value.values():
            yield from _components(child)
    elif isinstance(value, list):
        for child in value:
            yield from _components(child)


def _decorative(name: str, control_type: str) -> bool:
    lowered = f" {name.casefold()}"
    if any(word in lowered for word in DECORATIVE_WORDS):
        return True
    return control_type.casefold() in {"image", "label", "filmstrip"}


def extract_components(document: Any) -> list[dict[str, Any]]:
    """Return non-decorative parameter-bound controls from one UI document."""
    return list(_components(document))


def _score(name: str, learned: bool) -> int:
    lowered = name.casefold()
    score = 25 if learned else 0
    score += max((points for word, points in USEFUL_WORDS.items() if word in lowered), default=0)
    if any(word in lowered for word in ("select", "mode", "type", "source", "destination")):
        score -= 2
    return score


def _qlinks(plugin: Path) -> dict[int, list[str]]:
    result: dict[int, set[str]] = {}
    skin_root = plugin / "Plugin Skins"
    path = next(
        (
            skin_root / name
            for name in ("Q-Links.json", "Q-Links - 8by1.json")
            if (skin_root / name).is_file()
        ),
        None,
    )
    if path is None:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    for section in ("Screen Mode Q-Links", "Program Mode Q-Links"):
        maps = data.get(section, {}).get("map", [])
        for page in maps if isinstance(maps, list) else []:
            if not isinstance(page, dict):
                continue
            location = (
                f"{section.removesuffix(' Q-Links')} "
                f"T{page.get('Tab', '?')}/S{page.get('SubTab', '?')}"
            )
            for position, parameter in page.get("Q-Links", {}).items():
                if isinstance(parameter, int) and parameter >= 0:
                    result.setdefault(parameter, set()).add(f"{location} {position}")
    return {key: sorted(value) for key, value in result.items()}


def _learned(project: Path | None, plugin_name: str) -> list[dict[str, Any]]:
    if project is None:
        return []
    token = _normalize(plugin_name)
    rows = xpj.midi_learn_rows(xpj.load(project.expanduser().resolve()))
    return [row for row in rows if token and token in _normalize(str(row.get("track", "")))]


def inspect_plugin(plugin: Path, project: Path | None = None) -> dict[str, Any]:
    plugin = plugin.expanduser().resolve()
    skin_root = plugin / "Plugin Skins"
    if not skin_root.is_dir():
        raise NotADirectoryError(f"Plugin Skins not found under {plugin}")
    skin = next(
        (skin_root / name for name in SKIN_PREFERENCE if (skin_root / name).is_file()),
        None,
    )
    if skin is None:
        raise FileNotFoundError(f"no supported plugin UI JSON under {skin_root}")
    data = json.loads(skin.read_text(encoding="utf-8"))
    name = _plugin_name(plugin)
    learned = _learned(project, name)
    learned_by_parameter: dict[int, list[dict[str, Any]]] = {}
    for row in learned:
        parameter = row.get("parameter")
        if isinstance(parameter, int):
            learned_by_parameter.setdefault(parameter, []).append(row)
    qlinks = _qlinks(plugin)
    grouped: dict[int, list[dict[str, Any]]] = {}
    for component in extract_components(data):
        grouped.setdefault(component["ui_parameter"], []).append(component)
    offset_evidence = any(number + 4096 in learned_by_parameter for number in grouped)
    controls = []
    for ui_parameter, candidates in sorted(grouped.items()):
        candidates.sort(key=lambda item: (len(item["name"]), item["name"].casefold()))
        component = candidates[0]
        mpc_parameter = ui_parameter + 4096
        matches = learned_by_parameter.get(mpc_parameter, [])
        aliases = sorted({item["name"] for item in candidates if item["name"] != component["name"]})
        controls.append(
            {
                "ui_parameter": ui_parameter,
                "mpc_parameter": mpc_parameter,
                "mpc_parameter_basis": (
                    "verified"
                    if matches
                    else "inferred:+4096"
                    if offset_evidence
                    else "hypothesis:+4096"
                ),
                "name": component["name"],
                "aliases": aliases,
                "control_type": component["control_type"],
                "q_links": qlinks.get(ui_parameter, []),
                "learned": bool(matches),
                "learned_cc": sorted(
                    {row["number"] for row in matches if row.get("number") is not None}
                ),
                "learned_channel": sorted(
                    {row["channel"] for row in matches if row.get("channel") is not None}
                ),
                "usefulness_score": _score(component["name"], bool(matches)),
            }
        )
    return {
        "schema_version": 1,
        "plugin": name,
        "plugin_root": str(plugin),
        "skin": str(skin),
        "preset_count": len(list(plugin.rglob("*.xpl"))),
        "control_count": len(controls),
        "learned_control_count": sum(item["learned"] for item in controls),
        "controls": controls,
        "boundary": (
            "UI metadata enumerates visible controls; it does not prove every control is a stable "
            "MIDI Learn target. Inferred MPC parameter IDs use a +4096 relationship observed "
            "for the same plugin; hypothesis IDs have no same-plugin capture evidence."
        ),
    }


def discover(root: Path) -> list[Path]:
    root = root.expanduser().resolve()
    if (root / "Plugin Skins").is_dir():
        return [root]
    if not root.is_dir():
        raise NotADirectoryError(root)
    return sorted(path for path in root.iterdir() if (path / "Plugin Skins").is_dir())


def catalog(
    root: Path,
    project: Path | None = None,
    plugin_filter: str | None = None,
) -> dict[str, Any]:
    paths = discover(root)
    if plugin_filter:
        token = plugin_filter.casefold()
        paths = [path for path in paths if token in _plugin_name(path).casefold()]
    plugins = []
    skipped = []
    for path in paths:
        try:
            plugins.append(inspect_plugin(path, project))
        except (FileNotFoundError, json.JSONDecodeError) as error:
            skipped.append({"path": str(path), "reason": str(error)})
    if plugin_filter and not plugins:
        raise FileNotFoundError(
            f"no plugin matching {plugin_filter!r} with supported UI metadata under {root}"
        )
    return {
        "schema_version": 1,
        "root": str(root.expanduser().resolve()),
        "project": str(project) if project else None,
        "plugins": plugins,
        "skipped": skipped,
    }


def filtered(
    report: dict[str, Any],
    query: str | None,
    recommended: bool,
    limit: int | None,
) -> list[dict[str, Any]]:
    rows = []
    tokens = [part.casefold() for part in (query or "").split()]
    for plugin in report["plugins"]:
        for control in plugin["controls"]:
            haystack = " ".join([control["name"], *control["aliases"]]).casefold()
            if tokens and not all(token in haystack for token in tokens):
                continue
            if recommended and control["usefulness_score"] <= 0:
                continue
            rows.append({"plugin": plugin["plugin"], **control})
    rows.sort(
        key=lambda item: (
            -item["usefulness_score"],
            item["plugin"].casefold(),
            item["name"].casefold(),
        )
    )
    return rows[:limit] if limit is not None else rows


def render_markdown(report: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = ["# MPC plugin parameter catalog", "", f"Root: `{report['root']}`", ""]
    for plugin in report["plugins"]:
        lines.append(
            f"- **{plugin['plugin']}**: {plugin['control_count']} UI controls; "
            f"{plugin['learned_control_count']} verified by project MIDI Learn; "
            f"{plugin['preset_count']} presets."
        )
    lines.extend(
        [
            "",
            "| Plugin | Control | UI # | MPC ID | Evidence | Learned MIDI | Q-Link locations |",
            "|---|---|---:|---:|---|---|---|",
        ]
    )
    for row in rows:
        midi = ", ".join(
            f"ch{channel}/CC{cc}"
            for channel in row["learned_channel"]
            for cc in row["learned_cc"]
        ) or "—"
        locations = "; ".join(row["q_links"]) or "—"
        lines.append(
            f"| {row['plugin']} | {row['name']} | {row['ui_parameter']} | "
            f"{row['mpc_parameter']} | {row['mpc_parameter_basis']} | {midi} | "
            f"{locations} |"
        )
    lines.extend(
        [
            "",
            "MPC IDs marked `inferred:+4096` or `hypothesis:+4096` are "
            "candidates, not hardware-verified mappings.",
            "",
        ]
    )
    return "\n".join(lines)


def render_csv(rows: list[dict[str, Any]]) -> str:
    stream = io.StringIO()
    fields = (
        "plugin", "name", "ui_parameter", "mpc_parameter", "mpc_parameter_basis",
        "control_type", "usefulness_score", "learned_channel", "learned_cc", "q_links",
    )
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                key: "; ".join(map(str, row[key]))
                if isinstance(row[key], list)
                else row[key]
                for key in fields
            }
        )
    return stream.getvalue()


def _write_atomic(path: Path, text: str) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
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
    parser.add_argument("root", type=Path, help="one plugin directory or the MPC Synths directory")
    parser.add_argument("--plugin", help="case-insensitive plugin-name filter")
    parser.add_argument("--project", type=Path, help="optional MPC 3 XPJ with MIDI Learn evidence")
    parser.add_argument("--query", help="space-separated words that must occur in a control name")
    parser.add_argument("--recommended", action="store_true", help="show performance-useful controls first")
    parser.add_argument("--limit", type=int, default=100, help="maximum rendered rows; use 0 for all")
    parser.add_argument("--format", choices=("markdown", "json", "csv"), default="markdown")
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    report = catalog(args.root, args.project, args.plugin)
    rows = filtered(report, args.query, args.recommended, None if args.limit == 0 else args.limit)
    if args.format == "json":
        text = json.dumps({**report, "results": rows}, indent=2) + "\n"
    elif args.format == "csv":
        text = render_csv(rows)
    else:
        text = render_markdown(report, rows)
    if args.output:
        _write_atomic(args.output, text)
        print(f"Wrote: {args.output.expanduser().resolve()}")
    else:
        print(text, end="")
    return 0
