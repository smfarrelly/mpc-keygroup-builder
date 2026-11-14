"""Build a local Pocket Layers bank and render performances through the plugin DSP."""

from array import array
import base64
import io
import os
from pathlib import Path
import struct
import subprocess
import sys
import wave

from mpc_keygroup_builder import audition, pad_recorder

HERE = Path(__file__).resolve().parent
RATE = 44100


def pack(program, destination):
    layout, assets = pad_recorder.bank_data(program, "A")
    pads = layout["pads"]
    roles = sorted({p["role"] for p in pads})
    if len({p["note"] for p in pads}) != len(pads):
        raise ValueError("Pocket Layers requires a distinct source note for each pad")
    data = bytearray(b"FGL1" + bytes([len(pads)]))
    for p in pads:
        role = p["role"]
        kind = {"hihat.closed": 1, "hihat.open": 2}.get(
            role, 0 if role.split(".")[0] in {"kick", "snare", "tom"} else 3
        )
        layers = sorted(p["layers"], key=lambda l: l["high"])
        if len(layers) > 8:
            raise ValueError("at most eight velocity layers per pad")
        data.extend(
            bytes(
                [
                    p["pad"] - 1,
                    p["note"],
                    kind,
                    roles.index(role),
                    p["group"],
                    len(layers),
                ]
            )
        )
        for layer in layers:
            with io.BytesIO(base64.b64decode(assets[layer["audio"]])) as wav:
                samples, rate = audition.read_pcm_mono(wav)
            mono = audition.resample(samples, rate, layer["pitch"])
            pcm = array("h", (max(-32768, min(32767, round(n * 32768))) for n in mono))
            if sys.byteorder != "little":
                pcm.byteswap()
            data.extend(struct.pack("<BI", layer["high"], len(pcm)))
            data.extend(pcm.tobytes())
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as stream:
        stream.write(data)
    return layout


def compile_probe(sdk, scratch):
    binary = scratch / "render"
    subprocess.run(
        [
            "c++",
            "-std=c++17",
            "-O2",
            "-I",
            str(sdk / "framework"),
            str(HERE / "render.cpp"),
            "-o",
            str(binary),
        ],
        check=True,
    )
    return binary


def render(
    binary, scratch, plugin, frames, events, *, bpm=96, content=None, source=None
):
    schedule = scratch / "schedule.txt"
    schedule.write_text(
        "".join(
            f"{frame} {kind} {index} {value}\n"
            for frame, kind, index, value in sorted(events, key=lambda e: e[0])
        )
    )
    pcm = scratch / "render.pcm"
    env = dict(os.environ)
    if content:
        env["MPC_PLUGIN_FOLDER"] = str(content.resolve())
    subprocess.run(
        [
            str(binary),
            plugin,
            str(frames),
            str(bpm),
            str(schedule),
            str(source or "-"),
            str(pcm),
        ],
        env=env,
        check=True,
    )
    raw = pcm.read_bytes()
    if len(raw) != frames * 4:
        raise ValueError("incomplete stereo render")
    return raw


def write_wave(path, raw):
    with wave.open(str(path), "wb") as out:
        out.setparams((2, 2, RATE, 0, "NONE", ""))
        out.writeframes(raw)


def values(raw):
    pcm = array("h", raw)
    if sys.byteorder != "little":
        pcm.byteswap()
    return pcm
