"""Generate a ranked, review-required plugin performance profile draft."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from . import plugin_map, plugin_params


ROLE_WORDS = (
    ("envelope", ("attack", "decay", "sustain", "release", "envelope", " env")),
    ("tone", ("cutoff", "resonance", "filter", "tone", "color", "drive", "frequency")),
    ("movement", ("rate", "speed", "lfo", "mod", "feedback", "delay", "time", "pitch", "wow")),
    ("texture", ("noise", "crackle", "bit", "decim", "distort", "glitch", "dropout", "hum")),
    ("source", ("osc", "source", "sample", "wave", "saw", "pulse", "sub")),
    ("global", ("mix", "wet", "output", "gain", "level", "width", "volume", "amount")),
)
ROLE_COLORS = {
    "tone": "yellow", "movement": "blue", "texture": "orange", "source": "green",
    "global": "white", "envelope": "purple", "switch": "red", "other": "white",
}
GROUPS = ("top-encoder", "middle-encoder", "bottom-encoder", "fader")
PREFERENCES = {
    "tone": ("top-encoder", "middle-encoder", "bottom-encoder", "fader"),
    "movement": ("middle-encoder", "bottom-encoder", "top-encoder", "fader"),
    "texture": ("bottom-encoder", "middle-encoder", "top-encoder", "fader"),
    "global": ("fader", "top-encoder", "middle-encoder", "bottom-encoder"),
    "source": ("fader", "top-encoder", "middle-encoder", "bottom-encoder"),
    "envelope": ("fader", "middle-encoder", "top-encoder", "bottom-encoder"),
    "other": GROUPS,
}


def role(name: str, button: bool = False) -> str:
    if button:
        return "switch"
    lowered = f" {name.casefold()}"
    for candidate, words in ROLE_WORDS:
        if any(word in lowered for word in words):
            return candidate
    return "other"


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _rank(control: dict[str, Any]) -> tuple[int, int, int, str]:
    return (
        -int(control.get("usefulness_score", 0)),
        -int(bool(control.get("q_links"))),
        control["ui_parameter"],
        control["name"].casefold(),
    )


def seed_profile(plugin: dict[str, Any], slot: int, channel: int, limit: int = 40) -> dict[str, Any]:
    if not 1 <= slot <= 15:
        raise ValueError("slot must be 1..15")
    if not 1 <= channel <= 16:
        raise ValueError("channel must be 1..16")
    if not 1 <= limit <= 48:
        raise ValueError("limit must be 1..48")
    buttons = []
    continuous = []
    for control in plugin["controls"]:
        is_button = any(
            token in control["control_type"].casefold() for token in plugin_map.BUTTON_TYPES
        )
        (buttons if is_button else continuous).append(control)
    continuous.sort(key=_rank)
    buttons.sort(key=_rank)
    selected_continuous = continuous[: min(32, limit)]
    selected_buttons = buttons[: min(16, limit - len(selected_continuous))]
    available = {group: [f"{group}-{position}" for position in range(1, 9)] for group in GROUPS}
    rows = []
    for index, control in enumerate(selected_continuous):
        control_role = role(control["name"])
        endpoint = next(
            available[group].pop(0)
            for group in PREFERENCES[control_role]
            if available[group]
        )
        rows.append(
            {
                "control": endpoint,
                "ui_parameter": control["ui_parameter"],
                "name": control["name"],
                "label": control["name"][:16],
                "role": control_role,
                "priority": "core" if index < 16 else "secondary",
                "color": ROLE_COLORS[control_role],
            }
        )
    button_endpoints = [
        *(f"upper-button-{position}" for position in range(1, 9)),
        *(f"lower-button-{position}" for position in range(1, 9)),
    ]
    for control, endpoint in zip(selected_buttons, button_endpoints):
        rows.append(
            {
                "control": endpoint,
                "ui_parameter": control["ui_parameter"],
                "name": control["name"],
                "label": control["name"][:16],
                "role": "switch",
                "priority": "core" if control.get("usefulness_score", 0) >= 3 else "secondary",
                "color": ROLE_COLORS["switch"],
                "behavior": "toggle",
            }
        )
    if not rows:
        raise ValueError(f"plugin exposes no usable controls: {plugin['plugin']}")
    probe = next((item["control"] for item in rows if item["priority"] == "core"), rows[0]["control"])
    return {
        "schema_version": 1,
        "id": f"{_slug(plugin['plugin'])}-performance-draft",
        "plugin": plugin["plugin"],
        "name": f"{plugin['plugin']} Draft",
        "description": "Ranked profile seed; review roles, layout, labels, and musical usefulness before hardware use.",
        "slot": slot,
        "channel": channel,
        "probe": probe,
        "controls": rows,
        "source_control_count": plugin["control_count"],
    }


def render_toml(profile: dict[str, Any]) -> str:
    lines = [
        "# Generated draft: validate, review, and rename before treating it as a performance page.",
        "# Hardware status remains pending.",
        "schema_version = 1",
        f"id = {json.dumps(profile['id'])}",
        f"plugin = {json.dumps(profile['plugin'])}",
        f"name = {json.dumps(profile['name'])}",
        f"description = {json.dumps(profile['description'])}",
        f"slot = {profile['slot']}",
        f"channel = {profile['channel']}",
        f"probe = {json.dumps(profile['probe'])}",
        "",
    ]
    for control in profile["controls"]:
        lines.extend(
            (
                "[[controls]]",
                f"control = {json.dumps(control['control'])}",
                f"ui_parameter = {control['ui_parameter']}",
                f"name = {json.dumps(control['name'])}",
                f"label = {json.dumps(control['label'])}",
                f"role = {json.dumps(control['role'])}",
                f"priority = {json.dumps(control['priority'])}",
                f"color = {json.dumps(control['color'])}",
            )
        )
        if "behavior" in control:
            lines.append(f"behavior = {json.dumps(control['behavior'])}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plugin")
    parser.add_argument("--synth-root", type=Path, required=True)
    parser.add_argument("--project", type=Path)
    parser.add_argument("--slot", type=int, required=True)
    parser.add_argument("--channel", type=int, required=True)
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv or sys.argv[1:])
    catalog = plugin_params.catalog(args.synth_root.expanduser().resolve(), args.project)
    matches = [
        item for item in catalog["plugins"]
        if _normalized(item["plugin"]) == _normalized(args.plugin)
    ]
    if not matches:
        raise ValueError(f"plugin content not found: {args.plugin}")
    output = args.output.expanduser().resolve()
    if output.exists() and not args.force:
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    profile = seed_profile(matches[0], args.slot, args.channel, args.limit)
    output.write_text(render_toml(profile), encoding="utf-8")
    print(
        f"Wrote {len(profile['controls'])}/{profile['source_control_count']} ranked controls -> {output}"
    )
    print("Draft only: run mpc-plugin-map check, review the layout, then test one probe on hardware.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
