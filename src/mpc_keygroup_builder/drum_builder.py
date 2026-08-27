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
class LayerSpec:
    sample: str
    velocity_start: int = 0
    velocity_end: int = 127


@dataclass(frozen=True)
class PadSpec:
    pad: int
    sample: str | None = None
    mute_group: int = 0
    layers: tuple[LayerSpec, ...] = ()

    def resolved_layers(self) -> tuple[LayerSpec, ...]:
        if self.layers:
            return self.layers
        if self.sample is None:
            return ()
        return (LayerSpec(self.sample),)


@dataclass(frozen=True)
class DrumManifest:
    name: str
    pads: tuple[PadSpec, ...]


def _load_manifest(path: Path, loading: set[Path]) -> DrumManifest:
    path = path.resolve()
    if path in loading:
        raise ValueError(f"manifest inheritance cycle: {path}")
    loading.add(path)
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    base: DrumManifest | None = None
    inherited = data.get("extends")
    if inherited is not None:
        if not isinstance(inherited, str) or not inherited.strip():
            raise ValueError("manifest extends must be a non-empty path string")
        inherited_path = Path(inherited)
        if not inherited_path.is_absolute():
            inherited_path = path.parent / inherited_path
        base = _load_manifest(inherited_path, loading)
    name = data.get("name", base.name if base else None)
    if not isinstance(name, str) or not name.strip():
        raise ValueError("manifest name must be a non-empty string")
    raw_pads = data.get("pads", [])
    if not isinstance(raw_pads, list):
        raise ValueError("manifest pads must be [[pads]] tables")
    pads: list[PadSpec] = list(base.pads if base else ())
    seen = {spec.pad for spec in pads}
    for index, raw in enumerate(raw_pads, 1):
        if not isinstance(raw, dict):
            raise ValueError(f"pads entry {index} must be a table")
        pad = raw.get("pad")
        sample = raw.get("sample")
        raw_layers = raw.get("layers")
        mute_group = raw.get("mute_group", 0)
        if not isinstance(pad, int) or not 1 <= pad <= 128:
            raise ValueError(f"pads entry {index} has invalid pad {pad!r}")
        if pad in seen:
            raise ValueError(f"duplicate pad {pad}")
        layers: tuple[LayerSpec, ...] = ()
        if raw_layers is not None:
            if sample is not None:
                raise ValueError(f"pads entry {index} cannot set both sample and layers")
            if not isinstance(raw_layers, list) or not 1 <= len(raw_layers) <= 4:
                raise ValueError(f"pads entry {index} layers must contain one through four tables")
            parsed_layers = []
            for layer_index, layer in enumerate(raw_layers, 1):
                if not isinstance(layer, dict):
                    raise ValueError(f"pads entry {index} layer {layer_index} must be a table")
                layer_sample = layer.get("sample")
                velocity_start = layer.get("velocity_start")
                velocity_end = layer.get("velocity_end")
                if not isinstance(layer_sample, str) or not layer_sample.strip():
                    raise ValueError(f"pads entry {index} layer {layer_index} has no sample")
                if Path(layer_sample).name != layer_sample:
                    raise ValueError(
                        f"sample must be a basename, not a path: {layer_sample!r}"
                    )
                if (
                    not isinstance(velocity_start, int)
                    or not isinstance(velocity_end, int)
                    or not 0 <= velocity_start <= velocity_end <= 127
                ):
                    raise ValueError(
                        f"pads entry {index} layer {layer_index} has invalid velocity range "
                        f"{velocity_start!r}..{velocity_end!r}"
                    )
                parsed_layers.append(LayerSpec(layer_sample, velocity_start, velocity_end))
            parsed_layers.sort(key=lambda item: item.velocity_start)
            expected_start = 0
            for layer_index, layer in enumerate(parsed_layers, 1):
                if layer.velocity_start != expected_start:
                    raise ValueError(
                        f"pads entry {index} layers must cover velocities 0..127 without gaps "
                        "or overlaps"
                    )
                expected_start = layer.velocity_end + 1
            if expected_start != 128:
                raise ValueError(
                    f"pads entry {index} layers must cover velocities 0..127 without gaps or overlaps"
                )
            layers = tuple(parsed_layers)
            sample = None
        else:
            if not isinstance(sample, str) or not sample.strip():
                raise ValueError(f"pads entry {index} has no sample")
            if Path(sample).name != sample:
                raise ValueError(f"sample must be a basename, not a path: {sample!r}")
        if not isinstance(mute_group, int) or not 0 <= mute_group <= 32:
            raise ValueError(f"pads entry {index} has invalid mute_group {mute_group!r}")
        seen.add(pad)
        pads.append(PadSpec(pad=pad, sample=sample, mute_group=mute_group, layers=layers))
    if not pads:
        raise ValueError("manifest must contain at least one [[pads]] table")
    loading.remove(path)
    return DrumManifest(name=name.strip(), pads=tuple(sorted(pads, key=lambda item: item.pad)))


def load_manifest(path: Path) -> DrumManifest:
    return _load_manifest(path, set())


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
    active = layer.find("Active")
    if active is not None:
        active.text = "False"
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


def _set_layer(layer: ET.Element, spec: LayerSpec, frames: int) -> None:
    _clear_layer(layer)
    active = layer.find("Active")
    if active is None:
        active = ET.SubElement(layer, "Active")
    active.text = "True"
    sample_name = layer.find("SampleName")
    if sample_name is None:
        sample_name = ET.SubElement(layer, "SampleName")
    sample_name.text = Path(spec.sample).stem
    sample_file = layer.find("SampleFile")
    if sample_file is None:
        sample_file = ET.SubElement(layer, "SampleFile")
    sample_file.text = spec.sample
    for name, value in (("VelStart", spec.velocity_start), ("VelEnd", spec.velocity_end)):
        node = layer.find(name)
        if node is None:
            node = ET.SubElement(layer, name)
        node.text = str(value)
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
    sources: dict[int, tuple[tuple[LayerSpec, Path, int], ...]] = {}
    specs = {spec.pad: spec for spec in manifest.pads}
    for spec in manifest.pads:
        resolved = []
        layer_specs = spec.resolved_layers()
        if not layer_specs:
            raise ValueError(f"pad {spec.pad} has no sample layers")
        for layer_spec in layer_specs:
            source = source_root / layer_spec.sample
            if not source.is_file():
                raise FileNotFoundError(f"missing sample for pad {spec.pad}: {source}")
            resolved.append((layer_spec, source, _frames(source)))
        sources[spec.pad] = tuple(resolved)

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
        source_layers = sources.get(pad)
        if source_layers is None:
            for layer in layers:
                _clear_layer(layer)
            colors[f"value{pad - 1}"] = 0
            continue
        if len(source_layers) > len(layers):
            raise ValueError(
                f"template instrument {pad} has {len(layers)} layers, "
                f"but the manifest requires {len(source_layers)}"
            )
        for layer, (layer_spec, _, frames) in zip(layers, source_layers, strict=False):
            _set_layer(layer, layer_spec, frames)
        for layer in layers[len(source_layers):]:
            _clear_layer(layer)
        colors[f"value{pad - 1}"] = palette[classify_sample(source_layers[0][0].sample)]
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
            mute_group.text = str(specs[pad].mute_group)

    pad_node.text = json.dumps({"ProgramPads": settings}, indent=4)
    output.mkdir(parents=True, exist_ok=True)
    copied: set[Path] = set()
    for source_layers in sources.values():
        for _, source, _ in source_layers:
            if source not in copied:
                shutil.copy2(source, output / source.name)
                copied.add(source)
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
    copied = {layer.sample.casefold() for spec in manifest.pads for layer in spec.resolved_layers()}
    print(f"Pads: {len(manifest.pads)}; copied WAVs: {len(copied)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
