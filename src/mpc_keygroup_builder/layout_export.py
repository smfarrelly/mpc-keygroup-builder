"""Export Drum Program layouts without reconstructing instrument records."""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import html
import json
import os
import shutil
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .device import DeviceProfile, load_device
from .layout import LayoutPlan, LayoutPreset, arrange, load_preset, render_markdown
from .model import ProgramModel, from_xpm
from .testing import AUDIO_SUFFIXES, test_program


@dataclass(frozen=True)
class ExportReport:
    source: str
    output: str
    source_format: str
    source_name: str
    output_name: str
    preset: str
    assignments: int
    moved_assignments: int
    instrument_records: int
    preserved_sample_layers: int
    preserved_colors: int
    color_overrides: int
    record_bijection: bool
    colors_follow_records: bool
    global_settings_unchanged: bool


@dataclass(frozen=True)
class _Shape:
    container: str
    name: str
    records: dict[int, Any]
    colors: dict[int, Any]
    global_value: Any
    sample_layers: int


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _element_value(element: ET.Element, *, omit_number: bool = False) -> dict[str, Any]:
    attributes = dict(sorted(element.attrib.items()))
    if omit_number:
        attributes.pop("number", None)
    return {
        "tag": element.tag,
        "attributes": attributes,
        "text": (element.text or "").strip(),
        "children": [_element_value(child) for child in element],
    }


def _xml_settings(program: ET.Element, source: Path) -> tuple[ET.Element, dict[str, Any]]:
    node = program.find("ProgramPads")
    if node is None or not node.text:
        raise ValueError(f"Drum Program has no ProgramPads settings: {source}")
    settings = json.loads(html.unescape(node.text))
    value = settings.get("ProgramPads")
    if not isinstance(value, dict) or not isinstance(value.get("pads"), dict):
        raise ValueError(f"Drum Program has no pad-color map: {source}")
    return node, settings


def _color_slots(pads: dict[str, Any], count: int) -> dict[int, Any]:
    return {index: pads.get(f"value{index - 1}") for index in range(1, count + 1)}


def _xml_shape(path: Path) -> _Shape:
    root = ET.parse(path).getroot()
    program = root.find("Program")
    if program is None or program.get("type", "").casefold() != "drum":
        raise ValueError(f"not an XML Drum Program: {path}")
    instruments_node = program.find("Instruments")
    if instruments_node is None:
        raise ValueError(f"Drum Program has no Instruments: {path}")
    records = {
        int(instrument.get("number", "-1")): _element_value(instrument, omit_number=True)
        for instrument in instruments_node.findall("Instrument")
    }
    _, settings = _xml_settings(program, path)
    pad_settings = copy.deepcopy(settings["ProgramPads"])
    pads = pad_settings.pop("pads")
    dynamic = {"ProgramName", "ProgramPads", "Instruments"}
    global_value = {
        "root": {
            "tag": root.tag,
            "attributes": dict(sorted(root.attrib.items())),
            "children": [
                _element_value(child) for child in root if child is not program
            ],
        },
        "program_attributes": dict(sorted(program.attrib.items())),
        "program_children": [
            _element_value(child) for child in program if child.tag not in dynamic
        ],
        "instruments_attributes": dict(sorted(instruments_node.attrib.items())),
        "pad_settings": pad_settings,
    }
    sample_layers = sum(
        1
        for instrument in instruments_node.findall("Instrument")
        for layer in instrument.iter("Layer")
        if (layer.findtext("SampleFile") or layer.findtext("SampleName") or "").strip()
    )
    return _Shape(
        "xml",
        program.findtext("ProgramName", ""),
        records,
        _color_slots(pads, len(records)),
        global_value,
        sample_layers,
    )


def _read_compressed(path: Path) -> tuple[bytes, dict[str, Any]]:
    raw = gzip.decompress(path.read_bytes())
    start = raw.find(b"{")
    if not raw.startswith(b"ACVS\n") or start < 0:
        raise ValueError(f"unsupported compressed MPC program: {path}")
    return raw[:start], json.loads(raw[start:])


def _compressed_shape(path: Path) -> _Shape:
    prefix, document = _read_compressed(path)
    data = document.get("data", {})
    if data.get("type") != 0:
        raise ValueError(f"not a compressed Drum Program: {path}")
    drum = data.get("drum")
    instruments = drum.get("instruments") if isinstance(drum, dict) else None
    if not isinstance(instruments, list) or not all(isinstance(item, dict) for item in instruments):
        raise ValueError(f"compressed Drum Program has invalid instruments: {path}")
    settings = data.get("programPads")
    if not isinstance(settings, dict):
        raise ValueError(f"compressed Drum Program has no ProgramPads settings: {path}")
    pads = settings.get("pads")
    if not isinstance(pads, dict):
        raise ValueError(f"compressed Drum Program has no pad-color map: {path}")
    normalized = copy.deepcopy(document)
    normalized_data = normalized["data"]
    normalized_data["name"] = "<layout-export-name>"
    normalized_data["drum"]["instruments"] = []
    normalized_data["programPads"]["pads"] = {}
    sample_layers = sum(
        1
        for instrument in instruments
        for layer in instrument.get("layersv", [])
        if isinstance(layer, dict) and (layer.get("sampleFile") or layer.get("sampleName"))
    )
    return _Shape(
        "gzip-json",
        str(data.get("name", "")),
        {index: copy.deepcopy(item) for index, item in enumerate(instruments, 1)},
        _color_slots(pads, len(instruments)),
        {"prefix": prefix.decode("utf-8"), "document": normalized},
        sample_layers,
    )


def _shape(path: Path) -> _Shape:
    return _compressed_shape(path) if path.read_bytes()[:2] == b"\x1f\x8b" else _xml_shape(path)


def _permutation(plan: LayoutPlan, count: int) -> dict[int, int]:
    assigned = {item.slot: item.source_index for item in plan.assignments}
    if len(assigned) != len(plan.assignments):
        raise ValueError("layout contains duplicate destination slots")
    if len(set(assigned.values())) != len(assigned):
        raise ValueError("layout contains duplicate source zones")
    if any(not 1 <= value <= count for value in assigned):
        raise ValueError(f"layout slots and source zones must be within 1..{count}")
    remaining_destinations = [value for value in range(1, count + 1) if value not in assigned]
    remaining_sources = [value for value in range(1, count + 1) if value not in assigned.values()]
    assigned.update(zip(remaining_destinations, remaining_sources))
    if set(assigned) != set(assigned.values()) or set(assigned) != set(range(1, count + 1)):
        raise ValueError("layout did not produce a complete instrument-record permutation")
    return assigned


def _atomic_write(path: Path, payload: bytes, *, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"output exists; pass --force to replace it: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _export_xml(
    source: Path,
    output: Path,
    permutation: dict[int, int],
    name: str,
    *,
    color_overrides: dict[int, int | None],
    force: bool,
) -> None:
    tree = ET.parse(source)
    root = tree.getroot()
    program = root.find("Program")
    if program is None:
        raise ValueError(f"missing Program element: {source}")
    name_node = program.find("ProgramName")
    instruments_node = program.find("Instruments")
    if name_node is None or instruments_node is None:
        raise ValueError(f"Drum Program lacks name or instruments: {source}")
    records = {
        int(instrument.get("number", "-1")): copy.deepcopy(instrument)
        for instrument in instruments_node.findall("Instrument")
    }
    node, settings = _xml_settings(program, source)
    pads = settings["ProgramPads"]["pads"]
    source_colors = _color_slots(pads, len(records))
    for instrument in list(instruments_node):
        instruments_node.remove(instrument)
    for destination in range(1, len(records) + 1):
        instrument = records[permutation[destination]]
        instrument.set("number", str(destination))
        instruments_node.append(instrument)
        color = color_overrides.get(destination, source_colors[permutation[destination]])
        key = f"value{destination - 1}"
        if color is None:
            pads.pop(key, None)
        else:
            pads[key] = color
    name_node.text = name
    node.text = json.dumps(settings, indent=4)
    ET.indent(tree, space="  ")
    from io import BytesIO

    stream = BytesIO()
    tree.write(stream, encoding="UTF-8", xml_declaration=True)
    _atomic_write(output, stream.getvalue(), force=force)


def _export_compressed(
    source: Path,
    output: Path,
    permutation: dict[int, int],
    name: str,
    *,
    color_overrides: dict[int, int | None],
    force: bool,
) -> None:
    prefix, document = _read_compressed(source)
    data = document["data"]
    instruments = data["drum"]["instruments"]
    source_records = copy.deepcopy(instruments)
    pads = data["programPads"]["pads"]
    source_colors = _color_slots(pads, len(instruments))
    data["drum"]["instruments"] = [
        source_records[permutation[destination] - 1]
        for destination in range(1, len(instruments) + 1)
    ]
    for destination in range(1, len(instruments) + 1):
        color = color_overrides.get(destination, source_colors[permutation[destination]])
        key = f"value{destination - 1}"
        if color is None:
            pads.pop(key, None)
        else:
            pads[key] = color
    data["name"] = name
    payload = prefix + json.dumps(document, indent=4).encode("utf-8")
    _atomic_write(output, gzip.compress(payload, mtime=0), force=force)


def export_layout(
    source: Path,
    output: Path,
    plan: LayoutPlan,
    *,
    name: str,
    color_overrides: dict[int, int | None] | None = None,
    force: bool = False,
) -> ExportReport:
    if source.resolve() == output.resolve():
        raise ValueError("refusing in-place XPM modification")
    before = _shape(source)
    if len(before.records) != 128 or set(before.records) != set(range(1, 129)):
        raise ValueError("layout export requires exactly 128 Drum instrument records")
    permutation = _permutation(plan, len(before.records))
    overrides = dict(color_overrides or {})
    if any(not 1 <= slot <= len(before.records) for slot in overrides):
        raise ValueError("color override slots must be within 1..128")
    if any(color is not None and not 0 <= color <= 0xFFFFFF for color in overrides.values()):
        raise ValueError("color overrides must be RGB integers or null")
    if before.container == "xml":
        _export_xml(
            source,
            output,
            permutation,
            name,
            color_overrides=overrides,
            force=force,
        )
    else:
        _export_compressed(
            source,
            output,
            permutation,
            name,
            color_overrides=overrides,
            force=force,
        )
    return verify_layout_export(
        source,
        output,
        plan,
        expected_name=name,
        color_overrides=overrides,
    )


def verify_layout_export(
    source: Path,
    output: Path,
    plan: LayoutPlan,
    *,
    expected_name: str | None = None,
    color_overrides: dict[int, int | None] | None = None,
) -> ExportReport:
    """Independently verify that only name, placement, and declared colors changed."""
    before = _shape(source)
    if len(before.records) != 128 or set(before.records) != set(range(1, 129)):
        raise ValueError("layout verification requires exactly 128 Drum instrument records")
    permutation = _permutation(plan, len(before.records))
    overrides = dict(color_overrides or {})
    after = _shape(output)
    if after.container != before.container:
        raise ValueError("export changed the XPM container format")
    if expected_name is not None and after.name != expected_name:
        raise ValueError("exported program name mismatch")
    record_bijection = all(
        after.records[destination] == before.records[source_index]
        for destination, source_index in permutation.items()
    )
    colors_follow = all(
        after.colors[destination] == overrides.get(destination, before.colors[source_index])
        for destination, source_index in permutation.items()
    )
    globals_unchanged = after.global_value == before.global_value
    if not record_bijection:
        raise ValueError("instrument records changed during layout export")
    if not colors_follow:
        raise ValueError("pad colors did not match the declared layout colors")
    if not globals_unchanged:
        raise ValueError("non-layout program settings changed during export")
    if after.sample_layers != before.sample_layers:
        raise ValueError("sample-layer count changed during export")
    moved = sum(item.slot != item.source_index for item in plan.assignments)
    return ExportReport(
        str(source.resolve()),
        str(output.resolve()),
        before.container,
        before.name,
        after.name,
        plan.preset,
        len(plan.assignments),
        moved,
        len(before.records),
        before.sample_layers,
        sum(value is not None for value in before.colors.values()),
        len(overrides),
        record_bijection,
        colors_follow,
        globals_unchanged,
    )


def _sample_sources(source: Path, model: ProgramModel) -> dict[str, Path]:
    references = sorted(
        {
            layer.sample
            for zone in model.zones
            for layer in zone.layers
            if layer.sample
        },
        key=str.casefold,
    )
    compressed = source.read_bytes()[:2] == b"\x1f\x8b"
    root = source.with_name(f"{source.stem}_[ProgramData]") if compressed else source.parent
    paths = root.glob("*") if compressed else root.rglob("*")
    by_name: dict[str, list[Path]] = {}
    by_stem: dict[str, list[Path]] = {}
    for path in paths:
        if path.is_file() and path.suffix.casefold() in AUDIO_SUFFIXES:
            by_name.setdefault(path.name.casefold(), []).append(path)
            by_stem.setdefault(path.stem.casefold(), []).append(path)
    resolved: dict[str, Path] = {}
    for reference in references:
        name = Path(reference).name
        matches = by_name.get(name.casefold(), []) or by_stem.get(Path(name).stem.casefold(), [])
        if len(matches) != 1:
            raise ValueError(f"sample reference resolved to {len(matches)} files: {reference}")
        if name.casefold() in {value.casefold() for value in resolved}:
            raise ValueError(f"duplicate destination sample basename: {name}")
        resolved[name] = matches[0]
    return resolved


def _program_name(prefix: str, preset: LayoutPreset) -> str:
    value = f"{prefix} {preset.program_suffix or preset.id}".strip()
    if not value or Path(value).name != value:
        raise ValueError("generated program name must be a path-safe basename")
    return value


def build_hardware_package(
    source: Path,
    preset_paths: list[Path],
    device: DeviceProfile,
    output: Path,
    *,
    name_prefix: str | None = None,
) -> Path:
    if output.exists():
        raise FileExistsError(f"package output already exists: {output}")
    model = from_xpm(source)
    if model.kind != "drum":
        raise ValueError("layout hardware package requires a Drum Program")
    audio = _sample_sources(source, model)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{output.name}.", dir=output.parent) as temporary:
        staging = Path(temporary) / output.name
        staging.mkdir()
        variants = []
        maps = []
        for order, preset_path in enumerate(preset_paths, 1):
            preset = load_preset(preset_path)
            plan = arrange(model, preset, device)
            program_name = _program_name(name_prefix or model.name, preset)
            variant = staging / f"{order:02d}-{preset.id}"
            variant.mkdir()
            xpm_path = variant / f"{program_name}.xpm"
            report = export_layout(source, xpm_path, plan, name=program_name)
            audio_root = (
                xpm_path.with_name(f"{xpm_path.stem}_[ProgramData]")
                if report.source_format == "gzip-json"
                else variant
            )
            audio_root.mkdir(exist_ok=True)
            copied = []
            for filename, source_audio in audio.items():
                destination = audio_root / filename
                shutil.copy2(source_audio, destination)
                source_hash = _sha256(source_audio)
                destination_hash = _sha256(destination)
                if destination_hash != source_hash:
                    raise OSError(f"audio copy verification failed: {source_audio}")
                copied.append(
                    {
                        "path": str(destination.relative_to(staging)),
                        "bytes": destination.stat().st_size,
                        "sha256": destination_hash,
                    }
                )
            result = test_program(xpm_path, variant)
            if result.verdict != "pass":
                raise ValueError(f"generated variant did not pass simulation: {preset.id}")
            map_path = staging / f"{order:02d}-{preset.id}-pad-map.md"
            map_path.write_text(render_markdown(plan, device), encoding="utf-8")
            maps.append(str(map_path.relative_to(staging)))
            variants.append(
                {
                    "preset": preset.id,
                    "program": str(xpm_path.relative_to(staging)),
                    "program_sha256": _sha256(xpm_path),
                    "pad_map": str(map_path.relative_to(staging)),
                    "export": asdict(report),
                    "simulation": asdict(result),
                    "audio": copied,
                }
            )
        manifest = {
            "format": 1,
            "source_name": model.name,
            "source_file": source.name,
            "source_sha256": _sha256(source),
            "device": device.id,
            "sample_count": len(audio),
            "variants": variants,
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        lines = [
            f"# {model.name} layout hardware trial",
            "",
            f"Device: {device.name}",
            f"Variants: {len(variants)}",
            f"Samples copied per variant: {len(audio)}",
            "",
            "Each numbered folder is self-contained. Load its XPM as a new Drum Program; do not overwrite the source program.",
            "",
            "For every variant:",
            "",
            "1. Leave the Browser so fixed pad colors appear.",
            "2. Trigger all populated pads and compare the accompanying pad map.",
            "3. Record a short pattern, save/reload, and confirm sound, color, choke, and playback behavior persist.",
            "4. Rank muscle memory, one-handed reach, bank navigation, and mistakes.",
            "",
            "The manifest records XPM/audio checksums and local simulation results. Hardware acceptance remains manual.",
            "",
            "Pad maps:",
            "",
            *[f"- `{value}`" for value in maps],
            "",
        ]
        (staging / "README.md").write_text("\n".join(lines), encoding="utf-8")
        os.replace(staging, output)
    return output


def _inputs(args: argparse.Namespace) -> tuple[Path, DeviceProfile, list[tuple[LayoutPreset, LayoutPlan]]]:
    source = args.source.expanduser().resolve()
    device = load_device(args.device.expanduser().resolve())
    model = from_xpm(source)
    values = []
    for path in args.preset:
        preset = load_preset(path.expanduser().resolve())
        values.append((preset, arrange(model, preset, device)))
    return source, device, values


def export_main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--preset", type=Path, action="append", required=True)
    parser.add_argument("--device", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--name")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if len(args.preset) != 1:
        parser.error("mpc-layout-export requires exactly one --preset")
    source, _, values = _inputs(args)
    preset, plan = values[0]
    name = args.name or _program_name(from_xpm(source).name, preset)
    report = export_layout(
        source,
        args.output.expanduser().resolve(),
        plan,
        name=name,
        force=args.force,
    )
    print(json.dumps(asdict(report), indent=2))
    return 0


def verify_main() -> int:
    parser = argparse.ArgumentParser(description="Verify a layout-exported Drum Program")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--preset", type=Path, action="append", required=True)
    parser.add_argument("--device", type=Path, required=True)
    parser.add_argument("--name")
    args = parser.parse_args()
    if len(args.preset) != 1:
        parser.error("mpc-layout-verify requires exactly one --preset")
    source, _, values = _inputs(args)
    _, plan = values[0]
    report = verify_layout_export(
        source,
        args.output.expanduser().resolve(),
        plan,
        expected_name=args.name,
    )
    print(json.dumps(asdict(report), indent=2))
    return 0


def package_main() -> int:
    parser = argparse.ArgumentParser(description="Build a self-contained layout hardware-test package")
    parser.add_argument("source", type=Path)
    parser.add_argument("--preset", type=Path, action="append", required=True)
    parser.add_argument("--device", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--name-prefix")
    args = parser.parse_args()
    destination = build_hardware_package(
        args.source.expanduser().resolve(),
        [path.expanduser().resolve() for path in args.preset],
        load_device(args.device.expanduser().resolve()),
        args.output.expanduser().resolve(),
        name_prefix=args.name_prefix,
    )
    print(f"Wrote: {destination}")
    return 0
