"""Program-type detection and semantic pad colors for MPC programs."""

from __future__ import annotations

import argparse
import gzip
import html
import json
import re
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path


DEFAULT_COLORS = {
    "kick": "#ff0000",
    "snare": "#0022ff",
    "clap": "#ff00ff",
    "rim": "#ffffff",
    "closed_hat": "#e6ff00",
    "open_hat": "#00f7ff",
    "cymbal": "#ff8800",
    "tom": "#11ff00",
    "percussion": "#00a080",
    "fx": "#8000ff",
    "unknown": "#808080",
}

PRIMARY_PATTERNS = (
    ("kick", r"^(?:bd|kick|bass[ _-]?drum)(?:[ _-]|$)"),
    ("snare", r"^(?:sd|snare)(?:[ _-]|$)"),
    ("closed_hat", r"^(?:ch|closed[ _-]?(?:hat|hh)|hh[ _-]?closed)(?:[ _-]|$)"),
    ("open_hat", r"^(?:oh|open[ _-]?(?:hat|hh)|hh[ _-]?open)(?:[ _-]|$)"),
    ("clap", r"^(?:clap|snap)(?:[ _-]|$)"),
    ("rim", r"^(?:rim|sidestick)(?:[ _-]|$)"),
    ("cymbal", r"^(?:cymbal|crash|ride)(?:[ _-]|$)"),
    ("tom", r"^tom(?:[ _-]|$)"),
    (
        "percussion",
        r"^(?:perc|percussion|conga|bongo|cowbell|clave|shaker|tamb|maraca|woodblock|cabasa|triangle)(?:[ _-]|$)",
    ),
    ("fx", r"^(?:fx|vocal|texture|noise|static|crackle)(?:[ _-]|$)"),
)

CATEGORY_PATTERNS = (
    ("kick", r"(?:^|[ _-])(?:bd|kick|bass[ _-]?drum)(?:[ _-]|$)"),
    ("snare", r"(?:^|[ _-])(?:sd|snare)(?:[ _-]|$)"),
    ("closed_hat", r"(?:^|[ _-])(?:ch|closed[ _-]?(?:hat|hh)|hh[ _-]?closed)(?:[ _-]|$)"),
    ("open_hat", r"(?:^|[ _-])(?:oh|open[ _-]?(?:hat|hh)|hh[ _-]?open)(?:[ _-]|$)"),
    ("clap", r"(?:^|[ _-])(?:clap|snap)(?:[ _-]|$)"),
    ("rim", r"(?:^|[ _-])(?:rim|sidestick)(?:[ _-]|$)"),
    ("cymbal", r"(?:^|[ _-])(?:cymbal|crash|ride)(?:[ _-]|$)"),
    ("tom", r"(?:^|[ _-])tom(?:[ _-]|$)"),
    (
        "percussion",
        r"(?:^|[ _-])(?:perc|percussion|conga|bongo|cowbell|clave|shaker|tamb|maraca|woodblock|cabasa|triangle)(?:[ _-]|$)",
    ),
    ("fx", r"(?:^|[ _-])(?:fx|vocal|texture|noise|static|crackle)(?:[ _-]|$)"),
)


def classify_sample(name: str, overrides: dict[str, str] | None = None) -> str:
    if overrides:
        exact = overrides.get(Path(name).name.casefold())
        stem = overrides.get(Path(name).stem.casefold())
        if exact or stem:
            return exact or stem  # type: ignore[return-value]
    value = Path(name).stem.casefold()
    for category, pattern in PRIMARY_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE):
            return category
    for category, pattern in CATEGORY_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE):
            return category
    return "unknown"


def rgb888(value: str) -> int:
    match = re.fullmatch(r"#?([0-9a-fA-F]{6})", value)
    if match is None:
        raise ValueError(f"color must be six-digit RGB hex: {value!r}")
    # MPC program pad colors are stored as 24-bit 0xRRGGBB integers. This was
    # confirmed by resaving a hand-colored program on MPC 3.9.1.2.
    return int(match.group(1), 16)


def load_palette(path: Path | None = None) -> dict[str, int]:
    colors = dict(DEFAULT_COLORS)
    if path is not None:
        with path.open("rb") as stream:
            configured = tomllib.load(stream)
        section = configured.get("colors", configured)
        if not isinstance(section, dict):
            raise ValueError("palette must contain a [colors] table")
        unknown = set(section) - set(colors)
        if unknown:
            raise ValueError(f"unknown color categories: {', '.join(sorted(unknown))}")
        colors.update(section)
    return {category: rgb888(value) for category, value in colors.items()}


def load_overrides(path: Path | None = None) -> dict[str, str]:
    if path is None:
        return {}
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    section = data.get("overrides", {})
    if not isinstance(section, dict):
        raise ValueError("palette [overrides] must be a table")
    result: dict[str, str] = {}
    for filename, category in section.items():
        if not isinstance(category, str) or category not in DEFAULT_COLORS:
            raise ValueError(f"invalid override category for {filename!r}: {category!r}")
        result[filename.casefold()] = category
    return result


def _read_acvs(path: Path) -> tuple[bytes, dict]:
    raw = gzip.decompress(path.read_bytes())
    json_start = raw.find(b"{")
    if not raw.startswith(b"ACVS\n") or json_start < 0:
        raise ValueError(f"unsupported compressed MPC program: {path}")
    return raw[:json_start], json.loads(raw[json_start:])


def detect_program_type(path: Path) -> str:
    with path.open("rb") as stream:
        magic = stream.read(2)
    if magic == b"\x1f\x8b":
        _, document = _read_acvs(path)
        value = document.get("data", {}).get("type")
        if value == 0:
            return "drum"
        if value == 1:
            return "keygroup"
        raise ValueError(f"unsupported compressed program type {value!r}: {path}")
    root = ET.parse(path).getroot()
    program = root.find("Program")
    if program is None:
        raise ValueError(f"missing Program element: {path}")
    value = program.get("type", "").casefold()
    if value not in {"drum", "keygroup"}:
        raise ValueError(f"unsupported program type {value!r}: {path}")
    return value


def resolve_program_type(path: Path, requested: str) -> str:
    detected = detect_program_type(path)
    if requested == "auto":
        return detected
    if requested != detected:
        raise ValueError(f"requested {requested}, but {path.name} is {detected}")
    return requested


def _sample_for_instrument(instrument: ET.Element) -> str:
    for layer in instrument.iter("Layer"):
        value = (layer.findtext("SampleFile") or layer.findtext("SampleName") or "").strip()
        if value:
            return value
    return ""


def _sample_for_serialized_instrument(instrument: dict) -> str:
    for layer in instrument.get("layersv", []):
        value = (layer.get("sampleFile") or layer.get("sampleName") or "").strip()
        if value:
            return value
    return ""


def _set_pad_color_mode(program_pads: dict, source: Path) -> dict:
    universal = program_pads.get("Universal")
    if not isinstance(universal, dict) or "value0" not in universal:
        raise ValueError(f"Drum Program has no universal-color setting: {source}")
    universal["value0"] = False
    display_type = program_pads.get("Type")
    if not isinstance(display_type, dict) or "value0" not in display_type:
        raise ValueError(f"Drum Program has no pad-color display setting: {source}")
    # MPC Pad Color display modes: 1 is velocity colors; 2 is assigned/fixed colors.
    display_type["value0"] = 2
    return program_pads["pads"]


def colorize_drum_program(
    source: Path,
    destination: Path,
    palette: dict[str, int],
    *,
    name: str | None = None,
    overrides: dict[str, str] | None = None,
) -> dict[str, int]:
    with source.open("rb") as stream:
        compressed = stream.read(2) == b"\x1f\x8b"
    if compressed:
        prefix, document = _read_acvs(source)
        program = document.get("data", {})
        if program.get("type") != 0 or not isinstance(program.get("drum"), dict):
            raise ValueError(f"not a compressed Drum Program: {source}")
        if name is not None:
            program["name"] = name
        pads = _set_pad_color_mode(program["programPads"], source)
        counts = {category: 0 for category in palette}
        for index, instrument in enumerate(program["drum"].get("instruments", [])):
            sample = _sample_for_serialized_instrument(instrument)
            if not sample or index >= 128:
                continue
            category = classify_sample(sample, overrides)
            pads[f"value{index}"] = palette[category]
            counts[category] += 1
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = prefix + json.dumps(document, indent=4).encode("utf-8")
        destination.write_bytes(gzip.compress(payload, mtime=0))
        return {key: value for key, value in counts.items() if value}

    tree = ET.parse(source)
    root = tree.getroot()
    program = root.find("Program")
    if program is None or program.get("type", "").casefold() != "drum":
        raise ValueError(f"not an XML Drum Program: {source}")
    if name is not None:
        name_node = program.find("ProgramName")
        if name_node is None:
            raise ValueError(f"Drum Program has no ProgramName: {source}")
        name_node.text = name
    node = program.find("ProgramPads")
    if node is None or not node.text:
        raise ValueError(f"Drum Program has no ProgramPads color map: {source}")
    settings = json.loads(html.unescape(node.text))
    program_pads = settings["ProgramPads"]
    pads = _set_pad_color_mode(program_pads, source)
    counts = {category: 0 for category in palette}
    for instrument in program.findall("./Instruments/Instrument"):
        pad_number = int(instrument.get("number", "-1"))
        sample = _sample_for_instrument(instrument)
        if not sample or not 1 <= pad_number <= 128:
            continue
        category = classify_sample(sample, overrides)
        pads[f"value{pad_number - 1}"] = palette[category]
        counts[category] += 1
    node.text = json.dumps(settings, indent=4)
    ET.indent(tree, space="  ")
    destination.parent.mkdir(parents=True, exist_ok=True)
    tree.write(destination, encoding="UTF-8", xml_declaration=True)
    return {key: value for key, value in counts.items() if value}


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect and color an MPC Drum Program")
    parser.add_argument("program", type=Path)
    parser.add_argument("--program-type", choices=("auto", "drum", "keygroup"), default="auto")
    parser.add_argument("--palette", type=Path, help="TOML file containing a [colors] table")
    parser.add_argument("--name", help="program name stored inside the output XPM")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    program_type = resolve_program_type(args.program, args.program_type)
    print(f"Program type: {program_type}")
    if program_type != "drum":
        print("No pad colors changed; semantic pad colors apply to Drum Programs.")
        return 0
    destination = args.output or args.program
    if not args.dry_run and destination == args.program:
        parser.error("refusing in-place modification; pass --output")
    palette = load_palette(args.palette)
    overrides = load_overrides(args.palette)
    if args.dry_run:
        destination = Path("/dev/null")
    counts = colorize_drum_program(
        args.program, destination, palette, name=args.name, overrides=overrides
    )
    print("Classifications: " + ", ".join(f"{key}={value}" for key, value in counts.items()))
    if args.dry_run:
        print("Dry run only; no program written.")
    else:
        print(f"Wrote: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
