"""Create a compact pair of short reflection patterns from your own PCM one-shots."""

import argparse
import math
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
from .audition import read_pcm_mono
from .publication import publish_directory

REFERENCE_RATE = 32000


def reflections(path):
    body, rate = read_pcm_mono(path)
    peak = max(map(abs, body), default=0)
    if not peak:
        raise ValueError(f"Silent response source: {path}")
    attack = next(i for i, value in enumerate(body) if abs(value) >= peak * 0.12)
    # Skip the first 3 ms; preserve the following 60 ms as 48 signed reflections.
    start = attack + round(rate * 0.003)
    kernel = {}
    for j in range(48):
        lo = start + round(rate * 0.060 * j / 48)
        hi = min(len(body), start + round(rate * 0.060 * (j + 1) / 48))
        if hi <= lo:
            break
        index = max(range(lo, hi), key=lambda i: abs(body[i]))
        offset = round((index - start) * REFERENCE_RATE / rate)
        kernel[offset] = kernel.get(offset, 0) + body[index] * (1 - j / 48)
    power = math.sqrt(sum(v * v for v in kernel.values()))
    if power < 1e-8:
        raise ValueError(f"Response decays before the analysis window: {path}")
    return {delay: weight / power for delay, weight in kernel.items()}


def build(sources, output):
    if output.exists() or output.is_symlink():
        raise ValueError("Choose a new Content directory")
    if len(sources) != 2:
        raise ValueError("Choose exactly two donor WAVs")
    blob = bytearray(b"BOD1")
    for path in sources:
        taps = reflections(path)
        blob.append(len(taps))
        for delay, gain in sorted(taps.items()):
            blob.extend(struct.pack("<Hh", delay, round(32767 * gain)))
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent, prefix=".body-print-") as tmp:
        stage = Path(tmp)
        (stage / "bodies.bin").write_bytes(blob)
        publish_directory(stage, output)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("donors", type=Path, nargs=2, metavar="WAV")
    p.add_argument("--output", type=Path, required=True, help="new Content directory")
    args = p.parse_args()
    build(args.donors, args.output)
    print(args.output / "bodies.bin")
