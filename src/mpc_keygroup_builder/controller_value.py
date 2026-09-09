"""Audit whether controller layouts earn space in a live hardware rig."""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import shutil
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any

from . import plugin_map


KINDS = {
    "mpc-mix", "mpc-plugin", "mpc-effect", "external-instrument",
    "external-effect", "physical-mixer", "sequence-launch",
}
OWNERS = {"xl3", "mpc", "mpc-pads", "l6", "native"}
STATUSES = {"primary", "candidate", "conditional", "deferred"}
AUTOMATION = {"none", "optional", "required"}
HARDWARE = {"pending", "pass", "warn", "fail", "not-required"}


def _nonempty(row: dict[str, Any], field: str, context: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} requires {field}")
    return value


def load_policy(path: Path) -> dict[str, Any]:
    path = path.expanduser().resolve()
    with path.open("rb") as stream:
        document = tomllib.load(stream)
    if document.get("schema_version") != 1:
        raise ValueError(f"{path}: controller value policy requires schema_version=1")
    _nonempty(document, "name", str(path))
    default = _nonempty(document, "default_xl3_layout", str(path))
    for field in ("max_performance_controls", "max_core_controls"):
        value = document.get(field)
        if type(value) is not int or value < 1 or value > 48:
            raise ValueError(f"{path}: {field} must be an integer from 1 to 48")
    layouts = document.get("layouts")
    if not isinstance(layouts, list) or not layouts:
        raise ValueError(f"{path}: policy requires [[layouts]]")
    seen: set[str] = set()
    for index, row in enumerate(layouts, 1):
        context = f"{path}: layout {index}"
        if not isinstance(row, dict):
            raise ValueError(f"{context} must be a table")
        identifier = _nonempty(row, "id", context)
        _nonempty(row, "name", context)
        _nonempty(row, "friction_removed", context)
        if identifier in seen:
            raise ValueError(f"{path}: duplicate layout id {identifier}")
        seen.add(identifier)
        for field, choices in (
            ("kind", KINDS), ("owner", OWNERS), ("status", STATUSES),
            ("automation_need", AUTOMATION), ("hardware_status", HARDWARE),
        ):
            value = row.get(field)
            if value not in choices:
                raise ValueError(
                    f"{context} {field} must be one of: {', '.join(sorted(choices))}"
                )
        if type(row.get("native_panel")) is not bool:
            raise ValueError(f"{context} native_panel must be true or false")
        profile = row.get("profile")
        if profile is not None and (not isinstance(profile, str) or not profile.strip()):
            raise ValueError(f"{context} profile must be a nonempty relative path")
    if default not in seen:
        raise ValueError(f"{path}: default_xl3_layout does not name a layout: {default}")
    document["source_path"] = str(path)
    return document


def _profile_path(policy: dict[str, Any], relative: str) -> Path:
    if Path(relative).is_absolute():
        raise ValueError(f"profile path must be relative: {relative}")
    root = Path(policy["source_path"]).parent.resolve()
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ValueError(f"profile path escapes policy directory: {relative}") from error
    return path


def analyze(policy: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    layouts = []

    def finding(severity: str, code: str, layout: str, message: str) -> None:
        findings.append({
            "severity": severity, "code": code, "layout": layout,
            "message": message,
        })

    for source in policy["layouts"]:
        row = dict(source)
        identifier = row["id"]
        controls = core = faders = 0
        profile_ref = row.get("profile")
        if profile_ref:
            if row["owner"] != "xl3":
                finding("error", "profile-owner", identifier, "plugin profile requires owner=xl3")
            profile = plugin_map.load_profile(_profile_path(policy, profile_ref))
            if any(not isinstance(item, dict) for item in profile["controls"]):
                raise ValueError(f"{profile_ref}: every controls entry must be a table")
            controls = len(profile["controls"])
            core = sum(item.get("priority", "secondary") == "core" for item in profile["controls"])
            faders = sum(str(item.get("control", "")).startswith("fader-") for item in profile["controls"])
            row["profile_id"] = profile["id"]
            if controls > policy["max_performance_controls"]:
                finding(
                    "warning", "control-budget", identifier,
                    f"{controls} controls exceed compact performance budget "
                    f"{policy['max_performance_controls']}",
                )
            if core > policy["max_core_controls"]:
                finding(
                    "warning", "core-budget", identifier,
                    f"{core} core controls exceed memorable core budget "
                    f"{policy['max_core_controls']}",
                )
        if row["owner"] == "xl3" and row["kind"] in {
            "external-instrument", "external-effect", "physical-mixer",
        } and row["status"] == "primary":
            finding(
                "error", "panel-replication", identifier,
                "external hardware cannot be a primary XL3 layout",
            )
        if row["native_panel"] and row["owner"] == "xl3" and row["automation_need"] == "none":
            finding(
                "warning", "native-duplication", identifier,
                "XL3 duplicates a reachable native panel without an automation need",
            )
        if row["kind"] == "physical-mixer" and row["owner"] != "l6":
            finding("warning", "mixer-owner", identifier, "physical mix should be owned by the L6")
        if row["kind"] == "sequence-launch" and row["owner"] != "mpc-pads":
            finding("warning", "sequence-owner", identifier, "sequence launch should use MPC pads")
        if row["status"] in {"primary", "candidate"} and row["hardware_status"] == "pending":
            finding(
                "note", "hardware-pending", identifier,
                "short live-friction comparison remains pending",
            )
        row.update({"control_count": controls, "core_count": core, "fader_count": faders})
        layouts.append(row)

    default = next(item for item in layouts if item["id"] == policy["default_xl3_layout"])
    if default["owner"] != "xl3" or default["kind"] != "mpc-mix" or default["status"] != "primary":
        finding(
            "error", "default-layout", default["id"],
            "default XL3 layout must be a primary xl3-owned mpc-mix",
        )
    counts = {
        severity: sum(item["severity"] == severity for item in findings)
        for severity in ("error", "warning", "note")
    }
    return {
        "schema_version": 1,
        "kind": "mpc-controller-value-audit",
        "name": policy["name"],
        "source_path": policy["source_path"],
        "default_xl3_layout": policy["default_xl3_layout"],
        "budgets": {
            "performance_controls": policy["max_performance_controls"],
            "core_controls": policy["max_core_controls"],
        },
        "summary": {"layouts": len(layouts), **{f"{key}s": value for key, value in counts.items()}},
        "layouts": layouts,
        "findings": findings,
        "boundary": "Software checks structure and declared intent; only a short live comparison can prove that a mapping removes friction.",
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        f"# {report['name']}", "",
        f"Default XL3 layout: **{report['default_xl3_layout']}**.",
        f"Layouts: {summary['layouts']}; errors: {summary['errors']}; warnings: {summary['warnings']}; notes: {summary['notes']}.",
        f"Compact budgets: {report['budgets']['performance_controls']} total controls, {report['budgets']['core_controls']} core controls.",
        "", "## Layout decisions", "",
    ]
    for row in report["layouts"]:
        profile = (
            f"; profile {row['profile_id']} ({row['control_count']} controls, "
            f"{row['core_count']} core, {row['fader_count']} faders)"
            if row.get("profile_id") else ""
        )
        lines.append(
            f"- **{row['name']}** — {row['status']}; {row['owner']} owns "
            f"{row['kind']}; automation {row['automation_need']}; hardware "
            f"{row['hardware_status']}{profile}. Friction: {row['friction_removed']}"
        )
    lines.extend(("", "## Findings", ""))
    lines.extend(
        f"- [{item['severity'].upper()}] `{item['layout']}` / {item['code']}: {item['message']}"
        for item in report["findings"]
    )
    if not report["findings"]:
        lines.append("- None.")
    lines.extend(("", "## Evidence boundary", "", report["boundary"], ""))
    return "\n".join(lines)


def render_checklist(report: dict[str, Any]) -> str:
    lines = ["# Controller value hardware checklist", ""]
    for row in report["layouts"]:
        if row["owner"] != "xl3" or row["status"] == "deferred":
            continue
        lines.extend((
            f"## {row['name']}", "",
            f"Expected friction removed: {row['friction_removed']}", "",
            "- [ ] Load the layout and identify the native/menu alternative.",
            "- [ ] Use both paths during a short loop-based jam.",
            "- [ ] Confirm the stable fader convention remains understandable.",
            "- [ ] Record whether the page is faster, memorable, and worth its slot.",
            "- [ ] Mark pass, warn, or fail in the policy without changing software evidence.",
            "",
        ))
    return "\n".join(lines)


def render_csv(report: dict[str, Any]) -> str:
    fields = (
        "id", "name", "kind", "owner", "status", "automation_need",
        "hardware_status", "control_count", "core_count", "fader_count",
        "friction_removed",
    )
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(report["layouts"])
    return stream.getvalue()


def write_report(report: dict[str, Any], output: Path, *, force: bool = False) -> Path:
    output = output.expanduser().resolve()
    if output.exists() and not force:
        raise FileExistsError(f"controller value output already exists: {output}")
    if output.exists():
        receipt = output / "controller-value.json"
        if output.is_symlink() or not output.is_dir() or receipt.is_symlink() or not receipt.is_file():
            raise ValueError(f"refusing to replace unrecognized controller value output: {output}")
        try:
            previous = json.loads(receipt.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"refusing to replace invalid controller value output: {output}") from error
        if previous.get("kind") != "mpc-controller-value-audit":
            raise ValueError(f"refusing to replace unrecognized controller value output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        (staging / "controller-value.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        (staging / "CONTROLLER_VALUE.md").write_text(render_markdown(report), encoding="utf-8")
        (staging / "HARDWARE_CHECKLIST.md").write_text(render_checklist(report), encoding="utf-8")
        (staging / "layouts.csv").write_text(render_csv(report), encoding="utf-8")
        if output.exists():
            shutil.rmtree(output)
        os.replace(staging, output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("policy", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--strict", action="store_true", help="return 2 for warnings as well as errors")
    args = parser.parse_args(argv or sys.argv[1:])
    report = analyze(load_policy(args.policy))
    if args.output:
        write_report(report, args.output, force=args.force)
        print(f"Wrote: {args.output.expanduser().resolve()}")
    summary = report["summary"]
    print(
        f"Layouts: {summary['layouts']}; errors: {summary['errors']}; "
        f"warnings: {summary['warnings']}; notes: {summary['notes']}"
    )
    return 2 if summary["errors"] or (args.strict and summary["warnings"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
