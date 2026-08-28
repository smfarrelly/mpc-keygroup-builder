"""Validate Program Designer layout drafts and export source-safe artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .device import DeviceProfile, load_device
from .layout import LayoutAssignment, LayoutPlan
from .layout_export import export_layout
from .model import ProgramModel, Zone, from_drum_manifest, from_xpm
from .roles import load_role_overrides


DRAFT_KIND = "mpc-layout-draft"
DRAFT_SCHEMA_VERSION = 1


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def model_fingerprint(program: ProgramModel) -> str:
    """Hash normalized musical data while excluding machine-specific source paths."""
    payload = program.to_dict()
    payload.pop("source_path", None)
    payload.pop("provenance", None)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class DraftAssignment:
    slot: int
    label: str
    source_zone: int
    source_pad: int
    role: str
    source_color: int | None
    color: int | None
    source_locked: bool
    locked: bool
    playback_mode: str
    mute_group: int
    layers: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class LayoutDraft:
    schema_version: int
    kind: str
    program: str
    device: str
    source_path: str
    source_format: str
    source_sha256: str
    source_model_sha256: str
    assignments: tuple[DraftAssignment, ...]


@dataclass(frozen=True)
class DraftReport:
    draft: str
    source: str
    program: str
    device: str
    assignments: int
    moved_assignments: int
    color_changes: int
    lock_changes: int
    source_sha256: str
    source_model_sha256: str
    valid: bool


def _required(data: dict[str, Any], key: str, expected: type) -> Any:
    value = data.get(key)
    if not isinstance(value, expected) or (expected is int and isinstance(value, bool)):
        raise ValueError(f"draft {key} must be {expected.__name__}")
    return value


def _optional_color(data: dict[str, Any], key: str) -> int | None:
    if key not in data:
        raise ValueError(f"draft assignment is missing {key}")
    value = data.get(key)
    if value is not None and (not isinstance(value, int) or isinstance(value, bool)):
        raise ValueError(f"draft assignment {key} must be an RGB integer or null")
    if value is not None and not 0 <= value <= 0xFFFFFF:
        raise ValueError(f"draft assignment {key} must be within 0..16777215")
    return value


def load_draft(path: Path) -> LayoutDraft:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid layout draft JSON: {error}") from error
    if not isinstance(data, dict):
        raise ValueError("layout draft root must be an object")
    raw_assignments = _required(data, "assignments", list)
    assignments: list[DraftAssignment] = []
    for index, raw in enumerate(raw_assignments, 1):
        if not isinstance(raw, dict):
            raise ValueError(f"draft assignment {index} must be an object")
        layers = _required(raw, "layers", list)
        if not all(isinstance(layer, dict) for layer in layers):
            raise ValueError(f"draft assignment {index} layers must be objects")
        assignments.append(
            DraftAssignment(
                slot=_required(raw, "slot", int),
                label=_required(raw, "label", str),
                source_zone=_required(raw, "source_zone", int),
                source_pad=_required(raw, "source_pad", int),
                role=_required(raw, "role", str),
                source_color=_optional_color(raw, "source_color"),
                color=_optional_color(raw, "color"),
                source_locked=_required(raw, "source_locked", bool),
                locked=_required(raw, "locked", bool),
                playback_mode=_required(raw, "playback_mode", str),
                mute_group=_required(raw, "mute_group", int),
                layers=tuple(layers),
            )
        )
    return LayoutDraft(
        schema_version=_required(data, "schema_version", int),
        kind=_required(data, "kind", str),
        program=_required(data, "program", str),
        device=_required(data, "device", str),
        source_path=_required(data, "source_path", str),
        source_format=_required(data, "source_format", str),
        source_sha256=_required(data, "source_sha256", str),
        source_model_sha256=_required(data, "source_model_sha256", str),
        assignments=tuple(assignments),
    )


def load_source(path: Path, roles: Path | None = None) -> ProgramModel:
    overrides = load_role_overrides(roles) if roles else None
    return (
        from_drum_manifest(path, role_overrides=overrides)
        if path.suffix.casefold() == ".toml"
        else from_xpm(path, overrides)
    )


def _layer_payload(zone: Zone) -> tuple[dict[str, Any], ...]:
    return tuple(asdict(layer) for layer in zone.layers)


def validate_draft(
    draft: LayoutDraft,
    draft_path: Path,
    source: Path,
    program: ProgramModel,
    device: DeviceProfile,
) -> DraftReport:
    if draft.schema_version != DRAFT_SCHEMA_VERSION or draft.kind != DRAFT_KIND:
        raise ValueError(
            f"draft requires schema_version={DRAFT_SCHEMA_VERSION} and kind={DRAFT_KIND!r}"
        )
    if program.kind != "drum":
        raise ValueError("layout drafts currently require a Drum Program source")
    if draft.program != program.name:
        raise ValueError("draft program name does not match the source")
    if draft.device != device.id:
        raise ValueError("draft device does not match the selected device profile")
    if draft.source_format != program.source_format:
        raise ValueError("draft source format does not match the selected source")
    actual_file_hash = file_sha256(source)
    if draft.source_sha256 != actual_file_hash:
        raise ValueError("draft source SHA-256 does not match the selected source file")
    actual_model_hash = model_fingerprint(program)
    if draft.source_model_sha256 != actual_model_hash:
        raise ValueError("draft model fingerprint does not match the selected source")
    if len(draft.assignments) != len(program.zones):
        raise ValueError("draft must assign every populated source zone exactly once")
    slots = [item.slot for item in draft.assignments]
    zones = [item.source_zone for item in draft.assignments]
    if len(slots) != len(set(slots)):
        raise ValueError("draft contains duplicate destination slots")
    if len(zones) != len(set(zones)):
        raise ValueError("draft contains duplicate source zones")
    if any(not 1 <= slot <= device.capacity for slot in slots):
        raise ValueError(f"draft slots must be within the device capacity 1..{device.capacity}")
    source_by_index = {zone.index: zone for zone in program.zones}
    if set(zones) != set(source_by_index):
        raise ValueError("draft source-zone set does not match the selected source")
    for item in draft.assignments:
        zone = source_by_index[item.source_zone]
        expected = {
            "label": device.label(item.slot),
            "source_pad": zone.pad,
            "role": zone.role,
            "source_color": zone.color,
            "source_locked": zone.locked,
            "playback_mode": zone.playback_mode,
            "mute_group": zone.mute_group,
            "layers": _layer_payload(zone),
        }
        actual = {
            "label": item.label,
            "source_pad": item.source_pad,
            "role": item.role,
            "source_color": item.source_color,
            "source_locked": item.source_locked,
            "playback_mode": item.playback_mode,
            "mute_group": item.mute_group,
            "layers": item.layers,
        }
        for field, expected_value in expected.items():
            if actual[field] != expected_value:
                raise ValueError(
                    f"draft assignment {item.label} {field} does not match source zone {zone.index}"
                )
    moved = sum(item.slot != source_by_index[item.source_zone].pad for item in draft.assignments)
    colors = sum(item.color != item.source_color for item in draft.assignments)
    locks = sum(item.locked != item.source_locked for item in draft.assignments)
    return DraftReport(
        str(draft_path.resolve()),
        str(source.resolve()),
        program.name,
        device.id,
        len(draft.assignments),
        moved,
        colors,
        locks,
        actual_file_hash,
        actual_model_hash,
        True,
    )


def draft_to_plan(draft: LayoutDraft, program: ProgramModel, device: DeviceProfile) -> LayoutPlan:
    assignments = tuple(
        LayoutAssignment(
            item.slot,
            device.label(item.slot),
            item.source_zone,
            item.layers[0]["sample"] if item.layers else "",
            item.role,
            item.color,
            item.locked,
        )
        for item in sorted(draft.assignments, key=lambda value: value.slot)
    )
    assigned = {item.source_zone for item in draft.assignments}
    return LayoutPlan(
        program.name,
        "program-designer-draft",
        device.id,
        assignments,
        tuple(zone.index for zone in program.zones if zone.index not in assigned),
    )


def color_overrides(draft: LayoutDraft) -> dict[int, int | None]:
    return {
        item.slot: item.color
        for item in draft.assignments
        if item.color != item.source_color
    }


def render_manifest(draft: LayoutDraft, name: str) -> str:
    if not name.strip() or Path(name).name != name:
        raise ValueError("manifest name must be a non-empty path-safe name")
    lines = [
        "# Generated from a validated MPC Program Designer layout draft.",
        "# Pad colors and editor locks remain in the draft JSON; the Drum manifest schema",
        "# describes sample placement, velocity layers, and mute groups.",
        f"name = {json.dumps(name)}",
        "",
    ]
    for item in sorted(draft.assignments, key=lambda value: value.slot):
        layers = sorted(item.layers, key=lambda value: int(value["velocity_start"]))
        if not 1 <= len(layers) <= 4:
            raise ValueError(
                f"slot {item.label} has {len(layers)} layers; Drum manifests support one through four"
            )
        expected_start = 0
        for layer in layers:
            if int(layer["velocity_start"]) != expected_start:
                raise ValueError(
                    f"slot {item.label} layers cannot be represented without velocity gaps or overlaps"
                )
            expected_start = int(layer["velocity_end"]) + 1
        if expected_start != 128:
            raise ValueError(
                f"slot {item.label} layers cannot be represented without velocity gaps or overlaps"
            )
        lines.extend(["[[pads]]", f"pad = {item.slot}"])
        if item.mute_group:
            lines.append(f"mute_group = {item.mute_group}")
        if len(layers) == 1:
            lines.append(f"sample = {json.dumps(Path(str(layers[0]['sample'])).name)}")
        else:
            for layer in layers:
                lines.extend(
                    [
                        "[[pads.layers]]",
                        f"sample = {json.dumps(Path(str(layer['sample'])).name)}",
                        f"velocity_start = {int(layer['velocity_start'])}",
                        f"velocity_end = {int(layer['velocity_end'])}",
                    ]
                )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _atomic_text(path: Path, value: str, *, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"output exists; pass --force to replace it: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _validated(args: argparse.Namespace) -> tuple[LayoutDraft, ProgramModel, DeviceProfile, DraftReport]:
    draft_path = args.draft.expanduser().resolve()
    source = args.source.expanduser().resolve()
    device = load_device(args.device.expanduser().resolve())
    draft = load_draft(draft_path)
    program = load_source(
        source,
        args.roles.expanduser().resolve() if args.roles else None,
    )
    report = validate_draft(draft, draft_path, source, program, device)
    return draft, program, device, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("inspect", "manifest", "xpm"):
        child = subparsers.add_parser(command)
        child.add_argument("draft", type=Path)
        child.add_argument("--source", type=Path, required=True)
        child.add_argument("--device", type=Path, required=True)
        child.add_argument("--roles", type=Path, help="TOML file with exact [roles] overrides")
        if command != "inspect":
            child.add_argument("--output", type=Path, required=True)
            child.add_argument("--name")
            child.add_argument("--force", action="store_true")
    args = parser.parse_args()
    draft, program, device, report = _validated(args)
    if args.command == "inspect":
        print(json.dumps(asdict(report), indent=2))
        return 0
    name = args.name or f"{program.name} Draft"
    output = args.output.expanduser().resolve()
    if args.command == "manifest":
        _atomic_text(output, render_manifest(draft, name), force=args.force)
        payload = {**asdict(report), "output": str(output), "artifact": "drum-manifest"}
    else:
        if program.source_format not in {"xml", "gzip-json"}:
            raise ValueError("XPM export requires the exact source XPM, not a Drum manifest")
        exported = export_layout(
            args.source.expanduser().resolve(),
            output,
            draft_to_plan(draft, program, device),
            name=name,
            color_overrides=color_overrides(draft),
            force=args.force,
        )
        payload = {**asdict(report), "output": str(output), "artifact": "xpm", "export": asdict(exported)}
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
