"""Generate a freely redistributable end-to-end MPC workflow demonstration."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import shutil
import struct
import tempfile
import wave
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

from .arrangement import arrange_idea, render_markdown as render_arrangement_markdown
from .arrangement import render_section
from .catalog import build_catalog
from .bundle_verify import verify_bundle
from .drum_builder import build_drum_program, load_manifest
from .kit_select import load_recipe as load_kit_recipe
from .kit_select import render_manifest, render_markdown as render_selection_markdown
from .kit_select import select_kit, stage_audio
from .model import from_xpm
from .testing import test_program
from .workstation import generate_idea as generate_workstation
from .workstation import load_recipe as load_workstation
from .workstation import render_markdown as render_workstation_markdown
from .workstation import render_midi as render_workstation_midi


SAMPLE_RATE = 44_100
SOUNDS = (
    ("BD Synthetic Deep.wav", "kick", "kick", 0.42, 54.0),
    ("BD Synthetic Tight.wav", "kick", "kick", 0.24, 72.0),
    ("BD Synthetic Soft.wav", "kick", "kick", 0.55, 46.0),
    ("SD Synthetic Snap.wav", "snare", "snare", 0.28, 185.0),
    ("SD Synthetic Body.wav", "snare", "snare", 0.43, 150.0),
    ("SD Synthetic Soft.wav", "snare", "snare", 0.34, 125.0),
    ("Clap Synthetic Wide.wav", "clap", "clap", 0.31, 0.0),
    ("Rim Synthetic Wood.wav", "rim", "rim", 0.18, 720.0),
    ("CH Synthetic Crisp.wav", "hihat.closed", "hat", 0.12, 0.0),
    ("OH Synthetic Air.wav", "hihat.open", "hat", 0.58, 0.0),
    ("Tom Synthetic Low.wav", "tom", "tom", 0.46, 92.0),
    ("Tom Synthetic High.wav", "tom", "tom", 0.35, 164.0),
    ("Cymbal Synthetic Wash.wav", "cymbal", "cymbal", 0.86, 0.0),
    ("Cymbal Synthetic Bell.wav", "cymbal", "cymbal", 0.62, 510.0),
    ("Perc Synthetic Click.wav", "percussion", "rim", 0.16, 980.0),
    ("Perc Synthetic Shaker.wav", "percussion", "hat", 0.33, 0.0),
)


def _clamp(value: float) -> int:
    return max(-32768, min(32767, round(value * 32767)))


def _write_sound(path: Path, kind: str, duration: float, frequency: float, seed: int) -> None:
    rng = random.Random(seed)
    frames = []
    previous_noise = 0.0
    for index in range(round(SAMPLE_RATE * duration)):
        time = index / SAMPLE_RATE
        progress = time / duration
        noise = rng.uniform(-1.0, 1.0)
        high_noise = noise - previous_noise * 0.72
        previous_noise = noise
        if kind == "kick":
            phase = 2 * math.pi * (frequency * time + 42 * duration * (1 - math.exp(-8 * progress)))
            value = math.sin(phase) * math.exp(-7 * progress)
            value += 0.12 * high_noise * math.exp(-70 * progress)
        elif kind == "snare":
            body = math.sin(2 * math.pi * frequency * time) * math.exp(-12 * progress)
            value = 0.42 * body + 0.58 * high_noise * math.exp(-7 * progress)
        elif kind == "clap":
            bursts = sum(math.exp(-95 * abs(time - offset)) for offset in (0.0, 0.025, 0.052))
            value = high_noise * min(1.0, bursts) * math.exp(-3 * progress)
        elif kind == "hat":
            value = high_noise * math.exp(-9 * progress)
            value += 0.22 * math.sin(2 * math.pi * 6_137 * time) * math.exp(-11 * progress)
        elif kind == "cymbal":
            metallic = sum(
                math.sin(2 * math.pi * ratio * (frequency or 430) * time)
                for ratio in (1.0, 1.41, 1.73, 2.31)
            ) / 4
            value = (0.52 * metallic + 0.48 * high_noise) * math.exp(-4 * progress)
        else:
            value = math.sin(2 * math.pi * frequency * time) * math.exp(-12 * progress)
            value += 0.18 * high_noise * math.exp(-35 * progress)
        fade_in = min(1.0, index / 24)
        frames.append(_clamp(0.72 * value * fade_in))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(SAMPLE_RATE)
        stream.writeframes(b"".join(struct.pack("<h", value) for value in frames))


def write_drum_template(path: Path) -> None:
    pads = {f"value{index}": 0 for index in range(128)}
    root = ET.Element("MPCVObject")
    program = ET.SubElement(root, "Program", type="Drum")
    ET.SubElement(program, "ProgramName").text = "Portable Template"
    ET.SubElement(program, "ProgramPads").text = json.dumps(
        {"ProgramPads": {"Universal": {"value0": True}, "Type": {"value0": 1}, "pads": pads}}
    )
    note_map = ET.SubElement(program, "PadNoteMap")
    bank_a = (37, 36, 42, 82, 40, 38, 46, 44, 48, 47, 45, 43, 49, 55, 51, 53)
    note_values = bank_a + tuple(note for note in range(128) if note not in bank_a)
    for number, note in enumerate(note_values, 1):
        pad_note = ET.SubElement(note_map, "PadNote", number=str(number))
        ET.SubElement(pad_note, "Note").text = str(note)
    instruments = ET.SubElement(program, "Instruments")
    for number in range(1, 129):
        instrument = ET.SubElement(instruments, "Instrument", number=str(number))
        ET.SubElement(instrument, "Mono").text = "False"
        ET.SubElement(instrument, "Polyphony").text = "4"
        ET.SubElement(instrument, "MuteGroup").text = "0"
        ET.SubElement(instrument, "OneShot").text = "False"
        layers = ET.SubElement(instrument, "Layers")
        for layer_number in range(1, 5):
            layer = ET.SubElement(layers, "Layer", number=str(layer_number))
            ET.SubElement(layer, "Active").text = "False"
            ET.SubElement(layer, "SampleName")
            ET.SubElement(layer, "SampleFile")
            ET.SubElement(layer, "VelStart").text = "0"
            ET.SubElement(layer, "VelEnd").text = "127"
    ET.ElementTree(root).write(path, encoding="UTF-8", xml_declaration=True)


def _source_manifest() -> str:
    lines = ['name = "FG Portable Source Kit"', ""]
    for pad, (filename, role, *_rest) in enumerate(SOUNDS, 1):
        lines.extend(("[[pads]]", f"pad = {pad}", f"sample = {json.dumps(filename)}"))
        if role in {"hihat.closed", "hihat.open"}:
            lines.append("mute_group = 1")
        lines.append("")
    return "\n".join(lines)


def _selection_recipe(path: Path) -> None:
    roles = [role for _name, role, *_rest in SOUNDS]
    lines = [
        "schema_version = 1",
        'id = "portable-cross-kit"',
        'name = "FG Portable Cross Kit"',
        "seed = 37",
        "require_hardware_pass = false",
        "",
    ]
    for pad, role in enumerate(roles, 1):
        lines.extend(("[[pads]]", f"pad = {pad}", f"role = {json.dumps(role)}"))
        if role in {"hihat.closed", "hihat.open"}:
            lines.append("mute_group = 1")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_demo(root: Path) -> dict[str, object]:
    """Verify a generated demo without changing it or claiming a hardware pass."""
    root = root.expanduser().resolve()
    bundle = verify_bundle(root)

    acceptance = json.loads(
        (root / "software-acceptance.json").read_text(encoding="utf-8")
    )
    if acceptance.get("cross_kit_simulation") != "pass":
        raise ValueError("portable demo software acceptance is not pass")
    if acceptance.get("hardware_status") != "deferred":
        raise ValueError("portable demo receipt must leave hardware status deferred")
    program = root / "Cross Kit/FG Portable Cross Kit.xpm"
    simulation = test_program(program, program.parent)
    if simulation.verdict != "pass":
        raise ValueError("portable demo cross-kit simulation failed during verification")
    return {
        "schema_version": 1,
        "verified_files": bundle["verified_files"],
        "cross_kit_simulation": simulation.verdict,
        "hardware_status": "deferred",
    }


def _portable_paths(value: object, staging: Path) -> object:
    if isinstance(value, str):
        prefix = str(staging)
        if value == prefix:
            return "."
        if value.startswith(prefix + os.sep):
            return Path(value).relative_to(staging).as_posix()
        return value
    if isinstance(value, list):
        return [_portable_paths(item, staging) for item in value]
    if isinstance(value, tuple):
        return tuple(_portable_paths(item, staging) for item in value)
    if isinstance(value, dict):
        return {key: _portable_paths(item, staging) for key, item in value.items()}
    return value


def _write_ledger(path: Path) -> None:
    fields = (
        "path", "program_type", "format", "structural_status", "sample_references",
        "simulation_scope", "semantic_verdict", "semantic_issues", "hardware_status",
        "favorite", "scratchpad_role", "notes",
    )
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerow(
            {
                "path": "Source Program/FG Portable Source Kit.xpm",
                "program_type": "Drum",
                "format": "xml",
                "structural_status": "pass",
                "sample_references": len(SOUNDS),
                "simulation_scope": "portable fixture",
                "semantic_verdict": "pass",
                "hardware_status": "untested",
                "scratchpad_role": "redistributable workflow fixture",
                "notes": "Mathematically synthesized by mpc-portable-demo",
            }
        )


DEFAULT_CREATIVE_RECIPES = {
    "drums/dusty-pocket.toml": """schema_version = 1
id = "dusty-pocket"
name = "Dusty Pocket"
bars = 2
steps_per_bar = 16
swing = 0.57
gate = 0.45
channel = 10
[[events]]
role = "kick"
steps = [0, 7, 10, 16, 23, 26]
velocity = 112
humanize_velocity = 5
[[events]]
role = "snare"
steps = [4, 12, 20, 28]
velocity = 108
humanize_velocity = 4
selection = "cycle"
[[events]]
role = "hihat.closed"
steps = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30]
velocity = 78
probability = 0.88
humanize_velocity = 12
[[events]]
role = "hihat.open"
steps = [15, 31]
velocity = 90
probability = 0.7
""",
    "harmony/dusty-dorian.toml": """schema_version = 1
id = "dusty-dorian"
name = "Dusty Dorian"
key = "D"
scale = "dorian"
bars = 4
beats_per_bar = 4
progression = [1, 4, 2, 5]
chord_beats = [4, 4, 4, 4]
chord_notes = 4
chord_range = [48, 76]
bass_range = [28, 52]
bass_pattern = [0, 7, 12, 7, 0, 7, 10, 7]
bass_steps_per_beat = 2
chord_velocity = 82
bass_velocity = 102
gate = 0.82
humanize_velocity = 7
chord_channel = 1
bass_channel = 2
""",
    "melody/dusty-answer.toml": """schema_version = 1
id = "dusty-answer"
name = "Dusty Answer"
key = "D"
scale = "dorian"
bars = 4
beats_per_bar = 4
steps_per_beat = 4
motif_steps = 16
rhythm = [0, 3, 6, 10, 14]
contour = [0, 2, 4, 3, 1]
start_degree = 1
note_range = [60, 88]
variation = 0.28
rest_probability = 0.10
octave_probability = 0.08
velocity = 94
humanize_velocity = 7
gate = 0.72
channel = 3
""",
}


def _copy_creative_recipes(recipe_root: Path | None, destination: Path) -> Path:
    for relative, bundled in DEFAULT_CREATIVE_RECIPES.items():
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if recipe_root is None:
            target.write_text(bundled, encoding="utf-8")
            continue
        source = recipe_root / relative
        if not source.is_file():
            raise FileNotFoundError(f"portable demo recipe is missing: {source}")
        shutil.copy2(source, target)
    workstation = destination / "workstation/portable-demo.toml"
    workstation.parent.mkdir(parents=True, exist_ok=True)
    workstation.write_text(
        """schema_version = 1
id = "portable-demo"
name = "FG Portable Scratchpad"
drums = "../drums/dusty-pocket.toml"
harmony = "../harmony/dusty-dorian.toml"
melody = "../melody/dusty-answer.toml"

[programs]
drums = "FG Portable Cross Kit"
bass = "Any bass program"
chords = "Any keys or chord program"
melody = "Any lead or pad program"
""",
        encoding="utf-8",
    )
    return workstation


def _hardware_checklist() -> str:
    return f"""# FG Portable MPC Demo — hardware checklist

All audio in this bundle is generated mathematically and may be redistributed.
Software structure, samples, MIDI, and checksums pass; MPC listening is deferred.

## Drum Program

Path inside this demo: `Cross Kit/FG Portable Cross Kit.xpm`

- [ ] Program loads and all 16 Bank A pads sound.
- [ ] Pads A07/A08 behave as a closed/open-hat choke pair.
- [ ] Pad colors persist after save/reload.
- [ ] The source WAVs can be replaced and the manifest rebuilt.

## Creative MIDI

Path inside this demo: `Creative MIDI/portable-demo.mid`

- [ ] Import creates or exposes Drums, Bass, Chords, and Melody parts.
- [ ] Assign Drums to `FG Portable Cross Kit`; assign any local sounds to the other tracks.
- [ ] `main.mid`, `main-b.mid`, `breakdown.mid`, `build.mid`, and `outro.mid` import.
- [ ] Note any MPC OS-specific import behavior.

Verdict: [ ] pass  [ ] warn  [ ] fail
Notes:
"""


def build_demo(output: Path, recipe_root: Path | None = None) -> dict[str, object]:
    output = output.resolve()
    recipe_root = recipe_root.resolve() if recipe_root is not None else None
    if output.exists():
        raise FileExistsError(f"portable demo output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        audio = staging / "Synthetic Audio"
        for index, (name, _role, kind, duration, frequency) in enumerate(SOUNDS, 1):
            _write_sound(audio / name, kind, duration, frequency, seed=10_000 + index)
        template = staging / "Template/Portable Drum Template.xpm"
        template.parent.mkdir(parents=True)
        write_drum_template(template)
        source_manifest = staging / "Recipes/manifests/source-program.toml"
        source_manifest.parent.mkdir(parents=True)
        source_manifest.write_text(_source_manifest(), encoding="utf-8")
        source_program = build_drum_program(
            load_manifest(source_manifest), template, audio, staging / "Source Program"
        )
        ledger = staging / "source-ledger.csv"
        _write_ledger(ledger)
        catalog = build_catalog(ledger, staging, include_audio=True)
        catalog_path = staging / "catalog.json"
        catalog_path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")

        recipe_path = staging / "Recipes/kits/portable-cross-kit.toml"
        recipe_path.parent.mkdir(parents=True)
        _selection_recipe(recipe_path)
        plan = select_kit(load_kit_recipe(recipe_path), catalog, catalog_path=catalog_path)
        stage = stage_audio(plan, staging / "Selected Audio")
        persisted_catalog = dict(catalog)
        catalog_path.write_text(
            json.dumps(_portable_paths(persisted_catalog, staging), indent=2) + "\n",
            encoding="utf-8",
        )
        selection_root = staging / "Selection"
        selection_root.mkdir()
        (selection_root / "selection.json").write_text(
            json.dumps(_portable_paths(plan.to_dict(), staging), indent=2) + "\n",
            encoding="utf-8",
        )
        (selection_root / "SELECTION.md").write_text(
            render_selection_markdown(plan), encoding="utf-8"
        )
        (selection_root / "staging-checksums.json").write_text(
            json.dumps(_portable_paths(stage, staging), indent=2) + "\n",
            encoding="utf-8",
        )
        manifest = staging / "Recipes/manifests/cross-kit.toml"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(render_manifest(plan), encoding="utf-8")
        cross_program = build_drum_program(
            load_manifest(manifest), template, staging / "Selected Audio", staging / "Cross Kit"
        )
        simulation = test_program(cross_program, cross_program.parent)
        if simulation.verdict != "pass":
            raise ValueError("portable cross-kit simulation failed")

        workstation_path = _copy_creative_recipes(recipe_root, staging / "Recipes")
        loaded = load_workstation(workstation_path)
        model = from_xpm(cross_program)
        idea = generate_workstation(
            loaded, model, program_path=cross_program, seed=37, tempo=92.0, density=1.0
        )
        idea = replace(
            idea, drum_program_file=cross_program.relative_to(staging).as_posix()
        )
        midi_root = staging / "Creative MIDI"
        midi_root.mkdir()
        (midi_root / "portable-demo.mid").write_bytes(render_workstation_midi(idea, loaded))
        (midi_root / "portable-demo.json").write_text(
            json.dumps(idea.to_dict(), indent=2) + "\n", encoding="utf-8"
        )
        (midi_root / "README.md").write_text(
            render_workstation_markdown(idea, loaded), encoding="utf-8"
        )
        arrangement = arrange_idea(
            idea, loaded, arrangement_seed=1037, mutation=0.2, locked_tracks=()
        )
        arrangement_root = staging / "Arrangements"
        arrangement_root.mkdir()
        (arrangement_root / "arrangement.json").write_text(
            json.dumps(arrangement.to_dict(), indent=2) + "\n", encoding="utf-8"
        )
        (arrangement_root / "README.md").write_text(
            render_arrangement_markdown(arrangement), encoding="utf-8"
        )
        for section in arrangement.sections:
            (arrangement_root / f"{section.id}.mid").write_bytes(
                render_section(section, arrangement)
            )

        report = {
            "schema_version": 1,
            "license": "CC0-1.0 for generated audio; repository source remains MIT",
            "generated_samples": len(SOUNDS),
            "source_program": source_program.relative_to(staging).as_posix(),
            "cross_kit_program": cross_program.relative_to(staging).as_posix(),
            "cross_kit_simulation": simulation.verdict,
            "creative_midi_tracks": ["Drums", "Bass", "Chords", "Melody"],
            "arrangement_sections": [section.id for section in arrangement.sections],
            "hardware_status": "deferred",
            "staged_audio": _portable_paths(stage, staging),
        }
        (staging / "software-acceptance.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        (staging / "HARDWARE_CHECKLIST.md").write_text(
            _hardware_checklist(), encoding="utf-8"
        )
        (staging / "README.md").write_text(
            """# FG Portable MPC Workflow Demo

This is a self-contained, freely redistributable acceptance fixture. Its WAVs
are deterministic mathematical synthesis, not copies or derivatives of sample
libraries. It demonstrates source-program creation, audio cataloging,
descriptor-driven cross-kit selection, Drum Program construction, four-track
idea generation, and five traceable arrangement variants.

Start by running `mpc-portable-demo --verify PATH-TO-THIS-DIRECTORY`, then use
`HARDWARE_CHECKLIST.md` when an MPC is available. All editable TOML recipes and
complete JSON provenance are included so the workflow can be repeated or adapted.
""",
            encoding="utf-8",
        )
        (staging / "LICENSE-GENERATED-AUDIO.txt").write_text(
            """CC0 1.0 Universal

To the extent possible under law, the project contributors waive all copyright
and related or neighboring rights in the WAV audio generated by
mpc-portable-demo. You may copy, modify, distribute, and perform that generated
audio, including commercially, without asking permission.

Canonical legal code: https://creativecommons.org/publicdomain/zero/1.0/legalcode

This dedication applies only to the mathematically generated WAV audio. The
software source remains licensed under the repository's MIT License.
""",
            encoding="utf-8",
        )
        checksums = {
            path.relative_to(staging).as_posix(): _sha256(path)
            for path in sorted(staging.rglob("*"))
            if path.is_file() and path.name != "checksums.json"
        }
        (staging / "checksums.json").write_text(
            json.dumps(checksums, indent=2) + "\n", encoding="utf-8"
        )
        os.replace(staging, output)
        return report
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--output", type=Path)
    destination.add_argument("--verify", type=Path, metavar="DEMO")
    parser.add_argument(
        "--recipe-root", type=Path,
        help="optional checkout recipe directory; the installed command has bundled defaults",
    )
    args = parser.parse_args()
    if args.verify is not None:
        report = verify_demo(args.verify)
        print(f"Verified files: {report['verified_files']}; software acceptance: pass")
        print(f"Hardware status: {report['hardware_status']}")
        return 0
    recipe_root = args.recipe_root.expanduser() if args.recipe_root is not None else None
    report = build_demo(args.output.expanduser(), recipe_root)
    print(f"Built: {args.output.expanduser().resolve() / report['cross_kit_program']}")
    print(f"Synthetic WAVs: {report['generated_samples']}; software acceptance: pass")
    print(f"Hardware status: {report['hardware_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
