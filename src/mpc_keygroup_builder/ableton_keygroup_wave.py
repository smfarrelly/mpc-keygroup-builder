"""Plan conservative Ableton Keygroup waves for the existing batch builder."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any

from . import ableton
from .ableton_backlog import display_pack
from .ableton_wave import infer_pack_root
from .cli import wav_frames


def _category(path: str) -> str:
    lowered = path.casefold()
    for category, words in (
        ("Bass", ("/bass/", " bass")), ("Keys", ("/keys/", "piano", "organ", "wurli", "keys")),
        ("Pads", ("/pad/", "/pads/", " pad")), ("Leads", ("/lead/", "/leads/", " lead")),
    ):
        if any(word in lowered for word in words):
            return category
    return "Instruments"


def _range_for(roots: list[int], index: int) -> tuple[int, int]:
    low = 0 if index == 0 else (roots[index - 1] + roots[index]) // 2 + 1
    high = 127 if index == len(roots) - 1 else (roots[index] + roots[index + 1]) // 2
    return low, high


def preflight(entry: dict[str, Any], source_root: Path, *, allow_loop_loss: bool = False) -> dict[str, Any]:
    relative = entry.get("path")
    if not isinstance(relative, str) or not relative:
        raise ValueError("backlog entry path must be a non-empty string")
    preset = (source_root / relative).resolve()
    try:
        preset.relative_to(source_root.resolve())
    except ValueError as error:
        raise ValueError(f"preset escapes source root: {relative}") from error
    report = ableton.inspect(preset)
    zones = [zone for zone in report.get("zones", []) if zone.get("isactive") is not False]
    if not zones:
        raise ValueError("no active sample zones")
    pack_root = infer_pack_root(preset, source_root, report)
    samples: list[tuple[dict[str, Any], Path]] = []
    for index, zone in enumerate(zones, 1):
        sample = zone.get("sample")
        sample_relative = sample.get("relative_path") if isinstance(sample, dict) else None
        if not isinstance(sample_relative, str) or not sample_relative:
            raise ValueError(f"zone {index} lacks a relative WAV path")
        path = (pack_root / sample_relative).resolve()
        try:
            path.relative_to(pack_root.resolve())
        except ValueError as error:
            raise ValueError(f"zone {index} sample escapes pack root") from error
        if path.suffix.casefold() != ".wav" or not path.is_file():
            raise FileNotFoundError(f"zone {index} WAV not found: {path}")
        wav_frames(path)
        samples.append((zone, path))
    parents = {path.parent for _, path in samples}
    if len(parents) != 1:
        raise ValueError("referenced WAVs span multiple directories")
    names = [path.name for _, path in samples]
    if len(names) != len(set(names)):
        raise ValueError("referenced WAV basenames are not unique")
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    warnings = []
    for index, (zone, _) in enumerate(samples, 1):
        root = zone.get("rootkey")
        if isinstance(root, bool) or not isinstance(root, int) or not 0 <= root <= 127:
            raise ValueError(f"zone {index} has invalid root key")
        if zone.get("warped") is True:
            raise ValueError(f"zone {index} uses warp")
        for field in ("detune", "samplestart", "panorama"):
            if zone.get(field) not in (None, 0, 0.0):
                raise ValueError(f"zone {index} uses unsupported {field}={zone.get(field)}")
        for field in ("sustain_loop", "release_loop"):
            loop = zone.get(field)
            if isinstance(loop, dict) and loop.get("mode") not in (None, 0):
                if not allow_loop_loss:
                    raise ValueError(f"zone {index} uses unsupported {field}")
                warnings.append(
                    f"zone {index} {field} mode={loop.get('mode')} is omitted from the comparison build"
                )
        if zone.get("volume") not in (None, 1, 1.0):
            warnings.append(f"zone {index} source volume={zone.get('volume')} requires listening review")
        grouped[root].append(zone)
    roots = sorted(grouped)
    velocity_schemas = set()
    for root_index, root in enumerate(roots):
        root_zones = grouped[root]
        key_ranges = {
            (zone.get("key_range", {}).get("min"), zone.get("key_range", {}).get("max"))
            for zone in root_zones
        }
        expected = _range_for(roots, root_index)
        if key_ranges != {expected}:
            raise ValueError(f"root {root} key range {sorted(key_ranges)} differs from builder range {expected}")
        ranges = sorted(
            (0 if zone.get("velocity_range", {}).get("min") == 1 else zone.get("velocity_range", {}).get("min"), zone.get("velocity_range", {}).get("max"))
            for zone in root_zones
        )
        cursor = 0
        for low, high in ranges:
            if not isinstance(low, int) or not isinstance(high, int) or low != cursor or not low <= high <= 127:
                raise ValueError(f"root {root} has velocity gap, overlap, or invalid range")
            cursor = high + 1
        if cursor != 128 or len(ranges) > 8:
            raise ValueError(f"root {root} velocity layers do not cover 0..127 within the 8-layer limit")
        velocity_schemas.add(tuple(ranges))
    if len(velocity_schemas) > 1:
        raise ValueError("per-root velocity schemas differ and cannot use the current batch builder")
    sample_directory = next(iter(parents))
    return {
        "id": str(entry.get("id") or relative), "name": str(entry.get("name") or preset.stem),
        "collection": display_pack(str(entry.get("pack", ""))), "category": _category(relative),
        "preset": preset.relative_to(source_root).as_posix(),
        "sample_directory": sample_directory.relative_to(source_root).as_posix(),
        "samples": sorted(names), "roots": roots, "zones": len(zones), "warnings": warnings,
        "fidelity": "direct" if not warnings else "review-required",
    }


def _batch(selected: list[dict[str, Any]], name: str) -> dict[str, Any]:
    return {
        "version": 1, "library": name, "source_root": ".",
        "destination": "Programs/Keygroups/SFM Ableton Wave",
        "instruments": [
            {
                "name": item["name"], "category": item["category"],
                "source": item["sample_directory"], "velocity_preset": item["preset"],
                "install": "copy", "vendor_programs_checked": False,
                "sample_selection": {"include": item["samples"], "exclude": []},
            }
            for item in selected
        ],
    }


def plan(
    backlog_path: Path, source_root: Path, output: Path, *, count: int = 24,
    max_per_pack: int = 2, allow_loop_loss: bool = False,
) -> dict[str, Any]:
    if count < 1 or max_per_pack < 1:
        raise ValueError("count and max-per-pack must be positive")
    backlog_path, source_root, output = backlog_path.resolve(), source_root.resolve(), output.resolve()
    if output.exists():
        raise FileExistsError(f"Ableton Keygroup wave output already exists: {output}")
    raw = json.loads(backlog_path.read_text(encoding="utf-8"))
    entries = raw.get("entries")
    if not isinstance(entries, list):
        raise ValueError("backlog entries must be a list")
    groups: dict[str, deque[dict[str, Any]]] = defaultdict(deque)
    for entry in entries:
        if (
            isinstance(entry, dict) and entry.get("target") == "keygroup"
            and entry.get("priority") in {"P1", "P2"} and not entry.get("duplicate_of")
        ):
            groups[str(entry.get("pack", ""))].append(entry)
    selected = []
    rejected = []
    for _ in range(max_per_pack):
        for pack in sorted(list(groups), key=lambda value: (-int(groups[value][0].get("score", 0)), value)):
            accepted = False
            while groups[pack] and not accepted:
                entry = groups[pack].popleft()
                try:
                    selected.append(preflight(entry, source_root, allow_loop_loss=allow_loop_loss))
                    accepted = True
                except (ValueError, FileNotFoundError, TypeError) as error:
                    rejected.append({"path": str(entry.get("path", "")), "reason": str(error)})
            if not groups[pack]:
                groups.pop(pack, None)
            if len(selected) == count:
                break
        if len(selected) == count:
            break
    if len(selected) < count:
        raise ValueError(f"only {len(selected)} compatible diverse presets found; requested {count}")
    selected = selected[:count]
    name = "Samples From Mars Ableton Keygroup Wave"
    report = {
        "schema_version": 1, "kind": "mpc-ableton-keygroup-wave-plan", "name": name,
        "software_status": "preflight-pass", "hardware_status": "deferred",
        "allow_loop_loss": allow_loop_loss,
        "summary": {
            "programs": len(selected), "packs": len({item["collection"] for item in selected}),
            "zones": sum(item["zones"] for item in selected),
            "direct": sum(item["fidelity"] == "direct" for item in selected),
            "review_required": sum(item["fidelity"] == "review-required" for item in selected),
            "omitted_loop_diagnostics": sum(
                "omitted from the comparison build" in warning
                for item in selected for warning in item["warnings"]
            ),
            "rejected_during_selection": len(rejected),
        },
        "selection_policy": "priority P1-P2, unique source, round-robin packs, conservative topology preflight",
        "programs": selected, "rejections": rejected,
        "boundary": "Preflight proves compatibility with current builder topology, not sound, source effects/macros, or MPC hardware behavior.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        (staging / "keygroup-wave.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        (staging / "keygroup-batch.json").write_text(json.dumps(_batch(selected, name), indent=2) + "\n", encoding="utf-8")
        (staging / "settings-example.toml").write_text(
            'library_root = "/absolute/path/to/Samples From Mars"\nmpc_root = "/absolute/path/to/MPC media root"\ntemplate = "/absolute/path/to/known-good-keygroup.xpm"\nartifacts_root = "/absolute/path/to/local/build-artifacts"\n', encoding="utf-8",
        )
        lines = ["# Ableton Keygroup wave — hardware checklist", "", "Build and validate with `mpc-keygroup-batch` before copying to MPC media.", ""]
        for item in selected:
            loop_warnings = sum("omitted from the comparison build" in warning for warning in item["warnings"])
            lines.extend((f"## {item['collection']} / {item['name']}", "", f"Category: {item['category']}; roots: {item['roots']}; zones: {item['zones']}; fidelity: {item['fidelity']}; omitted loop diagnostics: {loop_warnings}.", "", "- [ ] Default Key 37 register triggers expected notes.", "- [ ] Pitch, layer transitions, level, tone, and save/reload checked.", "- [ ] Compare held/released notes with Ableton where loops were omitted.", "", "Verdict: [ ] pass  [ ] warn  [ ] fail", "Notes:", ""))
        (staging / "HARDWARE_CHECKLIST.md").write_text("\n".join(lines), encoding="utf-8")
        (staging / "README.md").write_text(
            "# Ableton Keygroup comparison wave\n\n"
            "1. Copy `settings-example.toml` to a local settings file and replace every absolute path.\n"
            "2. Run `mpc-keygroup-batch --config SETTINGS inspect keygroup-batch.json`.\n"
            "3. Run the same command with `build`, then `validate keygroup-batch.json`.\n"
            "4. Keep generated programs and licensed WAVs in ignored/external storage.\n\n"
            "This plan may explicitly omit Ableton loops. Read `keygroup-wave.json` and the hardware checklist before auditioning.\n",
            encoding="utf-8",
        )
        os.replace(staging, output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backlog", type=Path)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=24)
    parser.add_argument("--max-per-pack", type=int, default=2)
    parser.add_argument(
        "--allow-loop-loss", action="store_true",
        help="build an explicit comparison wave that omits unsupported Ableton loops",
    )
    args = parser.parse_args(argv or sys.argv[1:])
    report = plan(
        args.backlog, args.source_root, args.output, count=args.count,
        max_per_pack=args.max_per_pack, allow_loop_loss=args.allow_loop_loss,
    )
    print(f"Wrote: {args.output.resolve()}")
    print(f"Programs: {report['summary']['programs']}; packs: {report['summary']['packs']}; hardware: deferred")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
