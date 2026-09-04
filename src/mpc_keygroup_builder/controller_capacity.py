"""Validate the complete Launch Control Custom Mode slot and channel plan."""

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
from collections import defaultdict
from pathlib import Path
from typing import Any

from . import launch_control, plugin_map


def load_plan(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        document = tomllib.load(stream)
    if document.get("schema_version") != 1:
        raise ValueError(f"{path}: capacity plan requires schema_version=1")
    if not isinstance(document.get("name"), str) or not document["name"]:
        raise ValueError(f"{path}: capacity plan requires name")
    control_channel = document.get("control_channel")
    if not isinstance(control_channel, int) or not 1 <= control_channel <= 16:
        raise ValueError(f"{path}: capacity plan control_channel must be 1..16")
    external_channels = document.get("external_channels")
    if (
        not isinstance(external_channels, list)
        or any(not isinstance(item, int) or not 1 <= item <= 16 for item in external_channels)
        or len(external_channels) != len(set(external_channels))
    ):
        raise ValueError(f"{path}: capacity plan requires external_channels")
    if control_channel in external_channels:
        raise ValueError(f"{path}: control_channel cannot also be an external channel")
    if not isinstance(document.get("modes"), list):
        raise ValueError(f"{path}: capacity plan requires [[modes]]")
    return document


def analyze(
    plan: dict[str, Any],
    profiles: list[dict[str, Any]],
    captures: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    modes = []
    captures_by_name = {item["name"]: item for item in captures or []}
    for item in plan["modes"]:
        required = ("slot", "name", "channel", "role", "source")
        if any(field not in item for field in required):
            errors.append(f"capacity mode is missing one of: {', '.join(required)}")
            continue
        capture_status = "not-requested"
        capture_name = item.get("capture_name")
        if capture_name:
            capture = captures_by_name.get(capture_name)
            if capture is None:
                capture_status = "missing" if captures else "not-supplied"
                if captures:
                    warnings.append(f"slot {item['slot']}: capture not supplied: {capture_name}")
            elif capture["primary_channel"] != item["channel"]:
                capture_status = "channel-mismatch"
                errors.append(
                    f"slot {item['slot']}: {capture_name} expected channel {item['channel']}, "
                    f"capture uses {capture['primary_channel']}"
                )
            else:
                capture_status = "matched"
        modes.append(
            {
                **item,
                "control_count": item.get("control_count", ""),
                "slot_evidence": item.get("slot_evidence", "planned"),
                "capture_status": capture_status,
            }
        )
        if "confirm" in str(item.get("slot_evidence", "")).casefold():
            warnings.append(
                f"slot {item['slot']} placement for {item['name']} still needs Components confirmation"
            )
    for profile in profiles:
        endpoints = [item.get("control") for item in profile["controls"]]
        invalid_endpoints = sorted(
            repr(item)
            for item in endpoints
            if not isinstance(item, str) or plugin_map.ENDPOINT.fullmatch(item) is None
        )
        if invalid_endpoints:
            errors.append(
                f"slot {profile['slot']}: invalid profile endpoints: {', '.join(invalid_endpoints)}"
            )
        duplicates = sorted(
            {item for item in endpoints if isinstance(item, str) and endpoints.count(item) > 1}
        )
        if duplicates:
            errors.append(
                f"slot {profile['slot']}: duplicate profile endpoints: {', '.join(duplicates)}"
            )
        modes.append(
            {
                "slot": profile["slot"],
                "name": profile["name"],
                "channel": profile["channel"],
                "role": "plugin-performance",
                "source": "declarative-profile",
                "control_count": len(profile["controls"]),
                "slot_evidence": "declarative-profile",
                "capture_status": "hardware-pending",
            }
        )
    slots: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for mode in modes:
        slot = mode.get("slot")
        channel = mode.get("channel")
        if not isinstance(slot, int) or not 1 <= slot <= 15:
            errors.append(f"invalid Custom Mode slot: {slot!r}")
        else:
            slots[slot].append(mode)
        if not isinstance(channel, int) or not 1 <= channel <= 16:
            errors.append(f"slot {slot}: invalid MIDI channel {channel!r}")
        if mode.get("source") == "declarative-profile":
            if channel == plan["control_channel"]:
                errors.append(f"slot {slot}: plugin page collides with control channel {channel}")
            if channel in plan["external_channels"]:
                errors.append(f"slot {slot}: plugin page collides with external-device channel {channel}")
    for slot, entries in slots.items():
        if len(entries) > 1:
            errors.append(f"slot {slot} has {len(entries)} assignments: " + ", ".join(item["name"] for item in entries))
    missing_slots = [slot for slot in range(1, 16) if slot not in slots]
    channels: dict[int, list[str]] = defaultdict(list)
    for mode in modes:
        if isinstance(mode.get("channel"), int):
            channels[mode["channel"]].append(mode["name"])
    used = set(channels) | {plan["control_channel"]}
    spare_channels = [channel for channel in range(1, 17) if channel not in used]
    if missing_slots:
        warnings.append(f"unassigned Custom Mode slots: {', '.join(map(str, missing_slots))}")
    return {
        "schema_version": 1,
        "name": plan["name"],
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "modes": sorted(modes, key=lambda item: item.get("slot", 99)),
        "control_channel": plan["control_channel"],
        "external_channels": plan["external_channels"],
        "missing_slots": missing_slots,
        "spare_channels": spare_channels,
        "channel_usage": {str(key): value for key, value in sorted(channels.items())},
    }


def render_csv(report: dict[str, Any]) -> str:
    fields = (
        "slot", "name", "channel", "role", "source", "control_count", "slot_evidence",
        "capture_status",
    )
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    writer.writerows(report["modes"])
    return stream.getvalue()


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# {report['name']}",
        "",
        f"Custom Mode slots: {15 - len(report['missing_slots'])}/15 assigned.",
        f"Control channel: {report['control_channel']}.",
        f"External-device channels: {', '.join(map(str, report['external_channels']))}.",
        f"Unreserved channels: {', '.join(map(str, report['spare_channels'])) or 'none'}.",
        "",
        "## Slot plan",
        "",
    ]
    for mode in report["modes"]:
        count = f"; {mode['control_count']} controls" if mode["control_count"] != "" else ""
        lines.append(
            f"- Slot {mode['slot']}: **{mode['name']}** — channel {mode['channel']}; "
            f"{mode['role']}; {mode['source']}{count}; slot evidence {mode['slot_evidence']}; "
            f"capture {mode['capture_status']}."
        )
    for heading, key in (("Errors", "errors"), ("Warnings", "warnings")):
        lines.extend(("", f"## {heading}", ""))
        lines.extend(f"- {item}" for item in report[key])
        if not report[key]:
            lines.append("- None.")
    return "\n".join(lines).rstrip() + "\n"


def compile_plan(report: dict[str, Any], output: Path, force: bool = False) -> Path:
    if report["errors"]:
        raise ValueError("invalid controller capacity plan: " + "; ".join(report["errors"]))
    output = output.expanduser().resolve()
    if output.exists() and not force:
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        (staging / "capacity.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        (staging / "custom-modes.csv").write_text(render_csv(report), encoding="utf-8")
        (staging / "CAPACITY.md").write_text(render_markdown(report), encoding="utf-8")
        if output.exists():
            shutil.rmtree(output)
        os.replace(staging, output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("profiles", type=Path, nargs="+")
    parser.add_argument("--capture", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv or sys.argv[1:])
    plan = load_plan(args.plan)
    profiles = [plugin_map.load_profile(path) for path in args.profiles]
    captures = [launch_control.inspect(path) for path in args.capture]
    report = analyze(plan, profiles, captures)
    path = compile_plan(report, args.output, args.force)
    print(
        f"Wrote {len(report['modes'])} modes -> {path} "
        f"(slots={15 - len(report['missing_slots'])}/15, spare channels={report['spare_channels']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
