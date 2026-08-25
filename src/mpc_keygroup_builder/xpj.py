"""Inspect and compare MPC project (XPJ) containers without modifying them."""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


PROGRAM_TYPES = {
    0: "Drum",
    1: "Keygroup",
    2: "Unknown-2",
    3: "Plugin",
    4: "MIDI",
    5: "CV",
    6: "Audio",
    7: "Return",
    8: "Submix",
    9: "Output",
    10: "Input",
}


@dataclass(frozen=True)
class XPJHeader:
    magic: str
    firmware: str
    object_type: str
    encoding: str
    platform: str


@dataclass(frozen=True)
class XPJProject:
    path: Path
    generation: int
    header: XPJHeader | None
    document: dict[str, Any] | None

    @property
    def data(self) -> dict[str, Any]:
        if self.document is None:
            raise ValueError("MPC 2 XML projects do not contain MPC 3 JSON data")
        value = self.document.get("data")
        if not isinstance(value, dict):
            raise ValueError("XPJ JSON does not contain an object at data")
        return value


def detect_generation(raw: bytes) -> int:
    if raw.startswith(b"\x1f\x8b"):
        return 3
    if raw.lstrip().startswith((b"<?xml", b"<MPC")):
        return 2
    raise ValueError("not a recognized MPC XPJ container")


def load(path: Path) -> XPJProject:
    raw = path.read_bytes()
    generation = detect_generation(raw)
    if generation == 2:
        return XPJProject(path, generation, None, None)

    try:
        unpacked = gzip.decompress(raw)
    except (EOFError, OSError) as error:
        raise ValueError(f"invalid gzip container: {error}") from error
    lines = unpacked.split(b"\n", 5)
    if len(lines) != 6:
        raise ValueError("MPC 3 XPJ is missing its five-line ACVS header")
    try:
        header_values = [line.rstrip(b"\r").decode("utf-8") for line in lines[:5]]
    except UnicodeDecodeError as error:
        raise ValueError("XPJ header is not UTF-8 text") from error
    header = XPJHeader(*header_values)
    if header.magic != "ACVS":
        raise ValueError(f"unexpected XPJ header magic: {header.magic!r}")
    if header.encoding.casefold() != "json":
        raise ValueError(f"unsupported XPJ serialization: {header.encoding!r}")
    try:
        document = json.loads(lines[5])
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid XPJ JSON payload: {error}") from error
    if not isinstance(document, dict):
        raise ValueError("XPJ JSON payload must be an object")
    project = XPJProject(path, generation, header, document)
    project.data
    return project


def _sequence_values(data: dict[str, Any]) -> list[dict[str, Any]]:
    output = []
    for entry in data.get("sequences", []):
        if not isinstance(entry, dict):
            continue
        value = entry.get("value", entry)
        if isinstance(value, dict):
            output.append(value)
    return output


def summarize(project: XPJProject) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(project.path),
        "generation": project.generation,
        "format": "MPC 3 gzip/ACVS/JSON" if project.generation == 3 else "MPC 2 XML",
    }
    if project.generation == 2:
        return result
    data = project.data
    tracks = [item for item in data.get("tracks", []) if isinstance(item, dict)]
    type_counts: Counter[str] = Counter()
    track_details = []
    for index, track in enumerate(tracks):
        program = track.get("program") if isinstance(track.get("program"), dict) else {}
        type_id = program.get("type")
        type_name = PROGRAM_TYPES.get(type_id, f"Unknown-{type_id}")
        type_counts[type_name] += 1
        track_details.append(
            {
                "index": index,
                "name": track.get("name", ""),
                "program": program.get("name", ""),
                "type": type_name,
                "type_id": type_id,
                "sample_count": len(track.get("samples", []))
                if isinstance(track.get("samples"), list)
                else 0,
                "output_channel": track.get("outputChannel"),
            }
        )
    sequences = _sequence_values(data)
    result.update(
        {
            "header": asdict(project.header) if project.header else None,
            "format_version": project.document.get("formatVersion"),
            "schema_version": data.get("version"),
            "master_tempo": data.get("masterTempo"),
            "master_tempo_enabled": data.get("masterTempoEnabled"),
            "current_sequence": data.get("currentSequence"),
            "current_track_index": data.get("currentTrackIndex"),
            "track_count": len(tracks),
            "track_types": dict(sorted(type_counts.items())),
            "tracks": track_details,
            "sequence_count": len(sequences),
            "sequences": [
                {
                    "index": index,
                    "name": sequence.get("name", ""),
                    "bpm": sequence.get("bpm"),
                    "length_bars": sequence.get("lengthBars"),
                    "loop": sequence.get("loop"),
                }
                for index, sequence in enumerate(sequences)
            ],
            "project_sample_count": len(data.get("samples", []))
            if isinstance(data.get("samples"), list)
            else 0,
        }
    )
    return result


def normalized(project: XPJProject) -> dict[str, Any]:
    if project.generation != 3 or project.document is None:
        raise ValueError("normalized JSON extraction requires an MPC 3 XPJ")
    return project.document


def _pointer_part(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def differences(left: Any, right: Any, path: str = "") -> Iterable[dict[str, Any]]:
    if type(left) is not type(right):
        yield {"path": path or "/", "kind": "type", "left": type(left).__name__, "right": type(right).__name__}
        return
    if isinstance(left, dict):
        for key in sorted(left.keys() | right.keys()):
            child = f"{path}/{_pointer_part(str(key))}"
            if key not in left:
                yield {"path": child, "kind": "added", "right": right[key]}
            elif key not in right:
                yield {"path": child, "kind": "removed", "left": left[key]}
            else:
                yield from differences(left[key], right[key], child)
        return
    if isinstance(left, list):
        for index in range(max(len(left), len(right))):
            child = f"{path}/{index}"
            if index >= len(left):
                yield {"path": child, "kind": "added", "right": right[index]}
            elif index >= len(right):
                yield {"path": child, "kind": "removed", "left": left[index]}
            else:
                yield from differences(left[index], right[index], child)
        return
    if left != right:
        yield {"path": path or "/", "kind": "changed", "left": left, "right": right}


def compare(left: XPJProject, right: XPJProject) -> dict[str, Any]:
    if left.generation != 3 or right.generation != 3:
        raise ValueError("structural comparison currently requires two MPC 3 XPJ files")
    changes = list(differences(normalized(left), normalized(right)))
    return {
        "left": str(left.path),
        "right": str(right.path),
        "left_header": asdict(left.header) if left.header else None,
        "right_header": asdict(right.header) if right.header else None,
        "change_count": len(changes),
        "changes": changes,
    }


def _write_json(value: Any, output: Path | None) -> None:
    rendered = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if output is None:
        sys.stdout.write(rendered)
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect and compare Akai MPC XPJ projects")
    commands = parser.add_subparsers(dest="command", required=True)
    inspect_parser = commands.add_parser("inspect", help="print a compact project summary")
    inspect_parser.add_argument("project", type=Path)
    inspect_parser.add_argument("--output", type=Path)
    extract_parser = commands.add_parser("extract", help="write normalized MPC 3 JSON")
    extract_parser.add_argument("project", type=Path)
    extract_parser.add_argument("--output", type=Path)
    compare_parser = commands.add_parser("compare", help="show JSON-pointer structural changes")
    compare_parser.add_argument("left", type=Path)
    compare_parser.add_argument("right", type=Path)
    compare_parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            _write_json(summarize(load(args.project)), args.output)
        elif args.command == "extract":
            _write_json(normalized(load(args.project)), args.output)
        else:
            _write_json(compare(load(args.left), load(args.right)), args.output)
    except (OSError, ValueError) as error:
        parser.exit(2, f"error: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
