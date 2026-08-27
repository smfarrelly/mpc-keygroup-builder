"""Read-only Ableton ADG/ALS intent inventory for MPC translation planning."""

from __future__ import annotations

import argparse
import concurrent.futures
import gzip
import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


ABLETON_SUFFIXES = {".adg", ".als"}
BRANCH_TAGS = {
    "InstrumentBranchPreset",
    "DrumBranchPreset",
    "AudioEffectBranchPreset",
    "MidiEffectBranchPreset",
}


def local_tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def value(element: ET.Element | None, default=None):
    if element is None:
        return default
    raw = element.get("Value")
    if raw is None:
        return default
    if raw.casefold() in {"true", "false"}:
        return raw.casefold() == "true"
    try:
        return int(raw)
    except ValueError:
        try:
            return float(raw)
        except ValueError:
            return raw


def child(element: ET.Element, name: str) -> ET.Element | None:
    return next((item for item in element if local_tag(item) == name), None)


def descendant(element: ET.Element, name: str) -> ET.Element | None:
    return next((item for item in element.iter() if local_tag(item) == name), None)


def _parse(path: Path) -> ET.Element:
    if path.name.startswith("._") or "__MACOSX" in path.parts:
        raise ValueError(f"macOS metadata is not an Ableton preset: {path}")
    if path.suffix.casefold() not in ABLETON_SUFFIXES:
        raise ValueError(f"expected an .adg or .als file: {path}")
    try:
        with path.open("rb") as stream:
            magic = stream.read(2)
        if magic != b"\x1f\x8b":
            with path.open("rb") as stream:
                return ET.parse(stream).getroot()
        with gzip.open(path, "rb") as stream:
            return ET.parse(stream).getroot()
    except (EOFError, OSError, ET.ParseError) as error:
        raise ValueError(f"unreadable Ableton XML {path}: {error}") from error


def _range(part: ET.Element, name: str) -> dict[str, object] | None:
    element = child(part, name)
    if element is None:
        return None
    result = {}
    for field in ("Min", "Max", "CrossfadeMin", "CrossfadeMax"):
        current = child(element, field)
        if current is not None:
            result[field.casefold()] = value(current)
    return result or None


def _loop(part: ET.Element, name: str) -> dict[str, object] | None:
    element = child(part, name)
    if element is None:
        return None
    result = {}
    for field in ("Mode", "Start", "End", "Crossfade", "Link"):
        current = child(element, field)
        if current is not None:
            result[field.casefold()] = value(current)
    return result or None


def _file_reference(sample_ref: ET.Element) -> dict[str, object]:
    file_ref = descendant(sample_ref, "FileRef")
    if file_ref is None:
        return {"name": None, "relative_path": None}
    name = value(child(file_ref, "Name"))
    relative = child(file_ref, "RelativePath")
    parts = []
    if relative is not None:
        parts = [
            item.get("Dir", "")
            for item in relative
            if local_tag(item) == "RelativePathElement" and item.get("Dir")
        ]
    if name:
        parts.append(str(name))
    return {
        "name": name,
        "relative_path": "/".join(parts) if parts else name,
        "file_size": value(descendant(file_ref, "FileSize")),
        "crc": value(descendant(file_ref, "Crc")),
    }


def _zone(part: ET.Element) -> dict[str, object]:
    sample_ref = child(part, "SampleRef")
    if sample_ref is None:
        sample_ref = descendant(part, "SampleRef")
    result: dict[str, object] = {
        "name": value(child(part, "Name")),
        "sample": _file_reference(sample_ref) if sample_ref is not None else None,
        "key_range": _range(part, "KeyRange"),
        "velocity_range": _range(part, "VelocityRange"),
    }
    for field in (
        "RootKey",
        "Detune",
        "Volume",
        "Panorama",
        "SampleStart",
        "SampleEnd",
        "IsActive",
    ):
        current = child(part, field)
        if current is not None:
            result[field.casefold()] = value(current)
    result["sustain_loop"] = _loop(part, "SustainLoop")
    result["release_loop"] = _loop(part, "ReleaseLoop")
    warp = descendant(part, "IsWarped")
    result["warped"] = value(warp) if warp is not None else None
    return result


def _devices(root: ET.Element) -> list[dict[str, object]]:
    devices = []
    seen: set[int] = set()

    def append(actual: ET.Element) -> None:
        identity = id(actual)
        if identity in seen:
            return
        seen.add(identity)
        user_name = descendant(actual, "UserName")
        devices.append(
            {
                "type": local_tag(actual),
                "name": value(user_name) if user_name is not None else None,
            }
        )

    for wrapper in (item for item in root.iter() if local_tag(item) == "Device"):
        actual = next((item for item in wrapper if isinstance(item.tag, str)), None)
        if actual is None:
            continue
        append(actual)
    for container in (item for item in root.iter() if local_tag(item) == "Devices"):
        for actual in container:
            if isinstance(actual.tag, str):
                append(actual)
    return devices


def _macros(root: ET.Element) -> list[dict[str, object]]:
    macros = []
    for element in root.iter():
        tag = local_tag(element)
        if not tag.startswith("MacroDisplayNames."):
            continue
        try:
            index = int(tag.rsplit(".", 1)[1])
        except ValueError:
            continue
        name = value(element)
        if name and str(name).casefold() != f"macro {index + 1}".casefold():
            macros.append({"index": index + 1, "name": name})
    unique = {(item["index"], str(item["name"])): item for item in macros}
    return [unique[key] for key in sorted(unique)]


def _branches(root: ET.Element) -> list[dict[str, object]]:
    branches = []
    for element in root.iter():
        tag = local_tag(element)
        if tag not in BRANCH_TAGS:
            continue
        branches.append({"type": tag, "name": value(child(element, "Name"))})
    return branches


def _fidelity(
    zones: list[dict[str, object]],
    devices: list[dict[str, object]],
    branches: list[dict[str, object]],
    macros: list[dict[str, object]],
) -> dict[str, object]:
    types = {str(item["type"]) for item in devices}
    branch_types = Counter(str(item["type"]) for item in branches)
    if "PluginDevice" in types:
        return {
            "grade": "D",
            "label": "reference-only",
            "reason": "contains a plug-in device whose sound cannot be reconstructed from preset XML alone",
        }
    if (
        branch_types["DrumBranchPreset"]
        or branch_types["MidiEffectBranchPreset"]
        or branch_types["InstrumentBranchPreset"] > 1
    ):
        return {
            "grade": "C",
            "label": "template",
            "reason": "uses multiple or Drum Rack branches that likely require MPC tracks, pads, or routing",
        }
    if zones and (len(devices) > 2 or macros):
        return {
            "grade": "B",
            "label": "close",
            "reason": "sample mapping is readable but rack macros or additional devices need MPC-native substitutions",
        }
    if zones:
        return {
            "grade": "A",
            "label": "direct",
            "reason": "sample zones are readable and no multi-branch or plug-in dependency was detected",
        }
    return {
        "grade": "D",
        "label": "reference-only",
        "reason": "no directly translatable sample zones were detected",
    }


def inspect(path: Path) -> dict[str, object]:
    path = path.expanduser().resolve()
    root = _parse(path)
    if local_tag(root) != "Ableton":
        raise ValueError(f"XML root is not Ableton: {path}")
    zones = [_zone(item) for item in root.iter() if local_tag(item) == "MultiSamplePart"]
    devices = _devices(root)
    branches = _branches(root)
    macros = _macros(root)
    sample_names = sorted(
        {
            str(sample["name"])
            for zone in zones
            if isinstance(zone.get("sample"), dict)
            and (sample := zone["sample"]).get("name")
        }
    )
    warped = Counter(str(zone["warped"]).casefold() for zone in zones if zone["warped"] is not None)
    return {
        "format": 1,
        "path": str(path),
        "kind": path.suffix.casefold().lstrip("."),
        "ableton": {
            "major_version": root.get("MajorVersion"),
            "minor_version": root.get("MinorVersion"),
            "creator": root.get("Creator"),
            "revision": root.get("Revision"),
        },
        "name": next(
            (
                value(item)
                for item in root.iter()
                if local_tag(item) == "UserName" and value(item)
            ),
            path.stem,
        ),
        "devices": devices,
        "device_types": dict(sorted(Counter(str(item["type"]) for item in devices).items())),
        "branches": branches,
        "macros": macros,
        "zones": zones,
        "sample_references": sample_names,
        "summary": {
            "devices": len(devices),
            "branches": len(branches),
            "macros": len(macros),
            "zones": len(zones),
            "unique_samples": len(sample_names),
            "warped_zones": dict(sorted(warped.items())),
        },
        "suggested_fidelity": _fidelity(zones, devices, branches, macros),
    }


def _inventory_row(arguments: tuple[Path, Path]) -> tuple[dict[str, object] | None, str | None]:
    path, root = arguments
    try:
        report = inspect(path)
    except ValueError as error:
        return None, str(error)
    summary = report["summary"]
    fidelity = report["suggested_fidelity"]
    return (
        {
            "path": path.relative_to(root).as_posix(),
            "kind": report["kind"],
            "name": report["name"],
            **summary,
            "device_types": report["device_types"],
            "fidelity": fidelity,
        },
        None,
    )


def inventory(root: Path, *, jobs: int = 1) -> dict[str, object]:
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Ableton inventory root is missing: {root}")
    if jobs < 1:
        raise ValueError("inventory jobs must be at least one")
    paths = [
        path
        for path in sorted(root.rglob("*"))
        if not (
            not path.is_file()
            or path.suffix.casefold() not in ABLETON_SUFFIXES
            or path.name.startswith("._")
            or "__MACOSX" in path.parts
        )
    ]
    arguments = [(path, root) for path in paths]
    if jobs == 1:
        results = map(_inventory_row, arguments)
        materialized = list(results)
    else:
        with concurrent.futures.ProcessPoolExecutor(max_workers=jobs) as executor:
            materialized = list(executor.map(_inventory_row, arguments, chunksize=1))
    presets = [row for row, _ in materialized if row is not None]
    issues = [issue for _, issue in materialized if issue is not None]
    grades = Counter(str(item["fidelity"]["grade"]) for item in presets)
    return {
        "format": 1,
        "root": str(root),
        "presets": presets,
        "count": len(presets),
        "issues": issues,
        "fidelity_grades": dict(sorted(grades.items())),
    }


def _write_json(path: Path | None, report: dict[str, object]) -> None:
    text = json.dumps(report, indent=2) + "\n"
    if path is None:
        print(text, end="")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("path", type=Path)
    inspect_parser.add_argument("--json", type=Path)
    inventory_parser = subparsers.add_parser("inventory")
    inventory_parser.add_argument("root", type=Path)
    inventory_parser.add_argument("--json", type=Path)
    inventory_parser.add_argument("--jobs", type=int, default=1)
    args = parser.parse_args()
    report = (
        inspect(args.path)
        if args.command == "inspect"
        else inventory(args.root, jobs=args.jobs)
    )
    _write_json(args.json, report)
    if args.json:
        if args.command == "inspect":
            print(
                f"zones={report['summary']['zones']} devices={report['summary']['devices']} "
                f"fidelity={report['suggested_fidelity']['grade']}"
            )
        else:
            print(
                f"presets={report['count']} issues={len(report['issues'])} "
                f"fidelity={report['fidelity_grades']}"
            )
    return 0 if not report.get("issues") else 2


if __name__ == "__main__":
    raise SystemExit(main())
