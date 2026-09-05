"""Measure plugin mapping coverage and rank useful controls still omitted."""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from . import plugin_map, plugin_params


def _normalized(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def analyze(profiles: list[dict[str, Any]], catalog: dict[str, Any], omitted_limit: int = 10) -> dict[str, Any]:
    if omitted_limit < 0:
        raise ValueError("omitted-limit must be nonnegative")
    validation = plugin_map.validate_batch(profiles, catalog)
    if validation["errors"]:
        raise ValueError("invalid plugin mapping batch: " + "; ".join(validation["errors"]))
    planned: dict[str, list[dict[str, Any]]] = defaultdict(list)
    profile_names: dict[str, set[str]] = defaultdict(set)
    for result in validation["profiles"]:
        for row in result["controls"]:
            key = _normalized(row["plugin"])
            planned[key].append(row)
            profile_names[key].add(result["profile"]["id"])
    plugins = []
    overall = Counter()
    for source in sorted(catalog.get("plugins", []), key=lambda item: item["plugin"].casefold()):
        key = _normalized(source["plugin"])
        rows = planned.get(key, [])
        occurrences = Counter(row["ui_parameter"] for row in rows)
        planned_ids = set(occurrences)
        learned_ids = {control["ui_parameter"] for control in source["controls"] if control.get("learned")}
        covered_ids = planned_ids | learned_ids
        useful = [control for control in source["controls"] if int(control.get("usefulness_score", 0)) > 0]
        useful_ids = {control["ui_parameter"] for control in useful}
        omitted = sorted(
            (control for control in useful if control["ui_parameter"] not in covered_ids),
            key=lambda item: (-int(item["usefulness_score"]), -int(bool(item.get("q_links"))), item["name"].casefold()),
        )[:omitted_limit]
        roles = Counter(row["role"] for row in rows)
        evidence = Counter(row["evidence"] for row in rows)
        duplicate_targets = [
            {"ui_parameter": number, "name": next(row["name"] for row in rows if row["ui_parameter"] == number), "assignments": count}
            for number, count in sorted(occurrences.items()) if count > 1
        ]
        useful_covered = len(useful_ids & covered_ids)
        plugin = {
            "plugin": source["plugin"], "profiles": sorted(profile_names.get(key, set())),
            "discovered_controls": len(source["controls"]), "useful_controls": len(useful),
            "planned_controls": len(planned_ids), "learned_controls": len(learned_ids),
            "covered_controls": len(covered_ids), "useful_covered": useful_covered,
            "useful_coverage_percent": round(100 * useful_covered / len(useful), 1) if useful else 100.0,
            "roles": dict(sorted(roles.items())), "evidence": dict(sorted(evidence.items())),
            "duplicate_targets": duplicate_targets,
            "omitted_recommended": [
                {
                    "name": control["name"], "ui_parameter": control["ui_parameter"],
                    "mpc_parameter": control["mpc_parameter"], "evidence": control["mpc_parameter_basis"],
                    "usefulness_score": control["usefulness_score"], "q_links": control.get("q_links", []),
                }
                for control in omitted
            ],
        }
        plugins.append(plugin)
        overall.update({
            "plugins": 1, "discovered_controls": plugin["discovered_controls"],
            "useful_controls": plugin["useful_controls"], "planned_controls": plugin["planned_controls"],
            "learned_controls": plugin["learned_controls"], "covered_controls": plugin["covered_controls"],
            "useful_covered": plugin["useful_covered"], "duplicate_targets": len(duplicate_targets),
        })
    useful_total = overall["useful_controls"]
    summary = dict(overall)
    summary["useful_coverage_percent"] = round(100 * overall["useful_covered"] / useful_total, 1) if useful_total else 100.0
    return {
        "schema_version": 1, "kind": "mpc-plugin-mapping-coverage",
        "summary": summary, "validation_warnings": validation["warnings"], "plugins": plugins,
        "boundary": "Planned controls come from profiles; learned controls come from optional XPJ evidence. UI metadata does not prove an inferred parameter is hardware-mappable.",
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Plugin mapping coverage", "",
        f"{summary['plugins']} plugins; {summary['useful_covered']}/{summary['useful_controls']} useful controls covered ({summary['useful_coverage_percent']}%).",
        "Coverage is a planning signal, not a hardware verdict.", "",
    ]
    for item in report["plugins"]:
        profiles = ", ".join(item["profiles"]) or "none"
        lines.extend((
            f"## {item['plugin']} — {item['useful_coverage_percent']}% useful coverage", "",
            f"Profiles: {profiles}. Planned: {item['planned_controls']}; learned: {item['learned_controls']}; discovered: {item['discovered_controls']}.", "",
        ))
        if item["roles"]:
            lines.extend(("Roles: " + ", ".join(f"{name} {count}" for name, count in item["roles"].items()) + ".", ""))
        if item["duplicate_targets"]:
            lines.append("Redundant targets:")
            lines.extend(f"- {row['name']} (UI {row['ui_parameter']}) is assigned {row['assignments']} times." for row in item["duplicate_targets"])
            lines.append("")
        if item["omitted_recommended"]:
            lines.append("Best useful controls not yet covered:")
            for row in item["omitted_recommended"]:
                qlink = f"; Q-Link: {', '.join(row['q_links'])}" if row["q_links"] else ""
                lines.append(f"- {row['name']} — UI {row['ui_parameter']}, MPC {row['mpc_parameter']}, score {row['usefulness_score']}, {row['evidence']}{qlink}")
            lines.append("")
    lines.extend(("## Evidence boundary", "", report["boundary"], ""))
    return "\n".join(lines)


def write_report(report: dict[str, Any], output: Path) -> None:
    output = output.expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"plugin coverage output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        (staging / "plugin-mapping-coverage.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        (staging / "PLUGIN_MAPPING_COVERAGE.md").write_text(render_markdown(report), encoding="utf-8")
        with (staging / "plugin-mapping-coverage.csv").open("w", encoding="utf-8", newline="") as stream:
            fields = ("plugin", "profiles", "discovered_controls", "useful_controls", "planned_controls", "learned_controls", "covered_controls", "useful_covered", "useful_coverage_percent", "roles", "duplicate_targets", "top_omitted")
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for item in report["plugins"]:
                writer.writerow({
                    **{field: item[field] for field in fields if field in item and field not in {"profiles", "roles", "duplicate_targets"}},
                    "profiles": ";".join(item["profiles"]),
                    "roles": ";".join(f"{name}:{count}" for name, count in item["roles"].items()),
                    "duplicate_targets": len(item["duplicate_targets"]),
                    "top_omitted": ";".join(row["name"] for row in item["omitted_recommended"]),
                })
        os.replace(staging, output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profiles", type=Path, nargs="+")
    parser.add_argument("--synth-root", type=Path, required=True)
    parser.add_argument("--project", type=Path, help="optional MPC XPJ MIDI Learn evidence")
    parser.add_argument("--omitted-limit", type=int, default=10)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv or sys.argv[1:])
    profiles = [plugin_map.load_profile(path) for path in args.profiles]
    catalog = plugin_params.catalog(args.synth_root, args.project)
    report = analyze(profiles, catalog, args.omitted_limit)
    write_report(report, args.output)
    summary = report["summary"]
    print(f"Wrote: {args.output.expanduser().resolve()}")
    print(f"Useful coverage: {summary['useful_covered']}/{summary['useful_controls']} ({summary['useful_coverage_percent']}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
