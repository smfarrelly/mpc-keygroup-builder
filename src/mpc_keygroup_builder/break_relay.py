"""Pack two locally owned break recordings and their ordered slice maps for Break Relay."""

import argparse
from array import array
import math
from pathlib import Path
import struct
import sys
import tempfile
import tomllib
import wave

from .publication import publish_directory
from .wave_io import complete_riff_view

ROLES = ("kick", "snare", "hat", "pickup")
MAX_BYTES = 16 * 1024 * 1024


def pack_break(spec, root, output):
    bpm, beats = spec.get("bpm"), spec.get("beats")
    if not all(
        type(v) in (int, float) and math.isfinite(v) and v > 0 for v in (bpm, beats)
    ):
        raise ValueError("Each break needs positive bpm and beats")
    path = spec.get("file")
    if not isinstance(path, str) or not path:
        raise ValueError("Each break needs a source WAV file")
    source = root / path
    slices = spec.get("slices")
    if not isinstance(slices, list) or not 4 <= len(slices) <= 64:
        raise ValueError(f"{source.name}: list 4–64 ordered slices")
    offset = spec.get("offset_ms", 0)
    if type(offset) not in (int, float) or not math.isfinite(offset):
        raise ValueError("offset_ms must be finite")
    previous = -1
    roles = set()
    with source.open("rb") as f, wave.open(complete_riff_view(f), "rb") as wav:
        channels, width, rate, total, _, _ = wav.getparams()
        if (
            channels not in (1, 2)
            or width not in (1, 2, 3, 4)
            or not 8000 <= rate <= 96000
        ):
            raise ValueError(f"{source.name}: choose mono or stereo PCM at 8–96 kHz")
        output.extend(struct.pack("<IB", rate, len(slices)))
        for row in slices:
            if not isinstance(row, list) or len(row) != 3 or row[0] not in ROLES:
                raise ValueError("Use slices of the form [role, start beat, end beat]")
            role, start, end = row
            if (
                not all(
                    type(v) in (int, float) and math.isfinite(v) for v in (start, end)
                )
                or not 0 <= start < end <= beats
                or start < previous
            ):
                raise ValueError(
                    f"{source.name}: slices must be ordered within the declared beat range"
                )
            previous = start
            roles.add(role)
            first = max(0, round(rate * (60 * start / bpm + offset / 1000)))
            last = round(rate * (60 * end / bpm + offset / 1000))
            count = last - first
            if round(65535 * end / beats) <= round(65535 * start / beats):
                raise ValueError(
                    f"{source.name}: slice too small for the declared phrase"
                )
            if (
                not 8 <= count <= 2 * rate
                or last > total
                or len(output) + 9 + 4 * count > MAX_BYTES
            ):
                raise ValueError(
                    f"{source.name}: invalid bounds or bank too large at {role} beat {start}"
                )
            wav.setpos(first)
            raw = wav.readframes(count)
            if len(raw) != count * width * channels:
                raise ValueError(f"{source.name}: truncated PCM")
            output.extend(
                struct.pack(
                    "<BHHI",
                    ROLES.index(role),
                    round(65535 * start / beats),
                    round(65535 * end / beats),
                    count,
                )
            )
            pcm = array("h")
            for i in range(0, len(raw), width):
                if width == 1:
                    value = (raw[i] - 128) << 8
                else:
                    value = int.from_bytes(
                        raw[i : i + width], "little", signed=True
                    ) >> (8 * (width - 2))
                pcm.append(value)
                if channels == 1:
                    pcm.append(value)
            if sys.byteorder != "little":
                pcm.byteswap()
            output.extend(pcm.tobytes())
    if roles != set(ROLES):
        raise ValueError(f"{source.name}: include all four pad roles")


def build(manifest, root, output):
    if output.exists() or output.is_symlink():
        raise ValueError("Choose a new Content output folder")
    spec = tomllib.loads(manifest.read_text(encoding="utf-8"))
    banks = spec.get("breaks")
    if (
        not isinstance(banks, list)
        or len(banks) != 2
        or not all(isinstance(b, dict) for b in banks)
    ):
        raise ValueError("Describe exactly two [[breaks]]")
    blob = bytearray(b"BRK1")
    for bank in banks:
        try:
            pack_break(bank, root, blob)
        except (EOFError, wave.Error) as err:
            raise ValueError(f"Cannot read source WAV {bank.get('file')!r}: {err}") from err
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".break-relay-") as tmp:
        stage = Path(tmp)
        (stage / "pair.brk").write_bytes(blob)
        publish_directory(stage, output)
    return len(blob)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest", type=Path)
    p.add_argument(
        "--source-root",
        type=Path,
        help="resolve WAV paths here (default: beside manifest)",
    )
    p.add_argument("--output", required=True, type=Path, help="new Content directory")
    a = p.parse_args()
    size = build(a.manifest, a.source_root or a.manifest.parent, a.output)
    print(f"Packed two breaks ({size:,} bytes) into {a.output / 'pair.brk'}")
