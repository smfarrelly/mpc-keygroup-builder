"""Measure WAV audition levels and flag likely outliers before hardware testing."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path

from .audition import read_pcm_mono


def _db(value: float) -> float | None:
    return 20.0 * math.log10(value) if value > 0 else None


def analyze_file(path: Path) -> dict[str, object]:
    samples, rate = read_pcm_mono(path)
    count = len(samples)
    peak = max((abs(value) for value in samples), default=0.0)
    rms = math.sqrt(sum(value * value for value in samples) / count) if count else 0.0
    onset_count = min(count, max(1, round(rate * 0.05)))
    onset_rms = (
        math.sqrt(sum(value * value for value in samples[:onset_count]) / onset_count)
        if count
        else 0.0
    )
    body = samples[onset_count:]
    body_rms = (
        math.sqrt(sum(value * value for value in body) / len(body))
        if body
        else rms
    )
    peak_threshold = peak * 0.95
    peak_index = next(
        (index for index, value in enumerate(samples) if abs(value) >= peak_threshold),
        0,
    )
    return {
        "path": str(path.resolve()),
        "sample_rate": rate,
        "duration_seconds": count / rate,
        "peak_dbfs": _db(peak),
        "rms_dbfs": _db(rms),
        "crest_db": _db(peak / rms) if rms else None,
        "onset_rms_dbfs": _db(onset_rms),
        "body_rms_dbfs": _db(body_rms),
        "onset_to_body_db": (
            _db(onset_rms / body_rms)
            if body_rms
            else 120.0 if onset_rms else None
        ),
        "attack_milliseconds": peak_index / rate * 1000,
        "dc_offset": sum(samples) / count if count else 0.0,
        "clipped_fraction": sum(abs(value) >= 0.999 for value in samples) / count if count else 0.0,
        "silent_fraction": sum(abs(value) < 0.0001 for value in samples) / count if count else 1.0,
        "flags": [],
    }


def analyze(paths: list[Path], tolerance_db: float = 6.0) -> list[dict[str, object]]:
    if not math.isfinite(tolerance_db) or tolerance_db < 0:
        raise ValueError("level tolerance must be a finite nonnegative number")
    rows = [analyze_file(path) for path in paths]
    levels = [float(row["rms_dbfs"]) for row in rows if row["rms_dbfs"] is not None]
    median = statistics.median(levels) if levels else None
    for row in rows:
        flags = row["flags"]
        level = row["rms_dbfs"]
        if level is None or row["silent_fraction"] > 0.98:
            flags.append("silent")
        elif median is not None and abs(float(level) - median) > tolerance_db:
            flags.append("level-outlier")
        if row["clipped_fraction"] > 0:
            flags.append("clipping")
        if abs(float(row["dc_offset"])) > 0.01:
            flags.append("dc-offset")
    return rows


def discover(inputs: list[Path]) -> list[Path]:
    paths = []
    for path in inputs:
        if path.is_dir():
            paths.extend(
                item
                for item in path.rglob("*")
                if item.is_file() and item.suffix.casefold() == ".wav"
            )
        else:
            paths.append(path)
    paths = sorted(paths)
    if not paths:
        raise ValueError("no WAV files found in the requested paths")
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--tolerance-db", type=float, default=6.0)
    parser.add_argument("--format", choices=("json", "csv"), default="json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    paths = discover(args.paths)
    rows = analyze(paths, args.tolerance_db)
    if args.format == "json":
        rendered = json.dumps(rows, indent=2) + "\n"
    else:
        from io import StringIO
        output = StringIO()
        fields = [key for key in rows[0] if key != "flags"] + ["flags"] if rows else []
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows({**row, "flags": ";".join(row["flags"])} for row in rows)
        rendered = output.getvalue()
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 1 if any(row["flags"] for row in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
