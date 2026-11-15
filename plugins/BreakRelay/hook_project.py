"""Build private four-bar rehearsal projects from the Playable Scratchpad demo."""

import argparse
from copy import deepcopy
from dataclasses import astuple
import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import wave

from mpc_keygroup_builder import cli, xpj
from mpc_keygroup_builder.hook_rehearsal import arrange, verify_samples
from mpc_keygroup_builder.publication import publish_directory

HERE = Path(__file__).resolve().parent
ROLES = ("Kick", "Snare", "Hat", "Pickup")


def print_hits(program, media, sdk, content, scratch):
    if not (content / "pair.brk").is_file():
        raise ValueError("Choose the Break Relay Content folder containing pair.brk")
    (scratch / "Content").symlink_to(content.resolve())
    runner = scratch / "render"
    subprocess.run(["c++", "-O2", "-std=c++17", "-I", sdk / "framework",
                    HERE.parent / "DrumHands/tests/render.cpp", "-ldl", "-o", runner], check=True)
    samples = []
    mapping = program["padNoteMap"]["noteForPad"]
    for i, inst in enumerate(program["drum"]["instruments"]):
        for layer in inst["layersv"]:
            cli.disable_layer(layer)
        program["programPads"]["pads"][f"value{i}"] = 0
    for i, role in enumerate(ROLES):
        note = 36 + i
        slot = f"value{i}"
        other = next(k for k, v in mapping.items() if v == note)
        mapping[other], mapping[slot] = mapping[slot], note
        event = scratch / "event"
        event.write_text(f"0 {note} 127 144\n")
        raw = scratch / "raw"
        subprocess.run([runner, HERE / "build/native/break-relay.so", "88200", "120", event, raw],
                       env=dict(os.environ, MPC_PLUGIN_FOLDER=str(scratch)), check=True)
        path = media / f"Break Relay {role}.wav"
        with wave.open(str(path), "wb") as wav:
            wav.setparams((2, 2, 44100, 0, "NONE", ""))
            wav.writeframes(raw.read_bytes())
        inst = program["drum"]["instruments"][i]
        inst["whichMuteGroup"] = 1
        layer = inst["layersv"][0]
        cli.configure_layer(layer, cli.Sample(60, path, 88200))
        layer.update(keyTrackEnable=False, loop=False, loopMode=0)
        layer["sliceInfo"]["LoopMode"] = 0
        program["programPads"]["pads"][slot] = (0xFF3030, 0x288CFF, 0xF4CB31, 0xAE51FF)[i]
        entry = deepcopy(program["samples"][0])
        entry.update(name=path.stem, path=path.name)
        entry["metadata"].update(rootNote=60, tempo=0, tune=0, key="")
        samples.append(entry)
    program["samples"] = samples


def build(source, output, sdk, content):
    project = xpj.load(source)
    data = project.data
    tracks = {t["name"]: t for t in data["tracks"]}
    drum = tracks["Pocket Layers Print"]
    voices = [drum, tracks["Pluck Bass"], tracks["Wurli"]]
    data["tracks"] = voices + [t for t in data["tracks"] if t["program"]["type"] in (7, 8, 9, 10)]
    data["currentTrackIndex"] = 0
    drum["recordArm"] = True
    drum["name"] = drum["program"]["name"] = "Break Relay"
    seq, = [s["value"] for s in data["sequences"]]
    lane, = seq["trackClipMaps"]
    rhythm = next(r for r in lane if r["key"] == "Main Drums")
    rhythm["key"] = rhythm["value"]["name"] = drum["name"]
    retained = {t["name"] for t in data["tracks"]}
    controls = data["midiLearnSettings"]["controls"]
    controls[:] = [c for c in controls if all(t.get("track") in retained
                   for t in c["control"]["targetData"])]
    lane[:] = sorted((r for r in lane if r["key"] in retained), key=lambda r: r["key"])
    events = rhythm["value"]["eventList"]["events"]
    template = deepcopy(next(e for e in events if e["type"] == 3))
    events.clear()
    for step in range(32):
        event = deepcopy(template)
        event["time"] = step * 480
        pitch = (36, 38, 37, 38, 36, 38, 37, 38)[step % 8]
        event["note"].update(note=pitch, velocity=(0.55 if pitch == 38 else 0.88), length=120)
        events.append(event)
    seq.update(name="Hook", autoSelectTrackIndex=0)
    if output.exists() or output.is_symlink():
        raise ValueError("Choose a new output folder")
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as temp, TemporaryDirectory() as scratch:
        stage = Path(temp)
        demo = stage / "02 Hear the hook_[ProjectData]"
        demo.mkdir()
        print_hits(drum["program"], demo, sdk, content, Path(scratch))
        registry = {}
        donor = source.with_name(source.stem + "_[ProjectData]")
        for track in voices:
            for sample in track["program"]["samples"]:
                name = sample["path"]
                if not name or Path(name).name != name or "\\" in name:
                    raise ValueError(f"Expected a local sample filename: {name}")
                if track is not drum:
                    shutil.copyfile(donor / name, demo / name)
                registry[name] = sample
        data["samples"] = list(registry.values())
        empty = deepcopy(project)
        for row in empty.data["sequences"][0]["value"]["trackClipMaps"][0]:
            row["value"]["eventList"]["events"].clear()
        arrange(data)
        shutil.copytree(demo, stage / "01 Play your hook_[ProjectData]")
        for title, item in (("01 Play your hook", empty), ("02 Hear the hook", project)):
            path = stage / (title + ".xpj")
            payload = "\n".join(astuple(item.header)) + "\n" + json.dumps(item.document, separators=(",", ":"))
            path.write_bytes(gzip.compress(payload.encode(), mtime=0))
            saved = xpj.load(path)
            verify_samples(saved)
            if saved.document != item.document:
                raise ValueError(f"Failed readback: {path}")
        publish_directory(stage, output)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path, help="Playable Scratchpad / 02 Four Bar Jam.xpj")
    for arg in ("sdk", "content", "output"):
        p.add_argument("--" + arg, type=Path, required=True)
    args = p.parse_args()
    build(args.source, args.output, args.sdk, args.content)
