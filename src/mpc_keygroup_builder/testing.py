"""Local semantic simulation and validation for MPC XPM programs."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import wave
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable


AUDIO_SUFFIXES = {".wav", ".aif", ".aiff"}
TEST_VELOCITIES = (0, 1, 16, 32, 64, 96, 126, 127)


@dataclass(frozen=True)
class Issue:
    severity: str
    code: str
    message: str


@dataclass
class ProgramTest:
    path: str
    scope: str = "production"
    program_type: str = "Unknown"
    format: str = "unknown"
    verdict: str = "fail"
    sample_references: int = 0
    playable_notes: int = 0
    dead_trigger_cells: int = 0
    stacked_trigger_cells: int = 0
    issues: list[Issue] = field(default_factory=list)

    def error(self, code: str, message: str) -> None:
        self.issues.append(Issue("error", code, message))

    def warn(self, code: str, message: str) -> None:
        self.issues.append(Issue("warning", code, message))

    def finish(self) -> None:
        severities = {issue.severity for issue in self.issues}
        self.verdict = "fail" if "error" in severities else "warn" if severities else "pass"


def _integer(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _boolean(value: Any) -> bool:
    return value is True or str(value).casefold() == "true"


def _audio_index(root: Path, recursive: bool) -> tuple[dict[str, list[Path]], dict[str, list[Path]]]:
    paths = root.rglob("*") if recursive else root.glob("*")
    by_name: dict[str, list[Path]] = {}
    by_stem: dict[str, list[Path]] = {}
    for path in paths:
        if not path.is_file() or path.suffix.lower() not in AUDIO_SUFFIXES:
            continue
        by_name.setdefault(path.name.casefold(), []).append(path)
        by_stem.setdefault(path.stem.casefold(), []).append(path)
    return by_name, by_stem


def _resolve(reference: str, indexes: tuple[dict[str, list[Path]], dict[str, list[Path]]]) -> list[Path]:
    by_name, by_stem = indexes
    name = Path(reference).name
    return by_name.get(name.casefold(), []) or by_stem.get(Path(name).stem.casefold(), [])


def _wave_frames(path: Path, result: ProgramTest, reference: str) -> int | None:
    if path.stat().st_size == 0:
        result.error("zero_byte_sample", f"zero-byte sample: {reference}")
        return None
    if path.suffix.lower() != ".wav":
        return None
    try:
        with wave.open(str(path), "rb") as stream:
            frames = stream.getnframes()
            if frames <= 0:
                result.error("empty_audio", f"sample contains no frames: {reference}")
            if stream.getnchannels() not in (1, 2):
                result.warn("unusual_channels", f"sample has {stream.getnchannels()} channels: {reference}")
            return frames
    except (wave.Error, EOFError) as error:
        result.warn("wave_probe_unsupported", f"standard WAV probe could not read {reference}: {error}")
        return None


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _active_json_layers(instrument: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        layer
        for layer in instrument.get("layersv", [])
        if isinstance(layer, dict) and _boolean(layer.get("active")) and layer.get("sampleFile")
    ]


def _validate_json_audio(
    result: ProgramTest,
    instruments: list[dict[str, Any]],
    registry: dict[str, dict[str, Any]],
    data_root: Path,
) -> None:
    indexes = _audio_index(data_root, recursive=False) if data_root.is_dir() else ({}, {})
    seen: set[str] = set()
    for instrument in instruments:
        for layer in _active_json_layers(instrument):
            reference = str(layer["sampleFile"])
            seen.add(reference)
            matches = _resolve(reference, indexes)
            if not matches:
                result.error("missing_sample", f"missing ProgramData sample: {reference}")
                continue
            if len(matches) > 1:
                result.error("ambiguous_sample", f"ambiguous ProgramData sample: {reference}")
                continue
            frames = _wave_frames(matches[0], result, reference)
            if reference not in registry:
                result.error("unregistered_sample", f"layer sample absent from registry: {reference}")
            root_note = _integer(layer.get("rootNote"), -1)
            if not 0 <= root_note <= 127:
                result.error("invalid_root_note", f"root note {root_note} for {reference}")
            if frames is not None:
                slice_info = layer.get("sliceInfo", {})
                end = _integer(slice_info.get("End", layer.get("sampleEnd", 0)), 0)
                if end < 0 or end >= frames:
                    result.error("invalid_sample_end", f"sample end {end} outside {reference} ({frames} frames)")
                if _boolean(layer.get("loop")):
                    loop_start = _integer(layer.get("loopStart"), 0)
                    loop_end = _integer(layer.get("loopEnd"), 0)
                    if not 0 <= loop_start < loop_end <= frames:
                        result.error(
                            "invalid_loop", f"loop {loop_start}-{loop_end} outside {reference} ({frames} frames)"
                        )
    unused = sorted(set(registry) - seen)
    if unused:
        result.warn("unused_registry_samples", f"{len(unused)} registry samples are not used by active layers")


def _simulate_keygroup(result: ProgramTest, instruments: list[dict[str, Any]]) -> None:
    playable: set[int] = set()
    dead = 0
    stacked = 0
    for note in range(128):
        note_has_trigger = False
        for velocity in TEST_VELOCITIES:
            triggers = 0
            for instrument in instruments:
                low = _integer(instrument.get("lowNote"), -1)
                high = _integer(instrument.get("highNote"), -1)
                if not low <= note <= high:
                    continue
                for layer in _active_json_layers(instrument):
                    if _integer(layer.get("velocityStart"), 0) <= velocity <= _integer(
                        layer.get("velocityEnd"), 127
                    ):
                        triggers += 1
            if triggers == 0:
                dead += 1
            else:
                note_has_trigger = True
            if triggers > 1:
                stacked += 1
        if note_has_trigger:
            playable.add(note)
    result.playable_notes = len(playable)
    result.dead_trigger_cells = dead
    result.stacked_trigger_cells = stacked
    if dead:
        result.error("dead_note_velocity_cells", f"{dead} of {128 * len(TEST_VELOCITIES)} note/velocity probes trigger nothing")
    if stacked:
        result.warn("stacked_note_velocity_cells", f"{stacked} note/velocity probes trigger multiple layers")


def test_gzip_json(path: Path, relative: str) -> ProgramTest:
    scope = "testing" if relative.startswith("Programs/Keygroups/Testing/") else "production"
    result = ProgramTest(path=relative, scope=scope, format="gzip-json")
    try:
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            text = stream.read()
        start = text.find("{")
        if start < 0:
            raise ValueError("no JSON payload")
        if not text.startswith("ACVS\n") or "SerialisableProgramData\njson\n" not in text[:start]:
            result.error("invalid_header", "missing expected ACVS SerialisableProgramData JSON header")
        data = json.loads(text[start:]).get("data", {})
        keygroup = data.get("keygroup")
        drum = data.get("drum")
        if not isinstance(drum, dict) or not isinstance(drum.get("instruments"), list):
            result.error("missing_instruments", "program has no drum.instruments array")
            result.finish()
            return result
        all_instruments = [item for item in drum["instruments"] if isinstance(item, dict)]
        if isinstance(keygroup, dict) and _integer(keygroup.get("numKeygroups"), 0) > 0:
            result.program_type = "Keygroup"
            expected = _integer(keygroup.get("numKeygroups")) + 1
            if len(all_instruments) != expected:
                result.error("keygroup_count", f"expected {expected} instrument records, found {len(all_instruments)}")
            instruments = all_instruments[1:]
            _simulate_keygroup(result, instruments)
        else:
            result.program_type = "Drum"
            instruments = all_instruments
        registry_entries = data.get("samples", [])
        registry = {
            str(entry.get("path")): entry
            for entry in registry_entries
            if isinstance(entry, dict) and entry.get("path")
        }
        if len(registry) != len(registry_entries):
            result.error("sample_registry", "sample registry has blank or duplicate paths")
        result.sample_references = len(registry)
        _validate_json_audio(
            result, instruments, registry, path.with_name(f"{path.stem}_[ProgramData]")
        )
    except Exception as error:
        result.error("unreadable_program", str(error))
    result.finish()
    return result


def _xml_text(node: ET.Element, name: str, default: str = "") -> str:
    return (node.findtext(name) or default).strip()


def test_xml(path: Path, relative: str) -> ProgramTest:
    scope = "testing" if relative.startswith("Programs/Keygroups/Testing/") else "production"
    result = ProgramTest(path=relative, scope=scope, format="xml")
    try:
        root = ET.parse(path).getroot()
        program = root.find("Program")
        if program is None:
            raise ValueError("missing Program element")
        result.program_type = program.get("type", "Unknown")
        indexes = _audio_index(path.parent, recursive=True)
        references: list[str] = []
        playable = 0
        dead = 0
        stacked = 0
        numbers: set[int] = set()
        for instrument in root.iter("Instrument"):
            number = _integer(instrument.get("number"), -1)
            if number in numbers:
                result.error("duplicate_instrument", f"duplicate instrument number {number}")
            numbers.add(number)
            layers = []
            for layer in instrument.iter("Layer"):
                reference = _xml_text(layer, "SampleFile") or _xml_text(layer, "SampleName")
                if not reference:
                    continue
                references.append(reference)
                layers.append(layer)
                matches = _resolve(reference, indexes)
                if not matches:
                    result.error("missing_sample", f"missing sample: {reference}")
                    continue
                if len(matches) > 1:
                    result.error("ambiguous_sample", f"ambiguous sample: {reference}")
                    continue
                frames = _wave_frames(matches[0], result, reference)
                if frames is not None:
                    end = _integer(_xml_text(layer, "SliceEnd", "0"), 0)
                    if end == frames:
                        result.warn(
                            "exclusive_sample_end",
                            f"slice end equals frame count for {reference}; MPC may treat it as exclusive",
                        )
                    elif end < 0 or end > frames:
                        result.error("invalid_sample_end", f"slice end {end} outside {reference} ({frames} frames)")
            if layers:
                playable += 1
                for velocity in TEST_VELOCITIES:
                    triggers = sum(
                        _integer(_xml_text(layer, "VelStart", "0"), 0)
                        <= velocity
                        <= _integer(_xml_text(layer, "VelEnd", "127"), 127)
                        for layer in layers
                    )
                    if triggers == 0:
                        dead += 1
                    elif triggers > 1:
                        stacked += 1
        result.sample_references = len(_unique(references))
        result.playable_notes = playable
        result.dead_trigger_cells = dead
        result.stacked_trigger_cells = stacked
        if not references:
            result.error("no_samples", "program declares no sample layers")
        if dead:
            result.error("dead_pad_velocity_cells", f"{dead} populated-pad velocity probes trigger nothing")
        if stacked:
            result.warn("stacked_pad_velocity_cells", f"{stacked} populated-pad velocity probes trigger multiple layers")
        if len(numbers) > 128:
            result.error("too_many_instruments", f"program has {len(numbers)} instruments")
    except Exception as error:
        result.error("unreadable_program", str(error))
    result.finish()
    return result


def test_program(path: Path, root: Path) -> ProgramTest:
    relative = str(path.relative_to(root))
    try:
        magic = path.read_bytes()[:2]
    except OSError as error:
        result = ProgramTest(path=relative)
        result.error("unreadable_program", str(error))
        result.finish()
        return result
    return test_gzip_json(path, relative) if magic == b"\x1f\x8b" else test_xml(path, relative)


def run_suite(root: Path) -> list[ProgramTest]:
    return [test_program(path, root) for path in sorted(root.rglob("*.xpm"))]


def write_reports(results: list[ProgramTest], root: Path, json_path: Path, csv_path: Path) -> dict[str, Any]:
    verdicts = Counter(item.verdict for item in results)
    production_verdicts = Counter(item.verdict for item in results if item.scope == "production")
    testing_verdicts = Counter(item.verdict for item in results if item.scope == "testing")
    codes = Counter(issue.code for item in results for issue in item.issues)
    summary = {
        "root": str(root),
        "programs": len(results),
        "verdicts": dict(sorted(verdicts.items())),
        "production_verdicts": dict(sorted(production_verdicts.items())),
        "testing_verdicts": dict(sorted(testing_verdicts.items())),
        "issue_codes": dict(sorted(codes.items())),
        "dead_trigger_cells": sum(item.dead_trigger_cells for item in results),
        "stacked_trigger_cells": sum(item.stacked_trigger_cells for item in results),
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(
            {
                "summary": summary,
                "programs": [
                    {**asdict(item), "issues": [asdict(issue) for issue in item.issues]}
                    for item in results
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        fields = (
            "verdict", "scope", "program_type", "format", "sample_references", "playable_notes",
            "dead_trigger_cells", "stacked_trigger_cells", "errors", "warnings", "path",
        )
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for item in results:
            writer.writerow(
                {
                    "verdict": item.verdict,
                    "scope": item.scope,
                    "program_type": item.program_type,
                    "format": item.format,
                    "sample_references": item.sample_references,
                    "playable_notes": item.playable_notes,
                    "dead_trigger_cells": item.dead_trigger_cells,
                    "stacked_trigger_cells": item.stacked_trigger_cells,
                    "errors": " | ".join(
                        f"{issue.code}: {issue.message}" for issue in item.issues if issue.severity == "error"
                    ),
                    "warnings": " | ".join(
                        f"{issue.code}: {issue.message}" for issue in item.issues if issue.severity == "warning"
                    ),
                    "path": item.path,
                }
            )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--csv", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    results = run_suite(root)
    print(json.dumps(write_reports(results, root, args.json, args.csv), indent=2))
    return 1 if any(item.verdict == "fail" and item.scope == "production" for item in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
