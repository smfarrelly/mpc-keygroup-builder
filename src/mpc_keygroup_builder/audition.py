"""Render deterministic local audition WAVs from MPC XPM programs."""

from __future__ import annotations

import argparse
import gzip
import json
import struct
import wave
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .testing import _audio_index, _boolean, _integer, _resolve


OUTPUT_RATE = 44_100
KEYGROUP_NOTES = (48, 52, 55, 60, 64, 67, 72, 76, 79, 84)


@dataclass(frozen=True)
class AuditionEvent:
    index: int
    note_or_pad: int
    velocity: int
    sample: str
    root_note: int
    pitch_semitones: float


def read_pcm_mono(path: Path) -> tuple[list[float], int]:
    with wave.open(str(path), "rb") as stream:
        channels = stream.getnchannels()
        width = stream.getsampwidth()
        rate = stream.getframerate()
        frames = stream.readframes(stream.getnframes())
    if width not in (1, 2, 3, 4):
        raise ValueError(f"unsupported sample width {width}: {path}")
    if channels not in (1, 2):
        raise ValueError(f"unsupported channel count {channels}: {path}")
    frame_width = width * channels
    frames = frames[: len(frames) - (len(frames) % frame_width)]
    if width == 1:
        decoded = [(value - 128) / 128.0 for value in frames]
    elif width == 2:
        values = struct.unpack(f"<{len(frames) // 2}h", frames)
        decoded = [value / 32768.0 for value in values]
    elif width == 3:
        decoded = []
        for offset in range(0, len(frames), 3):
            value = int.from_bytes(frames[offset : offset + 3], "little", signed=True)
            decoded.append(value / 8_388_608.0)
    else:
        values = struct.unpack(f"<{len(frames) // 4}i", frames)
        decoded = [value / 2_147_483_648.0 for value in values]
    if channels == 1:
        return decoded, rate
    return [
        (decoded[index] + decoded[index + 1]) * 0.5
        for index in range(0, len(decoded), 2)
    ], rate


def resample(samples: list[float], source_rate: int, pitch_semitones: float) -> list[float]:
    step = (source_rate / OUTPUT_RATE) * (2.0 ** (pitch_semitones / 12.0))
    if not samples or step <= 0:
        return []
    length = max(1, int(len(samples) / step))
    output = []
    for index in range(length):
        position = index * step
        left = min(int(position), len(samples) - 1)
        right = min(left + 1, len(samples) - 1)
        fraction = position - left
        output.append(samples[left] * (1.0 - fraction) + samples[right] * fraction)
    return output


def shape(samples: list[float], velocity: int, max_seconds: float = 1.25) -> list[float]:
    limited = samples[: int(OUTPUT_RATE * max_seconds)]
    gain = max(0.05, min(1.0, velocity / 127.0)) * 0.8
    fade = min(len(limited), int(OUTPUT_RATE * 0.02))
    output = [sample * gain for sample in limited]
    for index in range(fade):
        output[-fade + index] *= 1.0 - index / max(1, fade - 1)
    return output


def write_wav(path: Path, samples: list[float]) -> None:
    peak = max((abs(sample) for sample in samples), default=1.0)
    scale = 0.95 / peak if peak > 1.0 else 0.95
    pcm = bytearray()
    for sample in samples:
        value = max(-32768, min(32767, round(sample * scale * 32767)))
        pcm.extend(struct.pack("<h", value))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(OUTPUT_RATE)
        stream.writeframes(bytes(pcm))


def _json_program(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        text = stream.read()
    return json.loads(text[text.find("{") :])["data"]


def keygroup_events(path: Path) -> tuple[list[AuditionEvent], list[list[float]]]:
    data = _json_program(path)
    instruments = data["drum"]["instruments"][1:]
    indexes = _audio_index(path.with_name(f"{path.stem}_[ProgramData]"), recursive=False)
    events = []
    audio = []
    for index, note in enumerate(KEYGROUP_NOTES):
        velocity = 48 if index % 2 == 0 else 108
        matches = []
        for instrument in instruments:
            if not _integer(instrument.get("lowNote"), -1) <= note <= _integer(
                instrument.get("highNote"), -1
            ):
                continue
            for layer in instrument.get("layersv", []):
                if (
                    isinstance(layer, dict)
                    and _boolean(layer.get("active"))
                    and layer.get("sampleFile")
                    and _integer(layer.get("velocityStart"), 0)
                    <= velocity
                    <= _integer(layer.get("velocityEnd"), 127)
                ):
                    matches.append((instrument, layer))
        if not matches:
            raise ValueError(f"no layer for MIDI {note} velocity {velocity}")
        instrument, layer = matches[0]
        reference = str(layer["sampleFile"])
        paths = _resolve(reference, indexes)
        if len(paths) != 1:
            raise ValueError(f"sample resolution returned {len(paths)} files: {reference}")
        root_note = _integer(layer.get("rootNote"), note)
        pitch = (
            note - root_note
            + float(layer.get("pitch", 0.0))
            + _integer(layer.get("coarseTune"), 0)
            + _integer(instrument.get("coarseTune"), 0)
            + float(layer.get("fineTune", 0.0)) / 100.0
            + float(instrument.get("fineTune", 0.0)) / 100.0
        )
        samples, rate = read_pcm_mono(paths[0])
        audio.append(shape(resample(samples, rate, pitch), velocity))
        events.append(AuditionEvent(index, note, velocity, reference, root_note, pitch))
    return events, audio


def drum_events(path: Path) -> tuple[list[AuditionEvent], list[list[float]]]:
    root = ET.parse(path).getroot()
    indexes = _audio_index(path.parent, recursive=True)
    events = []
    audio = []
    for instrument in root.iter("Instrument"):
        if len(events) >= 16:
            break
        selected = None
        for layer in instrument.iter("Layer"):
            reference = (layer.findtext("SampleFile") or layer.findtext("SampleName") or "").strip()
            start = _integer(layer.findtext("VelStart"), 0)
            end = _integer(layer.findtext("VelEnd"), 127)
            if reference and start <= 100 <= end:
                selected = (layer, reference)
                break
        if selected is None:
            continue
        layer, reference = selected
        paths = _resolve(reference, indexes)
        if len(paths) != 1:
            raise ValueError(f"sample resolution returned {len(paths)} files: {reference}")
        samples, rate = read_pcm_mono(paths[0])
        pitch = _integer(layer.findtext("TuneCoarse"), 0) + _integer(
            layer.findtext("TuneFine"), 0
        ) / 100.0
        audio.append(shape(resample(samples, rate, pitch), 100))
        pad = _integer(instrument.get("number"), len(events) + 1)
        events.append(AuditionEvent(len(events), pad, 100, reference, 0, pitch))
    if not events:
        raise ValueError("drum program has no populated layers")
    return events, audio


def render(program: Path, output: Path) -> dict[str, Any]:
    if program.read_bytes()[:2] == b"\x1f\x8b":
        events, clips = keygroup_events(program)
        program_type = "Keygroup"
    else:
        events, clips = drum_events(program)
        program_type = "Drum"
    silence = [0.0] * int(OUTPUT_RATE * 0.12)
    rendered = []
    for clip in clips:
        rendered.extend(clip)
        rendered.extend(silence)
    write_wav(output, rendered)
    manifest = {
        "program": str(program),
        "program_type": program_type,
        "output": str(output),
        "sample_rate": OUTPUT_RATE,
        "duration_seconds": len(rendered) / OUTPUT_RATE,
        "events": [asdict(event) for event in events],
        "limitations": "Approximate dry sample selection and pitch preview; MPC envelopes, filters, effects, warp, and voice behavior are not rendered.",
    }
    output.with_suffix(".json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("program", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(render(args.program.expanduser().resolve(), args.output.expanduser().resolve()), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
