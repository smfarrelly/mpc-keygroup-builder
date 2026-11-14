"""Render a Loop Throw gesture on a local PCM16 loop using the plugin DSP."""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import wave

from mpc_keygroup_builder.bundle_verify import sha256, verify_bundle
from mpc_keygroup_builder.publication import publish_directory

PLUGIN = Path(__file__).resolve().parents[1]
DIVISIONS = ("1/16", "1/8", "1/8D", "1/4")


def audition(source, sdk, output, bpm, beat, duration, division, repeats, tone, tail):
    if not (15 <= bpm <= 300 and beat >= 1 and 0 < duration <= 16 and
            0 <= repeats <= 85 and 400 <= tone <= 14000 and 0 <= tail <= 30):
        raise ValueError("use 15–300 BPM, beat >=1, length (0,16] beats, repeats 0–85%, tone 400–14000 Hz, tail 0–30 seconds")
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"choose a new output folder: {output}")
    if not (sdk / "framework/mpc_plugin.h").is_file():
        raise ValueError(f"Akai SDK framework not found under {sdk}")
    compiler = shutil.which("c++")
    if not compiler:
        raise ValueError("install a local C++17 compiler (on Ubuntu: sudo apt install g++)")
    with wave.open(str(source), "rb") as wav:
        channels, width, rate, frames, _, _ = wav.getparams()
        if width != 2 or channels not in (1, 2) or not 8000 <= rate <= 192000:
            raise ValueError("use a mono or stereo PCM16 WAV at 8–192 kHz")
        if not 0 < frames <= rate * 120:
            raise ValueError("choose a nonempty loop of up to 120 seconds")
        if beat > 1 + frames * bpm / (60 * rate):
            raise ValueError("the throw starts past the end of the loop")
        start = round((beat - 1) * rate * 60 / bpm)
        stop = round((beat - 1 + duration) * rate * 60 / bpm)
        if start >= frames or stop <= start:
            raise ValueError("the throw must capture at least one input frame")
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            private = Path(tmp)
            runner = private / "render"
            compile_run = subprocess.run([compiler, "-std=c++17", "-O2", "-I", str(sdk / "framework"),
                            str(PLUGIN / "tools/render.cpp"), "-o", str(runner)], capture_output=True, text=True)
            if compile_run.returncode:
                raise ValueError(f"C++ build failed: {compile_run.stderr[-2000:]}")
            args = [str(value) for value in (rate, bpm, start, stop, DIVISIONS.index(division), repeats, tone)]
            tail_frames = round(tail * rate)
            with (private / "input.pcm").open("w+b") as raw, (private / "output.pcm").open("w+b") as rendered:
                remaining = frames
                while remaining:
                    count = min(remaining, 8192)
                    block = wav.readframes(count)
                    if len(block) != count * channels * width:
                        raise ValueError("truncated input WAV")
                    if channels == 1:
                        stereo = bytearray(len(block) * 2)
                        for byte in (0, 1):
                            stereo[byte::4] = stereo[byte + 2::4] = block[byte::2]
                        block = stereo
                    raw.write(block)
                    remaining -= count
                raw.write(bytes(4 * tail_frames))
                raw.seek(0)
                run = subprocess.run([str(runner), *args], stdin=raw, stdout=rendered, stderr=subprocess.PIPE,
                                     check=True, timeout=120, text=True)
                if rendered.tell() != 4 * (frames + tail_frames):
                    raise ValueError("renderer returned an incomplete comparison")
                staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
                try:
                    for label, pcm in [("Dry", raw), ("Loop Throw", rendered)]:
                        pcm.seek(0)
                        with wave.open(str(staging / (label + ".wav")), "wb") as out:
                            out.setparams((2, 2, rate, frames + tail_frames, "NONE", ""))
                            while chunk := pcm.read(65536):
                                out.writeframesraw(chunk)
                    settings = {
                        "schema_version": 1, "kind": "loop-throw-audition", "source": source.name,
                        "sample_rate": rate, "source_channels": channels, "source_frames": frames,
                        "bpm": bpm, "beat": beat, "length_beats": duration, "division": division,
                        "repeats_percent": repeats, "tone_hz": tone, "tail_seconds": tail,
                        "open_frame": start, "close_frame": stop, "renderer_message": run.stderr.strip(),
                        "hardware_status": "untested",
                    }
                    (staging / "settings.json").write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
                    checksums = {p.name: sha256(p) for p in sorted(staging.iterdir())}
                    (staging / "checksums.json").write_text(json.dumps(checksums, indent=2) + "\n", encoding="utf-8")
                    verify_bundle(staging)
                    publish_directory(staging, output)
                    if run.stderr.strip():
                        print(run.stderr.strip())
                finally:
                    shutil.rmtree(staging, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="mono or stereo PCM16 WAV loop")
    parser.add_argument("--sdk", type=Path, required=True, help="local Akai SDK checkout")
    parser.add_argument("--output", type=Path, required=True, help="new folder for dry and processed files at the same gain")
    parser.add_argument("--bpm", type=float, required=True, help="source tempo")
    parser.add_argument("--beat", type=float, required=True, help="first beat to capture, counted from 1")
    parser.add_argument("--length", type=float, default=0.5, help="capture duration in beats")
    parser.add_argument("--division", choices=DIVISIONS, default="1/8")
    parser.add_argument("--repeats", type=float, default=50, help="feedback percent")
    parser.add_argument("--tone", type=float, default=5500, help="echo low-pass cutoff in Hz")
    parser.add_argument("--tail", type=float, default=2, help="seconds to append to both files")
    args = parser.parse_args()
    try:
        audition(args.input, args.sdk, args.output, args.bpm, args.beat, args.length,
                 args.division, args.repeats, args.tone, args.tail)
    except (OSError, ValueError, wave.Error, EOFError, subprocess.SubprocessError) as exc:
        parser.exit(2, f"Could not render this loop: {exc}\n")
    print(f"Dry and processed WAVs: {args.output.resolve()}")


if __name__ == "__main__":
    main()
