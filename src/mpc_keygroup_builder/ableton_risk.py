"""Turn Ableton conversion warnings into a prioritized hardware review queue."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


RULES = (
    (re.compile(r"\bwarp(?:ed|\s+behavior)?\b", re.I), "timing-warp", "critical", "Check tempo lock, transients, and loop alignment."),
    (re.compile(r"\bsamplestart\b", re.I), "sample-start", "high", "Compare attacks and timing with the Ableton source."),
    (re.compile(r"\b(?:sustain|release).*loop", re.I), "sample-loop", "high", "Hold pads and compare loop and release behavior."),
    (re.compile(r"\bdetune\b", re.I), "pitch", "high", "Compare pitch and tuning on every affected pad."),
    (re.compile(r"\bvolume=", re.I), "gain", "high", "Compare pad balance; adjust MPC mixer levels if needed."),
    (re.compile(r"\bpanorama=", re.I), "stereo", "medium", "Compare stereo placement and width."),
    (re.compile(r"device behavior", re.I), "devices", "medium", "Compare tone and space; recreate only musically useful processing."),
    (re.compile(r"Rack macros", re.I), "macros", "medium", "Identify useful performance gestures for Q-Link or MIDI mapping."),
)
SEVERITY = {"critical": 4, "high": 3, "medium": 2, "low": 1, "none": 0}
RISK_PRIORITY = {"timing-warp": 8, "sample-start": 7, "sample-loop": 6, "pitch": 5, "gain": 4, "stereo": 3, "devices": 2, "macros": 1, "other": 0}
PAD = re.compile(r"\bpad\s+(\d+)\b", re.I)


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def classify_warning(warning: str) -> dict[str, str]:
    for pattern, category, severity, review in RULES:
        if pattern.search(warning):
            return {"category": category, "severity": severity, "review": review}
    return {"category": "other", "severity": "medium", "review": "Compare the named source behavior with the MPC result."}


def analyze(report: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(report, dict) or report.get("kind") != "mpc-ableton-drum-wave-build":
        raise ValueError("input must be an mpc-ableton-drum-wave-build report")
    programs = report.get("programs")
    if not isinstance(programs, list):
        raise ValueError("programs must be a list")
    analyzed = []
    category_counts: Counter[str] = Counter()
    severity_counts: Counter[str] = Counter()
    for index, program in enumerate(programs):
        if not isinstance(program, dict):
            raise ValueError(f"programs[{index}] must be an object")
        # Wave build reports use translation_warnings; accept warnings as a
        # small fixture/producer compatibility alias.
        warnings = program.get("translation_warnings", program.get("warnings", []))
        if not isinstance(warnings, list) or not all(isinstance(item, str) for item in warnings):
            raise ValueError(f"programs[{index}].warnings must be a list of strings")
        groups: dict[str, dict[str, Any]] = {}
        for warning in warnings:
            rule = classify_warning(warning)
            group = groups.setdefault(rule["category"], {
                **rule, "warning_count": 0, "affected_pads": [], "examples": [],
            })
            group["warning_count"] += 1
            match = PAD.search(warning)
            if match and int(match.group(1)) not in group["affected_pads"]:
                group["affected_pads"].append(int(match.group(1)))
            if len(group["examples"]) < 2:
                group["examples"].append(warning)
        risks = sorted(groups.values(), key=lambda item: (-SEVERITY[item["severity"]], item["category"]))
        for risk in risks:
            risk["affected_pads"].sort()
            category_counts[risk["category"]] += 1
        level = max((risk["severity"] for risk in risks), key=SEVERITY.get, default="none")
        severity_counts[level] += 1
        analyzed.append({
            "id": _text(program.get("id"), f"programs[{index}].id"),
            "name": _text(program.get("name"), f"programs[{index}].name"),
            "collection": _text(program.get("collection"), f"programs[{index}].collection"),
            "program": _text(program.get("program"), f"programs[{index}].program"),
            "risk_level": level, "warning_count": len(warnings), "risks": risks,
        })
    analyzed.sort(key=lambda item: (
        -SEVERITY[item["risk_level"]],
        -max((RISK_PRIORITY[risk["category"]] for risk in item["risks"]), default=-1),
        item["collection"].casefold(), item["name"].casefold(),
    ))
    return {
        "schema_version": 1, "kind": "mpc-ableton-translation-risk",
        "source_kind": report["kind"], "hardware_status": "deferred",
        "summary": {"programs": len(analyzed), "risk_levels": dict(sorted(severity_counts.items())), "categories": dict(sorted(category_counts.items()))},
        "programs": analyzed,
    }


def _pads(values: list[int]) -> str:
    return ", ".join(str(value) for value in values) if values else "all/unspecified"


def render_markdown(result: dict[str, Any]) -> str:
    lines = ["# Ableton translation-risk review", "", "Prioritized source-to-MPC differences. Hardware status remains **deferred**.", ""]
    for item in result["programs"]:
        lines.extend((f"## {item['collection']} / {item['name']} — {item['risk_level']}", "", f"Load `{item['program']}`", ""))
        if not item["risks"]:
            lines.extend(("No converter warnings; perform a normal musical audition.", ""))
        for risk in item["risks"]:
            lines.extend((f"- **{risk['category']}** ({risk['severity']}; pads {_pads(risk['affected_pads'])}; {risk['warning_count']} diagnostic(s)): {risk['review']}",))
        lines.extend(("", "Verdict: [ ] pass  [ ] warn  [ ] fail", "Notes:", ""))
    return "\n".join(lines)


def write_review(report_path: Path, output: Path) -> dict[str, Any]:
    report_path, output = report_path.resolve(), output.resolve()
    if output.exists():
        raise FileExistsError(f"translation-risk output already exists: {output}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    result = analyze(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        (staging / "translation-risk.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        (staging / "TRANSLATION_REVIEW.md").write_text(render_markdown(result), encoding="utf-8")
        with (staging / "translation-risk.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=("id", "collection", "name", "risk_level", "warning_count", "categories", "affected_pads", "program"))
            writer.writeheader()
            for item in result["programs"]:
                writer.writerow({
                    "id": item["id"], "collection": item["collection"], "name": item["name"],
                    "risk_level": item["risk_level"], "warning_count": item["warning_count"],
                    "categories": ";".join(risk["category"] for risk in item["risks"]),
                    "affected_pads": ";".join(f"{risk['category']}:{','.join(map(str, risk['affected_pads']))}" for risk in item["risks"] if risk["affected_pads"]),
                    "program": item["program"],
                })
        os.replace(staging, output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build_report", type=Path, help="Ableton wave build-report.json")
    parser.add_argument("--output", type=Path, required=True, help="new review directory")
    args = parser.parse_args(argv or sys.argv[1:])
    result = write_review(args.build_report, args.output)
    print(f"Wrote: {args.output.resolve()}")
    print(f"Programs: {result['summary']['programs']}; risks: {result['summary']['risk_levels']}; hardware: deferred")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
