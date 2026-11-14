"""Compare saved Learn destinations for the same physical controller modes."""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any

from . import launch_control, xpj


def _canonical(rows: list[dict]) -> list[dict]:
    # Learn array order and instantaneous knob values do not change a binding.
    return sorted(rows, key=lambda row: json.dumps(row, sort_keys=True))


def _identity(target: dict, tracks: dict[str, list[str]]) -> tuple | None:
    track = target["track"]
    plugins = tracks.get(track, [])
    if len(plugins) != 1 or target.get("target_count") != 1 or type(target["parameter"]) is not int:
        return None
    name = target["name"]
    prefix = f"{track} ("
    if not isinstance(name, str) or not name.startswith(prefix) or not name.endswith(")"):
        return None
    return plugins[0], target["instrument_index"], target["parameter"], name[len(prefix):-1]


def _tracks(rows: list[dict]) -> dict[str, list[str]]:
    result = defaultdict(list)
    for row in rows:
        result[row["track"]].append(row["plugin"])
    return result


def compare_projects(before: Path, after: Path, paths: list[Path]) -> dict[str, Any]:
    modes = [launch_control.inspect(path) for path in paths]
    if len({mode["name"] for mode in modes}) != len(modes):
        raise ValueError("comparison requires distinct Components mode names")
    projects = [xpj.load(path) for path in (before, after)]
    left, right = [launch_control.audit_modes(project, modes) for project in projects]
    before_tracks, after_tracks = [_tracks(audit["plugin_tracks"]) for audit in (left, right)]
    candidates = defaultdict(list)
    for target in xpj.midi_learn_rows(projects[1]):
        key = _identity(target, after_tracks)
        if key is not None:
            candidates[key].append({field: target[field] for field in
                                    ("track", "name", "channel", "number", "control_type")})
    comparisons = []
    changed = False
    for old, new in zip(left["captures"], right["captures"], strict=True):
        rows = []
        counts = Counter()
        for old_control, new_control in zip(old["controls"], new["controls"], strict=True):
            previous = _canonical(old_control["learned_rows"])
            current = _canonical(new_control["learned_rows"])
            if previous == current:
                status = "same" if current else "unbound-in-both"
            elif not previous:
                status = "added"
            elif not current:
                status = "removed"
            else:
                status = "changed"
            counts[status] += 1
            if status in ("same", "unbound-in-both"):
                continue
            changed = True
            elsewhere = []
            for target in previous:
                key = _identity(target, before_tracks)
                for candidate in candidates.get(key, ()):
                    if (candidate["channel"], candidate["number"]) == (old_control["channel"], old_control["number"]):
                        continue
                    if candidate not in elsewhere:
                        elsewhere.append(candidate)
            rows.append({
                "endpoint": old_control["control"], "label": old_control["label"],
                "channel": old_control["channel"], "cc": old_control["number"],
                "channel_source": old_control["channel_source"], "status": status,
                "before": previous, "after": current, "other_saved_inputs": _canonical(elsewhere),
            })
        comparisons.append({"mode": old["name"], "sha256": old["sha256"], "summary": dict(counts), "changes": rows})
    presets = [_canonical(audit["plugin_tracks"]) for audit in (left, right)]
    return {
        "kind": "mpc-controller-project-comparison", "schema_version": 1,
        "before": before.name, "after": after.name,
        "before_presets": presets[0], "after_presets": presets[1],
        "presets_changed": presets[0] != presets[1], "changed": changed or presets[0] != presets[1],
        "captures": comparisons,
        "interpretation": (
            "Assignments compare saved Learn rows at each captured channel and number. "
            "Other saved inputs match instrument, parameter ID, target name and instrument index in the second project. "
            "Multiple instances or message types can give multiple candidates. Live response needs a listening test."
        ),
    }
