"""Check the playback loudness and peak headroom of a WAV export."""

import argparse
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

# Scan the same 192 kHz signal for integrated loudness and peak location.
# Short final frames are kept. The measured output goes to the null muxer.
RATE = 192000
WINDOW = 9600  # 50 ms at 192 kHz
GRAPH = (
    f"[0:a:0]aresample={RATE}:osf=dbl,asplit=2[level][peaks];"
    "[level]loudnorm=dual_mono=true:print_format=json,anullsink;"
    f"[peaks]asetnsamples=n={WINDOW}:p=0,"
    "astats=metadata=1:reset=1:measure_perchannel=none:measure_overall=Peak_level,"
    "ametadata=mode=print:key=lavfi.astats.Overall.Peak_level:file=-[measured]"
)


def measure(path):
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"Choose an existing WAV export: {path}")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise ValueError("Install FFmpeg, then reopen the terminal and run ffmpeg -version.")
    args = [ffmpeg, "-nostdin", "-hide_banner", "-nostats", "-xerror", "-f", "wav",
            "-i", str(path.resolve()), "-filter_complex", GRAPH, "-map", "[measured]",
            "-f", "null", "-"]
    peak = -math.inf
    peak_frame = None
    frame = None
    with tempfile.TemporaryFile() as log:
        with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=log, text=True,
                              encoding="utf-8", errors="replace") as process:
            for line in process.stdout:
                if line.startswith("frame:"):
                    frame = int(line.split()[0].split(":")[1])
                elif line.startswith("lavfi.astats.Overall.Peak_level="):
                    value = float(line.split("=")[1])
                    if value > peak:
                        peak, peak_frame = value, frame
            result = process.wait()
        log.seek(0)
        diagnostics = log.read().decode("utf-8", errors="replace")
    if result:
        detail = [s for s in diagnostics.splitlines() if "error" in s.lower() or "invalid" in s.lower()]
        raise ValueError(f"Could not measure {path.name}. Check the WAV and FFmpeg installation. "
                         + " ".join(detail[-3:]))
    summary = re.search(r'\{\s*"input_i"\s*:.*?\}', diagnostics, re.DOTALL)
    if summary is None or frame is None:
        raise ValueError(f"No audio measurement returned for {path.name}")
    integrated = float(json.loads(summary.group())["input_i"])
    return {"file": str(path), "integrated_lufs": integrated if math.isfinite(integrated) else None,
            "true_peak_dbtp": peak if math.isfinite(peak) else None,
            "peak_window_start_seconds": None if peak_frame is None else peak_frame * WINDOW / RATE}


def check(export, reference=None, ceiling=-1.0):
    if not math.isfinite(ceiling) or ceiling > 0:
        raise ValueError("Choose a finite true-peak ceiling of 0 dBTP or below.")
    source = measure(export)
    ref = measure(reference) if reference is not None else None
    peak = source["true_peak_dbtp"]
    headroom = None if peak is None else ceiling - peak
    gap = None
    if ref and ref["integrated_lufs"] is not None and source["integrated_lufs"] is not None:
        gap = ref["integrated_lufs"] - source["integrated_lufs"]
    return {"export": source, "reference": ref, "ceiling_dbtp": ceiling,
            "peak_window_ms": 50, "headroom_db": headroom, "gain_to_reference_db": gap,
            "reference_reachable_with_gain": None if gap is None or headroom is None else gap <= headroom}


def report(data):
    lines = []
    for label, item in (("Export", data["export"]), ("Reference", data["reference"])):
        if item is None:
            continue
        loudness = item["integrated_lufs"]
        peak = item["true_peak_dbtp"]
        level = "too short or quiet for integrated loudness" if loudness is None else f"{loudness:.2f} LUFS"
        maximum = "no measurable peak" if peak is None else f"{peak:.2f} dBTP"
        lines.append(f"{label}  {item['file']}  |  {level}  |  {maximum}")
    room = data["headroom_db"]
    if room is None:
        lines.append("No measurable export peak. Check the recorded source or export routing.")
        return "\n".join(lines)
    start = data["export"]["peak_window_start_seconds"]
    minutes, seconds = divmod(start, 60)
    lines.append(f"Listen at {int(minutes):02}:{seconds:06.3f} for the strongest 50 ms window.")
    ceiling = data["ceiling_dbtp"]
    if room < 0:
        lines.append(f"Lower gain by at least {math.ceil(-room*10)/10:.1f} dB to meet {ceiling:g} dBTP.")
    else:
        lines.append(f"Up to {math.floor(room*10)/10:.1f} dB of clean gain fits under {ceiling:g} dBTP.")
    gap = data["gain_to_reference_db"]
    if gap is not None:
        if abs(gap) < .01:
            lines.append("Export and reference have the same measured integrated loudness.")
        else:
            direction = "quieter" if gap > 0 else "louder"
            lines.append(f"The export is {abs(gap):.2f} LU {direction} than the reference. "
                         f"Estimated gain to match: {gap:+.2f} dB.")
        if not data["reference_reachable_with_gain"]:
            lines.append(f"Matching by gain alone would exceed the ceiling by {gap-room:.2f} dB. "
                         "Audition the peak before changing the mix or adding limiting.")
    elif data["reference"]:
        lines.append("A reference comparison needs a measurable integrated level for both files.")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export", type=Path, help="MPC Audio Mixdown or LiveTrak master WAV")
    parser.add_argument("--reference", type=Path, help="optional reference WAV")
    parser.add_argument("--ceiling", type=float, default=-1.0, metavar="DBTP",
                        help="chosen maximum true peak (default: -1 dBTP)")
    parser.add_argument("--json", action="store_true", help="print a machine-readable report")
    args = parser.parse_args()
    result = check(args.export, args.reference, args.ceiling)
    print(json.dumps(result, indent=2, allow_nan=False) if args.json else report(result))
