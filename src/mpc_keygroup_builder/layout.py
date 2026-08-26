"""Arrange normalized Drum Programs using reusable layouts and device profiles."""

from __future__ import annotations

import argparse
import json
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .device import DeviceProfile, load_device
from .model import ProgramModel, Zone, from_drum_manifest, from_xpm
from .roles import load_role_overrides, role_matches


@dataclass(frozen=True)
class LayoutPreset:
    schema_version: int
    id: str
    name: str
    strategy: str
    role_order: tuple[str, ...] = ()
    fill_remaining: bool = True


@dataclass(frozen=True)
class LayoutAssignment:
    slot: int
    label: str
    source_index: int
    sample: str
    role: str
    color: int | None
    locked: bool


@dataclass(frozen=True)
class LayoutPlan:
    program: str
    preset: str
    device: str
    assignments: tuple[LayoutAssignment, ...]
    unassigned_source_indexes: tuple[int, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_preset(path: Path) -> LayoutPreset:
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    required = ("schema_version", "id", "name", "strategy")
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"layout preset is missing: {', '.join(missing)}")
    if data["schema_version"] != 1:
        raise ValueError("layout preset requires schema_version=1")
    if data["strategy"] not in {"role-first", "sequential"}:
        raise ValueError(f"unsupported layout strategy: {data['strategy']!r}")
    role_order = data.get("role_order", [])
    if not isinstance(role_order, list) or not all(isinstance(item, str) and item for item in role_order):
        raise ValueError("layout role_order must be a list of roles")
    return LayoutPreset(
        1,
        data["id"],
        data["name"],
        data["strategy"],
        tuple(role_order),
        data.get("fill_remaining", True) is True,
    )


def _sample(zone: Zone) -> str:
    return zone.layers[0].sample if zone.layers else ""


def arrange(program: ProgramModel, preset: LayoutPreset, device: DeviceProfile) -> LayoutPlan:
    validation = program.validate()
    if validation["errors"]:
        raise ValueError("invalid Program Model: " + "; ".join(validation["errors"]))
    if program.kind != "drum":
        raise ValueError("layout engine currently requires a Drum Program Model")
    if len(preset.role_order) > device.pads_per_bank:
        raise ValueError("role_order cannot exceed one physical pad bank")
    assignments: dict[int, Zone] = {}
    remaining = list(program.zones)
    for zone in tuple(remaining):
        if zone.locked:
            if zone.pad is None or zone.pad > device.capacity:
                raise ValueError(f"locked zone {zone.index} has no valid device slot")
            if zone.pad in assignments:
                raise ValueError(f"multiple locked zones target slot {zone.pad}")
            assignments[zone.pad] = zone
            remaining.remove(zone)

    if preset.strategy == "sequential":
        for zone in tuple(remaining):
            preferred = zone.pad if zone.pad and 1 <= zone.pad <= device.capacity else None
            slot = preferred if preferred not in assignments else None
            if slot is None:
                slot = next((value for value in range(1, device.capacity + 1) if value not in assignments), None)
            if slot is None:
                break
            assignments[slot] = zone
            remaining.remove(zone)
    else:
        for slot, requested in enumerate(preset.role_order, 1):
            if slot in assignments:
                continue
            match = next((zone for zone in remaining if role_matches(zone.role, requested)), None)
            if match is not None:
                assignments[slot] = match
                remaining.remove(match)
        if preset.fill_remaining:
            for slot in range(1, device.capacity + 1):
                if not remaining:
                    break
                if slot not in assignments:
                    assignments[slot] = remaining.pop(0)

    rendered = tuple(
        LayoutAssignment(
            slot=slot,
            label=device.label(slot),
            source_index=zone.index,
            sample=_sample(zone),
            role=zone.role,
            color=zone.color,
            locked=zone.locked,
        )
        for slot, zone in sorted(assignments.items())
    )
    return LayoutPlan(
        program.name,
        preset.id,
        device.id,
        rendered,
        tuple(zone.index for zone in remaining),
    )


def render_markdown(plan: LayoutPlan, device: DeviceProfile) -> str:
    lines = [f"# {plan.program} — {plan.preset}", "", f"Device: {device.name}", ""]
    current_bank = ""
    for item in plan.assignments:
        bank = item.label[0]
        if bank != current_bank:
            current_bank = bank
            lines.extend(
                [
                    f"## Bank {bank}",
                    "",
                    "| Pad | Role | Color | Source pad | Sample |",
                    "|---|---|---:|---:|---|",
                ]
            )
        color = f"#{item.color & 0xFFFFFF:06X}" if item.color is not None else "-"
        sample = item.sample.replace("|", "\\|")
        lines.append(f"| {item.label} | {item.role} | {color} | {item.source_index} | {sample} |")
    if plan.unassigned_source_indexes:
        lines.extend(
            [
                "",
                "## Unassigned source zones",
                "",
                ", ".join(str(value) for value in plan.unassigned_source_indexes),
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--source-type", choices=("auto", "xpm", "manifest"), default="auto")
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--roles", type=Path, help="TOML file with explicit [roles] overrides")
    parser.add_argument("--preset", type=Path, required=True)
    parser.add_argument("--device", type=Path, required=True)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    source = args.source.expanduser().resolve()
    source_type = args.source_type
    if source_type == "auto":
        source_type = "manifest" if source.suffix.casefold() == ".toml" else "xpm"
    role_overrides = (
        load_role_overrides(args.roles.expanduser().resolve()) if args.roles else None
    )
    program = (
        from_drum_manifest(
            source,
            args.source_root.expanduser().resolve() if args.source_root else None,
            role_overrides,
        )
        if source_type == "manifest"
        else from_xpm(source, role_overrides)
    )
    preset = load_preset(args.preset.expanduser().resolve())
    device = load_device(args.device.expanduser().resolve())
    plan = arrange(program, preset, device)
    rendered = json.dumps(plan.to_dict(), indent=2) + "\n" if args.format == "json" else render_markdown(plan, device)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Wrote: {args.output}")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
