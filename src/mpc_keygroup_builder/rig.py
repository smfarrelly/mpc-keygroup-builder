"""Validate and render reusable MPC-centered hardware rig profiles."""

from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path
from typing import Any


TRACK_TYPES = {"drum", "keygroup", "plugin", "midi", "audio", "clip"}
CLOCK_VALUES = {"internal", "send", "receive", "none"}


def _tables(
    document: dict[str, Any], field: str, *, required: bool = False
) -> list[dict[str, Any]]:
    value = document.get(field, [])
    if not isinstance(value, list) or (required and not value):
        qualifier = "at least one " if required else ""
        raise ValueError(f"rig {field} must contain {qualifier}table")
    for index, item in enumerate(value, 1):
        if not isinstance(item, dict):
            raise ValueError(f"rig {field} entry {index} must be a table")
    return value


def _required_scalar(item: dict[str, Any], field: str, label: str, kind: type) -> None:
    value = item.get(field)
    invalid_integer = kind is int and (not isinstance(value, int) or isinstance(value, bool))
    if invalid_integer or not isinstance(value, kind) or (kind is str and not value.strip()):
        raise ValueError(f"{label} {field} must be a nonempty {kind.__name__}")


def load(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        document = tomllib.load(stream)
    if document.get("schema_version") != 1:
        raise ValueError("rig requires schema_version=1")
    if not isinstance(document.get("name"), str) or not document.get("name"):
        raise ValueError("rig requires a name")
    devices = _tables(document, "devices")
    tracks = _tables(document, "tracks", required=True)
    groups = _tables(document, "control_groups")
    for index, device in enumerate(devices, 1):
        _required_scalar(device, "id", f"device {index}", str)
        if "clock" in device:
            _required_scalar(device, "clock", f"device {index}", str)
    for index, track in enumerate(tracks, 1):
        label = f"track {index}"
        _required_scalar(track, "index", label, int)
        for field in ("name", "role", "type"):
            _required_scalar(track, field, label, str)
        if "device" in track:
            _required_scalar(track, "device", label, str)
    for index, group in enumerate(groups, 1):
        label = f"control group {index}"
        for field in ("controller", "controls", "semantic", "target"):
            _required_scalar(group, field, label, str)
        _required_scalar(group, "count", label, int)
    return document


def validate(document: dict[str, Any]) -> dict[str, list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    devices = document.get("devices", [])
    device_ids = [item.get("id") for item in devices]
    if len(device_ids) != len(set(device_ids)):
        errors.append("device ids must be unique")
    for device in devices:
        channel = device.get("midi_channel")
        if channel is not None and (not isinstance(channel, int) or not 1 <= channel <= 16):
            errors.append(f"{device.get('id', 'device')}: MIDI channel must be 1..16")
        if device.get("clock", "none") not in CLOCK_VALUES:
            errors.append(f"{device.get('id', 'device')}: invalid clock policy")

    external_routes: dict[tuple[str, int], str] = {}

    indexes, roles, names = [], [], []
    for track in document["tracks"]:
        index, kind = track.get("index"), track.get("type")
        if not isinstance(index, int) or not 1 <= index <= 128:
            errors.append("track index must be 1..128")
        indexes.append(index)
        roles.append(track.get("role"))
        names.append(track.get("name"))
        if kind not in TRACK_TYPES:
            errors.append(f"track {index}: invalid type {kind!r}")
        if track.get("device") and track["device"] not in device_ids:
            errors.append(f"track {index}: unknown device {track['device']}")
        channel = track.get("midi_channel")
        if channel is not None and (not isinstance(channel, int) or not 1 <= channel <= 16):
            errors.append(f"track {index}: MIDI channel must be 1..16")
        if kind in {"drum", "keygroup"} and not track.get("program"):
            warnings.append(f"track {index}: {kind} program remains to be selected")
        if track.get("device") in device_ids:
            device = devices[device_ids.index(track["device"])]
            device_channel = device.get("midi_channel")
            if channel is not None and device_channel is not None and channel != device_channel:
                errors.append(f"track {index}: MIDI channel differs from device {track['device']}")
            if kind == "midi" and channel is not None:
                route = (str(track.get("midi_port", device.get("midi_port", "default"))), channel)
                if route in external_routes:
                    errors.append(
                        f"track {index}: MIDI route {route[0]} channel {route[1]} "
                        f"already used by {external_routes[route]}"
                    )
                external_routes[route] = str(track.get("name", index))
    if len(indexes) != len(set(indexes)):
        errors.append("track indexes must be unique")
    if len(names) != len(set(names)):
        errors.append("track names must be unique")
    if len(roles) != len(set(roles)):
        warnings.append("track roles are not unique")

    controllers = {item.get("id") for item in devices if item.get("kind") == "controller"}
    endpoints = set()
    for group in document.get("control_groups", []):
        controller = group.get("controller")
        if controller not in controllers:
            errors.append(f"control group references unknown controller {controller!r}")
        count = group.get("count")
        if not isinstance(count, int) or count < 1:
            errors.append("control group count must be positive")
            continue
        for number in range(1, count + 1):
            endpoint = (controller, str(group.get("controls", "")).replace("{n}", str(number)))
            if endpoint in endpoints:
                errors.append(f"duplicate controller endpoint: {endpoint[0]} {endpoint[1]}")
            endpoints.add(endpoint)
        if group.get("message") == "learn":
            warnings.append(f"{controller} {group.get('controls')}: MIDI assignment requires hardware learn")
    return {"errors": sorted(set(errors)), "warnings": sorted(set(warnings))}


def render_markdown(document: dict[str, Any]) -> str:
    validation = validate(document)
    lines = [f"# {document['name']}", "", document.get("description", ""), "", "## Tracks", ""]
    for track in sorted(document["tracks"], key=lambda item: item["index"]):
        detail = track.get("program") or track.get("device") or "to be chosen"
        channel = f", MIDI ch {track['midi_channel']}" if track.get("midi_channel") else ""
        lines.append(f"- {track['index']}. **{track['name']}** — {track['role']} ({track['type']}: {detail}{channel})")
    if document.get("control_groups"):
        lines.extend(["", "## Controller semantics", ""])
        for group in document["control_groups"]:
            lines.append(
                f"- {group['controller']} `{group['controls']}` × {group['count']}: "
                f"{group['semantic']} → `{group['target']}` ({group.get('message', 'unspecified')})"
            )
    lines.extend(["", "## Validation", ""])
    lines.append(f"- Errors: {len(validation['errors'])}")
    lines.append(f"- Hardware/pending warnings: {len(validation['warnings'])}")
    lines.extend(f"  - {value}" for value in validation["warnings"])
    lines.extend(["", "## Hardware acceptance", ""])
    lines.extend(f"- [ ] {item}" for item in document.get("acceptance", []))
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("check", "plan"):
        child = subparsers.add_parser(command)
        child.add_argument("profile", type=Path)
        child.add_argument("--json", action="store_true")
        child.add_argument("--output", type=Path)
    args = parser.parse_args()
    document = load(args.profile)
    result = validate(document)
    if args.command == "check" or args.json:
        rendered = json.dumps({"name": document["name"], **result}, indent=2) + "\n"
    else:
        rendered = render_markdown(document)
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 2 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
