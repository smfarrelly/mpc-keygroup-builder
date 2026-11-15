"""Render short dry/wet comparisons from two of your own PCM samples on Linux."""

import argparse
from array import array
import math
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import wave

from mpc_keygroup_builder.audition import read_pcm_channels
from mpc_keygroup_builder.publication import publish_directory

RATE = 32000
HERE = Path(__file__).resolve().parent


def take(path, performance):
    channels, rate = read_pcm_channels(path)
    out = array("f", [0]) * (RATE * 4 * 2)
    for start, duration, level, pitch in performance:
        ratio = rate / RATE * 2 ** (pitch / 12)
        offset = round(start * RATE)
        length = min(
            int(duration * RATE),
            int((len(channels[0]) - 1) / ratio),
            len(out) // 2 - offset,
        )
        for i in range(length):
            pos = i * ratio
            k = int(pos)
            frac = pos - k
            amplitude = level * min(1, (length - i) / 160)
            for ch in range(2):
                src = channels[ch % len(channels)]
                out[2 * (offset + i) + ch] += amplitude * (
                    (1 - frac) * src[k] + frac * src[k + 1]
                )
    maximum = max(map(abs, out))
    if maximum < 1e-8:
        raise ValueError(f"Sample was silent: {path}")
    return array("f", (x * 0.64 / maximum for x in out))


def comparison(path, versions):
    gain = 30000 / max(max(map(abs, v)) for v in versions)
    with wave.open(str(path) if isinstance(path, Path) else path, "wb") as w:
        w.setparams((2, 2, RATE, 0, "NONE", "not compressed"))
        for v in versions:
            w.writeframes(array("h", (round(gain * x) for x in v)).tobytes())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("sdk", "snare", "keys", "output"):
        p.add_argument("--" + name, required=True, type=Path)
    p.add_argument(
        "--bank",
        type=Path,
        help="prepared Content folder; slot 1 shapes the keys example",
    )
    a = p.parse_args()
    if a.output.exists() or a.output.is_symlink():
        raise ValueError("Choose a new output folder")
    hits = [
        (i * 0.25, 0.23, v, 0)
        for i, v in enumerate([0.92, 0.24, 0.46, 0.18, 1, 0.19, 0.62, 0.27] * 2)
    ]
    drums = take(a.snare, hits)
    chord = take(
        a.keys,
        [
            (0, 1.85, 0.5, 0),
            (0, 1.85, 0.38, 7),
            (2, 1.85, 0.52, 3),
            (2, 1.85, 0.35, 10),
        ],
    )
    tails = take(
        a.keys, [(0.1, 0.43, 0.55, 0), (0.65, 0.43, 0.55, 3), (1.2, 0.43, 0.55, 7)]
    )
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with (
        TemporaryDirectory() as temp,
        TemporaryDirectory(dir=a.output.parent, prefix=".audition-") as stage,
    ):
        tmp = Path(temp)
        subprocess.run(
            [
                "c++",
                "-O2",
                "-std=c++17",
                "-I",
                str(a.sdk / "framework"),
                str(HERE / "render.cpp"),
                "-ldl",
                "-o",
                str(tmp / "render"),
            ],
            check=True,
        )
        env = os.environ.copy()
        if a.bank:
            if not (a.bank / "slot-1.gri").is_file():
                raise ValueError("The bank needs slot-1.gri")
            (tmp / "Content").symlink_to(a.bank.resolve(), target_is_directory=True)
            env["MPC_PLUGIN_FOLDER"] = str(tmp)

        def render(plugin, preset, audio):
            (binary,) = (HERE.parent / plugin / "build/native").glob("*.so")
            run = subprocess.run(
                [str(tmp / "render"), str(binary), str(preset)],
                input=audio.tobytes(),
                stdout=subprocess.PIPE,
                env=env,
                check=True,
            )
            result = array("f")
            result.frombytes(run.stdout)
            if (
                len(result) != len(audio)
                or not all(map(math.isfinite, result))
                or result == audio
            ):
                raise ValueError(f"{plugin}: expected a finite, audible change")
            return result

        dest = Path(stage)
        comparison(
            dest / "01 Ghost Fader - Dry, Ghosts, Accents.wav",
            [drums, render("GhostFader", 1, drums), render("GhostFader", 2, drums)],
        )
        comparison(
            dest / "02 Rhythm Imprint - Dry, Imprinted.wav",
            [chord, render("RhythmImprint", int(bool(a.bank)), chord)],
        )
        comparison(
            dest / "03 Tail Choir - Dry, Choir.wav",
            [tails, render("TailChoir", 0, tails)],
        )
        publish_directory(dest, a.output)


if __name__ == "__main__":
    main()
