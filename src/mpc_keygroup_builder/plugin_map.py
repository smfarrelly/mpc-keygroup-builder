"""Compile role-based Launch Control pages from discovered MPC plugin controls."""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import shutil
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any

from . import launch_control, plugin_params


ENDPOINT_GROUPS = {
    "top-encoder": 20,
    "middle-encoder": 28,
    "bottom-encoder": 36,
    "fader": 44,
    "upper-button": 52,
    "lower-button": 60,
}
ENDPOINT = re.compile(
    r"^(top-encoder|middle-encoder|bottom-encoder|fader|upper-button|lower-button)-([1-8])$"
)
BUTTON_TYPES = ("button", "switch", "btn")


def _load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        return tomllib.load(stream)


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def endpoint_cc(endpoint: str) -> int:
    match = ENDPOINT.fullmatch(endpoint)
    if match is None:
        raise ValueError(f"invalid Launch Control endpoint {endpoint!r}")
    return ENDPOINT_GROUPS[match.group(1)] + int(match.group(2)) - 1


def load_profile(path: Path) -> dict[str, Any]:
    document = _load_toml(path)
    if document.get("schema_version") != 1:
        raise ValueError(f"{path}: plugin profile requires schema_version=1")
    for field in ("id", "name", "description"):
        if not isinstance(document.get(field), str) or not document[field]:
            raise ValueError(f"{path}: profile requires {field}")
    plugin = document.get("plugin")
    plugins = document.get("plugins")
    has_plugin = isinstance(plugin, str) and bool(plugin)
    has_plugins = (
        isinstance(plugins, list)
        and bool(plugins)
        and all(isinstance(item, str) and item for item in plugins)
    )
    if has_plugin == has_plugins:
        raise ValueError(f"{path}: profile requires exactly one of plugin or plugins")
    if has_plugins and len(plugins) != len(set(plugins)):
        raise ValueError(f"{path}: plugins must not contain duplicates")
    channel = document.get("channel")
    slot = document.get("slot")
    if not isinstance(channel, int) or not 1 <= channel <= 16:
        raise ValueError(f"{path}: channel must be 1..16")
    if not isinstance(slot, int) or not 1 <= slot <= 15:
        raise ValueError(f"{path}: slot must be 1..15")
    controls = document.get("controls")
    if not isinstance(controls, list) or not controls:
        raise ValueError(f"{path}: profile requires [[controls]]")
    probe = document.get("probe")
    if probe is not None and (not isinstance(probe, str) or ENDPOINT.fullmatch(probe) is None):
        raise ValueError(f"{path}: probe must name a valid Launch Control endpoint")
    document["source_path"] = str(path.resolve())
    return document


def profile_plugins(profile: dict[str, Any]) -> list[str]:
    return [profile["plugin"]] if "plugin" in profile else list(profile["plugins"])


def _plugin_index(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {_normalized(item["plugin"]): item for item in catalog["plugins"]}


def validate_profile(
    profile: dict[str, Any],
    catalog: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    catalog_plugins = _plugin_index(catalog)
    declared_plugins = profile_plugins(profile)
    discovered_by_plugin: dict[str, dict[int, dict[str, Any]]] = {}
    for name in declared_plugins:
        plugin = catalog_plugins.get(_normalized(name))
        if plugin is None:
            errors.append(f"plugin content not found: {name}")
        else:
            discovered_by_plugin[name] = {
                item["ui_parameter"]: item for item in plugin["controls"]
            }
    endpoints: set[str] = set()
    messages: set[tuple[int, int]] = set()
    rows = []
    for item in profile["controls"]:
        endpoint = item.get("control")
        if not isinstance(endpoint, str) or ENDPOINT.fullmatch(endpoint) is None:
            errors.append(f"invalid Launch Control endpoint: {endpoint!r}")
            continue
        if endpoint in endpoints:
            errors.append(f"duplicate endpoint: {endpoint}")
        endpoints.add(endpoint)
        plugin_name = item.get("plugin", profile.get("plugin"))
        if plugin_name not in declared_plugins:
            errors.append(f"{endpoint}: undeclared plugin {plugin_name!r}")
            continue
        discovered = discovered_by_plugin.get(plugin_name)
        if discovered is None:
            continue
        ui_parameter = item.get("ui_parameter")
        if not isinstance(ui_parameter, int) or ui_parameter < 0:
            errors.append(f"{endpoint}: ui_parameter must be a nonnegative integer")
            continue
        source = discovered.get(ui_parameter)
        if source is None:
            errors.append(f"{endpoint}: UI parameter {ui_parameter} not found in {plugin_name}")
            continue
        expected_name = item.get("name")
        source_names = [source["name"], *source.get("aliases", [])]
        if not isinstance(expected_name, str) or _normalized(expected_name) not in {
            _normalized(name) for name in source_names
        }:
            errors.append(
                f"{endpoint}: parameter {ui_parameter} is {source['name']!r}, "
                f"not {expected_name!r}"
            )
        cc = endpoint_cc(endpoint)
        signature = (profile["channel"], cc)
        if signature in messages:
            errors.append(f"duplicate MIDI message ch{signature[0]}/CC{signature[1]}")
        messages.add(signature)
        endpoint_kind = endpoint.rsplit("-", 1)[0]
        source_type = source["control_type"].casefold()
        is_button = any(token in source_type for token in BUTTON_TYPES)
        if endpoint_kind.endswith("button") and not is_button:
            warnings.append(f"{endpoint}: {source['name']} is not described as a button")
        if not endpoint_kind.endswith("button") and is_button:
            warnings.append(f"{endpoint}: {source['name']} is described as a button")
        rows.append(
            {
                "plugin": plugin_name,
                "mode": profile["name"],
                "slot": profile["slot"],
                "channel": profile["channel"],
                "control": endpoint,
                "cc": cc,
                "label": item.get("label", source["name"])[:16],
                "role": item.get("role", "other"),
                "priority": item.get("priority", "secondary"),
                "color": item.get("color", "white"),
                "behavior": item.get("behavior", "toggle" if is_button else "absolute"),
                "name": source["name"],
                "ui_parameter": ui_parameter,
                "mpc_parameter": source["mpc_parameter"],
                "evidence": source["mpc_parameter_basis"],
                "q_links": source.get("q_links", []),
                "control_type": source["control_type"],
            }
        )
    if not any(row["priority"] == "core" for row in rows):
        warnings.append("profile has no core controls")
    if profile.get("probe") and profile["probe"] not in endpoints:
        errors.append(f"probe endpoint is not mapped: {profile['probe']}")
    return {"errors": sorted(set(errors)), "warnings": sorted(set(warnings)), "controls": rows}


def validate_batch(
    profiles: list[dict[str, Any]],
    catalog: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    slots: set[int] = set()
    channels: set[int] = set()
    ids: set[str] = set()
    results = []
    for profile in profiles:
        if profile["id"] in ids:
            errors.append(f"duplicate profile id: {profile['id']}")
        ids.add(profile["id"])
        if profile["slot"] in slots:
            errors.append(f"duplicate Custom Mode slot: {profile['slot']}")
        slots.add(profile["slot"])
        if profile["channel"] in channels:
            warnings.append(f"shared plugin control channel: {profile['channel']}")
        channels.add(profile["channel"])
        result = validate_profile(profile, catalog)
        errors.extend(f"{profile['id']}: {message}" for message in result["errors"])
        warnings.extend(f"{profile['id']}: {message}" for message in result["warnings"])
        results.append({"profile": profile, **result})
    return {
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "profiles": results,
    }


def _csv(headers: list[str], rows: list[dict[str, Any]]) -> str:
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=headers, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def _components_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "slot": row["slot"],
            "mode": row["mode"],
            "output": "usb",
            "control": row["control"],
            "message": "cc",
            "channel": row["channel"],
            "number": row["cc"],
            "min": 0,
            "max": 127,
            "behavior": row["behavior"],
            "display_name": row["label"],
            "color": row["color"],
        }
        for row in result["controls"]
    ]


def _learn_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "mode": row["mode"],
            "control": row["control"],
            "channel": row["channel"],
            "cc": row["cc"],
            "plugin": row["plugin"],
            "plugin_control": row["name"],
            "ui_parameter": row["ui_parameter"],
            "mpc_parameter": row["mpc_parameter"],
            "evidence": row["evidence"],
            "role": row["role"],
            "priority": row["priority"],
            "hardware_status": "pending",
        }
        for row in result["controls"]
    ]


def render_layout(result: dict[str, Any]) -> str:
    profile = result["profile"]
    plugins = profile_plugins(profile)
    lines = [
        f"# {profile['name']}",
        "",
        profile["description"],
        "",
        f"Custom Mode slot {profile['slot']}; MIDI channel {profile['channel']}; USB output.",
        "",
    ]
    for group in ENDPOINT_GROUPS:
        rows = [row for row in result["controls"] if row["control"].startswith(group)]
        if not rows:
            continue
        lines.extend((f"## {group.replace('-', ' ').title()}s", ""))
        for row in sorted(rows, key=lambda item: int(item["control"].rsplit("-", 1)[1])):
            qlink = f"; Q-Link: {', '.join(row['q_links'])}" if row["q_links"] else ""
            plugin = f"{row['plugin']}: " if len(plugins) > 1 else ""
            lines.append(
                f"- **{row['control']}** — {row['label']} → {plugin}{row['name']} "
                f"(ch {row['channel']}, CC {row['cc']}, MPC {row['mpc_parameter']}, "
                f"{row['evidence']}, {row['role']}/{row['priority']}{qlink})"
            )
        lines.append("")
    if result["warnings"]:
        lines.extend(("## Warnings", "", *(f"- {item}" for item in result["warnings"]), ""))
    return "\n".join(lines).rstrip() + "\n"


def capture_reference(
    captures: list[Path],
    project: Path | None,
) -> dict[str, Any]:
    inspected = [launch_control.inspect(path) for path in captures]
    audited = launch_control.audit(project, captures)["captures"] if project else []
    audit_by_path = {item["path"]: item for item in audited}
    rows = []
    control_rows = []
    for item in inspected:
        audit = audit_by_path.get(item["path"], {})
        rows.append(
            {
                "name": item["name"],
                "path": item["path"],
                "channel": item["primary_channel"],
                "enabled_controls": item["enabled_count"],
                "project_matches": audit.get("matched_control_count", 0),
                "sha256": item["sha256"],
            }
        )
        audited_controls = {
            control["control"]: control for control in audit.get("controls", [])
        }
        for control in item["controls"]:
            if not control["enabled"]:
                continue
            matched = audited_controls.get(control["control"], {})
            control_rows.append(
                {
                    "mode": item["name"],
                    "control": control["control"],
                    "channel": control["channel"],
                    "number": control["number"],
                    "label": control["label"],
                    "learned_targets": "; ".join(matched.get("learned_targets", [])),
                }
            )
    return {"captures": rows, "controls": control_rows}


def render_capture_comparison(
    profiles: list[dict[str, Any]],
    reference: dict[str, Any],
) -> str:
    used_channels = {item["channel"] for item in reference["captures"] if item["channel"]}
    lines = [
        "# Existing capture comparison",
        "",
        "The proposed pages are additive. They do not replace or rewrite captured SysEx files.",
        "",
        "## Captured modes",
        "",
    ]
    for item in reference["captures"]:
        lines.append(
            f"- **{item['name']}** — channel {item['channel'] or 'mixed/unknown'}, "
            f"{item['enabled_controls']} enabled controls, "
            f"{item['project_matches']} matching project MIDI Learn assignments."
        )
    lines.extend(("", "## Proposed pages", ""))
    for profile in profiles:
        collision = "CHANNEL COLLISION" if profile["channel"] in used_channels else "channel available"
        lines.append(
            f"- Slot {profile['slot']}: **{profile['name']}**, channel {profile['channel']} — {collision}."
        )
    lines.extend(
        (
            "",
            "OPx-4 and Jura retain their captured CC conventions. The new pages use one "
            "memorize-once convention on their own channels: top encoders CC20–27, middle "
            "CC28–35, bottom CC36–43, faders CC44–51, upper buttons CC52–59, and lower "
            "buttons CC60–67.",
            "",
        )
    )
    return "\n".join(lines)


def render_hardware_checklist(results: list[dict[str, Any]]) -> str:
    lines = [
        "# Plugin mapping minimal verification",
        "",
        "This work does not require the Volca MIDI splitter. Perform it later directly between "
        "the Launch Control XL 3 and MPC.",
        "",
        "For each plugin, first learn only the named probe control, move it across its full "
        "range, save an MPC-authored project, and inspect that XPJ before learning the rest.",
        "",
    ]
    for result in results:
        profile = result["profile"]
        plugins = profile_plugins(profile)
        core = [row for row in result["controls"] if row["priority"] == "core"]
        probe = next(
            (row for row in result["controls"] if row["control"] == profile.get("probe")),
            core[0] if core else result["controls"][0],
        )
        load_step = (
            f"- [ ] Load **{plugins[0]}** on a dedicated MPC track."
            if len(plugins) == 1
            else f"- [ ] On one test audio track, load this insert chain in order: "
            + ", ".join(f"**{item}**" for item in plugins)
            + "."
        )
        evidence_step = (
            "- [ ] Inspect the XPJ; promote the plugin's +4096 parameter relationship only if the probe agrees."
            if len(plugins) == 1
            else "- [ ] Inspect the XPJ; promote only the probed effect's +4096 parameter relationship."
        )
        lines.extend(
            (
                f"## {profile['name']}",
                "",
                load_step,
                f"- [ ] Create Components mode slot {profile['slot']} on channel {profile['channel']} from its worksheet.",
                f"- [ ] Probe: learn **{probe['label']}** from {probe['control']} (CC {probe['cc']}) to **{probe['plugin']} → {probe['name']}**.",
                "- [ ] Confirm minimum, midpoint, maximum, pickup behavior, and no unrelated movement.",
                "- [ ] Save/reload a small XPJ and verify the assignment persists.",
                evidence_step,
                f"- [ ] Learn and smoke-test the remaining {len(result['controls']) - 1} controls after the probe passes.",
                "",
            )
        )
    return "\n".join(lines).rstrip() + "\n"


def compile_batch(
    profiles: list[dict[str, Any]],
    catalog: dict[str, Any],
    output: Path,
    captures: list[Path] | None = None,
    project: Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    validation = validate_batch(profiles, catalog)
    if validation["errors"]:
        raise ValueError("invalid plugin mapping batch: " + "; ".join(validation["errors"]))
    output = output.expanduser().resolve()
    if output.exists() and not force:
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        summary_rows = []
        all_components = []
        all_learn = []
        for result in validation["profiles"]:
            profile = result["profile"]
            folder = staging / profile["id"]
            folder.mkdir()
            components = _components_rows(result)
            learn = _learn_rows(result)
            all_components.extend(components)
            all_learn.extend(learn)
            (folder / "launch-control-components.csv").write_text(
                _csv(list(components[0]), components), encoding="utf-8"
            )
            (folder / "mpc-midi-learn.csv").write_text(
                _csv(list(learn[0]), learn), encoding="utf-8"
            )
            (folder / "CONTROL_LAYOUT.md").write_text(render_layout(result), encoding="utf-8")
            (folder / "profile.json").write_text(
                json.dumps(result, indent=2) + "\n", encoding="utf-8"
            )
            summary_rows.append(
                {
                    "profile": profile["id"],
                    "plugin": "; ".join(profile_plugins(profile)),
                    "slot": profile["slot"],
                    "channel": profile["channel"],
                    "controls": len(result["controls"]),
                    "core_controls": sum(row["priority"] == "core" for row in result["controls"]),
                    "warnings": len(result["warnings"]),
                }
            )
        (staging / "profile-summary.csv").write_text(
            _csv(list(summary_rows[0]), summary_rows), encoding="utf-8"
        )
        (staging / "launch-control-components-all.csv").write_text(
            _csv(list(all_components[0]), all_components), encoding="utf-8"
        )
        (staging / "mpc-midi-learn-all.csv").write_text(
            _csv(list(all_learn[0]), all_learn), encoding="utf-8"
        )
        (staging / "HARDWARE_CHECKLIST.md").write_text(
            render_hardware_checklist(validation["profiles"]), encoding="utf-8"
        )
        reference = capture_reference(captures or [], project)
        (staging / "existing-capture-reference.csv").write_text(
            _csv(
                ["name", "path", "channel", "enabled_controls", "project_matches", "sha256"],
                reference["captures"],
            ),
            encoding="utf-8",
        )
        (staging / "existing-capture-controls.csv").write_text(
            _csv(
                ["mode", "control", "channel", "number", "label", "learned_targets"],
                reference["controls"],
            ),
            encoding="utf-8",
        )
        (staging / "CAPTURE_COMPARISON.md").write_text(
            render_capture_comparison(profiles, reference), encoding="utf-8"
        )
        manifest = {
            "schema_version": 1,
            "profiles": summary_rows,
            "validation": {"errors": validation["errors"], "warnings": validation["warnings"]},
            "capture_reference": reference,
            "evidence_boundary": (
                "UI names are discovered from installed content. MPC IDs remain hypotheses until "
                "a same-plugin MPC-authored XPJ verifies the relationship."
            ),
        }
        (staging / "batch.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        if output.exists():
            shutil.rmtree(output)
        os.replace(staging, output)
        return manifest
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="validate profiles against installed plugin UI metadata")
    compile_parser = commands.add_parser("compile", help="compile profiles into Components and MPC worksheets")
    for command in (check, compile_parser):
        command.add_argument("profiles", type=Path, nargs="+")
        command.add_argument("--synth-root", type=Path, required=True)
        command.add_argument("--project", type=Path, help="optional MPC XPJ evidence")
    compile_parser.add_argument("--capture", type=Path, action="append", default=[])
    compile_parser.add_argument("--output", type=Path, required=True)
    compile_parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    profiles = sorted((load_profile(path) for path in args.profiles), key=lambda item: item["slot"])
    catalog = plugin_params.catalog(args.synth_root, args.project)
    validation = validate_batch(profiles, catalog)
    if args.command == "check":
        print(json.dumps({"errors": validation["errors"], "warnings": validation["warnings"]}, indent=2))
        return 2 if validation["errors"] else 0
    manifest = compile_batch(
        profiles,
        catalog,
        args.output,
        captures=args.capture,
        project=args.project,
        force=args.force,
    )
    print(
        f"compiled {len(manifest['profiles'])} plugin profiles -> "
        f"{args.output.expanduser().resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
