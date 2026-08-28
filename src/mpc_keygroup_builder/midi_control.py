"""Compile declarative MIDI controller maps into setup and reference artifacts."""

from __future__ import annotations

import argparse
import copy
import csv
import io
import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


VALID_OUTPUTS = {"usb", "din-1", "din-2", "all"}
VALID_MESSAGES = {"cc", "note", "program-change", "nrpn"}
CONTROL_PATTERN = re.compile(
    r"^(?:fader|top-encoder|middle-encoder|bottom-encoder|upper-button|lower-button)-(?:[1-8])$"
)


@dataclass(frozen=True)
class DeviceDefinition:
    id: str
    name: str
    kind: str
    channel: int | None
    parameters: dict[str, dict[str, Any]]
    notes: dict[str, dict[str, Any]]
    sources: tuple[str, ...]
    path: Path


def _load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        return tomllib.load(stream)


def _load_map_document(path: Path, seen: tuple[Path, ...] = ()) -> dict[str, Any]:
    resolved = path.resolve()
    if resolved in seen:
        chain = " -> ".join(str(item) for item in (*seen, resolved))
        raise ValueError(f"control map inheritance cycle: {chain}")
    child = _load_toml(resolved)
    extends = child.get("extends")
    if not extends:
        return child
    if not isinstance(extends, str) or not extends:
        raise ValueError(f"{path}: extends must be a relative TOML path")
    parent_path = (resolved.parent / extends).resolve()
    try:
        parent_path.relative_to(resolved.parent)
    except ValueError as error:
        raise ValueError(f"{path}: extends escapes the map directory") from error
    parent = _load_map_document(parent_path, (*seen, resolved))
    merged = copy.deepcopy(parent)
    for key, value in child.items():
        if key in {"extends", "mode_overrides"}:
            continue
        if key == "topology":
            merged[key] = {**merged.get(key, {}), **value}
        elif key == "sources":
            merged[key] = list(dict.fromkeys([*merged.get(key, []), *value]))
        else:
            merged[key] = copy.deepcopy(value)
    modes = {mode["id"]: mode for mode in merged.get("modes", []) if "id" in mode}
    for override in child.get("mode_overrides", []):
        mode_id = override.get("id")
        if mode_id not in modes:
            raise ValueError(f"{path}: override references unknown mode {mode_id!r}")
        modes[mode_id].update({key: copy.deepcopy(value) for key, value in override.items() if key != "id"})
    return merged


def load_device(path: Path) -> DeviceDefinition:
    raw = _load_toml(path)
    if raw.get("schema_version") != 1:
        raise ValueError(f"{path}: device requires schema_version=1")
    device_id = raw.get("id")
    if not isinstance(device_id, str) or not device_id:
        raise ValueError(f"{path}: device requires id")
    channel = raw.get("midi_channel")
    if channel is not None and (not isinstance(channel, int) or not 1 <= channel <= 16):
        raise ValueError(f"{path}: midi_channel must be 1..16")

    def indexed_entries(label: str, number_field: str) -> dict[str, dict[str, Any]]:
        entries = raw.get(label, [])
        if not isinstance(entries, list):
            raise ValueError(f"{path}: {label} must be an array of tables")
        indexed: dict[str, dict[str, Any]] = {}
        numbers: set[int] = set()
        for entry in entries:
            entry_id = entry.get("id") if isinstance(entry, dict) else None
            number = entry.get(number_field) if isinstance(entry, dict) else None
            if not isinstance(entry_id, str) or not entry_id:
                raise ValueError(f"{path}: each {label} entry requires id")
            if entry_id in indexed:
                raise ValueError(f"{path}: duplicate {label} id {entry_id}")
            if not isinstance(number, int) or not 0 <= number <= 127:
                raise ValueError(f"{path}: {entry_id} {number_field} must be 0..127")
            if number in numbers:
                raise ValueError(f"{path}: duplicate {label} {number_field} {number}")
            indexed[entry_id] = entry
            numbers.add(number)
        return indexed

    parameters = indexed_entries("parameters", "cc")
    notes = indexed_entries("notes", "note")
    return DeviceDefinition(
        id=device_id,
        name=str(raw.get("name", device_id)),
        kind=str(raw.get("kind", "device")),
        channel=channel,
        parameters=parameters,
        notes=notes,
        sources=tuple(raw.get("sources", [])),
        path=path,
    )


def load_map(path: Path, device_root: Path | None = None) -> tuple[dict[str, Any], dict[str, DeviceDefinition]]:
    document = _load_map_document(path)
    if document.get("schema_version") != 1:
        raise ValueError("control map requires schema_version=1")
    if not document.get("name") or not document.get("modes"):
        raise ValueError("control map requires name and [[modes]]")
    root = device_root or path.parents[1] / "devices"
    resolved_root = root.resolve()
    devices: dict[str, DeviceDefinition] = {}
    for reference in document.get("device_definitions", []):
        definition_path = (resolved_root / reference).resolve()
        try:
            definition_path.relative_to(resolved_root)
        except ValueError as error:
            raise ValueError(f"device definition escapes device root: {reference}") from error
        definition = load_device(definition_path)
        if definition.id in devices:
            raise ValueError(f"duplicate device definition {definition.id}")
        devices[definition.id] = definition
    return document, devices


def validate(document: dict[str, Any], devices: dict[str, DeviceDefinition]) -> dict[str, list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    mode_ids: set[str] = set()
    slots: set[int] = set()
    route_devices: set[str] = set()

    topology = document.get("topology", {})
    merger = bool(topology.get("midi_merger", False))
    if topology.get("mpc_to_devices") == "passive-thru" and topology.get("launch_direct_din") and not merger:
        errors.append("direct Launch Control DIN and MPC DIN cannot be combined by a passive MIDI thru box")

    for mode in document.get("modes", []):
        mode_id = mode.get("id")
        slot = mode.get("slot")
        target = mode.get("target")
        output = mode.get("output", "usb")
        channel = mode.get("channel")
        if not isinstance(mode_id, str) or not mode_id:
            errors.append("each mode requires an id")
        elif mode_id in mode_ids:
            errors.append(f"duplicate mode id {mode_id}")
        else:
            mode_ids.add(mode_id)
        if not isinstance(slot, int) or not 1 <= slot <= 15:
            errors.append(f"{mode_id or 'mode'}: slot must be 1..15")
        elif slot in slots:
            errors.append(f"duplicate custom-mode slot {slot}")
        else:
            slots.add(slot)
        if output not in VALID_OUTPUTS:
            errors.append(f"{mode_id}: invalid output {output!r}")
        if not isinstance(channel, int) or not 1 <= channel <= 16:
            errors.append(f"{mode_id}: channel must be 1..16")
        if target != "mpc" and target not in devices:
            errors.append(f"{mode_id}: unknown target device {target!r}")
        if target in devices and devices[target].channel not in (None, channel):
            errors.append(f"{mode_id}: channel differs from {target} definition")
        if target in devices and output != "usb" and topology.get("mpc_to_devices") == "passive-thru" and not merger:
            warnings.append(f"{mode_id}: direct DIN use requires recabling or an active MIDI merger")

        endpoints: set[str] = set()
        messages: set[tuple[str, int, int]] = set()
        for control in mode.get("controls", []):
            endpoint = control.get("control")
            message = control.get("message", "cc")
            number = control.get("number")
            control_channel = control.get("channel", channel)
            target_parameter = control.get("target")
            if not isinstance(endpoint, str) or not CONTROL_PATTERN.fullmatch(endpoint):
                errors.append(f"{mode_id}: invalid Launch Control endpoint {endpoint!r}")
            elif endpoint in endpoints:
                errors.append(f"{mode_id}: duplicate endpoint {endpoint}")
            else:
                endpoints.add(endpoint)
            if message not in VALID_MESSAGES:
                errors.append(f"{mode_id}/{endpoint}: invalid message {message!r}")
            if not isinstance(number, int) or not 0 <= number <= 127:
                errors.append(f"{mode_id}/{endpoint}: number must be 0..127")
                continue
            if not isinstance(control_channel, int) or not 1 <= control_channel <= 16:
                errors.append(f"{mode_id}/{endpoint}: channel must be 1..16")
                continue
            message_key = (message, control_channel, number)
            if message_key in messages:
                errors.append(f"{mode_id}: duplicate message {message} ch {control_channel} number {number}")
            messages.add(message_key)

            if target == "mpc":
                if not isinstance(target_parameter, str) or not target_parameter:
                    errors.append(f"{mode_id}/{endpoint}: MPC control requires a target")
                if control.get("support") == "unverified":
                    warnings.append(f"{mode_id}/{endpoint}: MPC target remains unverified: {target_parameter}")
                continue
            if target not in devices or not isinstance(target_parameter, str):
                continue
            definition = devices[target]
            table = definition.notes if message == "note" else definition.parameters
            if target_parameter not in table:
                errors.append(f"{mode_id}/{endpoint}: {target} has no {message} target {target_parameter!r}")
                continue
            expected_field = "note" if message == "note" else "cc"
            expected = table[target_parameter].get(expected_field)
            if expected != number:
                errors.append(
                    f"{mode_id}/{endpoint}: {target_parameter} expects {expected_field} {expected}, got {number}"
                )

    for route in document.get("routes", []):
        device_id = route.get("device")
        if device_id not in devices:
            errors.append(f"route references unknown device {device_id!r}")
            continue
        route_devices.add(device_id)
        for field in ("input_channel", "output_channel"):
            channel = route.get(field)
            if not isinstance(channel, int) or not 1 <= channel <= 16:
                errors.append(f"{device_id} route {field} must be 1..16")
        if route.get("output_channel") != devices[device_id].channel:
            errors.append(f"{device_id} route output channel differs from device definition")
    for target in {mode.get("target") for mode in document.get("modes", []) if mode.get("target") != "mpc"}:
        if target in devices and target not in route_devices:
            warnings.append(f"{target}: control mode has no MPC pass-through route")

    warnings.append(
        "Launch Control custom-mode SysEx serialization is not public; "
        "use the generated Components worksheet"
    )
    warnings.append("MPC MIDI Learn targets are project-scoped and must be captured once in a baseline project")
    return {"errors": sorted(set(errors)), "warnings": sorted(set(warnings))}


def _csv_text(headers: list[str], rows: list[dict[str, Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=headers, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def _component_rows(document: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for mode in document["modes"]:
        for control in mode.get("controls", []):
            rows.append(
                {
                    "slot": mode["slot"],
                    "mode": mode["name"],
                    "output": mode.get("output", "usb"),
                    "control": control["control"],
                    "message": control.get("message", "cc"),
                    "channel": control.get("channel", mode["channel"]),
                    "number": control["number"],
                    "min": control.get("min", 0),
                    "max": control.get("max", 127),
                    "behavior": control.get("behavior", "absolute"),
                    "display_name": control.get("label", control["target"]),
                    "color": control.get("color", "white"),
                    "target": f"{mode['target']}:{control['target']}",
                }
            )
    return rows


def _learn_rows(document: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for mode in document["modes"]:
        if mode.get("target") != "mpc":
            continue
        for control in mode.get("controls", []):
            rows.append(
                {
                    "mode": mode["name"],
                    "control": control["control"],
                    "message": control.get("message", "cc"),
                    "channel": control.get("channel", mode["channel"]),
                    "number": control["number"],
                    "mpc_target": control["target"],
                    "support": control.get("support", "documented-category"),
                    "hardware_status": "pending",
                }
            )
    return rows


def _route_rows(document: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "track": route["track"],
            "device": route["device"],
            "input_port": route["input_port"],
            "input_channel": route["input_channel"],
            "output_port": route["output_port"],
            "output_channel": route["output_channel"],
            "monitor": route.get("monitor", "auto"),
            "clock": route.get("clock", "receive"),
        }
        for route in document.get("routes", [])
    ]


def _reference_rows(devices: dict[str, DeviceDefinition]) -> list[dict[str, Any]]:
    rows = []
    for definition in devices.values():
        for item in definition.parameters.values():
            rows.append(
                {
                    "device": definition.id,
                    "channel": definition.channel or "configurable",
                    "message": "cc",
                    "number": item["cc"],
                    "id": item["id"],
                    "label": item.get("label", item["id"]),
                    "scope": item.get("scope", "global"),
                    "evidence": item.get("evidence", "official"),
                }
            )
        for item in definition.notes.values():
            rows.append(
                {
                    "device": definition.id,
                    "channel": definition.channel or "configurable",
                    "message": "note",
                    "number": item["note"],
                    "id": item["id"],
                    "label": item.get("label", item["id"]),
                    "scope": item.get("scope", "global"),
                    "evidence": item.get("evidence", "official"),
                }
            )
    return rows


def render_setup(document: dict[str, Any], devices: dict[str, DeviceDefinition]) -> str:
    report = validate(document, devices)
    bridge = document.get("topology", {}).get("mpc_to_devices") == "launch-usb-din-bridge"
    topology_lines = (
        [
            "Launch Control XL 3 USB ↔ MPC Key 37; Launch Control DIN Out 1 → CME Thru5 → Volca Bass, Keys, and Drum.",
            "MPC Volca tracks address the Launch Control's host-visible "
            "`To DIN Out 1` port; Volca modes send directly to DIN 1.",
            "This lower-click topology remains hardware-pending until the Key 37 "
            "confirms the virtual DIN port and simultaneous traffic.",
        ]
        if bridge
        else [
            "Launch Control XL 3 USB → MPC Key 37; MPC MIDI Out → CME Thru5 → Volca Bass, Keys, and Drum.",
            "The passive Thru5 distributes one source. It does not merge Launch Control DIN with MPC DIN.",
        ]
    )
    output_setup = ", ".join(f"{mode['name']}={mode.get('output', 'usb')}" for mode in document["modes"])
    lines = [
        f"# {document['name']}",
        "",
        document.get("description", ""),
        "",
        "## Default topology",
        "",
        *topology_lines,
        "",
        "## One-time MPC setup",
        "",
        "1. In MIDI/SYNC preferences, enable **Global**, **Control**, and **Track** "
        "for the Launch Control main USB input.",
        f"2. Enable **Sync** and **Track** for "
        f"{'Launch Control XL 3 To DIN Out 1' if bridge else 'MPC MIDI Out'}. "
        "Send clock from the MPC.",
        "3. Create the three MIDI tracks exactly as listed in `mpc-track-routes.csv`; enable input monitoring.",
        "4. In MIDI Learn, apply `mpc-midi-learn.csv` while the `MPC Mix` custom mode is selected.",
        "5. Save these mappings in the reusable MPC project. Transport is handled by MPC clock/MMC, not MIDI Learn.",
        "",
        "## One-time Launch Control setup",
        "",
        "1. In Novation Components, create the modes from `launch-control-components.csv` in the listed slots.",
        f"2. Set each mode's Output exactly as listed ({output_setup}), set Merge "
        "to **Off**, and use the listed message/channel/number values.",
        "3. Export each Components mode as `.syx` and keep it beside this "
        "generated plan as the restorable binary artifact.",
        "4. Do not use DAW mode for this standalone rig; its DIN outputs are not active.",
        "",
        "A Components worksheet is generated because Novation documents Custom "
        "Mode capabilities and `.syx` export, but not the binary Custom Mode "
        "serialization needed for a trustworthy third-party `.syx` writer.",
        "",
        "## Custom modes",
        "",
    ]
    for mode in document["modes"]:
        lines.append(
            f"- Slot {mode['slot']}: **{mode['name']}** — {mode.get('description', '')} "
            f"(ch {mode['channel']}, {mode.get('output', 'usb')})"
        )
    lines.extend(["", "## MPC pass-through tracks", ""])
    for route in document.get("routes", []):
        lines.append(
            f"- **{route['track']}**: {route['input_port']} ch {route['input_channel']} → "
            f"{route['output_port']} ch {route['output_channel']} → {route['device']}"
        )
    lines.extend(["", "## Validation and remaining capture gates", "", f"- Errors: {len(report['errors'])}"])
    lines.extend(f"- ERROR: {message}" for message in report["errors"])
    lines.extend(f"- {message}" for message in report["warnings"])
    lines.extend(["", "## Primary sources", ""])
    for source in document.get("sources", []):
        lines.append(f"- {source}")
    for device in devices.values():
        lines.extend(f"- {source}" for source in device.sources)
    return "\n".join(lines).rstrip() + "\n"


def compile_map(
    document: dict[str, Any],
    devices: dict[str, DeviceDefinition],
    output: Path,
    force: bool = False,
) -> None:
    report = validate(document, devices)
    if report["errors"]:
        raise ValueError("invalid control map: " + "; ".join(report["errors"]))
    files = {
        "launch-control-components.csv": _csv_text(
            [
                "slot", "mode", "output", "control", "message", "channel",
                "number", "min", "max", "behavior", "display_name", "color", "target",
            ],
            _component_rows(document),
        ),
        "mpc-midi-learn.csv": _csv_text(
            ["mode", "control", "message", "channel", "number", "mpc_target", "support", "hardware_status"],
            _learn_rows(document),
        ),
        "mpc-track-routes.csv": _csv_text(
            ["track", "device", "input_port", "input_channel", "output_port", "output_channel", "monitor", "clock"],
            _route_rows(document),
        ),
        "device-midi-reference.csv": _csv_text(
            ["device", "channel", "message", "number", "id", "label", "scope", "evidence"],
            _reference_rows(devices),
        ),
        "SETUP.md": render_setup(document, devices),
        "mapping.json": json.dumps(
            {
                "map": document,
                "devices": {
                    key: {"name": value.name, "channel": value.channel}
                    for key, value in devices.items()
                },
                "validation": report,
            },
            indent=2,
        )
        + "\n",
    }
    output.mkdir(parents=True, exist_ok=True)
    collisions = [name for name in files if (output / name).exists()]
    if collisions and not force:
        raise FileExistsError(f"refusing to replace: {', '.join(collisions)}")
    for name, text in files.items():
        (output / name).write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check")
    check.add_argument("map", type=Path)
    check.add_argument("--device-root", type=Path)
    compile_parser = subparsers.add_parser("compile")
    compile_parser.add_argument("map", type=Path)
    compile_parser.add_argument("output", type=Path)
    compile_parser.add_argument("--device-root", type=Path)
    compile_parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    document, devices = load_map(args.map, args.device_root)
    report = validate(document, devices)
    if args.command == "check":
        print(json.dumps(report, indent=2))
    else:
        compile_map(document, devices, args.output, args.force)
        print(f"compiled {document['name']} -> {args.output}")
    return 2 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
