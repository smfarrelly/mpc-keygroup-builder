"""Derive compact, role-diverse performance cores from full plugin profiles."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

from . import plugin_map, plugin_seed


ENCODER_GROUPS = ("top-encoder", "middle-encoder", "bottom-encoder")
BUTTON_ENDPOINTS = tuple(
    f"{group}-button-{position}"
    for group in ("upper", "lower")
    for position in range(1, 9)
)


def _is_button(row: dict[str, Any]) -> bool:
    return "-button-" in str(row.get("control", ""))


def _diverse(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Round-robin roles without inventing a musical ranking."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    order: list[str] = []
    for row in rows:
        role = str(row.get("role", "other"))
        if role not in groups:
            order.append(role)
        groups[role].append(row)
    result = []
    while any(groups.values()):
        for role in order:
            if groups[role]:
                result.append(groups[role].pop(0))
    return result


def select_controls(
    profile: dict[str, Any], *, limit: int = 8, allow_faders: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    maximum = 48 if allow_faders else 40
    if not 1 <= limit <= maximum:
        raise ValueError(f"limit must be 1..{maximum}")
    controls = profile["controls"]
    if any(not isinstance(row, dict) for row in controls):
        raise ValueError("every controls entry must be a table")
    ranked = [
        *_diverse([row for row in controls if row.get("priority") == "core"]),
        *_diverse([row for row in controls if row.get("priority") != "core"]),
    ]
    continuous_capacity = 32 if allow_faders else 24
    selected_raw = []
    continuous_count = button_count = 0
    for row in ranked:
        button = _is_button(row)
        if button and button_count >= 16:
            continue
        if not button and continuous_count >= continuous_capacity:
            continue
        selected_raw.append(row)
        if button:
            button_count += 1
        else:
            continuous_count += 1
        if len(selected_raw) == limit:
            break
    selected_continuous = [row for row in selected_raw if not _is_button(row)]
    selected_buttons = [row for row in selected_raw if _is_button(row)]

    available = {
        group: [f"{group}-{position}" for position in range(1, 9)]
        for group in (*ENCODER_GROUPS, "fader")
    }
    if not allow_faders:
        available["fader"] = []
    selected = []
    for row in selected_continuous:
        role = str(row.get("role", "other"))
        preferences = tuple(
            group for group in plugin_seed.PREFERENCES.get(role, plugin_seed.GROUPS)
            if group in available
        )
        endpoint = next(
            (available[group].pop(0) for group in preferences if available[group]),
            None,
        )
        if endpoint is None:
            break
        mapped = {**row, "control": endpoint}
        mapped.setdefault("label", str(mapped.get("name", "Control"))[:16])
        mapped.setdefault("color", plugin_seed.ROLE_COLORS.get(role, "white"))
        selected.append(mapped)
    for row, endpoint in zip(selected_buttons, BUTTON_ENDPOINTS):
        mapped = {**row, "control": endpoint}
        mapped.setdefault("label", str(mapped.get("name", "Control"))[:16])
        mapped.setdefault("color", plugin_seed.ROLE_COLORS["switch"])
        mapped.setdefault("behavior", "toggle")
        selected.append(mapped)

    selected_keys = {
        (row.get("plugin", profile.get("plugin")), row.get("ui_parameter"))
        for row in selected
    }
    omitted = [
        row for row in controls
        if (row.get("plugin", profile.get("plugin")), row.get("ui_parameter"))
        not in selected_keys
    ]
    return selected, omitted


def core_profile(
    profile: dict[str, Any], *, limit: int = 8, allow_faders: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    selected, omitted = select_controls(profile, limit=limit, allow_faders=allow_faders)
    if not selected:
        raise ValueError(f"profile exposes no usable controls: {profile['id']}")
    result = {
        key: profile[key]
        for key in ("schema_version", "slot", "channel")
    }
    if "plugin" in profile:
        result["plugin"] = profile["plugin"]
    else:
        result["plugins"] = profile["plugins"]
    result.update({
        "id": f"{profile['id']}-core-draft",
        "name": f"{profile['name']} Core Draft",
        "description": (
            f"Role-diverse {len(selected)}-control draft derived from {profile['id']}; "
            "review musical value and hardware-test before replacing the full reference page."
        ),
        "probe": next(
            (row["control"] for row in selected if row.get("priority") == "core"),
            selected[0]["control"],
        ),
        "controls": selected,
    })
    report = {
        "source_profile": profile["id"],
        "core_profile": result["id"],
        "requested_limit": limit,
        "allow_faders": allow_faders,
        "source_controls": len(profile["controls"]),
        "selected_controls": len(selected),
        "selected_core": sum(row.get("priority") == "core" for row in selected),
        "selected_roles": sorted({str(row.get("role", "other")) for row in selected}),
        "omitted_controls": len(omitted),
        "selected": [
            {
                "control": row["control"], "name": row.get("name"),
                "role": row.get("role", "other"),
                "priority": row.get("priority", "secondary"),
                "plugin": row.get("plugin", profile.get("plugin")),
                "ui_parameter": row.get("ui_parameter"),
            }
            for row in selected
        ],
        "boundary": "Selection preserves declared priority and broad role diversity; it does not prove musical usefulness.",
    }
    return result, report


def render_markdown(reports: list[dict[str, Any]]) -> str:
    lines = ["# Compact plugin performance-core drafts", ""]
    for report in reports:
        lines.extend((
            f"## {report['source_profile']}", "",
            f"Selected {report['selected_controls']}/{report['source_controls']} controls; "
            f"{report['selected_core']} declared core; roles: "
            f"{', '.join(report['selected_roles']) or 'none'}; faders allowed: "
            f"{str(report['allow_faders']).lower()}.", "",
        ))
        for row in report["selected"]:
            plugin = f"{row['plugin']}: " if row.get("plugin") else ""
            lines.append(
                f"- {row['control']} → {plugin}{row['name']} "
                f"({row['role']}/{row['priority']}, UI {row['ui_parameter']})"
            )
        lines.extend(("", report["boundary"], ""))
    return "\n".join(lines)


def build(
    profile_paths: list[Path], output: Path, *, limit: int = 8,
    allow_faders: bool = False, force: bool = False,
) -> dict[str, Any]:
    if not profile_paths:
        raise ValueError("at least one plugin profile is required")
    sources = [path.expanduser().resolve() for path in profile_paths]
    output = output.expanduser().absolute()
    if output.is_symlink():
        raise ValueError(f"refusing symbolic-link plugin core output: {output}")
    resolved_output = output.resolve(strict=False)
    for source in sources:
        if source == resolved_output or source.is_relative_to(resolved_output):
            raise ValueError(f"plugin core output must not contain source profile: {source}")
    if output.exists() and not force:
        raise FileExistsError(f"plugin core output already exists: {output}")
    if output.exists():
        receipt = output / "plugin-core-report.json"
        if not output.is_dir() or receipt.is_symlink() or not receipt.is_file():
            raise ValueError(f"refusing to replace unrecognized plugin core output: {output}")
        try:
            previous = json.loads(receipt.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"refusing to replace invalid plugin core output: {output}") from error
        if previous.get("kind") != "mpc-plugin-core":
            raise ValueError(f"refusing to replace unrecognized plugin core output: {output}")
    profiles = [plugin_map.load_profile(path) for path in sources]
    ids = [profile["id"] for profile in profiles]
    if len(ids) != len(set(ids)):
        raise ValueError("plugin profile ids must be unique")
    cores, reports = zip(*(
        core_profile(profile, limit=limit, allow_faders=allow_faders)
        for profile in profiles
    ))
    receipt = {
        "schema_version": 1,
        "kind": "mpc-plugin-core",
        "limit": limit,
        "allow_faders": allow_faders,
        "profiles": list(reports),
        "hardware_status": "pending",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        profiles_dir = staging / "profiles"
        profiles_dir.mkdir()
        for profile in cores:
            (profiles_dir / f"{profile['id']}.toml").write_text(
                plugin_seed.render_toml(profile), encoding="utf-8"
            )
        (staging / "plugin-core-report.json").write_text(
            json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
        )
        (staging / "CORE_SELECTION.md").write_text(render_markdown(list(reports)), encoding="utf-8")
        if output.exists():
            shutil.rmtree(output)
        os.replace(staging, output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profiles", nargs="+", type=Path)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--allow-faders", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv or sys.argv[1:])
    report = build(
        args.profiles, args.output, limit=args.limit,
        allow_faders=args.allow_faders, force=args.force,
    )
    selected = sum(item["selected_controls"] for item in report["profiles"])
    source = sum(item["source_controls"] for item in report["profiles"])
    print(f"Wrote {len(report['profiles'])} core drafts with {selected}/{source} controls -> {args.output.resolve()}")
    print("Drafts only: compile against installed metadata, then compare live before replacing full profiles.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
