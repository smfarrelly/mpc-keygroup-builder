"""Measure Akai Drum Synth velocity response and build the ghost/accent listening pair."""

import argparse
from array import array
from dataclasses import replace
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import wave

from mpc_keygroup_builder import drum_builder, ideas, model, pattern_audio, sdk_kit
from mpc_keygroup_builder.bundle_verify import sha256, verify_bundle
from mpc_keygroup_builder.publication import publish_directory
from mpc_keygroup_builder.testing import test_program

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
VELOCITIES = (40, 80, 120)


def pcm(data):
    samples = array("h", data)
    if sys.byteorder != "little":
        samples.byteswap()
    return samples


def compare(reference, candidate):
    x, y = pcm(reference), pcm(candidate)
    if len(x) != len(y):
        raise ValueError("unaligned PCM renders")
    ex, ey = sum(v*v for v in x), sum(v*v for v in y)
    if not ex or not ey:
        raise ValueError("silent test render")
    gain = math.sqrt(ex / ey)
    residual = math.sqrt(sum((a - gain*b)**2 for a, b in zip(x, y)) / ex)
    return {"rms_gain_to_reference": gain, "relative_residual": residual}


def render(binary, preset, note, velocity):
    data = subprocess.check_output([str(binary), str(preset), str(note), str(velocity)], timeout=30)
    if len(data) != 88200 * 4:
        raise ValueError(f"incomplete hit for preset {preset}, note {note}, velocity {velocity}")
    return data


def build(sdk, baseline, output):
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"choose a new output folder: {output}")
    verify_bundle(baseline)
    source = sdk / "examples/DrumSynth/src/DrumSynth.cpp"
    base, _, notes = sdk_kit.load_kit(ROOT / "midi/sdk-kits/drum-synth.toml")
    alternate = drum_builder.load_manifest(HERE / "accent-kit.toml")
    if [p.pad for p in base.pads] != [p.pad for p in alternate.pads]:
        raise ValueError("pad layout differs between kits")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as scratch, tempfile.TemporaryDirectory(dir=output.parent) as stage:
        scratch, stage = Path(scratch), Path(stage)
        binary = scratch / "render"
        subprocess.run(["c++", "-std=c++17", "-O2", "-I", str(sdk / "framework"), "-I", str(source.parent),
                        str(HERE / "hit.cpp"), "-o", str(binary)], check=True)
        measurements = []
        for pad, target in zip(base.pads, alternate.pads, strict=True):
            name, note = pad.sample, notes[pad.pad]
            clean = render(binary, 0, note, 100)
            boom = render(binary, 1, note, 100)
            with wave.open(str(baseline / name)) as wav:
                existing = wav.readframes(wav.getnframes())
            stop = ((len(clean.rstrip(b"\0")) + 3) // 4) * 4
            start = ((len(clean) - len(clean.lstrip(b"\0"))) // 4) * 4
            if clean[start:stop] != existing:
                raise ValueError(f"{name}: SDK Clean Kit differs from supplied baseline")
            shutil.copyfile(baseline / name, scratch / name)
            measurements.append({"pad": pad.pad, "voice": name, "source_note": note,
                                 "clean_velocity": {v: compare(clean, render(binary, 0, note, v)) for v in VELOCITIES},
                                 "clean_vs_boom_at_100": compare(clean, boom)})
            if target.layers:
                with wave.open(str(scratch / "raw.wav"), "wb") as wav:
                    wav.setparams((2, 2, 44100, 88200, "NONE", ""))
                    wav.writeframes(boom)
                sdk_kit.trim_hit(scratch / "raw.wav", scratch / target.layers[1].sample)
        template = scratch / "template.xpm"
        drum_builder.write_drum_template(template)
        kit = drum_builder.build_drum_program(alternate, template, scratch, stage / "Kit")
        if test_program(kit, kit.parent).verdict != "pass":
            raise ValueError("alternate kit failed program validation")
        original = baseline / (base.name + ".xpm")
        recipe = ideas.load_recipe(ROOT / "recipes/drums/ghost-accents.toml")
        phrase = ideas.generate_idea(recipe, model.from_xpm(original), tempo=96, seed=37)
        (stage / "Ghost Accents.mid").write_bytes(ideas.render_midi(phrase))
        for title, program, kit_name in (("Original", original, base.name), ("Accent", kit, alternate.name)):
            pattern = stage / (title + "-idea.json")
            pattern.write_text(json.dumps(replace(phrase, program=kit_name).to_dict(), indent=2))
            pattern_audio.render_pattern(program, pattern, stage / (title + ".wav"))
        # Probe both sides of every boundary through the normal audio renderer.
        probes = [replace(phrase.events[0], tick=i*120, pad=zone.pad, midi_note=zone.midi_note,
                          sample=zone.layers[0].sample, velocity=v)
                  for i, (zone, v) in enumerate((zone, v) for zone in model.from_xpm(kit).zones
                                                for v in (95, 96))]
        probe = replace(phrase, program=alternate.name, events=tuple(probes))
        probe_file = scratch / "probe.json"
        probe_file.write_text(json.dumps(probe.to_dict()))
        played = pattern_audio.render_pattern(kit, probe_file, scratch / "boundary-audio.wav")["events"]
        expected = [layer.sample for pad in alternate.pads for layer in
                    (pad.resolved_layers()[0], pad.resolved_layers()[-1])]
        if [hit["sample"] for hit in played] != expected:
            raise ValueError("velocity boundary selected unexpected samples")
        report = {"reference_velocity": 100, "source_sha256": sha256(source), "voices": measurements,
                  "boundary_probes": played, "hardware_status": "untested"}
        (stage / "measurements.json").write_text(json.dumps(report, indent=2) + "\n")
        shutil.copyfile(HERE / "listen.html", stage / "index.html")
        hashes = {p.relative_to(stage).as_posix(): sha256(p) for p in sorted(stage.rglob("*")) if p.is_file()}
        (stage / "checksums.json").write_text(json.dumps(hashes, indent=2) + "\n")
        verify_bundle(stage)
        publish_directory(stage, output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", required=True, type=Path)
    parser.add_argument("--baseline", required=True, type=Path, help="verified SDK Drum Synth Kit folder")
    parser.add_argument("--output", required=True, type=Path, help="new folder for alternate kit and comparison")
    args = parser.parse_args()
    build(args.sdk.resolve(), args.baseline.resolve(), args.output.absolute())
    print((args.output / "index.html").resolve())
