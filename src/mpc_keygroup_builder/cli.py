#!/usr/bin/env python3
"""Build MPC 3.9 JSON keygroup programs from pitched WAV directories."""

from __future__ import annotations

import argparse
import copy
import gzip
import json
import os
import re
import shutil
import sys
import tempfile
import wave
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


MIDI_PREFIX = re.compile(
    r"^(?P<note>\d{1,3})(?=\D).*?(?:_(?P<variant>\d{4}))?\.wav$", re.IGNORECASE
)
MIDI_SUFFIX = re.compile(
    r"-(?P<note>\d{1,3})(?:_(?P<variant>\d{4}))?\.wav$", re.IGNORECASE
)
PITCH_SUFFIX = re.compile(
    r"(?:^|[ _])(?P<pitch>[A-G](?:#|b)?)(?P<octave>-?\d)(?:_\d{4})?\.wav$",
    re.IGNORECASE,
)
PITCH_BEFORE_ID = re.compile(
    r"(?:^|[ _-])(?P<pitch>[A-G](?:#|b)?)(?P<octave>-?\d)-[A-Z0-9]+\.wav$",
    re.IGNORECASE,
)
PITCH_CLASS = {"C": 0, "C#": 1, "DB": 1, "D": 2, "D#": 3, "EB": 3,
               "E": 4, "F": 5, "F#": 6, "GB": 6, "G": 7, "G#": 8,
               "AB": 8, "A": 9, "A#": 10, "BB": 10, "B": 11}


@dataclass(frozen=True)
class Sample:
    note: int
    path: Path
    frames: int
    velocity_start: int = 0
    velocity_end: int = 127


@dataclass(frozen=True)
class SampleGroup:
    note: int
    layers: tuple[Sample, ...]


def wav_frames(path: Path) -> int:
    try:
        with wave.open(str(path), "rb") as wav:
            frames = wav.getnframes()
    except (EOFError, wave.Error) as error:
        raise ValueError(f"unreadable WAV {path}: {error or 'truncated file'}") from error
    if frames < 1:
        raise ValueError(f"empty WAV: {path}")
    return frames


def filename_pitch(path: Path) -> int | None:
    """Return the library-convention MIDI note from a trailing pitch name."""
    pitch = PITCH_SUFFIX.search(path.name) or PITCH_BEFORE_ID.search(path.name)
    if pitch is None:
        return None
    named = (int(pitch.group("octave")) + 2) * 12 + PITCH_CLASS[pitch.group("pitch").upper()]
    if 0 <= named <= 127:
        return named
    return None


def read_ableton_velocity_ranges(preset: Path) -> dict[str, tuple[int, int]]:
    """Return WAV basename -> inclusive velocity range from an Ableton ADG."""
    try:
        with gzip.open(preset, "rb") as stream:
            root = ET.fromstring(stream.read())
    except (gzip.BadGzipFile, ET.ParseError) as error:
        raise ValueError(f"unreadable Ableton preset {preset}: {error}") from error

    result: dict[str, tuple[int, int]] = {}
    for part in root.iter("MultiSamplePart"):
        name = part.find("./SampleRef/FileRef/Name")
        velocity = part.find("./VelocityRange")
        if name is None or velocity is None:
            continue
        filename = name.get("Value", "")
        minimum = velocity.find("./Min")
        maximum = velocity.find("./Max")
        if not filename.lower().endswith(".wav") or minimum is None or maximum is None:
            continue
        low = int(minimum.get("Value", "-1"))
        high = int(maximum.get("Value", "-1"))
        if low == 1:
            low = 0
        if not 0 <= low <= high <= 127:
            raise ValueError(f"invalid velocity range {low}-{high} for {filename}")
        result[filename] = (low, high)
    if not result:
        raise ValueError(f"no WAV velocity zones in Ableton preset {preset}")
    return result


def read_ableton_root_notes(preset: Path) -> dict[str, int]:
    """Return WAV basename -> MIDI root note from an Ableton ADG."""
    try:
        with gzip.open(preset, "rb") as stream:
            root = ET.fromstring(stream.read())
    except (gzip.BadGzipFile, ET.ParseError) as error:
        raise ValueError(f"unreadable Ableton preset {preset}: {error}") from error
    result: dict[str, int] = {}
    for part in root.iter("MultiSamplePart"):
        name = part.find("./SampleRef/FileRef/Name")
        root_key = part.find("./RootKey")
        if name is None or root_key is None:
            continue
        filename = name.get("Value", "")
        note = int(root_key.get("Value", "-1"))
        if filename.lower().endswith(".wav") and 0 <= note <= 127:
            result[filename] = note
    return result


def _validate_velocity_layers(group: SampleGroup) -> None:
    expected = 0
    for sample in group.layers:
        if sample.velocity_start != expected or sample.velocity_end < sample.velocity_start:
            raise ValueError(
                f"velocity gap or overlap at MIDI {group.note}: expected {expected}, "
                f"got {sample.velocity_start}-{sample.velocity_end}"
            )
        expected = sample.velocity_end + 1
    if expected != 128:
        raise ValueError(f"velocity ranges for MIDI {group.note} do not end at 127")


def discover_samples(
    source: Path,
    velocity_preset: Path | None = None,
    filenames: set[str] | None = None,
) -> list[SampleGroup]:
    velocity_ranges = (
        read_ableton_velocity_ranges(velocity_preset) if velocity_preset is not None else {}
    )
    preset_roots = (
        read_ableton_root_notes(velocity_preset) if velocity_preset is not None else {}
    )
    preset_schema = sorted(
        {zone for zone in velocity_ranges.values() if zone != (0, 127)}
    )
    parsed: list[tuple[int, int, Path, int | None]] = []
    for path in sorted(source.glob("*.wav")):
        named_note = filename_pitch(path)
        preset_note = preset_roots.get(path.name)
        if filenames is not None and path.name not in filenames:
            continue
        match = MIDI_PREFIX.match(path.name) if preset_note is None else None
        suffix_match = MIDI_SUFFIX.search(path.name) if preset_note is None else None
        if preset_note is not None:
            variant = re.search(
                r"_(?P<variant>\d{4})\.wav$", path.name, re.IGNORECASE
            )
            note, suffix, candidate = preset_note, variant.group("variant") if variant else None, None
        elif match is not None:
            note = int(match.group("note"))
            suffix = match.group("variant")
            candidate = named_note
        elif suffix_match is not None:
            note = int(suffix_match.group("note"))
            suffix = suffix_match.group("variant")
            candidate = named_note
        elif named_note is not None:
            note = named_note
            variant = re.search(r"_(?P<variant>\d{4})\.wav$", path.name, re.IGNORECASE)
            suffix = variant.group("variant") if variant is not None else None
            candidate = None
        else:
            continue
        if not 0 <= note <= 127:
            continue
        index = 0 if suffix is None else int(suffix)
        parsed.append((note, index, path, candidate))
    raw_counts = Counter((note, index) for note, index, _, _ in parsed)
    raw_keys = set(raw_counts)
    found: dict[int, dict[int, Path]] = {}
    for note, index, path, candidate in parsed:
        if (
            raw_counts[(note, index)] > 1
            and candidate is not None
            and (candidate, index) not in raw_keys
        ):
            note = candidate
        note_layers = found.setdefault(note, {})
        if index in note_layers:
            raise ValueError(
                f"multiple WAVs map to MIDI {note} layer {index}: "
                f"{note_layers[index].name!r}, {path.name!r}"
            )
        note_layers[index] = path
    if not parsed:
        raise ValueError(f"no pitched WAV filenames in {source}")

    groups: list[SampleGroup] = []
    for note in sorted(found):
        indexed = found[note]
        if sorted(indexed) != list(range(len(indexed))):
            raise ValueError(f"non-contiguous WAV layer suffixes for MIDI {note}")
        if len(indexed) > 8:
            raise ValueError(f"MPC supports at most 8 layers per keygroup (MIDI {note})")
        if len(indexed) > 1 and velocity_preset is None:
            raise ValueError(
                f"multiple WAVs map to MIDI {note}; pass --velocity-preset to map layers"
            )
        layers: list[Sample] = []
        if len(indexed) > 1 and len(preset_schema) != len(indexed):
            raise ValueError(
                f"Ableton preset defines {len(preset_schema)} velocity layers, "
                f"but MIDI {note} has {len(indexed)} WAVs"
            )
        for layer_index, path in indexed.items():
            if velocity_preset is None or len(indexed) == 1:
                low, high = 0, 127
            else:
                low, high = preset_schema[layer_index]
            layers.append(Sample(note, path, wav_frames(path), low, high))
        group = SampleGroup(note, tuple(sorted(layers, key=lambda sample: sample.velocity_start)))
        _validate_velocity_layers(group)
        groups.append(group)
    return groups


def shift_sample_groups(samples: list[SampleGroup], semitones: int) -> list[SampleGroup]:
    """Move sampled roots into another playable register without changing audio."""
    if isinstance(semitones, bool) or not isinstance(semitones, int):
        raise TypeError("root shift must be an integer number of semitones")
    if semitones == 0:
        return samples
    shifted: list[SampleGroup] = []
    for group in samples:
        note = group.note + semitones
        if not 0 <= note <= 127:
            raise ValueError(
                f"root shift {semitones:+d} moves MIDI {group.note} outside 0..127"
            )
        layers = tuple(
            Sample(
                note,
                sample.path,
                sample.frames,
                sample.velocity_start,
                sample.velocity_end,
            )
            for sample in group.layers
        )
        shifted.append(SampleGroup(note, layers))
    return shifted


def read_xpm(path: Path) -> tuple[str, dict]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        text = stream.read()
    start = text.find("{")
    if start < 0:
        raise ValueError(f"no JSON payload in {path}")
    return text[:start], json.loads(text[start:])


def note_ranges(samples: list[SampleGroup]) -> list[tuple[int, int]]:
    """Partition MIDI 0..127 at midpoints between sampled root notes."""
    result: list[tuple[int, int]] = []
    for index, sample in enumerate(samples):
        low = 0 if index == 0 else (samples[index - 1].note + sample.note) // 2 + 1
        high = 127 if index == len(samples) - 1 else (sample.note + samples[index + 1].note) // 2
        result.append((low, high))
    return result


def configure_layer(layer: dict, sample: Sample) -> None:
    layer["active"] = True
    layer["mute"] = False
    layer["velocityStart"] = sample.velocity_start
    layer["velocityEnd"] = sample.velocity_end
    layer["sampleName"] = sample.path.stem
    layer["sampleFile"] = sample.path.name
    layer["rootNote"] = sample.note
    layer["keyTrackEnable"] = True
    layer["sampleStart"] = 0
    layer["sampleEnd"] = 0
    layer["sliceInfo"]["Start"] = 0
    layer["sliceInfo"]["End"] = sample.frames - 1


def disable_layer(layer: dict) -> None:
    layer["active"] = False
    layer["sampleName"] = ""
    layer["sampleFile"] = ""
    layer["velocityStart"] = 0
    layer["velocityEnd"] = 127
    layer["sampleStart"] = 0
    layer["sampleEnd"] = 0
    layer["sliceInfo"]["Start"] = 0
    layer["sliceInfo"]["End"] = 0


def configure_instrument(instrument: dict, group: SampleGroup) -> None:
    layers = instrument["layersv"]
    if len(group.layers) > len(layers):
        raise ValueError(f"template has too few layers for MIDI {group.note}")
    for index, layer in enumerate(layers):
        if index < len(group.layers):
            configure_layer(layer, group.layers[index])
        else:
            disable_layer(layer)


def all_samples(groups: list[SampleGroup]) -> list[Sample]:
    return [sample for group in groups for sample in group.layers]


def build_program(template: Path, samples: list[SampleGroup], name: str) -> tuple[str, dict]:
    header, program = read_xpm(template)
    data = program["data"]
    instruments = data["drum"]["instruments"]
    if len(instruments) < 2:
        raise ValueError("template must contain a universal record and a keygroup record")

    universal = copy.deepcopy(instruments[0])
    keygroup_template = instruments[1]
    configure_instrument(universal, samples[0])
    universal["lowNote"] = samples[0].note
    universal["highNote"] = samples[0].note

    generated = [universal]
    for group, (low, high) in zip(samples, note_ranges(samples)):
        instrument = copy.deepcopy(keygroup_template)
        instrument["lowNote"] = low
        instrument["highNote"] = high
        configure_instrument(instrument, group)
        generated.append(instrument)

    flattened = all_samples(samples)
    data["name"] = name
    data["drum"]["instruments"] = generated
    data["keygroup"]["numKeygroups"] = len(samples)
    data["samples"] = [
        {
            "version": 1,
            "name": sample.path.stem,
            "path": sample.path.name,
            "loadImpl": 0,
            "metadata": {
                "tempo": 0.0,
                "rootNote": sample.note,
                "tune": 0.0,
                "key": "",
            },
        }
        for sample in flattened
    ]
    validate_program(program, samples)
    return header, program


def validate_program(program: dict, samples: list[SampleGroup]) -> None:
    data = program["data"]
    instruments = data["drum"]["instruments"]
    if data["keygroup"]["numKeygroups"] != len(samples):
        raise ValueError("keygroup count mismatch")
    if len(instruments) != len(samples) + 1:
        raise ValueError("instrument record count mismatch")
    for instrument, group in zip(instruments[1:], samples):
        active = [
            layer
            for layer in instrument["layersv"]
            if layer["active"] and layer["sampleFile"]
        ]
        if len(active) != len(group.layers):
            raise ValueError(f"layer count mismatch for MIDI {group.note}")
        for layer, sample in zip(active, group.layers):
            if layer["sampleFile"] != sample.path.name:
                raise ValueError(f"sample reference mismatch for MIDI {sample.note}")
            if layer["sliceInfo"]["End"] != sample.frames - 1:
                raise ValueError(f"sample endpoint mismatch for MIDI {sample.note}")
            if (layer["velocityStart"], layer["velocityEnd"]) != (
                sample.velocity_start,
                sample.velocity_end,
            ):
                raise ValueError(f"velocity range mismatch for {sample.path.name}")


def validate_written_program(output: Path) -> dict[str, int]:
    header, program = read_xpm(output)
    if not header.startswith("ACVS\n") or "SerialisableProgramData\njson\n" not in header:
        raise ValueError(f"invalid MPC 3.9 header in {output}")

    data = program["data"]
    instruments = data["drum"]["instruments"]
    keygroup_count = data["keygroup"]["numKeygroups"]
    if len(instruments) != keygroup_count + 1:
        raise ValueError("written instrument record count mismatch")

    registry = {entry["path"]: entry for entry in data["samples"]}
    if len(registry) != len(data["samples"]):
        raise ValueError("written sample registry contains duplicate paths")

    data_dir = output.with_name(f"{output.stem}_[ProgramData]")
    expected_low = 0
    seen: set[str] = set()
    for instrument in instruments[1:]:
        low = instrument["lowNote"]
        high = instrument["highNote"]
        if low != expected_low or high < low:
            raise ValueError(f"MIDI range gap or overlap at {low}-{high}")
        expected_low = high + 1
        active = [
            layer
            for layer in instrument["layersv"]
            if layer["active"] and layer["sampleFile"]
        ]
        if not active:
            raise ValueError(f"keygroup {low}-{high} has no active layers")
        expected_velocity = 0
        for layer in sorted(active, key=lambda item: item["velocityStart"]):
            if layer["velocityStart"] != expected_velocity:
                raise ValueError(f"velocity gap or overlap in keygroup {low}-{high}")
            expected_velocity = layer["velocityEnd"] + 1
            filename = layer["sampleFile"]
            if not filename or filename not in registry:
                raise ValueError(f"unregistered layer sample: {filename!r}")
            sample_path = data_dir / filename
            if not sample_path.is_file():
                raise ValueError(f"missing ProgramData sample: {sample_path}")
            frames = wav_frames(sample_path)
            if layer["sliceInfo"]["End"] != frames - 1:
                raise ValueError(f"written endpoint mismatch: {filename}")
            if registry[filename]["metadata"]["rootNote"] != layer["rootNote"]:
                raise ValueError(f"root-note mismatch: {filename}")
            seen.add(filename)
        if expected_velocity != 128:
            raise ValueError(f"velocity ranges do not end at 127 in keygroup {low}-{high}")

    if expected_low != 128:
        raise ValueError("MIDI ranges do not end at 127")
    if seen != set(registry):
        raise ValueError("registry contains samples unused by keygroups")
    return {"keygroups": keygroup_count, "samples": len(registry)}


def write_program(
    header: str, program: dict, samples: list[SampleGroup], output: Path, *, force: bool
) -> None:
    data_dir = output.with_name(f"{output.stem}_[ProgramData]")
    targets = [output, data_dir]
    if not force and any(target.exists() for target in targets):
        raise FileExistsError("output exists; pass --force to replace it")
    output.parent.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    for sample in all_samples(samples):
        copy_file_durable(sample.path, data_dir / sample.path.name)
    write_xpm(header, program, output)
    validate_written_program(output)


def write_xpm(header: str, program: dict, output: Path) -> None:
    """Durably replace an XPM, avoiding zero-byte files on removable media."""
    payload = header + json.dumps(program, indent=4)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=output.parent, prefix=f".{output.name}.", delete=False
        ) as raw:
            temporary = Path(raw.name)
            with gzip.GzipFile(filename=output.name, mode="wb", fileobj=raw) as compressed:
                compressed.write(payload.encode("utf-8"))
            raw.flush()
            os.fsync(raw.fileno())
        os.replace(temporary, output)
        directory_fd = os.open(output.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def copy_file_durable(source: Path, destination: Path) -> None:
    """Copy a file with flush and atomic replacement for removable media."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=destination.parent, prefix=f".{destination.name}.", delete=False
        ) as output:
            temporary = Path(output.name)
            with source.open("rb") as input_stream:
                shutil.copyfileobj(input_stream, output)
            output.flush()
            os.fsync(output.fileno())
        shutil.copystat(source, temporary)
        os.replace(temporary, destination)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="directory containing pitched WAV files")
    parser.add_argument("--template", required=True, type=Path, help="working MPC 3.9 keygroup XPM")
    parser.add_argument("--velocity-preset", type=Path, help="Ableton ADG containing velocity zones")
    parser.add_argument("--output", type=Path, help="destination .xpm path")
    parser.add_argument("--name", help="MPC program name (defaults to source directory name)")
    parser.add_argument(
        "--root-shift",
        type=int,
        default=0,
        metavar="SEMITONES",
        help="shift all sample roots/playable ranges by a fixed semitone offset",
    )
    parser.add_argument("--force", action="store_true", help="replace an existing output program")
    parser.add_argument("--dry-run", action="store_true", help="inspect mapping without writing")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    source = args.source.resolve()
    samples = shift_sample_groups(
        discover_samples(source, args.velocity_preset), args.root_shift
    )
    ranges = note_ranges(samples)
    flattened = all_samples(samples)
    print(f"Program: {args.name or source.name}")
    print(f"Source: {source}")
    print(
        f"Keygroups: {len(samples)} ({samples[0].note}-{samples[-1].note}); "
        f"samples: {len(flattened)}"
    )
    for group, (low, high) in zip(samples, ranges):
        layer_text = ", ".join(
            f"v{sample.velocity_start}-{sample.velocity_end}:{sample.path.name}"
            for sample in group.layers
        )
        print(f"  MIDI {low:3d}-{high:3d} <- root {group.note:3d} [{layer_text}]")
    if args.dry_run:
        return 0
    if args.output is None:
        raise ValueError("--output is required unless --dry-run is used")
    name = args.name or source.name
    header, program = build_program(args.template, samples, name)
    write_program(header, program, samples, args.output, force=args.force)
    print(f"Created: {args.output}")
    print(f"Created: {args.output.with_name(f'{args.output.stem}_[ProgramData]')}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, FileExistsError, KeyError, ValueError, wave.Error) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2)
