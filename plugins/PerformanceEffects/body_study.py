"""Offline listening study: stamp a short sampled resonance onto a held chord."""

import argparse
from array import array
import math
from pathlib import Path

from audition import RATE, comparison, take
from mpc_keygroup_builder.audition import read_pcm_mono


def imprint(dry, path):
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
        offset = round((index - start) * RATE / rate)
        kernel[offset] = kernel.get(offset, 0) + body[index] * (1 - j / 48)
    power = math.sqrt(sum(v * v for v in kernel.values()))
    if power < 1e-8:
        raise ValueError(f"Response decays before the analysis window: {path}")
    wet = array("f", [0]) * len(dry)
    for offset, value in kernel.items():
        gain = value / power
        for i in range(offset * 2, len(wet)):
            wet[i] += gain * dry[i - offset * 2]
    # Level-match the colored path so the comparison isn't decided by added gain.
    scale = math.sqrt(sum(x * x for x in dry) / max(1e-14, sum(x * x for x in wet)))
    return array("f", (0.25 * x + 0.75 * y * scale for x, y in zip(dry, wet)))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--keys", type=Path, required=True)
    p.add_argument("--responses", nargs=2, type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    dry = take(
        a.keys,
        [
            (0, 1.85, 0.5, 0),
            (0, 1.85, 0.38, 7),
            (2, 1.85, 0.52, 3),
            (2, 1.85, 0.35, 10),
        ],
    )
    versions = [dry] + [imprint(dry, path) for path in a.responses]
    # Opening exclusively protects input WAVs and existing auditions.
    with a.output.open("xb") as f:
        comparison(f, versions)


if __name__ == "__main__":
    main()
