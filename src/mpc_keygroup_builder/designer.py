"""Render a self-contained, read-only MPC Program Designer viewer."""

from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median
from typing import Any

from .device import BUILTIN_DEVICES, DeviceProfile, resolve_device
from .layout import LayoutPreset, load_preset
from .layout_draft import DRAFT_KIND, file_sha256, model_fingerprint
from .midi_groove import MidiGroove, analyse_program_groove, load_groove
from .model import ProgramModel, Zone, from_drum_manifest, from_xpm
from .roles import load_role_overrides


AUDIO_SUFFIXES = {".wav", ".aif", ".aiff"}
SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


@dataclass(frozen=True)
class DesignerIssue:
    severity: str
    code: str
    message: str
    zone: int | None = None


def _color(value: int | None) -> str | None:
    return f"#{value & 0xFFFFFF:06X}" if value is not None else None


def _compact_ranges(values: list[int]) -> str:
    if not values:
        return ""
    ranges: list[str] = []
    start = previous = values[0]
    for value in values[1:]:
        if value == previous + 1:
            previous = value
            continue
        ranges.append(str(start) if start == previous else f"{start}-{previous}")
        start = previous = value
    ranges.append(str(start) if start == previous else f"{start}-{previous}")
    return ", ".join(ranges)


def _audio_index(root: Path | None) -> tuple[dict[str, list[Path]], dict[str, list[Path]]] | None:
    if root is None or not root.is_dir():
        return None
    by_name: dict[str, list[Path]] = {}
    by_stem: dict[str, list[Path]] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.casefold() not in AUDIO_SUFFIXES:
            continue
        by_name.setdefault(path.name.casefold(), []).append(path)
        by_stem.setdefault(path.stem.casefold(), []).append(path)
    return by_name, by_stem


def _sample_status(
    sample: str,
    index: tuple[dict[str, list[Path]], dict[str, list[Path]]] | None,
) -> tuple[str, int]:
    if index is None:
        return "unchecked", 0
    name = Path(sample).name
    by_name, by_stem = index
    matches = (
        by_name.get(name.casefold(), [])
        if Path(name).suffix
        else by_stem.get(Path(name).stem.casefold(), [])
    )
    if not matches:
        return "missing", 0
    if len(matches) > 1:
        return "ambiguous", len(matches)
    return "found", 1


def infer_sample_root(program: ProgramModel, source_root: Path | None = None) -> Path | None:
    if source_root is not None:
        return source_root.resolve()
    if not program.source_path or program.source_format == "drum-manifest-toml":
        return None
    source = Path(program.source_path)
    if program.source_format == "gzip-json":
        program_data = source.with_name(f"{source.stem}_[ProgramData]")
        if program_data.is_dir():
            return program_data.resolve()
    return source.parent.resolve() if source.parent.is_dir() else None


def analyse_program(
    program: ProgramModel,
    device: DeviceProfile,
    sample_root: Path | None = None,
) -> tuple[list[DesignerIssue], dict[int, list[dict[str, Any]]]]:
    issues: list[DesignerIssue] = []
    validation = program.validate()
    issues.extend(DesignerIssue("error", "model_validation", value) for value in validation["errors"])
    issues.extend(
        DesignerIssue("warning", "model_validation", value)
        for value in validation["warnings"]
    )
    audio = _audio_index(sample_root)
    layer_status: dict[int, list[dict[str, Any]]] = {}
    for zone in program.zones:
        statuses = []
        coverage = [0] * 128
        for layer in zone.layers:
            status, matches = _sample_status(layer.sample, audio)
            statuses.append({"status": status, "matches": matches})
            if status == "missing":
                issues.append(
                    DesignerIssue(
                        "error",
                        "missing_sample",
                        f"Sample not found below the selected sample root: {layer.sample}",
                        zone.index,
                    )
                )
            elif status == "ambiguous":
                issues.append(
                    DesignerIssue(
                        "error",
                        "ambiguous_sample",
                        f"Sample resolves to {matches} files: {layer.sample}",
                        zone.index,
                    )
                )
            for velocity in range(max(0, layer.velocity_start), min(127, layer.velocity_end) + 1):
                coverage[velocity] += 1
            if layer.sample_end is not None and layer.sample_end < layer.sample_start:
                issues.append(
                    DesignerIssue(
                        "error",
                        "invalid_sample_bounds",
                        f"Sample end {layer.sample_end} precedes start {layer.sample_start}",
                        zone.index,
                    )
                )
            if layer.loop_enabled and (layer.loop_start is None or layer.loop_end is None):
                issues.append(
                    DesignerIssue(
                        "warning",
                        "incomplete_loop",
                        f"Loop is enabled without complete bounds: {layer.sample}",
                        zone.index,
                    )
                )
        gaps = [velocity for velocity, count in enumerate(coverage) if count == 0]
        stacks = [velocity for velocity, count in enumerate(coverage) if count > 1]
        if gaps:
            issues.append(
                DesignerIssue(
                    "error",
                    "dead_velocity_range",
                    f"No layer triggers at velocities {_compact_ranges(gaps)}",
                    zone.index,
                )
            )
        if stacks:
            issues.append(
                DesignerIssue(
                    "warning",
                    "stacked_velocity_range",
                    f"Multiple layers trigger at velocities {_compact_ranges(stacks)}",
                    zone.index,
                )
            )
        layer_status[zone.index] = statuses

    if program.kind == "drum":
        outside = [zone.index for zone in program.zones if zone.pad and zone.pad > device.capacity]
        if outside:
            issues.append(
                DesignerIssue(
                    "error",
                    "device_capacity",
                    f"{len(outside)} populated pads exceed {device.name}'s {device.capacity}-slot capacity",
                )
            )
        groups: dict[int, list[Zone]] = {}
        for zone in program.zones:
            if zone.mute_group:
                groups.setdefault(zone.mute_group, []).append(zone)
        for group, zones in groups.items():
            if len(zones) == 1:
                issues.append(
                    DesignerIssue(
                        "warning",
                        "singleton_mute_group",
                        f"Mute Group {group} contains only one populated pad",
                        zones[0].index,
                    )
                )
        ungrouped_hats = [
            zone for zone in program.zones if zone.role.startswith("hihat.") and not zone.mute_group
        ]
        if ungrouped_hats:
            issues.append(
                DesignerIssue(
                    "warning",
                    "ungrouped_hats",
                    f"{len(ungrouped_hats)} hat pads have no mute group",
                )
            )
        missing_colors = sum(zone.color is None for zone in program.zones)
        if missing_colors:
            issues.append(
                DesignerIssue(
                    "info",
                    "missing_colors",
                    f"{missing_colors} populated pads have no explicit color",
                )
            )
        if not program.pad_note_map and all(zone.midi_note is None for zone in program.zones):
            issues.append(
                DesignerIssue(
                    "info",
                    "midi_map_unavailable",
                    "No explicit Drum PadNoteMap is available in the normalized source",
                )
            )
    return sorted(
        issues,
        key=lambda value: (SEVERITY_ORDER.get(value.severity, 9), value.zone or 0, value.code),
    ), layer_status


def _zone_payload(
    zone: Zone,
    program: ProgramModel,
    statuses: list[dict[str, Any]],
) -> dict[str, Any]:
    midi_note = zone.midi_note
    if midi_note is None and zone.pad is not None:
        midi_note = program.pad_note_map.get(zone.pad)
    return {
        "index": zone.index,
        "pad": zone.pad,
        "midi_note": midi_note,
        "low_note": zone.low_note,
        "high_note": zone.high_note,
        "role": zone.role,
        "color": zone.color,
        "color_hex": _color(zone.color),
        "playback_mode": zone.playback_mode,
        "mute_group": zone.mute_group,
        "polyphony": zone.polyphony,
        "monophonic": zone.monophonic,
        "locked": zone.locked,
        "layers": [
            {
                **asdict(layer),
                "sample_status": statuses[index]["status"],
                "sample_matches": statuses[index]["matches"],
            }
            for index, layer in enumerate(zone.layers)
        ],
    }


def build_view_data(
    program: ProgramModel,
    device: DeviceProfile,
    sample_root: Path | None = None,
    groove: MidiGroove | None = None,
) -> dict[str, Any]:
    issues, statuses = analyse_program(program, device, sample_root)
    zones = [
        _zone_payload(zone, program, statuses.get(zone.index, [])) for zone in program.zones
    ]
    groove_data = analyse_program_groove(program, device, groove)
    if groove_data is not None:
        for zone in zones:
            zone["groove"] = groove_data["zones"].get(str(zone["index"]))
    role_counts = Counter(zone.role for zone in program.zones)
    populated_banks: list[str] = []
    banks: dict[str, list[dict[str, Any] | None]] = {}
    zones_by_pad = {zone["pad"]: zone for zone in zones if zone["pad"] is not None}
    for bank_index, bank in enumerate(device.banks):
        offset = bank_index * device.pads_per_bank
        slots = [zones_by_pad.get(offset + position) for position in range(1, device.pads_per_bank + 1)]
        banks[bank] = slots
        if any(slots):
            populated_banks.append(bank)
    roots = [
        layer.root_note
        for zone in program.zones
        for layer in zone.layers
        if layer.root_note is not None
    ]
    ranges = [
        note
        for zone in program.zones
        for note in (zone.low_note, zone.high_note)
        if note is not None
    ]
    focus_notes = roots or ranges or [60]
    key_start = max(0, min(128 - max(1, device.keys), round(median(focus_notes)) - device.keys // 2))
    severity_counts = Counter(issue.severity for issue in issues)
    mute_groups: dict[str, list[str]] = {}
    for zone in program.zones:
        if zone.mute_group and zone.pad:
            label = device.label(zone.pad) if zone.pad <= device.capacity else f"Pad {zone.pad}"
            mute_groups.setdefault(str(zone.mute_group), []).append(label)
    source_path = Path(program.source_path) if program.source_path else None
    return {
        "schema_version": 1,
        "read_only": True,
        "program": {
            "name": program.name,
            "kind": program.kind,
            "source_format": program.source_format,
            "source_path": program.source_path,
            "source_sha256": (
                file_sha256(source_path) if source_path is not None and source_path.is_file() else ""
            ),
            "source_model_sha256": model_fingerprint(program),
            "zones": zones,
        },
        "device": {
            **asdict(device),
            "pads_per_bank": device.pads_per_bank,
            "capacity": device.capacity,
        },
        "summary": {
            "zones": len(program.zones),
            "layers": sum(len(zone.layers) for zone in program.zones),
            "populated_banks": populated_banks,
            "roles": dict(sorted(role_counts.items())),
            "mute_groups": mute_groups,
            "issues": dict(severity_counts),
            "sample_root": str(sample_root) if sample_root else None,
        },
        "banks": banks,
        "keyboard": {
            "keys": device.keys,
            "default_start": key_start,
            "minimum": 0,
            "maximum_start": max(0, 128 - max(1, device.keys)),
        },
        "issues": [asdict(issue) for issue in issues],
        "groove": groove_data,
    }


def _identifier(value: str, used: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "program"
    candidate = base
    suffix = 2
    while candidate in used:
        candidate = f"{base}-{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


def _zone_location(zone: dict[str, Any], view: dict[str, Any]) -> str:
    if view["program"]["kind"] != "drum":
        return f"Zone {zone['index']}"
    pad = zone.get("pad")
    if not isinstance(pad, int) or pad < 1:
        return f"Zone {zone['index']}"
    per_bank = int(view["device"]["pads_per_bank"])
    banks = view["device"]["banks"]
    bank_index = (pad - 1) // per_bank
    if bank_index >= len(banks):
        return f"Pad {pad}"
    return f"{banks[bank_index]}{((pad - 1) % per_bank) + 1:02d}"


def _comparison_signature(zone: dict[str, Any]) -> dict[str, Any]:
    return {
        "role": zone["role"],
        "color": zone["color_hex"],
        "midi_note": zone["midi_note"],
        "key_range": [zone["low_note"], zone["high_note"]],
        "playback_mode": zone["playback_mode"],
        "mute_group": zone["mute_group"],
        "polyphony": zone["polyphony"],
        "monophonic": zone["monophonic"],
        "layers": [
            {
                "sample": layer["sample"],
                "velocity": [layer["velocity_start"], layer["velocity_end"]],
                "root_note": layer["root_note"],
                "loop_enabled": layer["loop_enabled"],
            }
            for layer in zone["layers"]
        ],
    }


def compare_view_data(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic, machine-readable comparison of two rendered views."""
    left_zones = {
        _zone_location(zone, left): zone for zone in left["program"]["zones"]
    }
    right_zones = {
        _zone_location(zone, right): zone for zone in right["program"]["zones"]
    }
    locations = []
    for location in sorted(
        set(left_zones) | set(right_zones),
        key=lambda value: (
            re.sub(r"\d+$", "", value),
            int(re.search(r"\d+$", value).group()) if re.search(r"\d+$", value) else 0,
        ),
    ):
        left_zone = left_zones.get(location)
        right_zone = right_zones.get(location)
        left_signature = _comparison_signature(left_zone) if left_zone else None
        right_signature = _comparison_signature(right_zone) if right_zone else None
        changed_fields = []
        if left_signature is None or right_signature is None:
            changed_fields.append("population")
        else:
            changed_fields = [
                field
                for field in left_signature
                if left_signature[field] != right_signature[field]
            ]
        locations.append(
            {
                "location": location,
                "changed": bool(changed_fields),
                "changed_fields": changed_fields,
                "left": left_zone,
                "right": right_zone,
            }
        )
    left_issues = left["summary"]["issues"]
    right_issues = right["summary"]["issues"]
    return {
        "left_name": left["program"]["name"],
        "right_name": right["program"]["name"],
        "same_kind": left["program"]["kind"] == right["program"]["kind"],
        "kind": (
            left["program"]["kind"]
            if left["program"]["kind"] == right["program"]["kind"]
            else "mixed"
        ),
        "summary": {
            "changed_locations": sum(item["changed"] for item in locations),
            "unchanged_locations": sum(not item["changed"] for item in locations),
            "left_only": sum(item["left"] is not None and item["right"] is None for item in locations),
            "right_only": sum(item["left"] is None and item["right"] is not None for item in locations),
            "zone_delta": right["summary"]["zones"] - left["summary"]["zones"],
            "layer_delta": right["summary"]["layers"] - left["summary"]["layers"],
            "error_delta": right_issues.get("error", 0) - left_issues.get("error", 0),
            "warning_delta": right_issues.get("warning", 0) - left_issues.get("warning", 0),
        },
        "locations": locations,
    }


def build_view_bundle(
    programs: list[tuple[ProgramModel, Path | None]],
    devices: list[DeviceProfile],
    layouts: list[LayoutPreset] | None = None,
    groove: MidiGroove | None = None,
) -> dict[str, Any]:
    """Render every requested program/device combination into a portable bundle."""
    if not programs:
        raise ValueError("at least one program is required")
    if not devices:
        raise ValueError("at least one device profile is required")
    used_program_ids: set[str] = set()
    used_device_ids: set[str] = set()
    program_items = [
        {
            "id": _identifier(program.name, used_program_ids),
            "name": program.name,
            "kind": program.kind,
            "source_path": program.source_path,
            "model": program,
            "sample_root": sample_root,
        }
        for program, sample_root in programs
    ]
    device_items = [
        {
            "id": _identifier(device.id, used_device_ids),
            "name": device.name,
            "profile": device,
        }
        for device in devices
    ]
    views: dict[str, dict[str, dict[str, Any]]] = {}
    for program_item in program_items:
        views[program_item["id"]] = {}
        for device_item in device_items:
            views[program_item["id"]][device_item["id"]] = build_view_data(
                program_item["model"],
                device_item["profile"],
                program_item["sample_root"],
                groove,
            )
    comparisons: dict[str, dict[str, dict[str, Any]]] = {}
    for device_item in device_items:
        device_id = device_item["id"]
        comparisons[device_id] = {}
        for left in program_items:
            comparisons[device_id][left["id"]] = {}
            for right in program_items:
                if left["id"] == right["id"]:
                    continue
                comparisons[device_id][left["id"]][right["id"]] = compare_view_data(
                    views[left["id"]][device_id],
                    views[right["id"]][device_id],
                )
    return {
        "schema_version": 3,
        "read_only": True,
        "default_program": program_items[0]["id"],
        "default_device": device_items[0]["id"],
        "programs": [
            {key: item[key] for key in ("id", "name", "kind", "source_path")}
            for item in program_items
        ],
        "devices": [
            {"id": item["id"], "name": item["name"]} for item in device_items
        ],
        "layouts": [asdict(layout) for layout in (layouts or [])],
        "views": views,
        "comparisons": comparisons,
    }


HTML_TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__TITLE__ — MPC Program Designer</title>
  <style>
    :root { color-scheme: dark; --bg:#0d1014; --panel:#171b21; --panel2:#20262e; --line:#343c47; --text:#f4f6f8; --muted:#9aa5b1; --accent:#f3b33d; --danger:#ff6b6b; --warn:#f6c85f; --info:#61b8ff; }
    * { box-sizing:border-box; }
    body { margin:0; font:15px/1.45 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:radial-gradient(circle at top left,#1a2029 0,#0d1014 42rem); color:var(--text); }
    button,select { font:inherit; }
    .shell { max-width:1440px; margin:auto; padding:28px; }
    header { display:flex; justify-content:space-between; gap:24px; align-items:flex-start; margin-bottom:22px; }
    .eyebrow { color:var(--accent); text-transform:uppercase; letter-spacing:.14em; font-size:12px; font-weight:800; }
    h1 { margin:4px 0 6px; font-size:clamp(28px,4vw,48px); line-height:1.05; }
    .source { color:var(--muted); max-width:900px; overflow-wrap:anywhere; }
    .readonly { border:1px solid #725b26; background:#2b2414; color:#ffd77d; padding:7px 11px; border-radius:999px; white-space:nowrap; font-weight:700; }
    .toolbar { display:flex; flex-wrap:wrap; gap:12px; padding:14px 16px; margin-bottom:18px; align-items:end; }
    .control { display:grid; gap:5px; min-width:190px; }
    .control label { color:var(--muted); font-size:11px; font-weight:800; letter-spacing:.08em; text-transform:uppercase; }
    .control select { color:var(--text); border:1px solid var(--line); background:#11151a; border-radius:9px; padding:8px 10px; }
    .toolbar-note { color:var(--muted); margin-left:auto; padding:8px 4px; }
    .action { color:var(--text); border:1px solid var(--line); background:#11151a; border-radius:9px; padding:8px 11px; cursor:pointer; }
    .action:hover,.action:focus-visible { border-color:#687483; outline:none; }
    .action.primary { border-color:#725b26; background:#352a16; color:#ffd579; }
    .action:disabled { cursor:default; opacity:.42; }
    .chips { display:flex; flex-wrap:wrap; gap:9px; margin:0 0 22px; }
    .chip { padding:7px 10px; border:1px solid var(--line); border-radius:999px; background:#12161b; color:#dbe1e7; }
    .groove-strip { display:flex; flex-wrap:wrap; align-items:center; gap:10px; margin:-8px 0 20px; padding:11px 14px; border:1px solid #725b26; border-radius:12px; background:#2b2414; color:#f5d98b; }
    .groove-strip span { color:#d8c99f; }
    .layout { display:grid; grid-template-columns:minmax(0,1.35fr) minmax(320px,.65fr); gap:20px; align-items:start; }
    .panel { background:linear-gradient(180deg,rgba(32,38,46,.96),rgba(21,25,31,.98)); border:1px solid var(--line); border-radius:18px; box-shadow:0 18px 50px rgba(0,0,0,.26); }
    .panel-head { padding:18px 20px; border-bottom:1px solid var(--line); display:flex; align-items:center; justify-content:space-between; gap:12px; }
    .panel-head h2 { margin:0; font-size:18px; }
    .panel-body { padding:20px; }
    .banks { display:flex; flex-wrap:wrap; gap:8px; }
    .bank { min-width:42px; padding:8px 12px; border-radius:10px; border:1px solid var(--line); color:var(--text); background:#11151a; cursor:pointer; }
    .bank.active { border-color:var(--accent); background:#352a16; color:#ffd579; }
    .bank.empty { opacity:.46; }
    .pad-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; max-width:760px; margin:18px auto 8px; }
    .pad { position:relative; min-height:128px; padding:12px; border:2px solid rgba(255,255,255,.18); border-radius:14px; cursor:pointer; text-align:left; background:#303740; color:white; overflow:hidden; transition:transform .12s ease,border-color .12s ease,box-shadow .12s ease; }
    .pad:hover,.pad:focus-visible { transform:translateY(-2px); border-color:white; box-shadow:0 10px 28px rgba(0,0,0,.35); outline:none; }
    .pad.selected { border-color:var(--accent); box-shadow:0 0 0 3px rgba(243,179,61,.22); }
    .pad.empty { cursor:default; opacity:.28; background:#222830!important; }
    .pad.editable { cursor:grab; }
    .pad.editable:active { cursor:grabbing; }
    .pad.move-target { cursor:copy; outline:2px dashed var(--info); outline-offset:-7px; }
    .pad.locked { background-image:repeating-linear-gradient(135deg,transparent,transparent 12px,rgba(0,0,0,.13) 12px,rgba(0,0,0,.13) 18px)!important; }
    .pad.heated::after { content:""; position:absolute; inset:3px; border-radius:10px; pointer-events:none; box-shadow:inset 0 0 0 var(--heat-width) rgba(255,222,96,var(--heat-alpha)); }
    .pad > * { position:relative; z-index:1; }
    .pad-label { font-weight:900; letter-spacing:.06em; }
    .pad-role { display:block; margin-top:22px; font-size:13px; font-weight:750; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .pad-sample { display:block; margin-top:4px; font-size:11px; opacity:.82; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .badges { display:flex; gap:5px; position:absolute; right:8px; top:8px; }
    .badge { border-radius:999px; padding:2px 6px; font-size:10px; font-weight:850; background:rgba(0,0,0,.45); color:white; }
    .detail-empty { color:var(--muted); padding:16px 0; }
    .kv { display:grid; grid-template-columns:120px 1fr; gap:7px 14px; margin:0 0 18px; }
    .kv dt { color:var(--muted); }
    .kv dd { margin:0; overflow-wrap:anywhere; }
    .layer { padding:12px; border:1px solid var(--line); background:#12161b; border-radius:12px; margin-top:10px; }
    .layer-top { display:flex; justify-content:space-between; gap:10px; }
    .layer-sample { font-weight:750; overflow-wrap:anywhere; }
    .status { font-size:11px; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); }
    .status.found { color:#72d69b; } .status.missing,.status.ambiguous { color:var(--danger); }
    .velocity { position:relative; height:8px; margin-top:10px; background:#303741; border-radius:999px; overflow:hidden; }
    .velocity span { position:absolute; top:0; bottom:0; background:linear-gradient(90deg,#df8c2d,#f2d36c); border-radius:999px; }
    .issues { margin-top:20px; }
    .issue { border-left:4px solid var(--line); background:#12161b; padding:11px 12px; margin-top:8px; border-radius:0 10px 10px 0; }
    .issue.error { border-color:var(--danger); } .issue.warning { border-color:var(--warn); } .issue.info { border-color:var(--info); }
    .issue strong { text-transform:uppercase; font-size:11px; letter-spacing:.09em; }
    .issue p { margin:3px 0 0; color:#d8dee5; }
    .issue code { color:var(--muted); }
    .key-controls { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
    .key-controls button { color:var(--text); border:1px solid var(--line); background:#11151a; border-radius:9px; padding:7px 10px; cursor:pointer; }
    .keybed-wrap { overflow-x:auto; padding:8px 0 12px; }
    .keybed { display:grid; grid-template-columns:repeat(var(--keys),minmax(30px,1fr)); min-width:1000px; gap:3px; align-items:start; }
    .key { height:150px; border:1px solid #89929c; border-radius:0 0 7px 7px; background:#e9edf1; color:#111; padding:8px 2px; display:flex; align-items:flex-end; justify-content:center; cursor:pointer; font-size:10px; white-space:pre-line; }
    .key.black { height:98px; background:#171a1f; color:white; border-color:#050607; z-index:2; }
    .key.active { box-shadow:inset 0 -8px 0 var(--accent); }
    .key.selected { outline:3px solid var(--info); outline-offset:2px; }
    .zone-list { display:grid; gap:10px; }
    .zone-card { border:1px solid var(--line); background:#12161b; border-radius:12px; padding:12px; cursor:pointer; }
    .zone-card:hover { border-color:#687483; }
    .zone-card strong { display:block; }
    .zone-card span { color:var(--muted); }
    .editor { margin-top:20px; }
    .editor-toolbar { display:flex; flex-wrap:wrap; gap:9px; align-items:end; }
    .editor-toolbar .control { min-width:220px; }
    .editor-note { color:var(--muted); margin:12px 0 0; }
    .selection-editor { border-top:1px solid var(--line); margin-top:18px; padding-top:16px; display:grid; gap:10px; }
    .selection-editor label { color:var(--muted); font-size:12px; }
    .color-row { display:flex; gap:10px; align-items:center; }
    .color-row input { width:52px; height:34px; padding:2px; border:1px solid var(--line); border-radius:8px; background:#11151a; }
    .draft-layout { display:grid; grid-template-columns:minmax(0,1.25fr) minmax(280px,.75fr); gap:16px; margin-top:18px; }
    .draft-json { max-height:360px; overflow:auto; margin:0; padding:13px; border:1px solid var(--line); border-radius:11px; background:#0c1014; color:#b8d8c2; font:12px/1.45 ui-monospace,SFMono-Regular,Consolas,monospace; white-space:pre-wrap; overflow-wrap:anywhere; }
    .draft-grid { display:grid; gap:7px; }
    .draft-row { display:grid; grid-template-columns:62px minmax(0,1fr) minmax(0,1fr); gap:8px; }
    .draft-row.changed .compare-location { color:#ffd579; border-color:#725b26; background:#2b2414; }
    .draft-card { padding:9px 10px; border:1px solid var(--line); background:#12161b; border-radius:9px; overflow:hidden; }
    .draft-card strong,.draft-card span { display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .draft-card span { color:var(--muted); font-size:11px; }
    .comparison { margin-top:20px; }
    .comparison-summary { display:flex; flex-wrap:wrap; gap:9px; margin-bottom:16px; }
    .comparison-grid { display:grid; gap:8px; }
    .compare-row { display:grid; grid-template-columns:72px minmax(0,1fr) minmax(0,1fr); gap:9px; align-items:stretch; }
    .compare-location { display:flex; align-items:center; justify-content:center; color:var(--muted); font-weight:850; border:1px solid var(--line); border-radius:10px; background:#11151a; }
    .compare-card { padding:10px 12px; border:1px solid var(--line); background:#12161b; border-radius:10px; overflow-wrap:anywhere; }
    .compare-card strong,.compare-card span { display:block; }
    .compare-card span { color:var(--muted); font-size:12px; margin-top:2px; }
    .compare-row.changed .compare-location { color:#ffd579; border-color:#725b26; background:#2b2414; }
    .compare-fields { grid-column:2/4; color:#d8b765; font-size:11px; padding:0 4px 4px; }
    .hidden { display:none!important; }
    footer { color:var(--muted); margin:22px 2px; font-size:13px; }
    @media (max-width:900px) { .layout,.draft-layout { grid-template-columns:1fr; } .shell { padding:18px; } header { flex-direction:column; } .pad { min-height:108px; } }
    @media (max-width:520px) { .pad-grid { gap:7px; } .pad { min-height:94px; padding:8px; } .pad-role { margin-top:15px; font-size:11px; } .pad-sample { display:none; } .kv { grid-template-columns:90px 1fr; } .compare-row { grid-template-columns:55px 1fr; } .compare-card:last-of-type { grid-column:2; } .compare-fields { grid-column:2; } }
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div><div class="eyebrow">MPC Program Designer · v0.3 source-safe</div><h1 id="title"></h1><div class="source" id="source"></div></div>
      <div class="readonly">Draft only · source unchanged</div>
    </header>
    <section class="panel toolbar" aria-label="Viewer controls">
      <div class="control"><label for="program-select">Inspect source</label><select id="program-select"></select></div>
      <div class="control"><label for="device-select">Device profile</label><select id="device-select"></select></div>
      <div class="control"><label for="compare-select">Compare with</label><select id="compare-select"></select></div>
      <button class="action primary hidden" id="groove-toggle" type="button">Groove heat: on</button>
      <div class="toolbar-note" id="bundle-note"></div>
    </section>
    <div class="chips" id="chips"></div>
    <div class="groove-strip hidden" id="groove-strip"><strong id="groove-title"></strong><span id="groove-summary"></span></div>
    <div class="layout">
      <main class="panel">
        <div class="panel-head"><h2 id="surface-title">Performance surface</h2><div class="banks" id="banks"></div><div class="key-controls hidden" id="key-controls"><button id="oct-down">− octave</button><strong id="key-window"></strong><button id="oct-up">+ octave</button></div></div>
        <div class="panel-body"><div id="drum-surface"><div class="pad-grid" id="pad-grid"></div></div><div class="hidden" id="keygroup-surface"><div class="keybed-wrap"><div class="keybed" id="keybed"></div></div><div class="zone-list" id="zone-list"></div></div></div>
      </main>
      <aside>
        <section class="panel"><div class="panel-head"><h2>Selection</h2></div><div class="panel-body" id="detail"><div class="detail-empty">Select a populated pad or key.</div></div></section>
        <section class="panel issues"><div class="panel-head"><h2>Validation</h2><span id="issue-total"></span></div><div class="panel-body" id="issues"></div></section>
      </aside>
    </div>
    <section class="panel editor hidden" id="editor-panel">
      <div class="panel-head"><h2>Layout draft workspace</h2><span id="layout-status">Source view</span></div>
      <div class="panel-body">
        <div class="editor-toolbar">
          <button class="action primary" id="edit-toggle" type="button">Start layout draft</button>
          <button class="action" id="move-toggle" type="button" disabled>Move / swap selected</button>
          <button class="action" id="mirror-bank" type="button" disabled>Mirror current bank</button>
          <div class="control"><label for="layout-select">Semantic preset</label><select id="layout-select" disabled></select></div>
          <button class="action" id="apply-layout" type="button" disabled>Apply preset</button>
          <div class="control"><label for="ergonomic-select">Groove suggestion</label><select id="ergonomic-select" disabled><option value="right">Right-hand usage compact</option><option value="left">Left-hand usage compact</option></select></div>
          <button class="action" id="apply-ergonomic" type="button" disabled>Apply suggestion</button>
          <button class="action" id="undo-layout" type="button" disabled>Undo</button>
          <button class="action" id="redo-layout" type="button" disabled>Redo</button>
          <button class="action" id="reset-bank" type="button" disabled>Reset bank</button>
          <button class="action" id="reset-layout" type="button" disabled>Reset all</button>
          <button class="action primary" id="download-draft" type="button" disabled>Download draft JSON</button>
        </div>
        <p class="editor-note" id="editor-note">Start a draft to rearrange pads without changing the embedded source model.</p>
        <div class="draft-layout hidden" id="draft-layout">
          <div><h3 id="draft-title">Source ↔ draft · current bank</h3><div class="draft-grid" id="draft-grid"></div></div>
          <div><h3>Deterministic draft assignments</h3><pre class="draft-json" id="draft-json"></pre></div>
        </div>
      </div>
    </section>
    <section class="panel comparison hidden" id="comparison-panel">
      <div class="panel-head"><h2 id="comparison-title">Side-by-side comparison</h2><span id="comparison-total"></span></div>
      <div class="panel-body"><div class="comparison-summary" id="comparison-summary"></div><div class="comparison-grid" id="comparison-grid"></div></div>
    </section>
    <footer>Generated locally from the normalized Program Model. Layout edits remain an in-memory draft; no source or audio file is opened for writing.</footer>
  </div>
  <script>const BUNDLE=__DATA__;
  const $=id=>document.getElementById(id);
  const el=(tag,cls,text)=>{const node=document.createElement(tag);if(cls)node.className=cls;if(text!==undefined)node.textContent=text;return node;};
  const basename=value=>String(value||'').split(/[\\/]/).pop();
  const noteName=n=>['C','C♯','D','D♯','E','F','F♯','G','G♯','A','A♯','B'][n%12]+(Math.floor(n/12)-1);
  const isBlack=n=>[1,3,6,8,10].includes(n%12);
  const clone=value=>JSON.parse(JSON.stringify(value));
  let programId=BUNDLE.default_program,deviceId=BUNDLE.default_device,compareId=null,DATA=null;
  let selectedSlot=null,currentBank=null,keyStart=0,selectedNote=null,editMode=false,moveMode=false,draggedSlot=null,grooveHeat=true;
  const drafts=new Map();

  function currentView(){return BUNDLE.views[programId][deviceId];}
  function option(value,label){const node=el('option','',label);node.value=value;return node;}
  function addChip(text){$('chips').append(el('span','chip',text));}
  function contrast(hex){if(!hex)return '#fff';const n=parseInt(hex.slice(1),16),r=n>>16,g=n>>8&255,b=n&255;return (.299*r+.587*g+.114*b)>155?'#111':'#fff';}
  function slotLabel(slot){const per=DATA.device.pads_per_bank,bank=DATA.device.banks[Math.floor((slot-1)/per)];return `${bank}${String((slot-1)%per+1).padStart(2,'0')}`;}
  function bankOffset(bank){return DATA.device.banks.indexOf(bank)*DATA.device.pads_per_bank;}
  function sourceSlots(){const slots=Array(DATA.device.capacity).fill(null);DATA.program.zones.forEach(zone=>{if(zone.pad>=1&&zone.pad<=slots.length)slots[zone.pad-1]=clone(zone);});return slots;}
  function draftKey(){return `${programId}|${deviceId}`;}
  function currentDraft(){if(!drafts.has(draftKey())){const source=sourceSlots();drafts.set(draftKey(),{source,slots:clone(source),history:[],future:[]});}return drafts.get(draftKey());}
  function slotsForBank(bank){const all=editMode?currentDraft().slots:currentDraft().source,offset=bankOffset(bank);return all.slice(offset,offset+DATA.device.pads_per_bank);}
  function snapshot(slots){return JSON.stringify(slots);}
  function remember(draft){draft.history.push(snapshot(draft.slots));if(draft.history.length>50)draft.history.shift();draft.future=[];}
  function sameZone(left,right){return (!left&&!right)||Boolean(left&&right&&left.index===right.index&&left.color_hex===right.color_hex&&left.locked===right.locked);}
  function draftChangeCount(draft=currentDraft()){return draft.slots.reduce((count,zone,index)=>count+(sameZone(draft.source[index],zone)?0:1),0);}
  function roleMatches(role,requested){return role===requested||role.startsWith(`${requested}.`);}

  function populateControls(){
    const program=$('program-select'),device=$('device-select'),compare=$('compare-select');
    BUNDLE.programs.forEach(item=>program.append(option(item.id,`${item.name} · ${item.kind}`)));
    BUNDLE.devices.forEach(item=>device.append(option(item.id,item.name)));
    program.value=programId;device.value=deviceId;
    $('bundle-note').textContent=`Portable bundle · ${BUNDLE.programs.length} source${BUNDLE.programs.length===1?'':'s'} · ${BUNDLE.devices.length} device profile${BUNDLE.devices.length===1?'':'s'} · ${BUNDLE.layouts.length} layout${BUNDLE.layouts.length===1?'':'s'}`;
    function fillCompare(){const previous=compareId;compare.replaceChildren(option('','No comparison'));BUNDLE.programs.filter(item=>item.id!==programId).forEach(item=>compare.append(option(item.id,`${item.name} · ${item.kind}`)));compareId=previous&&previous!==programId&&BUNDLE.programs.some(item=>item.id===previous)?previous:(BUNDLE.programs.find(item=>item.id!==programId)?.id||null);compare.value=compareId||'';}
    fillCompare();
    program.addEventListener('change',()=>{programId=program.value;fillCompare();renderAll();});
    device.addEventListener('change',()=>{deviceId=device.value;renderAll();});
    compare.addEventListener('change',()=>{compareId=compare.value||null;renderComparison();});
    $('groove-toggle').addEventListener('click',()=>{grooveHeat=!grooveHeat;renderGroove();if(DATA.program.kind==='drum')renderBank(currentBank);});
  }

  function populateEditorControls(){
    const select=$('layout-select');
    if(BUNDLE.layouts.length)BUNDLE.layouts.forEach(layout=>select.append(option(layout.id,layout.name)));
    else select.append(option('','No presets bundled'));
    $('edit-toggle').addEventListener('click',()=>{editMode=!editMode;moveMode=false;selectedSlot=null;renderDrums();renderEditorWorkspace();});
    $('move-toggle').addEventListener('click',()=>{moveMode=!moveMode;$('editor-note').textContent=moveMode?'Select any unlocked destination pad, including one in another bank.':'Move / swap mode cancelled.';renderBank(currentBank);});
    $('mirror-bank').addEventListener('click',mirrorCurrentBank);
    $('apply-layout').addEventListener('click',applySelectedLayout);
    $('apply-ergonomic').addEventListener('click',applyErgonomicSuggestion);
    $('ergonomic-select').addEventListener('change',renderGroove);
    $('undo-layout').addEventListener('click',undoDraft);
    $('redo-layout').addEventListener('click',redoDraft);
    $('reset-bank').addEventListener('click',resetCurrentBank);
    $('reset-layout').addEventListener('click',resetDraft);
    $('download-draft').addEventListener('click',downloadDraft);
  }

  function renderHeader(){const p=DATA.program,s=DATA.summary;$('title').textContent=p.name||'Unnamed program';document.title=`${p.name||'Unnamed program'} — MPC Program Designer`;$('source').textContent=`${p.kind} · ${p.source_format} · ${p.source_path||'in-memory source'}`;$('chips').replaceChildren();addChip(`${s.zones} zones`);addChip(`${s.layers} layers`);addChip(DATA.device.name);if(p.kind==='drum')addChip(`${s.populated_banks.length}/${DATA.device.banks.length} populated banks`);if(DATA.groove)addChip(`${DATA.groove.mapped_events}/${DATA.groove.note_events} groove hits mapped`);Object.entries(s.issues).forEach(([kind,count])=>addChip(`${count} ${kind}${count===1?'':'s'}`));renderGroove();}
  function renderGroove(){const available=Boolean(DATA?.groove),toggle=$('groove-toggle'),strip=$('groove-strip');toggle.classList.toggle('hidden',!available);strip.classList.toggle('hidden',!available);if(!available)return;toggle.textContent=`Groove heat: ${grooveHeat?'on':'off'}`;const g=DATA.groove,select=$('ergonomic-select');Array.from(select.options).forEach(option=>{const suggestion=g.suggestions?.[option.value];if(suggestion)option.textContent=`${suggestion.name} · ${suggestion.reach_improvement_percent}% · ${suggestion.moved_assignments} moves`;});const suggestion=g.suggestions?.[select.value];$('groove-title').textContent=`${g.sources.length} MIDI groove${g.sources.length===1?'':'s'}`;$('groove-summary').textContent=`${g.note_events} note-ons · ${g.mapped_events} mapped · ${g.active_zones} active sounds · ${g.unmapped_events} unmapped${suggestion?` · selected model ${suggestion.reach_improvement_percent}% / ${suggestion.moved_assignments} moves`:''}`;}
  function renderIssues(){const box=$('issues');box.replaceChildren();$('issue-total').textContent=DATA.issues.length?`${DATA.issues.length} findings`:'clear';if(!DATA.issues.length){box.append(el('div','detail-empty','No model, sample, velocity, or mute-group findings.'));return;}DATA.issues.forEach(issue=>{const card=el('div',`issue ${issue.severity}`);card.append(el('strong','',`${issue.severity} · ${issue.code}`));card.append(el('p','',`${issue.zone?`Zone ${issue.zone}: `:''}${issue.message}`));box.append(card);});}
  function layerNode(layer){const card=el('div','layer'),top=el('div','layer-top');top.append(el('span','layer-sample',basename(layer.sample)));top.append(el('span',`status ${layer.sample_status}`,layer.sample_status));card.append(top);card.append(el('div','source',`Velocity ${layer.velocity_start}–${layer.velocity_end}${layer.root_note!==null?` · root MIDI ${layer.root_note}`:''}${layer.loop_enabled?' · loop':''}`));const velocity=el('div','velocity'),fill=el('span');fill.style.left=`${layer.velocity_start/128*100}%`;fill.style.width=`${(layer.velocity_end-layer.velocity_start+1)/128*100}%`;velocity.append(fill);card.append(velocity);return card;}

  function renderZone(zone,label,slot=null){
    const box=$('detail');box.replaceChildren();
    if(!zone){box.append(el('div','detail-empty',`${label} is empty.${editMode?' Use Move / swap to place a sound here.':''}`));return;}
    const rows=[['Location',label],['Role',zone.role]];
    if(zone.low_note!==null&&zone.high_note!==null)rows.push(['Key range',`${noteName(zone.low_note)}–${noteName(zone.high_note)} · MIDI ${zone.low_note}–${zone.high_note}`]);
    if(zone.midi_note!==null)rows.push(['MIDI note',`${zone.midi_note} (${noteName(zone.midi_note)})`]);
    if(zone.groove)rows.push(['Groove hits',zone.groove.hits],['Average velocity',zone.groove.average_velocity],['Groove share',`${(zone.groove.share*100).toFixed(1)}%`]);
    rows.push(['Playback',zone.playback_mode],['Mute group',zone.mute_group||'none'],['Polyphony',zone.polyphony],['Monophonic',zone.monophonic?'yes':'no'],['Color',zone.color_hex||'not declared'],['Locked',zone.locked?'yes':'no']);
    const dl=el('dl','kv');rows.forEach(([key,value])=>{dl.append(el('dt','',key));dl.append(el('dd','',String(value)));});box.append(dl);
    box.append(el('h3','',`Layers · ${zone.layers.length}`));zone.layers.forEach(layer=>box.append(layerNode(layer)));
    if(editMode&&slot){
      const editor=el('div','selection-editor'),row=el('div','color-row'),input=el('input');input.type='color';input.value=zone.color_hex||'#39424D';
      row.append(el('label','',`Draft pad color`));row.append(input);editor.append(row);
      const lock=el('button','action',zone.locked?'Unlock position':'Lock position');lock.type='button';editor.append(lock);
      input.addEventListener('change',()=>{const draft=currentDraft();remember(draft);draft.slots[slot-1].color_hex=input.value.toUpperCase();draft.slots[slot-1].color=parseInt(input.value.slice(1),16);renderBank(currentBank);});
      lock.addEventListener('click',()=>{const draft=currentDraft();remember(draft);draft.slots[slot-1].locked=!draft.slots[slot-1].locked;renderBank(currentBank);});
      box.append(editor);
    }
  }

  function selectDraftSlot(slot,zone){selectedSlot=slot;document.querySelectorAll('.pad').forEach(node=>node.classList.toggle('selected',Number(node.dataset.slot)===slot));renderZone(zone,slotLabel(slot),slot);renderEditorWorkspace();}
  function moveSlot(from,to){const draft=currentDraft(),source=draft.slots[from-1],target=draft.slots[to-1];if(!source||source.locked||target?.locked){$('editor-note').textContent='Locked pads cannot be moved or replaced.';return;}remember(draft);[draft.slots[from-1],draft.slots[to-1]]=[target,source];selectedSlot=to;moveMode=false;$('editor-note').textContent=`Moved ${source.role} from ${slotLabel(from)} to ${slotLabel(to)}${target?' and swapped the destination':''}.`;renderDrums();}

  function renderBank(bank){
    currentBank=bank;document.querySelectorAll('.bank').forEach(node=>node.classList.toggle('active',node.dataset.bank===bank));
    const grid=$('pad-grid');grid.replaceChildren();const slots=slotsForBank(bank),cols=DATA.device.pad_columns,rows=DATA.device.pad_rows,offset=bankOffset(bank);
    for(let row=rows-1;row>=0;row--){for(let col=0;col<cols;col++){
      const position=row*cols+col,slot=offset+position+1,zone=slots[position],label=slotLabel(slot),classes=`pad${zone?'':' empty'}${editMode?' editable':''}${moveMode?' move-target':''}${zone?.locked?' locked':''}`;
      const button=el('button',classes);button.type='button';button.dataset.label=label;button.dataset.slot=String(slot);button.append(el('span','pad-label',label));
      if(zone){button.style.background=zone.color_hex||'#39424d';button.style.color=contrast(zone.color_hex);const badges=el('span','badges');if(zone.layers.length>1)badges.append(el('span','badge',`${zone.layers.length}L`));if(zone.mute_group)badges.append(el('span','badge',`M${zone.mute_group}`));if(zone.locked)badges.append(el('span','badge','LOCK'));if(grooveHeat&&zone.groove){button.classList.add('heated');button.style.setProperty('--heat-width',`${2+Math.round(zone.groove.intensity*7)}px`);button.style.setProperty('--heat-alpha',String(.35+zone.groove.intensity*.55));badges.append(el('span','badge',`${zone.groove.hits}×`));}button.append(badges);button.append(el('span','pad-role',zone.role));button.append(el('span','pad-sample',basename(zone.layers[0]?.sample)));}
      else button.append(el('span','pad-role','Empty'));
      if(!editMode&&!zone)button.disabled=true;
      button.draggable=Boolean(editMode&&zone&&!zone.locked);
      button.addEventListener('click',()=>{if(editMode&&moveMode&&selectedSlot&&slot!==selectedSlot){moveSlot(selectedSlot,slot);return;}selectDraftSlot(slot,zone);});
      button.addEventListener('dragstart',event=>{draggedSlot=slot;event.dataTransfer.effectAllowed='move';event.dataTransfer.setData('text/plain',String(slot));});
      button.addEventListener('dragover',event=>{if(editMode&&!zone?.locked&&draggedSlot)event.preventDefault();});
      button.addEventListener('drop',event=>{event.preventDefault();const source=draggedSlot||Number(event.dataTransfer.getData('text/plain'));if(source&&source!==slot)moveSlot(source,slot);draggedSlot=null;});
      button.addEventListener('dragend',()=>{draggedSlot=null;});
      if(slot===selectedSlot)button.classList.add('selected');grid.append(button);
    }}
    const selected=grid.querySelector(`[data-slot="${selectedSlot}"]`),first=grid.querySelector('.pad:not(.empty)');
    if(selected){const slot=Number(selected.dataset.slot),zone=(editMode?currentDraft().slots:currentDraft().source)[slot-1];renderZone(zone,slotLabel(slot),slot);}
    else if(first&&!moveMode){first.click();}
    renderEditorWorkspace();renderComparison();
  }

  function renderDrums(){
    $('editor-panel').classList.remove('hidden');$('banks').replaceChildren();
    DATA.device.banks.forEach(bank=>{const populated=slotsForBank(bank).some(Boolean),button=el('button',`bank${populated?'':' empty'}`,bank);button.type='button';button.dataset.bank=bank;button.disabled=!populated&&!editMode;button.addEventListener('click',()=>renderBank(bank));$('banks').append(button);});
    const requested=currentBank&&DATA.device.banks.includes(currentBank)?currentBank:(DATA.summary.populated_banks[0]||DATA.device.banks[0]);renderBank(requested);
  }

  function mirrorCurrentBank(){const draft=currentDraft(),offset=bankOffset(currentBank),cols=DATA.device.pad_columns,rows=DATA.device.pad_rows;remember(draft);let swaps=0;for(let row=0;row<rows;row++){for(let col=0;col<Math.floor(cols/2);col++){const left=offset+row*cols+col,right=offset+row*cols+(cols-1-col);if(draft.slots[left]?.locked||draft.slots[right]?.locked)continue;[draft.slots[left],draft.slots[right]]=[draft.slots[right],draft.slots[left]];swaps++;}}$('editor-note').textContent=`Mirrored Bank ${currentBank}; ${swaps} unlocked pad pairs swapped.`;selectedSlot=null;renderDrums();}
  function applySelectedLayout(){const preset=BUNDLE.layouts.find(item=>item.id===$('layout-select').value);if(!preset)return;const draft=currentDraft(),currentByIndex=new Map(draft.slots.filter(Boolean).map(zone=>[zone.index,zone])),ordered=DATA.program.zones.map(zone=>currentByIndex.get(zone.index)).filter(Boolean),result=Array(DATA.device.capacity).fill(null),remaining=[];ordered.forEach(zone=>{const current=draft.slots.indexOf(zone);if(zone.locked&&current>=0)result[current]=zone;else remaining.push(zone);});if(preset.strategy==='sequential'){remaining.slice().forEach(zone=>{const preferred=zone.pad>=1&&zone.pad<=result.length&&result[zone.pad-1]===null?zone.pad-1:result.findIndex(value=>value===null);if(preferred>=0){result[preferred]=zone;remaining.splice(remaining.indexOf(zone),1);}});}else{preset.role_order.forEach((requested,index)=>{if(index>=result.length||result[index])return;const found=remaining.findIndex(zone=>roleMatches(zone.role,requested));if(found>=0)result[index]=remaining.splice(found,1)[0];});if(preset.fill_remaining)result.forEach((value,index)=>{if(value===null&&remaining.length)result[index]=remaining.shift();});}remember(draft);draft.slots=result;$('editor-note').textContent=`Applied ${preset.name}; locked positions were preserved.`;selectedSlot=null;renderDrums();}
  function applyErgonomicSuggestion(){const suggestion=DATA.groove?.suggestions?.[$('ergonomic-select').value];if(!suggestion)return;const draft=currentDraft(),currentByIndex=new Map(draft.slots.filter(Boolean).map(zone=>[zone.index,zone])),result=Array(DATA.device.capacity).fill(null),remaining=[];draft.slots.forEach((zone,index)=>{if(zone?.locked)result[index]=zone;});suggestion.assignments.forEach(item=>{const zone=currentByIndex.get(item.source_zone);if(!zone||zone.locked)return;if(!result[item.slot-1])result[item.slot-1]=zone;else remaining.push(zone);});draft.slots.filter(zone=>zone&&!zone.locked&&!result.includes(zone)&&!remaining.includes(zone)).forEach(zone=>remaining.push(zone));result.forEach((zone,index)=>{if(!zone&&remaining.length)result[index]=remaining.shift();});remember(draft);draft.slots=result;$('editor-note').textContent=`Applied ${suggestion.name}: ${suggestion.reach_improvement_percent}% modeled reach improvement. Current draft locks were preserved.`;selectedSlot=null;renderDrums();}
  function undoDraft(){const draft=currentDraft();if(!draft.history.length)return;draft.future.push(snapshot(draft.slots));draft.slots=JSON.parse(draft.history.pop());selectedSlot=null;$('editor-note').textContent='Undid the last draft change.';renderDrums();}
  function redoDraft(){const draft=currentDraft();if(!draft.future.length)return;draft.history.push(snapshot(draft.slots));draft.slots=JSON.parse(draft.future.pop());selectedSlot=null;$('editor-note').textContent='Redid the draft change.';renderDrums();}
  function resetCurrentBank(){const draft=currentDraft(),offset=bankOffset(currentBank),count=DATA.device.pads_per_bank;remember(draft);draft.slots.splice(offset,count,...clone(draft.source.slice(offset,offset+count)));selectedSlot=null;$('editor-note').textContent=`Reset Bank ${currentBank} to the source layout.`;renderDrums();}
  function resetDraft(){const draft=currentDraft();remember(draft);draft.slots=clone(draft.source);selectedSlot=null;$('editor-note').textContent='Reset the entire draft to the source layout.';renderDrums();}

  function draftPayload(){const draft=currentDraft(),sourceByZone=new Map(draft.source.filter(Boolean).map(zone=>[zone.index,zone]));return {schema_version:1,kind:'__DRAFT_KIND__',program:DATA.program.name,device:DATA.device.id,source_path:DATA.program.source_path,source_format:DATA.program.source_format,source_sha256:DATA.program.source_sha256,source_model_sha256:DATA.program.source_model_sha256,assignments:draft.slots.map((zone,index)=>{if(!zone)return null;const source=sourceByZone.get(zone.index);return {slot:index+1,label:slotLabel(index+1),source_zone:zone.index,source_pad:source.pad,role:source.role,source_color:source.color,color:zone.color,source_locked:Boolean(source.locked),locked:Boolean(zone.locked),playback_mode:source.playback_mode,mute_group:source.mute_group,layers:source.layers.map(layer=>({sample:layer.sample,velocity_start:layer.velocity_start,velocity_end:layer.velocity_end,root_note:layer.root_note,sample_start:layer.sample_start,sample_end:layer.sample_end,loop_enabled:layer.loop_enabled,loop_start:layer.loop_start,loop_end:layer.loop_end}))};}).filter(Boolean)};}
  function draftFilename(){const slug=String(DATA.program.name||'mpc-program').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')||'mpc-program';return `${slug}-${DATA.device.id}-layout-draft.json`;}
  function downloadDraft(){const payload=JSON.stringify(draftPayload(),null,2)+'\n',blob=new Blob([payload],{type:'application/json'}),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=draftFilename();document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),0);$('editor-note').textContent=`Downloaded ${link.download}. Validate it with mpc-layout-draft before exporting.`;}
  function draftCard(zone){if(!zone)return el('div','draft-card detail-empty','Empty');const card=el('div','draft-card');card.append(el('strong','',zone.role));card.append(el('span','',`${basename(zone.layers[0]?.sample)}${zone.locked?' · locked':''}`));return card;}
  function renderEditorWorkspace(){
    if(DATA.program.kind!=='drum'){$('editor-panel').classList.add('hidden');return;}
    const draft=currentDraft(),changes=draftChangeCount(draft),active=editMode;
    $('editor-panel').classList.remove('hidden');$('edit-toggle').textContent=active?'View source':changes?'Resume layout draft':'Edit layout draft';$('layout-status').textContent=active?`${changes} changed slot${changes===1?'':'s'}`:changes?`Source view · ${changes} draft change${changes===1?'':'s'} retained`:'Source view';
    ['move-toggle','mirror-bank','layout-select','apply-layout','reset-bank','reset-layout','download-draft'].forEach(id=>$(id).disabled=!active);
    $('ergonomic-select').disabled=!active||!DATA.groove||!DATA.groove.active_zones;$('apply-ergonomic').disabled=$('ergonomic-select').disabled;
    $('move-toggle').disabled=!active||!selectedSlot||!draft.slots[selectedSlot-1]||draft.slots[selectedSlot-1].locked;$('move-toggle').textContent=moveMode?'Cancel move':'Move / swap selected';
    $('undo-layout').disabled=!active||!draft.history.length;$('redo-layout').disabled=!active||!draft.future.length;$('apply-layout').disabled=!active||!BUNDLE.layouts.length;
    $('draft-layout').classList.toggle('hidden',!active);if(!active){$('editor-note').textContent=changes?`${changes} draft change${changes===1?' is':'s are'} retained in this page; resume editing to inspect them.`:'Start a draft to rearrange pads without changing the embedded source model.';return;}
    $('draft-title').textContent=`Source ↔ draft · Bank ${currentBank} · ${changes} changed overall`;
    const grid=$('draft-grid');grid.replaceChildren();const offset=bankOffset(currentBank);
    for(let index=0;index<DATA.device.pads_per_bank;index++){const source=draft.source[offset+index],candidate=draft.slots[offset+index],changed=!sameZone(source,candidate),row=el('div',`draft-row${changed?' changed':''}`);row.append(el('div','compare-location',slotLabel(offset+index+1)));row.append(draftCard(source));row.append(draftCard(candidate));grid.append(row);}
    $('draft-json').textContent=JSON.stringify(draftPayload(),null,2);
  }

  function activeZones(note){return DATA.program.zones.filter(zone=>zone.low_note!==null&&zone.high_note!==null&&zone.low_note<=note&&note<=zone.high_note);}
  function renderNote(note){selectedNote=note;document.querySelectorAll('.key').forEach(node=>node.classList.toggle('selected',Number(node.dataset.note)===note));const zones=activeZones(note);if(!zones.length){$('detail').replaceChildren(el('div','detail-empty',`${noteName(note)} · MIDI ${note} has no mapped zone.`));return;}renderZone(zones[0],`${noteName(note)} · MIDI ${note}`);}
  function renderKeybed(){const bed=$('keybed');bed.replaceChildren();if(DATA.keyboard.keys<1){$('key-window').textContent='No physical keys in this device profile';return;}bed.style.setProperty('--keys',DATA.keyboard.keys);$('key-window').textContent=`${noteName(keyStart)}–${noteName(keyStart+DATA.keyboard.keys-1)} · MIDI ${keyStart}–${keyStart+DATA.keyboard.keys-1}`;for(let note=keyStart;note<keyStart+DATA.keyboard.keys;note++){const zones=activeZones(note),key=el('button',`key ${isBlack(note)?'black':'white'}${zones.length?' active':''}`,`${noteName(note)}\n${note}`);key.type='button';key.dataset.note=String(note);key.title=zones.length?zones.map(zone=>`${zone.index}: ${basename(zone.layers[0]?.sample)}`).join('\n'):'Unmapped';key.addEventListener('click',()=>renderNote(note));bed.append(key);}if(selectedNote===null||selectedNote<keyStart||selectedNote>=keyStart+DATA.keyboard.keys)renderNote(keyStart+Math.floor(DATA.keyboard.keys/2));else renderNote(selectedNote);}
  function renderKeygroups(){$('editor-panel').classList.add('hidden');$('drum-surface').classList.add('hidden');$('keygroup-surface').classList.remove('hidden');$('banks').classList.add('hidden');$('key-controls').classList.remove('hidden');$('surface-title').textContent=`${DATA.keyboard.keys}-note keybed viewport`;$('oct-down').onclick=()=>{keyStart=Math.max(DATA.keyboard.minimum,keyStart-12);renderKeybed();};$('oct-up').onclick=()=>{keyStart=Math.min(DATA.keyboard.maximum_start,keyStart+12);renderKeybed();};const list=$('zone-list');list.replaceChildren();DATA.program.zones.forEach(zone=>{const card=el('button','zone-card');card.type='button';card.append(el('strong','',`Zone ${zone.index} · MIDI ${zone.low_note}–${zone.high_note}`));card.append(el('span','',`${zone.layers.length} layer${zone.layers.length===1?'':'s'} · ${basename(zone.layers[0]?.sample)}`));card.addEventListener('click',()=>renderZone(zone,`Zone ${zone.index} · MIDI ${zone.low_note}–${zone.high_note}`));list.append(card);});renderKeybed();}

  function compareCard(zone,emptyLabel){if(!zone)return el('div','compare-card detail-empty',emptyLabel);const card=el('div','compare-card');card.append(el('strong','',zone.role));card.append(el('span','',`${zone.layers.length} layer${zone.layers.length===1?'':'s'} · ${basename(zone.layers[0]?.sample)}`));return card;}
  function signed(value){return value>0?`+${value}`:String(value);}
  function renderComparison(){const panel=$('comparison-panel');if(!compareId){panel.classList.add('hidden');return;}const comparison=BUNDLE.comparisons[deviceId]?.[programId]?.[compareId];if(!comparison){panel.classList.add('hidden');return;}panel.classList.remove('hidden');$('comparison-title').textContent=`${comparison.left_name} ↔ ${comparison.right_name}`;const summary=comparison.summary,summaryBox=$('comparison-summary');summaryBox.replaceChildren();[`Zones ${signed(summary.zone_delta)}`,`Layers ${signed(summary.layer_delta)}`,`Errors ${signed(summary.error_delta)}`,`Warnings ${signed(summary.warning_delta)}`,`${summary.left_only} left only`,`${summary.right_only} right only`].forEach(text=>summaryBox.append(el('span','chip',text)));const grid=$('comparison-grid');grid.replaceChildren();let rows=comparison.locations;if(comparison.kind==='drum'&&currentBank)rows=rows.filter(item=>item.location.startsWith(currentBank));const changed=rows.filter(item=>item.changed).length,unchanged=rows.length-changed;$('comparison-total').textContent=comparison.kind==='drum'&&currentBank?`${changed} changed in Bank ${currentBank} · ${unchanged} unchanged · ${summary.changed_locations} changed overall`:`${changed} changed · ${unchanged} unchanged`;if(!rows.length){grid.append(el('div','detail-empty','No comparable locations in the current bank.'));return;}rows.forEach(item=>{const row=el('div',`compare-row${item.changed?' changed':''}`);row.append(el('div','compare-location',item.location));row.append(compareCard(item.left,'Empty'));row.append(compareCard(item.right,'Empty'));if(item.changed_fields.length)row.append(el('div','compare-fields',`Changed: ${item.changed_fields.join(', ')}`));grid.append(row);});}

  function renderAll(){DATA=currentView();selectedSlot=null;selectedNote=null;currentBank=null;keyStart=DATA.keyboard.default_start;editMode=false;moveMode=false;$('detail').replaceChildren(el('div','detail-empty','Select a populated pad or key.'));$('drum-surface').classList.remove('hidden');$('keygroup-surface').classList.add('hidden');$('banks').classList.remove('hidden');$('key-controls').classList.add('hidden');$('surface-title').textContent='Performance surface';renderHeader();renderIssues();if(DATA.program.kind==='drum')renderDrums();else renderKeygroups();renderComparison();}
  populateControls();populateEditorControls();renderAll();
  </script>
</body>
</html>
'''


def render_html(data: dict[str, Any]) -> str:
    if "views" not in data:
        device_id = str(data["device"]["id"])
        data = {
            "schema_version": 3,
            "read_only": True,
            "default_program": "program",
            "default_device": device_id,
            "programs": [
                {
                    "id": "program",
                    "name": data["program"]["name"],
                    "kind": data["program"]["kind"],
                    "source_path": data["program"]["source_path"],
                }
            ],
            "devices": [{"id": device_id, "name": data["device"]["name"]}],
            "layouts": [],
            "views": {"program": {device_id: data}},
            "comparisons": {device_id: {"program": {}}},
        }
    first_view = data["views"][data["default_program"]][data["default_device"]]
    title = html.escape(
        str(first_view["program"]["name"] or "Unnamed program"), quote=True
    )
    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    payload = payload.replace("&", "\\u0026").replace("<", "\\u003C").replace(">", "\\u003E")
    return (
        HTML_TEMPLATE.replace("__TITLE__", title)
        .replace("__DATA__", payload)
        .replace("__DRAFT_KIND__", DRAFT_KIND)
    )


def load_program(
    source: Path,
    source_type: str = "auto",
    source_root: Path | None = None,
    roles: Path | None = None,
) -> ProgramModel:
    resolved_type = source_type
    if resolved_type == "auto":
        resolved_type = "manifest" if source.suffix.casefold() == ".toml" else "xpm"
    overrides = load_role_overrides(roles) if roles else None
    return (
        from_drum_manifest(source, source_root, overrides)
        if resolved_type == "manifest"
        else from_xpm(source, overrides)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument(
        "--compare",
        action="append",
        default=[],
        type=Path,
        metavar="SOURCE",
        help="additional XPM or manifest to bundle and compare; repeatable",
    )
    parser.add_argument("--source-type", choices=("auto", "xpm", "manifest"), default="auto")
    parser.add_argument("--source-root", type=Path, help="optional WAV root for manifest validation")
    parser.add_argument(
        "--compare-source-root",
        action="append",
        default=[],
        type=Path,
        metavar="PATH",
        help="WAV root for the corresponding --compare source; repeatable",
    )
    parser.add_argument("--roles", type=Path, help="TOML file with explicit [roles] overrides")
    parser.add_argument(
        "--layout",
        action="append",
        default=[],
        type=Path,
        metavar="PRESET",
        help="layout preset available to the browser draft editor; repeatable",
    )
    parser.add_argument(
        "--groove",
        action="append",
        default=[],
        type=Path,
        metavar="MIDI",
        help="Standard MIDI groove used for heat maps and suggestions; repeatable",
    )
    parser.add_argument(
        "--device",
        action="append",
        default=[],
        metavar="KEY37|KEY61|TOML",
        help="built-in key37/key61 or a device TOML; repeatable (default: key37)",
    )
    parser.add_argument("--format", choices=("html", "json"), default="html")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true", help="replace an existing viewer output")
    args = parser.parse_args()
    source = args.source.expanduser().resolve()
    compare_sources = [path.expanduser().resolve() for path in args.compare]
    groove_paths = [path.expanduser().resolve() for path in args.groove]
    source_root = args.source_root.expanduser().resolve() if args.source_root else None
    compare_roots = [path.expanduser().resolve() for path in args.compare_source_root]
    roles = args.roles.expanduser().resolve() if args.roles else None
    output = args.output.expanduser().resolve()
    if len(compare_roots) > len(compare_sources):
        parser.error("--compare-source-root requires a corresponding --compare source")
    if output in {source, *compare_sources, *groove_paths}:
        parser.error("viewer output cannot replace a source program or MIDI groove")
    if output.exists() and not args.force:
        parser.error(f"viewer output exists; use --force to replace it: {output}")
    program = load_program(source, args.source_type, source_root, roles)
    programs = [(program, infer_sample_root(program, source_root))]
    for index, compare_source in enumerate(compare_sources):
        compare_root = compare_roots[index] if index < len(compare_roots) else None
        compare_program = load_program(compare_source, "auto", compare_root, roles)
        programs.append(
            (compare_program, infer_sample_root(compare_program, compare_root))
        )
    devices = [resolve_device(value) for value in args.device] or [BUILTIN_DEVICES["key37"]]
    layouts = [load_preset(path.expanduser().resolve()) for path in args.layout]
    groove = (
        load_groove(groove_paths)
        if groove_paths
        else None
    )
    data = build_view_bundle(programs, devices, layouts, groove)
    rendered = json.dumps(data, indent=2) + "\n" if args.format == "json" else render_html(data)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    view_list = [view for device_views in data["views"].values() for view in device_views.values()]
    error_count = sum(view["summary"]["issues"].get("error", 0) for view in view_list)
    print(f"Wrote: {output}")
    print(
        f"Programs: {len(programs)}; devices={len(devices)}; layouts={len(layouts)}; "
        f"grooves={len(args.groove)}; "
        f"comparisons={len(programs) * max(0, len(programs) - 1) * len(devices)}"
    )
    return 2 if error_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
