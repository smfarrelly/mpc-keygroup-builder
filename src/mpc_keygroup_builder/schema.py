"""Discover published schemas and semantically validate declarative project files."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Callable

from . import (
    controller_capacity,
    device,
    drum_builder,
    harmony,
    ideas,
    keygroup_variant,
    kit_select,
    layout,
    melody,
    midi_control,
    plugin_map,
    rig,
    workstation,
)


@dataclass(frozen=True)
class SchemaSpec:
    name: str
    summary: str
    filename: str
    examples: tuple[str, ...]
    validator: Callable[[Path], None]


def _rig(path: Path) -> None:
    result = rig.validate(rig.load(path))
    if result["errors"]:
        raise ValueError("; ".join(result["errors"]))


def _midi_map(path: Path) -> None:
    document, devices = midi_control.load_map(path)
    result = midi_control.validate(document, devices)
    if result["errors"]:
        raise ValueError("; ".join(result["errors"]))


SCHEMAS = {
    "controller-capacity": SchemaSpec(
        "controller-capacity",
        "Launch Control Custom Mode slots and MIDI channel reservations",
        "controller-capacity.schema.json",
        ("midi/controller-capacity.toml",),
        lambda path: controller_capacity.load_plan(path),
    ),
    "device-profile": SchemaSpec(
        "device-profile",
        "MPC keyboard and pad-bank geometry",
        "device-profile.schema.json",
        ("devices/mpc-key-37.toml", "devices/mpc-key-61.toml"),
        lambda path: device.load_device(path),
    ),
    "drum-manifest": SchemaSpec(
        "drum-manifest",
        "Drum pads, samples, velocity layers, and mute groups",
        "drum-manifest.schema.json",
        ("inventory/fg-vinyl-layered-kit.toml",),
        lambda path: drum_builder.load_manifest(path),
    ),
    "drum-recipe": SchemaSpec(
        "drum-recipe",
        "Role-addressed deterministic Drum pattern",
        "drum-recipe.schema.json",
        ("recipes/drums/dusty-pocket.toml", "recipes/drums/electro-grid.toml"),
        lambda path: ideas.load_recipe(path),
    ),
    "harmony-recipe": SchemaSpec(
        "harmony-recipe",
        "Chord progression and constrained Bass pattern",
        "harmony-recipe.schema.json",
        ("recipes/harmony/dusty-dorian.toml", "recipes/harmony/ambient-minor.toml"),
        lambda path: harmony.load_recipe(path),
    ),
    "layout-preset": SchemaSpec(
        "layout-preset",
        "Reusable semantic or sequential pad-layout strategy",
        "layout-preset.schema.json",
        ("layouts/classic-mpc.toml", "layouts/right-handed-performance.toml"),
        lambda path: layout.load_preset(path),
    ),
    "kit-recipe": SchemaSpec(
        "kit-recipe",
        "Deterministic semantic cross-library Drum selection",
        "kit-recipe.schema.json",
        ("recipes/kits/dusty-cross-library.toml", "recipes/kits/ambient-percussion.toml"),
        lambda path: kit_select.load_recipe(path),
    ),
    "melody-recipe": SchemaSpec(
        "melody-recipe",
        "Scale-safe repeating and varied Melody motif",
        "melody-recipe.schema.json",
        ("recipes/melody/dusty-answer.toml", "recipes/melody/electro-hook.toml"),
        lambda path: melody.load_recipe(path),
    ),
    "keygroup-variant": SchemaSpec(
        "keygroup-variant",
        "Preservation-safe expressive Keygroup parameter changes",
        "keygroup-variant.schema.json",
        ("variants/keygroups/warm.toml", "variants/keygroups/pluck.toml"),
        lambda path: keygroup_variant.load_variant(path),
    ),
    "midi-control-map": SchemaSpec(
        "midi-control-map",
        "Launch Control modes, routes, messages, and target devices",
        "midi-control-map.schema.json",
        ("midi/maps/fg-key37-lcxl3-volcas.toml", "midi/maps/fg-key37-lcxl3-volcas-bridge.toml"),
        _midi_map,
    ),
    "midi-device": SchemaSpec(
        "midi-device",
        "External MIDI device CC and note chart",
        "midi-device.schema.json",
        ("midi/devices/volca-bass.toml", "midi/devices/volca-keys.toml"),
        lambda path: midi_control.load_device(path),
    ),
    "plugin-profile": SchemaSpec(
        "plugin-profile",
        "Launch Control performance page for one or more MPC plugins",
        "plugin-profile.schema.json",
        ("midi/plugins/vintage-filter-performance.toml",),
        lambda path: plugin_map.load_profile(path),
    ),
    "rig-profile": SchemaSpec(
        "rig-profile",
        "Tracks, devices, controller groups, and hardware acceptance checks",
        "rig-profile.schema.json",
        ("rigs/fg-vinyl-scratchpad.toml", "rigs/fg-volca-direct-123.toml"),
        _rig,
    ),
    "workstation-recipe": SchemaSpec(
        "workstation-recipe",
        "Compatible Drum, harmony, Melody, and program selection",
        "workstation-recipe.schema.json",
        ("recipes/workstation/dusty-scratchpad.toml", "recipes/workstation/ambient-scratchpad.toml"),
        lambda path: workstation.load_recipe(path),
    ),
}

STARTER_FAMILIES = {
    "dusty": (
        "drums/dusty-pocket.toml", "harmony/dusty-dorian.toml",
        "melody/dusty-answer.toml", "workstation/dusty-scratchpad.toml",
    ),
    "ambient": (
        "drums/sparse-weird.toml", "harmony/ambient-minor.toml",
        "melody/ambient-drift.toml", "workstation/ambient-scratchpad.toml",
    ),
    "electro": (
        "drums/electro-grid.toml", "harmony/electro-minor.toml",
        "melody/electro-hook.toml", "workstation/electro-scratchpad.toml",
    ),
    "funk": (
        "drums/funk-machine.toml", "harmony/funk-minor.toml",
        "melody/funk-call.toml", "workstation/funk-scratchpad.toml",
    ),
    "house": (
        "drums/house-foundation.toml", "harmony/house-minor.toml",
        "melody/house-spark.toml", "workstation/house-scratchpad.toml",
    ),
    "weird": (
        "drums/texture-collage.toml", "harmony/strange-mixolydian.toml",
        "melody/odd-signal.toml", "workstation/weird-scratchpad.toml",
    ),
}


def schema_document(name: str) -> dict:
    spec = SCHEMAS[name]
    resource = resources.files("mpc_keygroup_builder.data.schemas").joinpath(spec.filename)
    return json.loads(resource.read_text(encoding="utf-8"))


def catalog() -> list[dict]:
    return [
        {
            "name": spec.name,
            "summary": spec.summary,
            "schema": spec.filename,
            "examples": list(spec.examples),
        }
        for spec in SCHEMAS.values()
    ]


def validate_files(name: str, paths: list[Path]) -> list[dict]:
    spec = SCHEMAS[name]
    results = []
    for path in paths:
        resolved = path.expanduser().resolve()
        try:
            spec.validator(resolved)
        except (OSError, ValueError, tomllib.TOMLDecodeError) as error:
            results.append({"path": str(resolved), "status": "fail", "error": str(error)})
        else:
            results.append({"path": str(resolved), "status": "pass", "error": None})
    return results


def initialize_workstation(output: Path, family: str) -> Path:
    output = output.expanduser().resolve()
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    packaged = resources.files("mpc_keygroup_builder.data.showcase_recipes")
    try:
        for relative in STARTER_FAMILIES[family]:
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(packaged.joinpath(relative).read_text(encoding="utf-8"), encoding="utf-8")
        workstation_file = next(
            relative for relative in STARTER_FAMILIES[family] if relative.startswith("workstation/")
        )
        (staging / "README.md").write_text(
            f"# {family.title()} workstation recipe starter\n\n"
            f"Start with `{workstation_file}`. Its sibling references are already valid.\n"
            "Edit values, then run `mpc-schema validate` for each recipe type.\n",
            encoding="utf-8",
        )
        workstation.load_recipe(staging / workstation_file)
        os.replace(staging, output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version="%(prog)s 1")
    commands = parser.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("list", help="list published declarative formats")
    listing.add_argument("--json", action="store_true")
    show = commands.add_parser("show", help="print or copy one JSON Schema document")
    show.add_argument("schema", choices=sorted(SCHEMAS))
    show.add_argument("--output", type=Path)
    show.add_argument("--force", action="store_true")
    initialize = commands.add_parser("init", help="create a complete editable recipe starter")
    initialize.add_argument("template", choices=("workstation",))
    initialize.add_argument("--family", choices=sorted(STARTER_FAMILIES), default="dusty")
    initialize.add_argument("--output", type=Path, required=True)
    validate = commands.add_parser("validate", help="run the native semantic validator")
    validate.add_argument("schema", choices=sorted(SCHEMAS))
    validate.add_argument("files", type=Path, nargs="+")
    validate.add_argument("--json", action="store_true")
    args = parser.parse_args(argv or sys.argv[1:])

    if args.command == "list":
        rows = catalog()
        if args.json:
            print(json.dumps({"schema_version": 1, "schemas": rows}, indent=2))
        else:
            for row in rows:
                print(f"{row['name']:<22} {row['summary']}")
        return 0
    if args.command == "show":
        rendered = json.dumps(schema_document(args.schema), indent=2) + "\n"
        if args.output:
            output = args.output.expanduser().resolve()
            if output.exists() and not args.force:
                raise FileExistsError(output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(rendered, encoding="utf-8")
            print(f"Wrote: {output}")
        else:
            print(rendered, end="")
        return 0
    if args.command == "init":
        path = initialize_workstation(args.output, args.family)
        print(f"Wrote {args.family} workstation starter: {path}")
        return 0

    results = validate_files(args.schema, args.files)
    if args.json:
        print(json.dumps({"schema": args.schema, "results": results}, indent=2))
    else:
        for result in results:
            detail = f" — {result['error']}" if result["error"] else ""
            print(f"{result['status'].upper():<4} {result['path']}{detail}")
    return 2 if any(result["status"] == "fail" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
