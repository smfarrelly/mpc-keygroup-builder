"""Create safe, explicit starter folders for common MPC workflows."""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from importlib import resources
from pathlib import Path

from . import drum_builder, plugin_map, schema, workstation


KINDS = ("workstation", "drum", "keygroup", "controller-page")


def _slug(value: str) -> str:
    result = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    if not result:
        raise ValueError("name must contain at least one letter or number")
    return result


def _receipt(kind: str, name: str, status: str, start: str) -> str:
    return json.dumps(
        {
            "schema_version": 1,
            "kind": "mpc-workflow-scaffold",
            "workflow": kind,
            "name": name,
            "software_status": status,
            "hardware_status": "deferred",
            "start_here": start,
        },
        indent=2,
    ) + "\n"


def _workstation(root: Path, family: str) -> tuple[str, str]:
    packaged = resources.files("mpc_keygroup_builder.data.showcase_recipes")
    for relative in schema.STARTER_FAMILIES[family]:
        target = root / "Recipes" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            packaged.joinpath(relative).read_text(encoding="utf-8"), encoding="utf-8"
        )
    relative = next(
        item for item in schema.STARTER_FAMILIES[family]
        if item.startswith("workstation/")
    )
    workstation.load_recipe(root / "Recipes" / relative)
    start = f"Recipes/{relative}"
    readme = f"""# Workstation starter

Start with `{start}`. Its Drum, harmony, and Melody dependencies are complete
and compatible. Replace the suggested program names with sounds available on
your MPC, then validate the tree with `mpc-recipe-audit Recipes`.

Software recipe validation: **PASS**

MPC import and listening: **DEFERRED**
"""
    return start, readme


def _drum(root: Path, name: str) -> tuple[str, str]:
    manifest = root / "manifest.toml"
    manifest.write_text(
        f"""name = {json.dumps(name)}

[[pads]]
pad = 1
sample = "Kick.wav"

[[pads]]
pad = 2
sample = "Snare.wav"

[[pads]]
pad = 3
sample = "Closed Hat.wav"
mute_group = 1

[[pads]]
pad = 4
sample = "Open Hat.wav"
mute_group = 1
""",
        encoding="utf-8",
    )
    drum_builder.load_manifest(manifest)
    (root / "Samples").mkdir()
    (root / "Samples/PLACE_WAV_FILES_HERE.txt").write_text(
        "Add Kick.wav, Snare.wav, Closed Hat.wav, and Open Hat.wav here.\n",
        encoding="utf-8",
    )
    readme = f"""# {name} Drum Program starter

`manifest.toml` passes structural validation. Add the four named WAV files to
`Samples/`, then build with an MPC-authored Drum template:

```bash
mpc-drum-build manifest.toml --samples Samples --template /path/to/template.xpm \\
  --output Program
```

Manifest validation: **PASS**

Required WAVs, template, MPC load, and listening: **PENDING**
"""
    return "manifest.toml", readme


def _keygroup(root: Path, name: str) -> tuple[str, str]:
    (root / "Samples").mkdir()
    (root / "Samples/PLACE_PITCHED_WAVS_HERE.txt").write_text(
        "Add pitched WAVs such as Piano C3.wav, Piano F#3.wav, and Piano C4.wav.\n",
        encoding="utf-8",
    )
    readme = f"""# {name} Keygroup starter

Add pitched WAVs to `Samples/`. Obtain one working Keygroup XPM saved by your
MPC; it is a schema template and is never modified. Inspect the mapping first:

```bash
mpc-keygroup Samples --template /path/to/template.xpm --name {json.dumps(name)} --dry-run
```

Then repeat with `--output {json.dumps(name + '.xpm')}`. No program is generated
until real WAVs and a template are supplied.

Scaffold status: **INPUTS REQUIRED**

MPC load and listening: **DEFERRED**
"""
    return "README.md", readme


def _controller_page(root: Path, name: str, slug: str) -> tuple[str, str]:
    profile = root / "profile.toml"
    profile.write_text(
        f"""# Replace plugin and parameter evidence before hardware use.
schema_version = 1
id = {json.dumps(slug + '-performance-draft')}
plugin = "REPLACE WITH INSTALLED PLUGIN"
name = {json.dumps(name + ' Draft')}
description = "Review-required Launch Control performance-page starter."
slot = 1
channel = 1
probe = "top-encoder-1"

[[controls]]
control = "top-encoder-1"
ui_parameter = 0
name = "REPLACE WITH PARAMETER NAME"
label = "Probe"
role = "tone"
priority = "core"
color = "yellow"
""",
        encoding="utf-8",
    )
    plugin_map.load_profile(profile)
    readme = """# Controller performance-page starter

`profile.toml` passes structural validation but deliberately contains placeholder
plugin evidence. Use `mpc-plugin-params` to find the installed plugin and exact
UI parameter, then run `mpc-plugin-map check` before assigning MIDI Learn.

Structural validation: **PASS**

Installed-content validation and hardware MIDI Learn: **PENDING**
"""
    return "profile.toml", readme


def create(kind: str, name: str, output: Path, family: str = "dusty") -> Path:
    if kind not in KINDS:
        raise ValueError(f"unknown scaffold kind: {kind}")
    if family not in schema.STARTER_FAMILIES:
        raise ValueError(f"unknown workstation family: {family}")
    if kind != "workstation" and family != "dusty":
        raise ValueError("family applies only to workstation starters")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be a non-empty string")
    slug = _slug(name)
    output = output.expanduser().resolve()
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        if kind == "workstation":
            start, readme = _workstation(staging, family)
            status = "pass"
        elif kind == "drum":
            start, readme = _drum(staging, name.strip())
            status = "inputs-required"
        elif kind == "keygroup":
            start, readme = _keygroup(staging, name.strip())
            status = "inputs-required"
        else:
            start, readme = _controller_page(staging, name.strip(), slug)
            status = "structural-pass"
        (staging / "README.md").write_text(readme, encoding="utf-8")
        (staging / "scaffold.json").write_text(
            _receipt(kind, name.strip(), status, start), encoding="utf-8"
        )
        os.replace(staging, output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return output
