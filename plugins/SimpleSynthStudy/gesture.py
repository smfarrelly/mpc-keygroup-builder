"""Audition XL3 encoder movements on the bass part of a verified SDK rhythm section."""

import argparse
import csv
import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
import tomllib

from build import HERE, RATE, compile_host, listening_page, mix_stems, render_synth, repeat_notes
from mpc_keygroup_builder import harmony, pad_recorder, plugin_map, sdk_params
from mpc_keygroup_builder.bundle_verify import sha256, verify_bundle
from mpc_keygroup_builder.midi_writer import MidiControlChange, MidiTrack, render_standard_midi
from mpc_keygroup_builder.publication import publish_directory


def moves_for(document, controls, end_tick):
    if document.get("schema_version") != 1 or not isinstance(document.get("name"), str) or not document["name"].strip():
        raise ValueError("gesture needs schema_version=1 and a name")
    lanes = document.get("lanes")
    if not isinstance(lanes, list) or not lanes:
        raise ValueError("add at least one [[lanes]] entry")
    used, rows = set(), []
    for lane in lanes:
        if not isinstance(lane, dict) or not isinstance(lane.get("control"), str):
            raise ValueError("each lane requires a mapped encoder")
        endpoint = lane["control"]
        if endpoint not in controls or "encoder" not in endpoint:
            raise ValueError(f"choose a mapped encoder: {endpoint}")
        ctrl = controls[endpoint]
        if ctrl["ui_parameter"] in used:
            raise ValueError(f"duplicate lane for {ctrl['name']}")
        used.add(ctrl["ui_parameter"])
        points = lane.get("points")
        if not isinstance(points, list) or not points:
            raise ValueError(f"{endpoint}: add at least one [beat, value] point")
        ticks = []
        for point in points:
            if not isinstance(point, list) or len(point) != 2:
                raise ValueError(f"{endpoint}: expected [beat, value]")
            beat, value = point
            if type(beat) not in (int, float) or not 1 <= beat < 1 + end_tick / 480:
                raise ValueError(f"{endpoint}: beat must be within the sketch, counting from 1")
            pos = (beat - 1) * 480
            tick = round(pos)
            if tick >= end_tick or not math.isclose(pos, tick, rel_tol=0, abs_tol=1e-7) or (ticks and tick <= ticks[-1][0]):
                raise ValueError(f"{endpoint}: use increasing points on the 480 PPQ clock")
            if type(value) is not int or not 0 <= value <= 127:
                raise ValueError(f"{endpoint}: CC value must be an integer from 0 to 127")
            ticks.append((tick, value))
        curve = dict(ticks)
        for (a, v), (b, w) in zip(ticks, ticks[1:]):
            for tick in range((a // 120 + 1) * 120, b, 120):
                curve[tick] = round(v + (w - v) * (tick - a) / (b - a))
        previous = None
        for tick, value in sorted(curve.items()):
            if value != previous:
                rows.append({k: ctrl[k] for k in ("control", "name", "ui_parameter", "channel", "cc")} |
                            {"tick": tick, "beat": 1 + tick / 480, "value": value})
            previous = value
    return sorted(rows, key=lambda row: (row["tick"], row["cc"]))


def build(sketch, gesture, profile_path, sdk, output):
    output = pad_recorder._new_folder(output)
    verified = verify_bundle(sketch)
    info = json.loads((sketch / "sketch.json").read_text())
    if info.get("kind") != "sdk-rhythm-section" or info.get("version") != 1:
        raise ValueError("choose a rhythm section sketch bundle")
    if sha256(sdk / "examples/SimpleSynth/src/SimpleSynth.cpp") != info["sdk_synth_sha256"]:
        raise ValueError("SDK Simple Synth source differs from the sketch")
    dump = sdk / "examples/SimpleSynth/build/params.json"
    if not dump.is_file():
        raise ValueError("build the SDK Simple Synth native example to create build/params.json")
    profile = plugin_map.load_profile(profile_path)
    checked = plugin_map.validate_profile(profile, {"plugins": [sdk_params.inspect(dump)]})
    if checked["errors"]:
        raise ValueError("; ".join(checked["errors"]))
    gesture_bytes = gesture.read_bytes()
    document = tomllib.loads(gesture_bytes.decode())
    end = info["bars"] * 1920
    moves = moves_for(document, {c["control"]: c for c in checked["controls"]}, end)
    recipe = harmony.load_recipe(sketch / "harmony.toml")
    phrase = harmony.generate_idea(recipe, seed=info["seed"], tempo=info["tempo"])
    notes = repeat_notes([e for e in phrase.events if e.part == "bass"], recipe.bass_channel, recipe.bars, info["bars"])
    preset = next(stem["sound"] for stem in info["stems"] if stem["part"] == "Bass")
    with tempfile.TemporaryDirectory(dir=output.parent) as work, tempfile.TemporaryDirectory(dir=output.parent) as stage:
        scratch, folder = Path(work), Path(stage)
        binary = compile_host(sdk, scratch)
        reference = scratch / "reference.wav"
        render_synth(binary, preset, notes, info["tempo"], end, reference)
        if sha256(reference) != sha256(sketch / "Bass.wav"):
            raise ValueError("reference bass no longer matches the sketch; rebuild it with this SDK and recipe")
        for row in moves:
            row["frame"] = round(row["tick"] * RATE * 60 / (info["tempo"] * 480))
        schedule = scratch / "controls.txt"
        schedule.write_text("".join(f'{m["frame"]} {m["ui_parameter"]} {m["value"]} {json.dumps(m["name"])}\n'
                                    for m in moves))
        render_synth(binary, preset, notes, info["tempo"], end, folder / "Bass.wav", moves=schedule)
        mix_stems(folder, info["frames"], sources=[sketch / "Drums.wav", folder / "Bass.wav", sketch / "Chords.wav"])
        shutil.copyfile(sketch / "Mix.wav", folder / "Original.wav")
        shutil.copyfile(reference, folder / "Original Bass.wav")
        cc = tuple(MidiControlChange(m["tick"], m["cc"], m["value"], m["channel"]) for m in moves)
        (folder / "Controls.mid").write_bytes(render_standard_midi((MidiTrack(document["name"], (), cc),),
                                                tempo=info["tempo"], ppq=480, end_tick=end))
        with (folder / "controls.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(moves[0]))
            writer.writeheader()
            writer.writerows(moves)
        (folder / "gesture.toml").write_bytes(gesture_bytes)
        report = {"kind": "sdk-gesture-audition", "version": 1, "name": document["name"], "preset": preset,
                  "source_sketch": verified["package_sha256"], "profile_sha256": sha256(profile_path),
                  "host_dump_sha256": sha256(dump), "project": info["name"], "bars": info["bars"], "tempo": info["tempo"],
                  "controls": sorted({m["name"] for m in moves}), "events": len(moves),
                  "first_frame": moves[0]["frame"], "audio_changed": sha256(reference) != sha256(folder / "Bass.wav"),
                  "hardware_status": "untested"}
        (folder / "gesture.json").write_text(json.dumps(report, indent=2) + "\n")
        page = listening_page(report["name"], "Encoder audition",
                              f'{info["bars"]} bars · {info["tempo"]:g} BPM · {preset}',
                              "First move on beat " + str(moves[0]["beat"]) + " · " + ", ".join(report["controls"]),
                              [("Original", "Original mix"), ("Mix", "With encoders"),
                               ("Original Bass", "Original bass"), ("Bass", "Bass with encoders")],
                              [("Controls.mid", "Controller MIDI"), ("controls.csv", "Encoder moves"),
                               ("gesture.toml", "Editable gesture"), ("gesture.json", "Render settings"),
                               ("Mix.wav", "Mix with encoders"), ("Bass.wav", "Bass with encoders")])
        (folder / "index.html").write_text(page, encoding="utf-8")
        pad_recorder.receipt(folder)
        publish_directory(folder, output)
    return output / "index.html"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sketch", type=Path)
    parser.add_argument("gesture", type=Path)
    parser.add_argument("--profile", type=Path, default=HERE.parents[1] / "midi/sdk-examples/simple-synth.toml")
    parser.add_argument("--sdk", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(build(args.sketch, args.gesture, args.profile, args.sdk, args.output))
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(2, f"{parser.prog}: {error}\n")
