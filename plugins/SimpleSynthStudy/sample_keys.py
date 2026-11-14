"""Sample SDK Simple Synth presets into portable MPC 3 Keygroup programs."""

import argparse
from array import array
from html import escape
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import wave

from build import HERE, PRESETS, RATE, compile_host, render_synth
from mpc_keygroup_builder import audition, cli, pad_recorder
from mpc_keygroup_builder.bundle_verify import sha256
from mpc_keygroup_builder.midi_writer import MidiNote
from mpc_keygroup_builder.publication import publish_directory
from mpc_keygroup_builder.testing import test_program

ROOTS = range(12, 121, 6)
# Quarter-note ticks at 120 BPM. Keep the slow pad attack and its longer release.
HOLD_TAIL = {"Fat Bass": (1440, 480), "Pluck": (960, 480),
             "Soft Pad": (2880, 1920), "Init Saw": (1920, 960)}


def finish_sample(path):
    """Remove digital silence after release, keeping the complete attack and a smooth end."""
    with wave.open(str(path)) as wav:
        data = array("h", wav.readframes(wav.getnframes()))
    if sys.byteorder != "little":
        data.byteswap()
    while data and not data[-1]:
        data.pop()
    if not data:
        raise ValueError(f"silent sample: {path.name}")
    tail = min(220, len(data))
    if tail > 1:
        for i in range(tail):
            index = len(data) - tail + i
            data[index] = round(data[index] * (1 - i / (tail - 1)))
    count = len(data)
    if sys.byteorder != "little":
        data.byteswap()
    with wave.open(str(path), "wb") as wav:
        wav.setparams((1, 2, RATE, count, "NONE", ""))
        wav.writeframes(data.tobytes())
    return count


def sampled_program(binary, template, preset, scratch, target):
    hold, tail = HOLD_TAIL[preset]
    name = "SDK " + preset
    groups = []
    for note in ROOTS:
        wav = scratch / f"{name} - MIDI {note:03d}.wav"
        render_synth(binary, preset, [MidiNote(0, hold, note, 100, 1)], 120, hold + tail, wav)
        frames = finish_sample(wav)
        groups.append(cli.SampleGroup(note, (cli.Sample(note, wav, frames),)))
    header, program = cli.build_program(template, groups, name)
    # Each capture already contains its own pitch, attack and release.
    program["data"]["transpose"] = 0
    for instrument in program["data"]["drum"]["instruments"]:
        instrument.update(coarseTune=0, fineTune=0, warpEnable=False, ignoreBaseNote=False)
        for layer in instrument["layersv"]:
            if not layer.get("active"):
                continue
            layer.update(pitch=0.0, coarseTune=0, fineTune=0, direction=0, loop=False,
                         loopMode=0, loopStart=0, loopEnd=0, oscillatorMode=False,
                         pitchRandom=0.0, playbackOffset=0.0, offset=0)
            layer["sliceInfo"].update(LoopMode=0, LoopStart=0)
    xpm = target / (name + ".xpm")
    cli.write_program(header, program, groups, xpm, force=False)
    checked = test_program(xpm, target)
    if checked.verdict != "pass" or checked.playable_notes != 128:
        raise ValueError(f"{name}: key mapping failed software checks: {checked.issues}")
    preview = audition.render(xpm, target / "Preview.wav")
    if not preview["events"]:
        raise ValueError(f"{name}: no preview notes")
    return {"name": name, "preset": preset, "program": xpm.name, "notes": list(ROOTS), "source_velocity": 100,
            "hold_seconds": hold / 960, "release_capture_seconds": tail / 960,
            "playable_notes": checked.playable_notes, "dead_cells": checked.dead_trigger_cells,
            "stacked_cells": checked.stacked_trigger_cells, "preview_notes": len(preview["events"]),
            "sample_bytes": sum(g.layers[0].frames * 2 for g in groups)}


def index(instruments):
    cards = []
    for item in instruments:
        name = escape(item["name"])
        cards.append(f'<section><h2>{name}</h2><p>{item["hold_seconds"]:g} s sampled hold · '
                     f'{len(item["notes"])} roots</p><audio controls preload="none" aria-label="{name} preview" '
                     f'src="{name}/Preview.wav"></audio><p>Program folder: <code>{name}/</code></p></section>')
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SDK sampled keys</title><style>:root{color-scheme:dark;font:17px/1.45 "Barlow",system-ui,sans-serif;background:#181c18;color:#f4f0e5}
main{max-width:56rem;margin:auto;padding:clamp(1rem,4vw,3rem)}h1{font-size:clamp(2rem,6vw,3.6rem);letter-spacing:-.045em}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,18rem),1fr));gap:1rem}section{border:1px solid #596459;border-radius:.45rem;padding:1rem;background:#252d27}
h2{margin:0}p{color:#d1d0c5}audio{width:100%}a{color:#ebc780}</style><main><h1>SDK sampled keys</h1>
<p>Play a ten-note preview to hear the sampled instrument across the keyboard. Each program folder contains its XPM and companion ProgramData folder. Keep those together when transferring an instrument.</p>
<div class="grid">''' + "".join(cards) + '''</div><p><a href="instruments.json">Sampling and range report</a></p></main>
<script>document.addEventListener("play",e=>{for(const a of document.querySelectorAll("audio"))if(a!==e.target)a.pause()},true);</script></html>'''


def build(sdk, template, output, presets):
    output = pad_recorder._new_folder(output)
    if not presets or any(p not in PRESETS for p in presets) or len(set(presets)) != len(presets):
        raise ValueError("choose one or more distinct Simple Synth presets")
    _, source = cli.read_xpm(template)
    data = source.get("data", {})
    if not isinstance(data.get("keygroup"), dict) or data["keygroup"].get("numKeygroups", 0) < 1:
        raise ValueError("choose an MPC 3 Keygroup template with at least one keygroup")
    original = sha256(template)
    with tempfile.TemporaryDirectory(dir=output.parent) as work, tempfile.TemporaryDirectory(dir=output.parent) as stage:
        scratch, folder = Path(work), Path(stage)
        binary = compile_host(sdk, scratch)
        items = []
        for preset in presets:
            target = folder / ("SDK " + preset)
            target.mkdir()
            items.append(sampled_program(binary, template, preset, scratch, target))
        if sha256(template) != original:
            raise ValueError("template changed while sampling")
        report = {"kind": "sdk-sampled-keys", "version": 1, "template_sha256": original,
                  "sdk_synth_sha256": sha256(sdk / "examples/SimpleSynth/src/SimpleSynth.cpp"),
                  "renderer_sha256": sha256(HERE / "render.cpp"), "instruments": items,
                  "hardware_status": "untested"}
        (folder / "instruments.json").write_text(json.dumps(report, indent=2) + "\n")
        (folder / "index.html").write_text(index(items), encoding="utf-8")
        pad_recorder.receipt(folder)
        publish_directory(folder, output)
    return output / "index.html"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", type=Path, required=True)
    parser.add_argument("--template", type=Path, required=True, help="known-working MPC 3 JSON Keygroup XPM")
    parser.add_argument("--preset", choices=PRESETS, action="append", help="repeat to choose presets; defaults to all four")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(build(args.sdk, args.template, args.output, args.preset or list(PRESETS)))
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(2, f"{parser.prog}: {error}\n")
