"""Read and cross-check Novation Launch Control XL 3 Components captures."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from . import xpj


NOVATION_HEADER = bytes((0xF0, 0x00, 0x20, 0x29, 0x02, 0x15, 0x05, 0x00, 0x45))
SECTION_CONTINUOUS = 0x00
SECTION_FADERS_BUTTONS = 0x03


def endpoint(control_id: int) -> str:
    groups = (
        (0x10, "top-encoder"),
        (0x18, "middle-encoder"),
        (0x20, "bottom-encoder"),
        (0x28, "fader"),
        (0x30, "upper-button"),
        (0x38, "lower-button"),
    )
    for start, name in groups:
        if start <= control_id < start + 8:
            return f"{name}-{control_id - start + 1}"
    return f"unknown-{control_id}"


def _messages(raw: bytes) -> list[bytes]:
    messages: list[bytes] = []
    cursor = 0
    while cursor < len(raw):
        start = raw.find(b"\xF0", cursor)
        if start < 0:
            break
        end = raw.find(b"\xF7", start + 1)
        if end < 0:
            raise ValueError("unterminated SysEx message")
        if any(raw[cursor:start]):
            raise ValueError("nonzero data found outside SysEx messages")
        messages.append(raw[start : end + 1])
        cursor = end + 1
    if any(raw[cursor:]):
        raise ValueError("nonzero trailing data found after SysEx message")
    if not messages:
        raise ValueError("file contains no SysEx messages")
    return messages


def _parse_block(message: bytes, cursor: int, start: int, count: int) -> tuple[list[dict[str, Any]], int]:
    controls: list[dict[str, Any]] = []
    for control_id in range(start, start + count):
        if cursor >= len(message) - 1:
            raise ValueError(f"control block at 0x{start:02x} is truncated")
        marker = message[cursor]
        if marker == 0x40:
            record = message[cursor : cursor + 2]
            cursor += 2
            if len(record) != 2 or record[1] != control_id:
                raise ValueError(f"malformed disabled control 0x{control_id:02x}")
            controls.append(
                {
                    "id": control_id,
                    "control": endpoint(control_id),
                    "enabled": False,
                    "label": "",
                    "number": None,
                    "channel": None,
                    "channel_source": None,
                    "raw": record.hex(),
                }
            )
            continue
        if marker != 0x49:
            raise ValueError(f"unexpected control marker 0x{marker:02x} at 0x{cursor:x}")
        record = message[cursor : cursor + 11]
        cursor += 11
        if len(record) != 11 or record[1] != control_id:
            raise ValueError(f"malformed active control 0x{control_id:02x}")
        is_button = control_id >= 0x30
        encoded_channel = record[5]
        channel = None if is_button or encoded_channel > 15 else encoded_channel + 1
        controls.append(
            {
                "id": control_id,
                "control": endpoint(control_id),
                "enabled": True,
                "label": "",
                "number": record[8],
                "channel": channel,
                "channel_source": "encoded" if channel is not None else None,
                "message_code": record[2],
                "minimum": record[10],
                "maximum": record[9],
                "raw": record.hex(),
            }
        )
    by_id = {item["id"]: item for item in controls}
    for control_id in range(start, start + count):
        if cursor + 2 > len(message) - 1:
            raise ValueError("Custom Mode label table is truncated")
        encoded_length = message[cursor]
        label_id = message[cursor + 1]
        length = encoded_length - 0x60
        if not 0 <= length <= 31 or label_id != control_id:
            raise ValueError(f"malformed label for control 0x{control_id:02x}")
        label_end = cursor + 2 + length
        try:
            label = message[cursor + 2 : label_end].decode("ascii")
        except UnicodeDecodeError as error:
            raise ValueError(f"control 0x{control_id:02x} label is not ASCII") from error
        by_id[control_id]["label"] = label
        cursor = label_end
    return controls, cursor


def _parse_message(message: bytes) -> dict[str, Any]:
    if not message.startswith(NOVATION_HEADER) or message[-1] != 0xF7:
        raise ValueError("not a recognized Launch Control XL 3 Components message")
    if len(message) < 15 or message[10:12] != bytes((0x7F, 0x20)):
        raise ValueError("invalid Components Custom Mode header")
    section = message[9]
    if section not in {SECTION_CONTINUOUS, SECTION_FADERS_BUTTONS}:
        raise ValueError(f"unsupported Components section 0x{section:02x}")
    name_length = message[12]
    name_end = 13 + name_length
    if name_end >= len(message) - 1:
        raise ValueError("Custom Mode name extends beyond the SysEx message")
    try:
        name = message[13:name_end].decode("ascii")
    except UnicodeDecodeError as error:
        raise ValueError("Custom Mode name is not ASCII") from error
    cursor = name_end
    if section == SECTION_CONTINUOUS:
        controls, cursor = _parse_block(message, cursor, 0x10, 24)
    else:
        faders, cursor = _parse_block(message, cursor, 0x28, 8)
        buttons, cursor = _parse_block(message, cursor, 0x30, 16)
        controls = [*faders, *buttons]
    if cursor != len(message) - 1:
        raise ValueError(f"unexpected {len(message) - 1 - cursor} bytes after label table")
    return {"name": name, "section": section, "controls": controls}


def inspect(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    sections = [_parse_message(message) for message in _messages(raw)]
    names = {section["name"] for section in sections}
    if len(names) != 1:
        raise ValueError(f"{path}: sections disagree on Custom Mode name")
    section_ids = [section["section"] for section in sections]
    if len(section_ids) != len(set(section_ids)):
        raise ValueError(f"{path}: duplicate Custom Mode section")
    primary_channels = Counter(
        control["channel"]
        for section in sections
        if section["section"] == SECTION_CONTINUOUS
        for control in section["controls"]
        if control["enabled"] and control["channel"] is not None
    )
    primary_channel = primary_channels.most_common(1)[0][0] if primary_channels else None
    controls = [control for section in sections for control in section["controls"]]
    for control in controls:
        if control["enabled"] and control["id"] >= 0x30 and primary_channel is not None:
            control["channel"] = primary_channel
            control["channel_source"] = "inferred-from-encoder-section"
    return {
        "path": str(path),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "byte_count": len(raw),
        "format": "Novation Launch Control XL 3 Components SysEx",
        "name": next(iter(names)),
        "primary_channel": primary_channel,
        "sections": sorted(section_ids),
        "enabled_count": sum(control["enabled"] for control in controls),
        "controls": controls,
        "limitations": [
            "Read-only parser for observed Components exports; it does not serialize SysEx.",
            "Button channels are inferred from the mode's encoder section and labeled as inferred.",
            "Undocumented behavior, color, output, and message-code fields remain available only as raw bytes.",
        ],
    }


def inspect_many(paths: list[Path]) -> dict[str, Any]:
    return {"schema_version": 1, "captures": [inspect(path) for path in paths]}


def audit(project_path: Path, syx_paths: list[Path]) -> dict[str, Any]:
    project = xpj.load(project_path)
    learned = xpj.midi_learn_rows(project)
    by_signature: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in learned:
        channel = row.get("channel")
        number = row.get("number")
        if isinstance(channel, int) and isinstance(number, int):
            by_signature[(channel, number)].append(row)
    captures = []
    for path in syx_paths:
        capture = inspect(path)
        controls = []
        for control in capture["controls"]:
            if not control["enabled"]:
                continue
            key = (control.get("channel"), control.get("number"))
            matches = by_signature.get(key, []) if all(isinstance(value, int) for value in key) else []
            controls.append(
                {
                    "control": control["control"],
                    "label": control["label"],
                    "channel": control["channel"],
                    "channel_source": control["channel_source"],
                    "number": control["number"],
                    "learned_targets": [row["name"] for row in matches],
                }
            )
        captures.append(
            {
                "path": capture["path"],
                "name": capture["name"],
                "sha256": capture["sha256"],
                "enabled_count": len(controls),
                "matched_control_count": sum(bool(item["learned_targets"]) for item in controls),
                "controls": controls,
            }
        )
    return {
        "schema_version": 1,
        "project": str(project_path),
        "project_firmware": project.header.firmware if project.header else None,
        "project_midi_learn_count": len(learned),
        "captures": captures,
        "interpretation": (
            "A missing learned target is not automatically an error: direct hardware/Volca controls "
            "are expected to bypass MPC MIDI Learn. Matches prove only the captured channel/number pair."
        ),
    }


def _write(value: dict[str, Any], output: Path | None) -> None:
    rendered = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if output is None:
        sys.stdout.write(rendered)
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inspect_parser = commands.add_parser("inspect", help="inspect Components .syx exports")
    inspect_parser.add_argument("captures", type=Path, nargs="+")
    inspect_parser.add_argument("--output", type=Path)
    audit_parser = commands.add_parser("audit", help="cross-check .syx channel/numbers against an MPC XPJ")
    audit_parser.add_argument("project", type=Path)
    audit_parser.add_argument("captures", type=Path, nargs="+")
    audit_parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "inspect":
        _write(inspect_many(args.captures), args.output)
    else:
        _write(audit(args.project, args.captures), args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
