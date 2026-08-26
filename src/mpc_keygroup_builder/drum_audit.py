"""Read-only Drum Program pad, playback, and hat-choke audit."""

from __future__ import annotations

import argparse
import gzip
import json
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from .programs import classify_sample


@dataclass(frozen=True)
class PadPerformance:
    pad: int
    sample: str
    category: str
    mute_group: int
    polyphony: int
    monophonic: bool
    playback_mode: str


def _boolean(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"1", "true", "yes", "on"}


def _integer(value: object, default: int = 0) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _xml_sample(instrument: ET.Element) -> str:
    for layer in instrument.iter("Layer"):
        sample = (layer.findtext("SampleFile") or layer.findtext("SampleName") or "").strip()
        if sample:
            return sample
    return ""


def _xml_pads(path: Path) -> list[PadPerformance]:
    root = ET.parse(path).getroot()
    program = root.find("Program")
    if program is None or program.get("type", "").casefold() != "drum":
        raise ValueError(f"not an XML Drum Program: {path}")
    pads = []
    for instrument in program.findall("./Instruments/Instrument"):
        sample = _xml_sample(instrument)
        if not sample:
            continue
        one_shot = _boolean(instrument.findtext("OneShot"))
        pads.append(
            PadPerformance(
                pad=_integer(instrument.get("number"), len(pads) + 1),
                sample=sample,
                category=classify_sample(sample),
                mute_group=_integer(instrument.findtext("MuteGroup")),
                polyphony=_integer(instrument.findtext("Polyphony"), 1),
                monophonic=_boolean(instrument.findtext("Mono")),
                playback_mode="one-shot" if one_shot else "note-on",
            )
        )
    return pads


def _serialized_sample(instrument: dict) -> str:
    for layer in instrument.get("layersv", []):
        if not isinstance(layer, dict):
            continue
        sample = (layer.get("sampleFile") or layer.get("sampleName") or "").strip()
        if sample:
            return sample
    return ""


def _serialized_pads(path: Path) -> list[PadPerformance]:
    raw = gzip.decompress(path.read_bytes())
    start = raw.find(b"{")
    if not raw.startswith(b"ACVS\n") or start < 0:
        raise ValueError(f"unsupported compressed MPC program: {path}")
    data = json.loads(raw[start:]).get("data", {})
    if data.get("type") != 0 or not isinstance(data.get("drum"), dict):
        raise ValueError(f"not a compressed Drum Program: {path}")
    pads = []
    for index, instrument in enumerate(data["drum"].get("instruments", []), 1):
        if not isinstance(instrument, dict):
            continue
        sample = _serialized_sample(instrument)
        if not sample:
            continue
        pads.append(
            PadPerformance(
                pad=index,
                sample=sample,
                category=classify_sample(sample),
                mute_group=_integer(instrument.get("whichMuteGroup")),
                polyphony=_integer(instrument.get("polyphony"), 1),
                monophonic=_boolean(instrument.get("monophonic")),
                playback_mode=f"trigger-mode-{_integer(instrument.get('triggerMode'))}",
            )
        )
    return pads


def audit_drum_program(path: Path) -> dict[str, object]:
    compressed = path.read_bytes()[:2] == b"\x1f\x8b"
    pads = _serialized_pads(path) if compressed else _xml_pads(path)
    issues = []
    hat_groups: dict[int, set[str]] = defaultdict(set)
    group_categories: dict[int, set[str]] = defaultdict(set)
    for pad in pads:
        if pad.polyphony < 1:
            issues.append(f"pad {pad.pad} has invalid polyphony {pad.polyphony}")
        if pad.mute_group > 0:
            group_categories[pad.mute_group].add(pad.category)
        if pad.category in {"closed_hat", "open_hat"}:
            if pad.mute_group <= 0:
                issues.append(f"pad {pad.pad} {pad.category} has no mute group: {pad.sample}")
            else:
                hat_groups[pad.mute_group].add(pad.category)
    for group, categories in sorted(hat_groups.items()):
        missing = {"closed_hat", "open_hat"} - categories
        if missing:
            issues.append(f"mute group {group} is missing {', '.join(sorted(missing))}")
        non_hats = group_categories[group] - {"closed_hat", "open_hat"}
        if non_hats:
            issues.append(
                f"hat mute group {group} also contains {', '.join(sorted(non_hats))}"
            )
    categories = Counter(pad.category for pad in pads)
    groups: dict[str, list[int]] = defaultdict(list)
    for pad in pads:
        if pad.mute_group > 0:
            groups[str(pad.mute_group)].append(pad.pad)
    return {
        "program": str(path.resolve()),
        "format": "gzip-json" if compressed else "xml",
        "verdict": "warn" if issues else "pass",
        "populated_pads": len(pads),
        "categories": dict(sorted(categories.items())),
        "mute_groups": dict(sorted(groups.items(), key=lambda item: int(item[0]))),
        "issues": issues,
        "pads": [asdict(pad) for pad in pads],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("program", type=Path)
    parser.add_argument("--json", action="store_true", help="print the complete JSON report")
    args = parser.parse_args()
    report = audit_drum_program(args.program.expanduser().resolve())
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(
            f"{str(report['verdict']).upper()}: {args.program.name} "
            f"({report['format']}, {report['populated_pads']} populated pads)"
        )
        print(
            "Categories: "
            + ", ".join(f"{key}={value}" for key, value in report["categories"].items())
        )
        groups = report["mute_groups"]
        print(
            "Mute groups: "
            + (", ".join(f"{group}={pads}" for group, pads in groups.items()) or "none")
        )
        for issue in report["issues"]:
            print(f"WARN: {issue}")
    return 0 if report["verdict"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
