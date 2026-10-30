"""Render deterministic local audition WAVs from MPC XPM programs."""

from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import os
import struct
import tempfile
import wave
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, BinaryIO

from .wave_io import complete_riff_view, counted_zero_padding
from .program_io import read_payload, serialized_document, xml_root
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
    sample_start: int = 0
    sample_end: int | None = None


def trim_sample(samples: list[float], start: object, end: object) -> tuple[list[float], int, int]:
    """Apply inclusive source-frame bounds before pitch/rate conversion."""
    def frame(value: object, default: int) -> int:
        if value is None:
            return default
        if type(value) is int:
            return value
        if isinstance(value, str) and value.strip().lstrip('-').isdigit():
            return int(value)
        raise ValueError(f"sample bounds must be integer frame offsets, got {value!r}")

    first, last = frame(start, 0), frame(end, len(samples) - 1)
    if not 0 <= first <= last < len(samples):
        raise ValueError(f"sample bounds {first}..{last} are invalid for {len(samples)} frames")
    return samples[first:last + 1], first, last


def read_pcm_channels(path: Path | BinaryIO) -> tuple[list[list[float]], int]:
    try:
        with ExitStack() as stack:
            source = stack.enter_context(path.open("rb")) if isinstance(path, Path) else path
            stream = stack.enter_context(wave.open(complete_riff_view(source), "rb"))
            channels = stream.getnchannels()
            width = stream.getsampwidth()
            rate = stream.getframerate()
            count = stream.getnframes()
            if width not in (1, 2, 3, 4):
                raise ValueError(f"unsupported sample width {width}: {path}")
            if channels not in (1, 2):
                raise ValueError(f"unsupported channel count {channels}: {path}")
            if rate <= 0 or count <= 0:
                raise ValueError(f"empty WAV or invalid sample rate: {path}")
            frames = stream.readframes(count + 1)
    except (wave.Error, EOFError) as error:
        raise ValueError(f"unreadable WAV: {error or 'truncated header'}: {path}") from error
    frame_width = width * channels
    if len(frames) > count * frame_width:
        if counted_zero_padding(channels, width, count, frames[count * frame_width:]):
            frames = frames[:count * frame_width]
        else:
            raise ValueError(f"WAV data contains an incomplete PCM frame: {path}")
    if len(frames) != count * frame_width:
        raise ValueError(f"truncated WAV: expected {count * frame_width} PCM bytes, got {len(frames)}: {path}")
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
    return [decoded[channel::channels] for channel in range(channels)], rate


def read_pcm_mono(path: Path | BinaryIO) -> tuple[list[float], int]:
    channels, rate = read_pcm_channels(path)
    if len(channels) == 1:
        return channels[0], rate
    return [(left + right) * 0.5 for left, right in zip(*channels)], rate


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
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with wave.open(str(temporary), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(OUTPUT_RATE)
            stream.writeframes(bytes(pcm))
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def output_paths(program: Path, output: Path) -> tuple[Path, Path]:
    requested = output.expanduser()
    if requested.suffix.casefold() != ".wav":
        raise ValueError("audition output must use a .wav extension")
    manifest_requested = requested.with_suffix(".json")
    for label, path in (("audio", requested), ("manifest", manifest_requested)):
        if path.is_symlink():
            raise ValueError(f"audition {label} output may not be a symbolic link: {path}")
        resolved = path.resolve()
        if resolved == program.expanduser().resolve():
            raise ValueError(f"audition {label} output may not replace the input program: {path}")
        if resolved.exists() and not resolved.is_file():
            raise ValueError(f"audition {label} output is not a regular file: {path}")
    return requested.resolve(), manifest_requested.resolve()


def _json_program(path: Path, *, raw: bytes | None = None) -> dict[str, Any]:
    if raw is None:
        raw, compressed = read_payload(path)
        if not compressed:
            raise ValueError("Keygroup audition requires a compressed MPC program")
    _, document = serialized_document(raw)
    data = document.get("data", {})
    # Untyped legacy payloads must explicitly declare a keygroup section.
    kind = data.get("type")
    if kind != 1 and not (kind is None and isinstance(data.get("keygroup"), dict)):
        raise ValueError("audition supports compressed Keygroups only; compressed Drum programs are not supported")
    instruments = data.get("drum", {}).get("instruments", [])
    if any(not isinstance(instrument, dict) for instrument in instruments):
        raise ValueError("Keygroup instruments must be objects")
    return data


def keygroup_events(path: Path, *, raw: bytes | None = None) -> tuple[list[AuditionEvent], list[list[float]]]:
    data = _json_program(path, raw=raw)
    instruments = data.get("drum", {}).get("instruments", [])[1:]
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
        bounds = layer.get("sliceInfo") or {}
        if not isinstance(bounds, dict):
            raise ValueError("sliceInfo must contain source-frame bounds")
        samples, first, last = trim_sample(
            samples, bounds.get("Start", layer.get("sampleStart")),
            bounds.get("End", layer.get("sampleEnd")),
        )
        audio.append(shape(resample(samples, rate, pitch), velocity))
        events.append(AuditionEvent(index, note, velocity, reference, root_note, pitch, first, last))
    return events, audio


def _drum_velocities(values) -> tuple[int, ...]:
    values = tuple(values)
    if not 1 <= len(values) <= 8 or any(type(v) is not int or not 1 <= v <= 127 for v in values):
        raise ValueError("choose 1–8 Drum audition velocities, each an integer from 1 to 127")
    return values


def drum_events(path: Path, *, raw: bytes | None = None,
                velocities: tuple[int, ...] = (100,), bank: str | None = None) -> tuple[list[AuditionEvent], list[list[float]]]:
    velocities = _drum_velocities(velocities)
    if bank is not None and bank not in tuple("ABCDEFGH"):
        raise ValueError("Drum audition bank must be A–H")
    first_pad = 1 + 16 * "ABCDEFGH".index(bank) if bank is not None else None
    if raw is None:
        raw, compressed = read_payload(path)
        if compressed:
            raise ValueError("Drum audition requires an XML Drum program")
    root = xml_root(raw)
    program = root.find("Program")
    if program is not None and program.get("type") not in {None, "Drum"}:
        raise ValueError("XML audition supports Drum programs only")
    indexes = _audio_index(path.parent, recursive=True)
    events = []
    audio = []
    populated = 0
    for instrument in root.iter("Instrument"):
        number = _integer(instrument.get("number"), None)
        if first_pad is not None:
            if number is None or not 1 <= number <= 128:
                raise ValueError("bank selection requires instrument numbers from 1 to 128")
            if not first_pad <= number < first_pad + 16:
                continue
        layers = [(layer, (layer.findtext("SampleFile") or layer.findtext("SampleName") or "").strip())
                  for layer in instrument.iter("Layer")]
        layers = [(layer, reference) for layer, reference in layers if reference]
        if not layers:
            continue
        if populated >= 16:
            break
        populated += 1
        pad = _integer(instrument.get("number"), populated)
        for velocity in velocities:
            selected = next(((layer, reference) for layer, reference in layers
                             if _integer(layer.findtext("VelStart"), 0) <= velocity
                             <= _integer(layer.findtext("VelEnd"), 127)), None)
            if selected is None:
                raise ValueError(f"no layer for pad {pad} velocity {velocity}")
            layer, reference = selected
            paths = _resolve(reference, indexes)
            if len(paths) != 1:
                raise ValueError(f"sample resolution returned {len(paths)} files: {reference}")
            samples, rate = read_pcm_mono(paths[0])
            samples, first, last = trim_sample(
                samples, layer.findtext("SliceStart", layer.findtext("SampleStart")),
                layer.findtext("SliceEnd", layer.findtext("SampleEnd")),
            )
            pitch = _integer(layer.findtext("TuneCoarse"), 0) + _integer(
                layer.findtext("TuneFine"), 0
            ) / 100.0
            audio.append(shape(resample(samples, rate, pitch), velocity))
            events.append(AuditionEvent(len(events), pad, velocity, reference, 0, pitch, first, last))
    if not events:
        raise ValueError(f"drum program has no populated layers{' in bank ' + bank if bank else ''}")
    return events, audio


def render(program: Path, output: Path, *, drum_velocities: tuple[int, ...] | None = None,
           drum_bank: str | None = None) -> dict[str, Any]:
    output, manifest_path = output_paths(program, output)
    raw, compressed = read_payload(program)
    if compressed:
        if drum_velocities is not None or drum_bank is not None:
            raise ValueError("--drum-velocities and --drum-bank apply only to XML Drum programs")
        events, clips = keygroup_events(program, raw=raw)
        program_type = "Keygroup"
    else:
        events, clips = drum_events(program, raw=raw, velocities=(100,) if drum_velocities is None else drum_velocities, bank=drum_bank)
        program_type = "Drum"
    silence = [0.0] * int(OUTPUT_RATE * 0.12)
    rendered = []
    for clip in clips:
        rendered.extend(clip)
        rendered.extend(silence)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_wav(output, rendered)
    manifest = {
        "program": str(program),
        "program_type": program_type,
        "output": str(output),
        "sample_rate": OUTPUT_RATE,
        "duration_seconds": len(rendered) / OUTPUT_RATE,
        "events": [asdict(event) for event in events],
        "limitations": "Approximate dry sample selection, inclusive source-frame trim, and pitch preview; MPC loops, envelopes, filters, effects, warp, and voice behavior are not rendered. Each event is capped at 1.25 seconds with a synthetic fade.",
    }
    if program_type == "Drum":
        manifest["drum_bank"] = drum_bank
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{manifest_path.name}.", dir=manifest_path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(json.dumps(manifest, indent=2) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, manifest_path)
    finally:
        temporary.unlink(missing_ok=True)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("program", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--drum-velocities", nargs="+", type=int, metavar="VELOCITY",
                        help="XML Drum only: 1–8 velocities (1–127) played in order on each of the first 16 populated pads; default: 100")
    parser.add_argument("--drum-bank", type=str.upper, choices=tuple("ABCDEFGH"),
                        help="XML Drum only: preview populated pads in one bank A–H")
    args = parser.parse_args()
    print(json.dumps(render(args.program.expanduser().resolve(), args.output.expanduser().resolve(),
                            drum_velocities=args.drum_velocities, drum_bank=args.drum_bank), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
