"""Prepare up to four local MIDI grooves for the Rhythm Imprint effect."""

import argparse
from pathlib import Path
import tempfile

from .midi_groove import parse_midi
from .publication import publish_directory


def encode(source, bar, note=None):
    info, events = parse_midi(source)
    if bar < 1 or (note is not None and not 0 <= note <= 127):
        raise ValueError("Choose a bar starting at 1 and a MIDI note from 0 to 127")
    length = info.ppq * 4
    start = (bar - 1) * length
    hits = {}
    for event in events:
        offset = event.tick - start
        if 0 <= offset < length and (note is None or event.note == note):
            tick = min(4095, round(offset * 4096 / length))
            hits[tick] = max(event.velocity, hits.get(tick, 0))
    if not 1 <= len(hits) <= 64:
        raise ValueError(
            f"{source.name}: found {len(hits)} attacks in bar {bar}; select 1–64, optionally with --note"
        )
    peak = max(hits.values())
    data = bytearray([1, len(hits)])
    for tick, level in sorted(hits.items()):
        data.extend((tick & 255, tick >> 8, max(1, round(level * 127 / peak))))
    return bytes(data)


def build(sources, destination, bar, note):
    if not 1 <= len(sources) <= 4:
        raise ValueError("Supply one to four MIDI files in slot order")
    if destination.exists() or destination.is_symlink():
        raise ValueError(f"Choose a new output directory: {destination}")
    grooves = [encode(path, bar, note) for path in sources]
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent, prefix=".imprint-") as tmp:
        stage = Path(tmp)
        for index, data in enumerate(grooves, 1):
            (stage / f"slot-{index}.gri").write_bytes(data)
        (stage / "Grooves.txt").write_text(
            "\n".join(
                f"Slot {i}: {p.stem} (4/4 bar {bar}, {g[1]} attacks)"
                for i, (p, g) in enumerate(zip(sources, grooves), 1)
            )
            + "\n",
            encoding="utf-8",
        )
        publish_directory(stage, destination)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "files", nargs="+", type=Path, help="Standard MIDI files in slot order"
    )
    p.add_argument("--bar", type=int, default=1, help="4/4 bar to extract (default 1)")
    p.add_argument("--note", type=int, help="use only this MIDI note number")
    p.add_argument(
        "--output", required=True, type=Path, help="new Content folder for the plugin"
    )
    args = p.parse_args()
    build(args.files, args.output, args.bar, args.note)
    print((args.output / "Grooves.txt").read_text(), end="")
