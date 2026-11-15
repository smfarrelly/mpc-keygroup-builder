"""Offline listening study: stamp a short sampled resonance onto a held chord."""

import argparse
from array import array
import math
from pathlib import Path

from audition import comparison, take
from mpc_keygroup_builder.body_print import reflections


def imprint(dry, path):
    kernel = reflections(path)
    wet = array("f", [0]) * len(dry)
    for offset, value in kernel.items():
        gain = value
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
