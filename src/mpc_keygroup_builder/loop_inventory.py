"""Index tempo-named WAV loops for future MPC Clip Program generation."""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import wave
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path


BPM_PATTERN = re.compile(r"^(?P<bpm>\d{3})\s+")


@dataclass(frozen=True)
class LoopInfo:
    path: str
    name: str
    bpm: int
    variant: str
    frames: int
    sample_rate: int
    channels: int
    duration_seconds: float
    estimated_beats: float
    nearest_beats: int
    beat_error: float


def classify_variant(name: str) -> str:
    value = Path(name).stem.casefold()
    for label, token in (
        ("no-percussion", "no perc"),
        ("no-snare", "no snare"),
        ("percussion", "percussion"),
        ("full", " full "),
        ("pitched", "pitched"),
        ("clean", "clean"),
        ("colored", "color"),
        ("degraded", "degraded"),
    ):
        if token in f" {value} ":
            return label
    return "other"


def inspect_loop(path: Path, root: Path) -> LoopInfo:
    match = BPM_PATTERN.match(path.name)
    if match is None:
        raise ValueError(f"filename has no leading three-digit BPM: {path.name}")
    bpm = int(match.group("bpm"))
    if not 20 <= bpm <= 400:
        raise ValueError(f"filename BPM is outside 20..400: {path.name}")
    try:
        with wave.open(str(path), "rb") as stream:
            frames = stream.getnframes()
            sample_rate = stream.getframerate()
            channels = stream.getnchannels()
    except (EOFError, wave.Error) as error:
        raise ValueError(f"unreadable WAV {path}: {error or 'truncated file'}") from error
    if frames < 1 or sample_rate < 1:
        raise ValueError(f"empty WAV: {path}")
    duration = frames / sample_rate
    beats = duration * bpm / 60
    nearest = round(beats)
    return LoopInfo(
        path=str(path.relative_to(root)),
        name=path.name,
        bpm=bpm,
        variant=classify_variant(path.name),
        frames=frames,
        sample_rate=sample_rate,
        channels=channels,
        duration_seconds=round(duration, 6),
        estimated_beats=round(beats, 4),
        nearest_beats=nearest,
        beat_error=round(abs(beats - nearest), 4),
    )


def scan(root: Path) -> dict[str, object]:
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"loop inventory root is not a directory: {root}")
    loops = []
    issues = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.casefold() != ".wav" or path.name.startswith("._"):
            continue
        try:
            loops.append(inspect_loop(path, root))
        except ValueError as error:
            issues.append(str(error))
    variants = Counter(loop.variant for loop in loops)
    rates = Counter(loop.sample_rate for loop in loops)
    channels = Counter(loop.channels for loop in loops)
    timing_warnings = [
        f"{loop.path}: {loop.estimated_beats} estimated beats at {loop.bpm} BPM"
        for loop in loops
        if loop.beat_error > 0.05
    ]
    return {
        "root": str(root.resolve()),
        "count": len(loops),
        "bpm_min": min((loop.bpm for loop in loops), default=None),
        "bpm_max": max((loop.bpm for loop in loops), default=None),
        "variants": dict(sorted(variants.items())),
        "sample_rates": {str(key): value for key, value in sorted(rates.items())},
        "channels": {str(key): value for key, value in sorted(channels.items())},
        "issues": issues,
        "timing_warnings": timing_warnings,
        "loops": [asdict(loop) for loop in loops],
    }


def render_csv(report: dict[str, object]) -> str:
    fields = tuple(LoopInfo.__dataclass_fields__)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for loop in report["loops"]:  # type: ignore[union-attr]
        writer.writerow(loop)
    return stream.getvalue()


def output_paths(json_path: Path, csv_path: Path) -> tuple[Path, Path]:
    paths = []
    for label, path in (("JSON", json_path), ("CSV", csv_path)):
        path = path.expanduser()
        if path.is_symlink():
            raise ValueError(f"loop inventory {label} output may not be a symbolic link: {path}")
        if path.exists() and not path.is_file():
            raise ValueError(
                f"loop inventory {label} output must be a regular file: {path}"
            )
        paths.append(path.resolve())
    if paths[0] == paths[1]:
        raise ValueError("loop inventory JSON and CSV outputs must be different files")
    return paths[0], paths[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--csv", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    json_path, csv_path = output_paths(args.json, args.csv)
    report = scan(root)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    csv_path.write_text(render_csv(report), encoding="utf-8")
    print(
        f"loops={report['count']} bpm={report['bpm_min']}..{report['bpm_max']} "
        f"issues={len(report['issues'])} timing_warnings={len(report['timing_warnings'])}"
    )
    return 0 if not report["issues"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
