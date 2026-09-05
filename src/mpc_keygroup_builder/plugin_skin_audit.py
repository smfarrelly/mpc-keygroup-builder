"""Compare MPC plugin UI skins before trusting their parameter metadata."""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

from . import plugin_params


SKINS = ("GUI-Popout.json", "GUI.json", "TUI.json")


def _normalized(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def inspect_plugin(path: Path) -> dict[str, Any]:
    skin_root = path / "Plugin Skins"
    documents: dict[str, dict[int, list[dict[str, Any]]]] = {}
    parse_errors = []
    for name in SKINS:
        source = skin_root / name
        if not source.is_file():
            continue
        try:
            raw = json.loads(source.read_text(encoding="utf-8"))
            grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
            for control in plugin_params.extract_components(raw):
                grouped[control["ui_parameter"]].append(control)
            documents[name] = dict(grouped)
        except (OSError, json.JSONDecodeError) as error:
            parse_errors.append({"skin": name, "error": str(error)})
    selected = next((name for name in plugin_params.SKIN_PREFERENCE if name in documents), None)
    union = sorted({number for document in documents.values() for number in document})
    selected_ids = set(documents.get(selected, {})) if selected else set()
    missing = [
        {
            "ui_parameter": number,
            "names": sorted({row["name"] for document in documents.values() for row in document.get(number, [])}),
            "present_in": sorted(name for name, document in documents.items() if number in document),
        }
        for number in union if number not in selected_ids
    ]
    name_variants = []
    types_variants = []
    name_bindings: dict[str, dict[str, set[int]]] = defaultdict(lambda: defaultdict(set))
    for number in union:
        names = {row["name"] for document in documents.values() for row in document.get(number, [])}
        normalized = {_normalized(name) for name in names}
        if len(normalized) > 1:
            name_variants.append({"ui_parameter": number, "names": sorted(names)})
        types = {row["control_type"] for document in documents.values() for row in document.get(number, [])}
        if len({_normalized(value) for value in types}) > 1:
            types_variants.append({"ui_parameter": number, "control_types": sorted(types)})
        for skin, document in documents.items():
            for row in document.get(number, []):
                name_bindings[_normalized(row["name"])][skin].add(number)
    binding_conflicts = []
    for token, bindings_by_skin in sorted(name_bindings.items()):
        distinct = {tuple(sorted(numbers)) for numbers in bindings_by_skin.values()}
        if token and len(bindings_by_skin) > 1 and len(distinct) > 1:
            names = sorted({row["name"] for document in documents.values() for rows in document.values() for row in rows if _normalized(row["name"]) == token})
            binding_conflicts.append({
                "name": names[0],
                "skins": [
                    {"skin": skin, "ui_parameters": sorted(numbers)}
                    for skin, numbers in sorted(bindings_by_skin.items())
                ],
            })
    blockers = len(parse_errors) + len(missing) + len(binding_conflicts)
    return {
        "plugin": path.name.split(" - MPC - ", 1)[-1], "path": str(path.resolve()),
        "selected_skin": selected, "skins": [
            {"name": name, "control_count": len(document)} for name, document in documents.items()
        ],
        "union_control_count": len(union), "selected_control_count": len(selected_ids),
        "missing_from_selected": missing, "name_variants": name_variants,
        "control_type_variants": types_variants, "binding_conflicts": binding_conflicts,
        "parse_errors": parse_errors,
        "status": "fail" if parse_errors or not selected else "warn" if blockers else "pass",
    }


def audit(root: Path) -> dict[str, Any]:
    paths = plugin_params.discover(root)
    plugins = [inspect_plugin(path) for path in paths]
    summary = {
        "plugins": len(plugins),
        "pass": sum(item["status"] == "pass" for item in plugins),
        "warn": sum(item["status"] == "warn" for item in plugins),
        "fail": sum(item["status"] == "fail" for item in plugins),
        "missing_from_selected": sum(len(item["missing_from_selected"]) for item in plugins),
        "binding_conflicts": sum(len(item["binding_conflicts"]) for item in plugins),
        "name_variants": sum(len(item["name_variants"]) for item in plugins),
    }
    return {
        "schema_version": 1, "kind": "mpc-plugin-skin-audit", "root": str(root.expanduser().resolve()),
        "summary": summary, "plugins": plugins,
        "boundary": "Skin agreement strengthens UI metadata evidence but does not prove MIDI Learn availability or stable MPC parameter IDs.",
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# MPC plugin skin consistency", "",
        f"{summary['plugins']} plugins: {summary['pass']} pass, {summary['warn']} warn, {summary['fail']} fail.",
        f"Missing from selected skin: {summary['missing_from_selected']}; binding conflicts: {summary['binding_conflicts']}; name variants: {summary['name_variants']}.", "",
    ]
    for item in report["plugins"]:
        skin_counts = ", ".join(f"{row['name']} {row['control_count']}" for row in item["skins"]) or "none"
        lines.extend((
            f"## {item['plugin']} — {item['status']}", "",
            f"Selected: {item['selected_skin'] or 'none'} ({item['selected_control_count']} controls); union: {item['union_control_count']}. Skins: {skin_counts}.", "",
        ))
        for row in item["missing_from_selected"]:
            lines.append(f"- Missing UI {row['ui_parameter']} ({', '.join(row['names'])}) from selected skin; present in {', '.join(row['present_in'])}.")
        for row in item["binding_conflicts"]:
            bindings = "; ".join(f"{value['skin']} UI {', '.join(map(str, value['ui_parameters']))}" for value in row["skins"])
            lines.append(f"- Binding conflict for {row['name']}: {bindings}.")
        for row in item["parse_errors"]:
            lines.append(f"- Cannot parse {row['skin']}: {row['error']}")
        if item["missing_from_selected"] or item["binding_conflicts"] or item["parse_errors"]:
            lines.append("")
    lines.extend(("## Evidence boundary", "", report["boundary"], ""))
    return "\n".join(lines)


def write_report(report: dict[str, Any], output: Path) -> None:
    output = output.expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"plugin skin audit output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        (staging / "plugin-skin-audit.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        (staging / "PLUGIN_SKIN_AUDIT.md").write_text(render_markdown(report), encoding="utf-8")
        with (staging / "plugin-skin-audit.csv").open("w", newline="", encoding="utf-8") as stream:
            fields = ("plugin", "status", "selected_skin", "selected_controls", "union_controls", "missing_from_selected", "binding_conflicts", "name_variants", "control_type_variants", "parse_errors")
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for item in report["plugins"]:
                writer.writerow({
                    "plugin": item["plugin"], "status": item["status"], "selected_skin": item["selected_skin"] or "",
                    "selected_controls": item["selected_control_count"], "union_controls": item["union_control_count"],
                    "missing_from_selected": len(item["missing_from_selected"]), "binding_conflicts": len(item["binding_conflicts"]),
                    "name_variants": len(item["name_variants"]), "control_type_variants": len(item["control_type_variants"]),
                    "parse_errors": len(item["parse_errors"]),
                })
        os.replace(staging, output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="one plugin directory or MPC Synths directory")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fail-on-issue", action="store_true", help="exit 2 when any plugin warns or fails")
    args = parser.parse_args(argv or sys.argv[1:])
    report = audit(args.root)
    write_report(report, args.output)
    summary = report["summary"]
    print(f"Wrote: {args.output.expanduser().resolve()}")
    print(f"Plugins: {summary['plugins']}; pass: {summary['pass']}; warn: {summary['warn']}; fail: {summary['fail']}")
    return 2 if args.fail_on_issue and (summary["warn"] or summary["fail"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
