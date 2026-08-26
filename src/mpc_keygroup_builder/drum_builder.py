"""Build a self-contained legacy MPC Drum Program from a pad manifest."""

from __future__ import annotations

import argparse
import json
import shutil
import tomllib
import wave
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from .programs import classify_sample, load_palette


@dataclass(frozen=True)
class PadSpec:
    pad: int
    sample: str


@dataclass(frozen=True)
class DrumManifest:
    name: str
    pads: tuple[PadSpec, ...]


def load_manifest(path: Path) -> DrumManifest:
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("manifest name must be a non-empty string")
    raw_pads = data.get("pads")
    if not isinstance(raw_pads, list) or not raw_pads:
        raise ValueError("manifest must contain at least one [[pads]] table")
    pads: list[PadSpec] = []
    seen: set[int] = set()
    for index, raw in enumerate(raw_pads, 1):
        if not isinstance(raw, dict):
            raise ValueError(f"pads entry {index} must be a table")
        pad = raw.get("pad")
        sample = raw.get("sample")
        if not isinstance(pad, int) or not 1 <= pad <= 128:
            raise ValueError(f"pads entry {index} has invalid pad {pad!r}")
        if pad in seen:
            raise ValueError(f"duplicate pad {pad}")
        if not isinstance(sample, str) or not sample.strip():
            raise ValueError(f"pads entry {index} has no sample")
        if Path(sample).name != sample:
            raise ValueError(f"sample must be a basename, not a path: {sample!r}")
        seen.add(pad)
        pads.append(PadSpec(pad=pad, sample=sample))
    return DrumManifest(name=name.strip(), pads=tuple(sorted(pads, key=lambda item: item.pad)))


def _frames(path: Path) -> int:
    try:
        with wave.open(str(path), "rb") as stream:
            frames = stream.getnframes()
    except (EOFError, wave.Error) as error:
        raise ValueError(f"unreadable WAV {path}: {error or 'truncated file'}") from error
    if frames < 1:
        raise ValueError(f"empty WAV: {path}")
    return frames


def _clear_layer(layer: ET.Element) -> None:
    for name in ("SampleName", "SampleFile"):
        node = layer.find(name)
        if node is not None:
            node.text = None
    for name, value in (
        ("SampleStart", "0"),
        ("SampleEnd", "0"),
        ("SliceStart", "0"),
        ("SliceEnd", "0"),
        ("SliceLoopStart", "0"),
        ("SliceLoop", "0"),
    ):
        node = layer.find(name)
        if node is not None:
            node.text = value


def _set_layer(layer: ET.Element, sample: str, frames: int) -> None:
    _clear_layer(layer)
    sample_name = layer.find("SampleName")
    if sample_name is None:
        sample_name = ET.SubElement(layer, "SampleName")
    sample_name.text = Path(sample).stem
    sample_file = layer.find("SampleFile")
    if sample_file is None:
        sample_file = ET.SubElement(layer, "SampleFile")
    sample_file.text = sample
    for name, value in (
        ("SampleStart", "0"),
        ("SampleEnd", str(frames - 1)),
        ("SliceStart", "0"),
        ("SliceEnd", str(frames - 1)),
    ):
        node = layer.find(name)
        if node is None:
            node = ET.SubElement(layer, name)
        node.text = value


def build_drum_program(
    manifest: DrumManifest,
    template: Path,
    source_root: Path,
    output: Path,
) -> Path:
    if output.exists():
        if not output.is_dir():
            raise FileExistsError(f"output path is not a directory: {output}")
        if any(output.iterdir()):
            raise FileExistsError(f"output directory is not empty: {output}")
    tree = ET.parse(template)
    root = tree.getroot()
    program = root.find("Program")
    if program is None or program.get("type", "").casefold() != "drum":
        raise ValueError(f"template is not an XML Drum Program: {template}")
    instruments = {
        int(node.get("number", "-1")): node
        for node in program.findall("./Instruments/Instrument")
    }
    if set(instruments) != set(range(1, 129)):
        raise ValueError("template must contain instruments 1 through 128")
    sources: dict[int, tuple[Path, int]] = {}
    for spec in manifest.pads:
        source = source_root / spec.sample
        if not source.is_file():
            raise FileNotFoundError(f"missing sample for pad {spec.pad}: {source}")
        sources[spec.pad] = (source, _frames(source))

    name_node = program.find("ProgramName")
    if name_node is None:
        raise ValueError("template has no ProgramName")
    name_node.text = manifest.name
    palette = load_palette()
    pad_node = program.find("ProgramPads")
    if pad_node is None or not pad_node.text:
        raise ValueError("template has no ProgramPads settings")
    settings = json.loads(pad_node.text)["ProgramPads"]
    settings["Universal"]["value0"] = False
    settings["Type"]["value0"] = 2
    colors = settings["pads"]

    for pad, instrument in instruments.items():
        layers = instrument.findall("./Layers/Layer")
        if not layers:
            raise ValueError(f"template instrument {pad} has no layers")
        source_info = sources.get(pad)
        if source_info is None:
            for layer in layers:
                _clear_layer(layer)
            colors[f"value{pad - 1}"] = 0
            continue
        source, frames = source_info
        _set_layer(layers[0], source.name, frames)
        for layer in layers[1:]:
            _clear_layer(layer)
        colors[f"value{pad - 1}"] = palette[classify_sample(source.name)]
        one_shot = instrument.find("OneShot")
        if one_shot is not None:
            one_shot.text = "True"
        mono = instrument.find("Mono")
        if mono is not None:
            mono.text = "True"
        polyphony = instrument.find("Polyphony")
        if polyphony is not None:
            polyphony.text = "1"
        mute_group = instrument.find("MuteGroup")
        if mute_group is not None:
            mute_group.text = "0"

    pad_node.text = json.dumps({"ProgramPads": settings}, indent=4)
    output.mkdir(parents=True, exist_ok=True)
    for source, _ in sources.values():
        shutil.copy2(source, output / source.name)
    destination = output / f"{manifest.name}.xpm"
    ET.indent(tree, space="  ")
    tree.write(destination, encoding="UTF-8", xml_declaration=True)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = load_manifest(args.manifest.expanduser().resolve())
    destination = build_drum_program(
        manifest,
        args.template.expanduser().resolve(),
        args.source_root.expanduser().resolve(),
        args.output.expanduser().resolve(),
    )
    print(f"Wrote: {destination}")
    print(f"Pads: {len(manifest.pads)}; copied WAVs: {len(manifest.pads)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
