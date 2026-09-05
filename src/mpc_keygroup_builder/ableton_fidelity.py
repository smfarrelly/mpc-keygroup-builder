"""Normalize Ableton preset evidence into an explicit MPC translation contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from . import ableton


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _present(zones: list[dict[str, Any]], field: str) -> bool:
    return any(zone.get(field) not in (None, {}, []) for zone in zones)


def _nondefault(zones: list[dict[str, Any]], field: str, default: object) -> bool:
    return any(zone.get(field) not in (None, default) for zone in zones)


def _active_loop(zones: list[dict[str, Any]], field: str) -> bool:
    return any(
        isinstance(zone.get(field), dict)
        and zone[field].get("mode") not in (None, 0)
        for zone in zones
    )


def _feature(name: str, evidence: object, translation: str, reason: str) -> dict[str, object]:
    return {"feature": name, "source_evidence": evidence, "translation": translation, "reason": reason}


def normalize(report: dict[str, Any], *, source_path: str | None = None) -> dict[str, Any]:
    zones = [item for item in report.get("zones", []) if isinstance(item, dict)]
    pads = [item for item in report.get("drum_pads", []) if isinstance(item, dict)]
    macros = [item for item in report.get("macros", []) if isinstance(item, dict)]
    devices = report.get("device_types", {})
    device_types = dict(devices) if isinstance(devices, dict) else {}
    target = "drum" if pads else "keygroup" if zones else "reference"
    features = [
        _feature("sample references", len(report.get("sample_references", [])), "direct" if zones else "absent", "Referenced sample filenames and relative paths are readable." if zones else "No readable sample zones."),
        _feature("key ranges", _present(zones, "key_range"), "direct" if _present(zones, "key_range") else "absent", "MPC Keygroup ranges can represent these values."),
        _feature("velocity ranges", _present(zones, "velocity_range"), "direct" if _present(zones, "velocity_range") else "absent", "MPC layer velocity ranges can represent these values."),
        _feature("root notes", _present(zones, "rootkey"), "direct" if _present(zones, "rootkey") else "review-required", "Readable values map directly; missing values require filename/audio inference."),
        _feature("drum note assignments", len(pads), "direct" if pads else "absent", "Receiving notes are retained as provenance; MPC pad order remains an explicit conversion choice."),
        _feature("choke groups", sum(bool(item.get("choke_group")) for item in pads), "direct" if pads else "absent", "Ableton choke groups map to MPC mute groups when in range."),
        _feature("sample start/end", (endpoint := _nondefault(zones, "samplestart", 0) or _present(zones, "sampleend")), "review-required" if endpoint else "absent", "Current Drum builder does not serialize non-default start/end values."),
        _feature("tune/gain/pan", (mix := any(_nondefault(zones, field, default) for field, default in (("detune", 0), ("volume", 1), ("panorama", 0)))), "review-required" if mix else "absent", "Values are inspectable but need MPC-native serializer coverage."),
        _feature("loops", (loops := _active_loop(zones, "sustain_loop") or _active_loop(zones, "release_loop")), "review-required" if loops else "absent", "Loop modes and crossfades require explicit MPC translation tests."),
        _feature("warp", sum(zone.get("warped") is True for zone in zones), "reference-only" if any(zone.get("warped") is True for zone in zones) else "absent", "Ableton warp behavior is not portable to MPC sample zones."),
        _feature("rack macros", [item.get("name") for item in macros], "template" if macros else "absent", "Macro names describe intent, but mappings and device behavior need MPC-native substitutes."),
        _feature("devices/effects/routing", device_types, "reference-only" if "PluginDevice" in device_types else "template" if len(device_types) > 2 else "absent", "Non-sampler devices are retained as reference evidence, not claimed as reconstructed sound."),
    ]
    translations = Counter(str(item["translation"]) for item in features)
    if not zones:
        grade, label, reason = "D", "reference-only", "No readable sample zones were found."
    elif "PluginDevice" in device_types or translations["reference-only"]:
        grade, label, reason = "D", "reference-only", "Warp or plug-in behavior prevents a faithful automatic reconstruction."
    elif translations["review-required"] or translations["template"]:
        grade, label, reason = "B" if not pads else "C", "close" if not pads else "template", "Sample intent is readable, but one or more behaviors require MPC-native decisions."
    else:
        grade, label, reason = "A", "direct", "All detected source features have direct MPC representations."
    normalized_zones = []
    for zone in zones:
        normalized_zones.append({key: zone.get(key) for key in (
            "name", "sample", "key_range", "velocity_range", "rootkey", "detune",
            "volume", "panorama", "samplestart", "sampleend", "sustain_loop",
            "release_loop", "warped", "isactive",
        )})
    normalized_pads = [{
        "name": pad.get("name"), "receiving_note": pad.get("receiving_note"),
        "sending_note": pad.get("sending_note"), "choke_group": pad.get("choke_group"),
        "zones": len(pad.get("zones", [])) if isinstance(pad.get("zones"), list) else 0,
    } for pad in pads]
    return {
        "schema_version": 1, "kind": "mpc-ableton-translation-model",
        "source": source_path, "name": report.get("name"), "source_kind": report.get("kind"),
        "target": target, "fidelity": {"grade": grade, "label": label, "reason": reason},
        "summary": {"zones": len(zones), "pads": len(pads), "macros": len(macros), "features": dict(sorted(translations.items()))},
        "features": features, "zones": normalized_zones, "pads": normalized_pads,
        "macros": macros, "device_types": device_types,
    }


def inspect_path(path: Path, *, relative_to: Path | None = None) -> dict[str, Any]:
    path = path.expanduser().resolve()
    source = path.relative_to(relative_to.resolve()).as_posix() if relative_to else path.name
    result = normalize(ableton.inspect(path), source_path=source)
    result["source_sha256"] = _sha256(path)
    return result


def build_catalog(paths: list[Path], output: Path, *, source_root: Path | None = None) -> dict[str, Any]:
    output = output.expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"Ableton fidelity output already exists: {output}")
    models = [inspect_path(path, relative_to=source_root) for path in paths]
    grades = Counter(item["fidelity"]["grade"] for item in models)
    targets = Counter(item["target"] for item in models)
    catalog = {"schema_version": 1, "kind": "mpc-ableton-fidelity-catalog", "summary": {"presets": len(models), "grades": dict(sorted(grades.items())), "targets": dict(sorted(targets.items()))}, "presets": models}
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        (staging / "fidelity-catalog.json").write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
        lines = ["# Ableton → MPC translation fidelity", "", "This report separates readable source evidence from behavior that still needs an MPC-native decision.", "", f"Presets: {len(models)} · grades: {dict(sorted(grades.items()))}", ""]
        for model in models:
            lines.extend((f"## {model['name']}", "", f"Target: `{model['target']}` · fidelity: **{model['fidelity']['grade']} / {model['fidelity']['label']}**", "", str(model["fidelity"]["reason"]), ""))
            for feature in model["features"]:
                if feature["translation"] != "absent":
                    lines.append(f"- `{feature['translation']}` — {feature['feature']}: {feature['reason']}")
            lines.append("")
        (staging / "README.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        os.replace(staging, output)
    except Exception:
        import shutil
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return catalog


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("presets", type=Path, nargs="+")
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv or sys.argv[1:])
    catalog = build_catalog(args.presets, args.output, source_root=args.source_root)
    print(f"Wrote: {args.output.expanduser().resolve()}")
    print(f"Presets: {catalog['summary']['presets']}; grades: {catalog['summary']['grades']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
