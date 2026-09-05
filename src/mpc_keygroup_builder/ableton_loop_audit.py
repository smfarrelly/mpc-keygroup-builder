"""Inventory Ableton sample-loop signatures and choose representative fixtures."""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from . import ableton
from .ableton_backlog import display_pack


def _contained(root: Path, relative: str) -> Path:
    if Path(relative).is_absolute():
        raise ValueError(f"preset path must be relative: {relative}")
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"preset path escapes source root: {relative}") from error
    return path


def audit(
    backlog_path: Path, source_root: Path, *, target: str = "keygroup",
    representative_limit: int = 3, limit_presets: int | None = None,
) -> dict[str, Any]:
    if target not in {"keygroup", "drum", "all"}:
        raise ValueError("target must be keygroup, drum, or all")
    if representative_limit < 1:
        raise ValueError("representative-limit must be positive")
    if limit_presets is not None and limit_presets < 1:
        raise ValueError("limit-presets must be positive")
    backlog_path, source_root = backlog_path.resolve(), source_root.resolve()
    raw = json.loads(backlog_path.read_text(encoding="utf-8"))
    entries = raw.get("entries")
    if not isinstance(entries, list):
        raise ValueError("backlog entries must be a list")
    candidates = [
        entry for entry in entries
        if isinstance(entry, dict) and not entry.get("duplicate_of")
        and (target == "all" or entry.get("target") == target)
    ]
    candidates.sort(key=lambda item: (-int(item.get("score", 0)), str(item.get("path", ""))))
    if limit_presets is not None:
        candidates = candidates[:limit_presets]
    observations = []
    issues = []
    presets_with_active = set()
    packs_with_active: dict[str, set[str]] = defaultdict(set)
    for entry in candidates:
        relative = entry.get("path")
        if not isinstance(relative, str) or not relative:
            issues.append({"path": str(relative), "error": "backlog entry path must be a non-empty string"})
            continue
        try:
            report = ableton.inspect(_contained(source_root, relative))
        except (FileNotFoundError, ValueError, OSError) as error:
            issues.append({"path": relative, "error": str(error)})
            continue
        pack = display_pack(str(entry.get("pack", "")))
        for zone_index, zone in enumerate(report.get("zones", []), 1):
            if not isinstance(zone, dict) or zone.get("isactive") is False:
                continue
            sample = zone.get("sample") if isinstance(zone.get("sample"), dict) else {}
            for kind, field in (("sustain", "sustain_loop"), ("release", "release_loop")):
                loop = zone.get(field)
                if not isinstance(loop, dict) or loop.get("mode") is None:
                    continue
                mode = loop.get("mode")
                nonzero = mode != 0
                if nonzero:
                    presets_with_active.add(relative)
                    packs_with_active[pack].add(relative)
                start, end = loop.get("start"), loop.get("end")
                observations.append({
                    "preset": relative, "name": str(entry.get("name") or report.get("name") or Path(relative).stem),
                    "collection": pack, "target": entry.get("target"), "priority": entry.get("priority"),
                    "zone": zone_index, "sample": sample.get("name"), "root_key": zone.get("rootkey"),
                    "loop_kind": kind, "mode": mode, "nonzero_mode": nonzero,
                    "start": start, "end": end, "crossfade": loop.get("crossfade"),
                    "span_frames": end - start if isinstance(start, int) and isinstance(end, int) else None,
                    "start_zero": start == 0,
                    "end_matches_sample_end": isinstance(end, int) and isinstance(zone.get("sampleend"), int) and end == zone["sampleend"],
                })
    signature_groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in observations:
        signature_groups[(row["loop_kind"], row["mode"], bool(row["crossfade"]), row["start_zero"], row["end_matches_sample_end"])].append(row)
    signatures = []
    for signature, rows in sorted(signature_groups.items(), key=lambda item: (item[0][0], str(item[0][1:]))):
        kind, mode, crossfade_present, start_zero, end_matches = signature
        unique_presets = []
        seen = set()
        for row in rows:
            if row["preset"] not in seen:
                unique_presets.append({key: row[key] for key in ("preset", "name", "collection", "priority", "zone", "sample", "root_key", "start", "end", "span_frames")})
                seen.add(row["preset"])
            if len(unique_presets) == representative_limit:
                break
        signatures.append({
            "loop_kind": kind, "mode": mode, "nonzero_mode": mode != 0,
            "crossfade_present": crossfade_present,
            "crossfade_values": {
                "distinct": len({row["crossfade"] for row in rows}),
                "min": min((row["crossfade"] for row in rows if isinstance(row["crossfade"], (int, float))), default=None),
                "max": max((row["crossfade"] for row in rows if isinstance(row["crossfade"], (int, float))), default=None),
            },
            "start_zero": start_zero, "end_matches_sample_end": end_matches,
            "observations": len(rows), "presets": len({row["preset"] for row in rows}),
            "representatives": unique_presets,
        })
    mode_counts = Counter(f"{row['loop_kind']}:mode-{row['mode']}" for row in observations)
    nonzero = [row for row in observations if row["nonzero_mode"]]
    return {
        "schema_version": 1, "kind": "mpc-ableton-loop-audit", "source_root": str(source_root),
        "target": target, "summary": {
            "candidate_presets": len(candidates), "inspected_presets": len(candidates) - len(issues),
            "issues": len(issues), "loop_observations": len(observations),
            "nonzero_mode_observations": len(nonzero), "presets_with_nonzero_modes": len(presets_with_active),
            "signature_count": len(signatures), "mode_counts": dict(sorted(mode_counts.items())),
            "packs_with_nonzero_modes": {
                pack: len(presets) for pack, presets in sorted(packs_with_active.items())
            },
        },
        "signatures": signatures, "issues": issues,
        "boundary": "Numeric Ableton mode values and endpoint patterns are source evidence only. Their MPC meaning requires representative MPC-authored captures and listening tests.",
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Ableton sample-loop audit", "",
        f"Target: {report['target']}; inspected {summary['inspected_presets']}/{summary['candidate_presets']} presets; {summary['presets_with_nonzero_modes']} contain nonzero loop modes.",
        f"Observations: {summary['loop_observations']} total, {summary['nonzero_mode_observations']} nonzero, {summary['signature_count']} distinct signatures.", "",
        "Mode numbers are deliberately not given semantic names until MPC-authored comparisons prove them.", "",
    ]
    for item in report["signatures"]:
        lines.extend((
            f"## {item['loop_kind']} mode {item['mode']} — {'nonzero' if item['nonzero_mode'] else 'zero'}", "",
            f"Crossfade present: {item['crossfade_present']} (values {item['crossfade_values']['min']}–{item['crossfade_values']['max']}, {item['crossfade_values']['distinct']} distinct); start zero: {item['start_zero']}; end matches sample end: {item['end_matches_sample_end']}; {item['observations']} zones across {item['presets']} presets.", "",
        ))
        for row in item["representatives"]:
            lines.append(f"- {row['collection']} / {row['name']} — zone {row['zone']}, {row['sample']}, root {row['root_key']}, frames {row['start']}–{row['end']}.")
        lines.append("")
    if report["issues"]:
        lines.extend(("## Inspection issues", ""))
        lines.extend(f"- `{row['path']}`: {row['error']}" for row in report["issues"])
        lines.append("")
    lines.extend(("## Evidence boundary", "", report["boundary"], ""))
    return "\n".join(lines)


def write_report(report: dict[str, Any], output: Path) -> None:
    output = output.expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"Ableton loop audit output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        (staging / "ableton-loop-audit.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        (staging / "ABLETON_LOOP_AUDIT.md").write_text(render_markdown(report), encoding="utf-8")
        with (staging / "loop-signatures.csv").open("w", newline="", encoding="utf-8") as stream:
            fields = ("loop_kind", "mode", "nonzero_mode", "crossfade_present", "crossfade_min", "crossfade_max", "crossfade_distinct", "start_zero", "end_matches_sample_end", "observations", "presets", "representative_presets")
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for item in report["signatures"]:
                writer.writerow({
                    **{field: item[field] for field in fields if field in item},
                    "crossfade_min": item["crossfade_values"]["min"],
                    "crossfade_max": item["crossfade_values"]["max"],
                    "crossfade_distinct": item["crossfade_values"]["distinct"],
                    "representative_presets": ";".join(row["preset"] for row in item["representatives"]),
                })
        os.replace(staging, output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backlog", type=Path)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--target", choices=("keygroup", "drum", "all"), default="keygroup")
    parser.add_argument("--representative-limit", type=int, default=3)
    parser.add_argument("--limit-presets", type=int)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv or sys.argv[1:])
    report = audit(args.backlog, args.source_root, target=args.target, representative_limit=args.representative_limit, limit_presets=args.limit_presets)
    write_report(report, args.output)
    summary = report["summary"]
    print(f"Wrote: {args.output.resolve()}")
    print(f"Presets: {summary['inspected_presets']}; nonzero modes: {summary['nonzero_mode_observations']}; signatures: {summary['signature_count']}")
    return 2 if summary["issues"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
