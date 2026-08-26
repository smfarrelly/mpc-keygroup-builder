"""Inspect and compare legacy XML and MPC 3 compressed XPM programs."""

from __future__ import annotations

import argparse
import gzip
import html
import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any

from .programs import classify_sample
from .structural import compare


TYPE_NAMES = {0: "Drum", 1: "Keygroup"}


def _xml_value(element: ET.Element) -> Any:
    value: dict[str, Any] = {}
    if element.attrib:
        value["@attributes"] = dict(sorted(element.attrib.items()))
    text = (element.text or "").strip()
    if text:
        if element.tag == "ProgramPads":
            try:
                value["#json"] = json.loads(html.unescape(text))
            except json.JSONDecodeError:
                value["#text"] = text
        else:
            value["#text"] = text
    children: dict[str, list[Any]] = {}
    for child in element:
        children.setdefault(child.tag, []).append(_xml_value(child))
    for tag, items in children.items():
        value[tag] = items[0] if len(items) == 1 else items
    return value


def _read_compressed(path: Path) -> tuple[list[str], dict[str, Any]]:
    raw = gzip.decompress(path.read_bytes())
    start = raw.find(b"{")
    if not raw.startswith(b"ACVS\n") or start < 0:
        raise ValueError(f"unsupported compressed MPC program: {path}")
    header = raw[:start].decode("utf-8").rstrip("\n").splitlines()
    return header, json.loads(raw[start:])


def load_normalized(path: Path) -> dict[str, Any]:
    if path.read_bytes()[:2] == b"\x1f\x8b":
        header, document = _read_compressed(path)
        return {"container": "gzip-json", "header": header, "document": document}
    root = ET.parse(path).getroot()
    return {"container": "xml", "document": {root.tag: _xml_value(root)}}


def _sample_stem(name: object) -> str:
    return Path(str(name)).stem if name else ""


def _xml_semantic(path: Path) -> dict[str, Any]:
    root = ET.parse(path).getroot()
    program = root.find("Program")
    if program is None:
        raise ValueError(f"missing Program element: {path}")
    settings: dict[str, Any] = {}
    node = program.find("ProgramPads")
    if node is not None and node.text:
        try:
            settings = _pad_settings(json.loads(html.unescape(node.text)))
        except json.JSONDecodeError:
            pass
    instruments = []
    for instrument in program.findall("./Instruments/Instrument"):
        layers = []
        for layer in instrument.iter("Layer"):
            sample = layer.findtext("SampleName") or layer.findtext("SampleFile")
            if sample:
                layers.append(_sample_stem(sample))
        if not layers:
            continue
        one_shot = str(instrument.findtext("OneShot", "False")).casefold() == "true"
        instruments.append(
            {
                "number": int(instrument.get("number", len(instruments) + 1)),
                "samples": layers,
                "mute_group": int(instrument.findtext("MuteGroup", "0")),
                "polyphony": int(instrument.findtext("Polyphony", "1")),
                "monophonic": str(instrument.findtext("Mono", "False")).casefold() == "true",
                "playback_mode": "one-shot" if one_shot else "note-on",
            }
        )
    pads = settings.get("pads", {}) if isinstance(settings.get("pads"), dict) else {}
    return {
        "name": program.findtext("ProgramName", ""),
        "program_type": program.get("type", "").casefold(),
        "program_pads": {
            "universal": settings.get("Universal", {}).get("value0")
            if isinstance(settings.get("Universal"), dict)
            else None,
            "display_type": settings.get("Type", {}).get("value0")
            if isinstance(settings.get("Type"), dict)
            else None,
            "colors": {key: value for key, value in sorted(pads.items()) if key.startswith("value")},
        },
        "instruments": instruments,
    }


def _serialized_semantic(path: Path) -> dict[str, Any]:
    _, document = _read_compressed(path)
    data = document.get("data", {})
    settings = _pad_settings(data.get("programPads"))
    instruments = []
    for number, instrument in enumerate(data.get("drum", {}).get("instruments", []), 1):
        if not isinstance(instrument, dict):
            continue
        layers = []
        for layer in instrument.get("layersv", []):
            if not isinstance(layer, dict):
                continue
            sample = layer.get("sampleName") or layer.get("sampleFile")
            if sample:
                layers.append(_sample_stem(sample))
        if not layers:
            continue
        trigger_mode = instrument.get("triggerMode")
        playback_mode = "one-shot" if trigger_mode == 0 else f"trigger-mode-{trigger_mode}"
        instruments.append(
            {
                "number": number,
                "samples": layers,
                "mute_group": int(instrument.get("whichMuteGroup", 0)),
                "polyphony": int(instrument.get("polyphony", 1)),
                "monophonic": bool(instrument.get("monophonic", False)),
                "playback_mode": playback_mode,
            }
        )
    pads = settings.get("pads", {}) if isinstance(settings.get("pads"), dict) else {}
    program_type = TYPE_NAMES.get(data.get("type"), str(data.get("type"))).casefold()
    return {
        "name": str(data.get("name", "")),
        "program_type": program_type,
        "program_pads": {
            "universal": settings.get("Universal", {}).get("value0")
            if isinstance(settings.get("Universal"), dict)
            else None,
            "display_type": settings.get("Type", {}).get("value0")
            if isinstance(settings.get("Type"), dict)
            else None,
            "colors": {key: value for key, value in sorted(pads.items()) if key.startswith("value")},
        },
        "instruments": instruments,
    }


def load_semantic(path: Path) -> dict[str, Any]:
    return _serialized_semantic(path) if path.read_bytes()[:2] == b"\x1f\x8b" else _xml_semantic(path)


def _xml_samples(program: ET.Element) -> list[str]:
    return sorted(
        {
            value.strip()
            for layer in program.iter("Layer")
            for value in (layer.findtext("SampleFile"), layer.findtext("SampleName"))
            if value and value.strip()
        }
    )


def _serialized_samples(data: dict[str, Any]) -> list[str]:
    values = set()
    for instrument in data.get("drum", {}).get("instruments", []):
        if not isinstance(instrument, dict):
            continue
        for layer in instrument.get("layersv", []):
            if not isinstance(layer, dict):
                continue
            sample = layer.get("sampleFile") or layer.get("sampleName")
            if isinstance(sample, str) and sample.strip():
                values.add(sample.strip())
    return sorted(values)


def _pad_settings(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return value.get("ProgramPads", value)


def _color_summary(settings: dict[str, Any]) -> dict[str, int]:
    pads = settings.get("pads", {})
    if not isinstance(pads, dict):
        return {}
    colors = Counter(
        f"#{color & 0xFFFFFF:06X}"
        for color in pads.values()
        if isinstance(color, int) and color != 0
    )
    return dict(sorted(colors.items()))


def inspect(path: Path) -> dict[str, Any]:
    compressed = path.read_bytes()[:2] == b"\x1f\x8b"
    if compressed:
        header, document = _read_compressed(path)
        data = document.get("data", {})
        program_type = TYPE_NAMES.get(data.get("type"), f"Unknown ({data.get('type')})")
        samples = _serialized_samples(data)
        settings = _pad_settings(data.get("programPads"))
        instruments = data.get("drum", {}).get("instruments", [])
        populated = sum(
            1
            for instrument in instruments
            if isinstance(instrument, dict)
            and any(
                isinstance(layer, dict) and (layer.get("sampleFile") or layer.get("sampleName"))
                for layer in instrument.get("layersv", [])
            )
        )
        firmware = header[1] if len(header) > 1 else ""
        name = str(data.get("name", ""))
    else:
        root = ET.parse(path).getroot()
        program = root.find("Program")
        if program is None:
            raise ValueError(f"missing Program element: {path}")
        program_type = program.get("type", "Unknown")
        samples = _xml_samples(program)
        node = program.find("ProgramPads")
        settings = {}
        if node is not None and node.text:
            try:
                settings = _pad_settings(json.loads(html.unescape(node.text)))
            except json.JSONDecodeError:
                pass
        populated = sum(1 for item in program.findall("./Instruments/Instrument") if _xml_samples(item))
        firmware = root.get("Version", "")
        name = program.findtext("ProgramName", "")
    categories = Counter(classify_sample(sample) for sample in samples)
    return {
        "path": str(path.resolve()),
        "format": "gzip-json" if compressed else "xml",
        "firmware_or_schema": firmware,
        "name": name,
        "program_type": program_type,
        "sample_references": len(samples),
        "populated_instruments": populated,
        "sample_categories": dict(sorted(categories.items())),
        "pad_color_mode": settings.get("Type", {}).get("value0")
        if isinstance(settings.get("Type"), dict)
        else None,
        "universal_pad_color": settings.get("Universal", {}).get("value0")
        if isinstance(settings.get("Universal"), dict)
        else None,
        "pad_colors": _color_summary(settings),
    }


def compare_programs(before: Path, after: Path) -> dict[str, Any]:
    before_value = load_semantic(before)
    after_value = load_semantic(after)
    changes = compare(before_value, after_value)
    before_container = load_normalized(before)
    after_container = load_normalized(after)
    same_container = before_container["container"] == after_container["container"]
    report = {
        "before": str(before.resolve()),
        "after": str(after.resolve()),
        "before_format": before_container["container"],
        "after_format": after_container["container"],
        "changes": changes,
        "change_count": len(changes),
    }
    if same_container:
        structural_changes = compare(before_container["document"], after_container["document"])
        report["structural_changes"] = structural_changes
        report["structural_change_count"] = len(structural_changes)
    else:
        report["structural_changes"] = []
        report["structural_change_count"] = None
        report["structural_note"] = (
            "Raw structural comparison omitted because the MPC rewrote the program container; "
            "changes contains the cross-format semantic comparison."
        )
    return report


def _write_or_print(value: dict[str, Any], output: Path | None) -> None:
    rendered = json.dumps(value, indent=2) + "\n"
    if output is None:
        print(rendered, end="")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        print(f"Wrote: {output}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("program", type=Path)
    inspect_parser.add_argument("--output", type=Path)
    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("before", type=Path)
    compare_parser.add_argument("after", type=Path)
    compare_parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "inspect":
        _write_or_print(inspect(args.program.expanduser().resolve()), args.output)
    else:
        _write_or_print(
            compare_programs(args.before.expanduser().resolve(), args.after.expanduser().resolve()),
            args.output,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
