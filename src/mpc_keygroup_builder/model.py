"""Normalized, format-independent MPC Program Model v1."""

from __future__ import annotations

import argparse
import gzip
import html
import json
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from .drum_builder import load_manifest
from .programs import classify_sample, load_palette
from .roles import infer_role, load_role_overrides


ProgramKind = Literal["drum", "keygroup", "clip"]


@dataclass(frozen=True)
class SampleLayer:
    sample: str
    velocity_start: int = 0
    velocity_end: int = 127
    root_note: int | None = None
    sample_start: int = 0
    sample_end: int | None = None
    loop_enabled: bool = False
    loop_start: int | None = None
    loop_end: int | None = None


@dataclass(frozen=True)
class Zone:
    index: int
    role: str
    layers: tuple[SampleLayer, ...]
    pad: int | None = None
    low_note: int | None = None
    high_note: int | None = None
    color: int | None = None
    playback_mode: str = "note-on"
    mute_group: int = 0
    polyphony: int = 1
    monophonic: bool = False
    locked: bool = False


@dataclass(frozen=True)
class ProgramModel:
    schema_version: int
    name: str
    kind: ProgramKind
    zones: tuple[Zone, ...]
    source_format: str
    source_path: str = ""
    provenance: dict[str, str] = field(default_factory=dict)

    def validate(self) -> dict[str, list[str]]:
        errors: list[str] = []
        warnings: list[str] = []
        if self.schema_version != 1:
            errors.append("Program Model requires schema_version=1")
        if not self.name:
            errors.append("program name is empty")
        indexes = [zone.index for zone in self.zones]
        if len(indexes) != len(set(indexes)):
            errors.append("zone indexes must be unique")
        pads = [zone.pad for zone in self.zones if zone.pad is not None]
        if self.kind == "drum":
            if len(pads) != len(self.zones):
                errors.append("every Drum Program zone requires a pad")
            if any(not 1 <= int(pad) <= 128 for pad in pads):
                errors.append("drum pads must be 1..128")
            if len(pads) != len(set(pads)):
                errors.append("drum pads must be unique")
        for zone in self.zones:
            if not zone.layers:
                warnings.append(f"zone {zone.index} has no sample layers")
            if zone.polyphony < 1:
                errors.append(f"zone {zone.index} has invalid polyphony")
            if self.kind == "keygroup":
                if zone.low_note is None or zone.high_note is None:
                    errors.append(f"keygroup zone {zone.index} requires a note range")
                elif not 0 <= zone.low_note <= zone.high_note <= 127:
                    errors.append(f"keygroup zone {zone.index} has invalid note range")
            for layer in zone.layers:
                if not 0 <= layer.velocity_start <= layer.velocity_end <= 127:
                    errors.append(f"zone {zone.index} has invalid velocity range")
                if layer.root_note is not None and not 0 <= layer.root_note <= 127:
                    errors.append(f"zone {zone.index} has invalid root note")
        return {"errors": sorted(set(errors)), "warnings": sorted(set(warnings))}

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def from_drum_manifest(
    path: Path,
    source_root: Path | None = None,
    role_overrides: dict[str, str] | None = None,
) -> ProgramModel:
    manifest = load_manifest(path)
    palette = load_palette()
    zones = []
    for spec in manifest.pads:
        if source_root is not None and not (source_root / spec.sample).is_file():
            raise FileNotFoundError(f"missing sample for pad {spec.pad}: {source_root / spec.sample}")
        category = classify_sample(spec.sample)
        zones.append(
            Zone(
                index=spec.pad,
                pad=spec.pad,
                role=infer_role(spec.sample, role_overrides),
                color=palette[category],
                layers=(SampleLayer(sample=spec.sample),),
                playback_mode="one-shot",
                monophonic=True,
            )
        )
    return ProgramModel(
        schema_version=1,
        name=manifest.name,
        kind="drum",
        zones=tuple(zones),
        source_format="drum-manifest-toml",
        source_path=str(path.resolve()),
    )


def _integer(value: object, default: int | None = 0) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _boolean(value: object) -> bool:
    return value is True or str(value).casefold() in {"1", "true", "yes", "on"}


def _xml_layer(layer: ET.Element) -> SampleLayer | None:
    sample = (layer.findtext("SampleFile") or layer.findtext("SampleName") or "").strip()
    if not sample:
        return None
    return SampleLayer(
        sample=sample,
        velocity_start=int(_integer(layer.findtext("VelStart"), 0) or 0),
        velocity_end=int(_integer(layer.findtext("VelEnd"), 127) or 127),
        root_note=_integer(layer.findtext("RootNote"), None),
        sample_start=int(_integer(layer.findtext("SliceStart"), 0) or 0),
        sample_end=_integer(layer.findtext("SliceEnd"), None),
        loop_enabled=_boolean(layer.findtext("Loop")),
        loop_start=_integer(layer.findtext("LoopStart"), None),
        loop_end=_integer(layer.findtext("LoopEnd"), None),
    )


def _xml_model(path: Path, role_overrides: dict[str, str] | None = None) -> ProgramModel:
    root = ET.parse(path).getroot()
    program = root.find("Program")
    if program is None:
        raise ValueError(f"missing Program element: {path}")
    kind = program.get("type", "").casefold()
    if kind not in {"drum", "keygroup"}:
        raise ValueError(f"unsupported XML program type: {kind!r}")
    colors: dict[str, int] = {}
    pads_node = program.find("ProgramPads")
    if pads_node is not None and pads_node.text:
        try:
            settings = json.loads(html.unescape(pads_node.text)).get("ProgramPads", {})
            colors = settings.get("pads", {}) if isinstance(settings.get("pads"), dict) else {}
        except json.JSONDecodeError:
            pass
    zones = []
    for sequence, instrument in enumerate(program.findall("./Instruments/Instrument"), 1):
        layers = tuple(
            value for layer in instrument.findall("./Layers/Layer") if (value := _xml_layer(layer))
        )
        if not layers:
            continue
        number = int(instrument.get("number", sequence))
        zones.append(
            Zone(
                index=number,
                pad=number if kind == "drum" else None,
                low_note=_integer(instrument.findtext("LowNote"), None),
                high_note=_integer(instrument.findtext("HighNote"), None),
                role=(
                    infer_role(layers[0].sample, role_overrides)
                    if kind == "drum"
                    else "melodic.instrument"
                ),
                color=colors.get(f"value{number - 1}"),
                layers=layers,
                playback_mode="one-shot" if _boolean(instrument.findtext("OneShot")) else "note-on",
                mute_group=int(_integer(instrument.findtext("MuteGroup"), 0) or 0),
                polyphony=int(_integer(instrument.findtext("Polyphony"), 1) or 1),
                monophonic=_boolean(instrument.findtext("Mono")),
            )
        )
    return ProgramModel(1, program.findtext("ProgramName", ""), kind, tuple(zones), "xml", str(path.resolve()))


def _json_layer(layer: dict[str, Any]) -> SampleLayer | None:
    sample = layer.get("sampleFile") or layer.get("sampleName")
    if not isinstance(sample, str) or not sample.strip():
        return None
    slice_info = layer.get("sliceInfo", {}) if isinstance(layer.get("sliceInfo"), dict) else {}
    return SampleLayer(
        sample=sample,
        velocity_start=int(_integer(layer.get("velocityStart"), 0) or 0),
        velocity_end=int(_integer(layer.get("velocityEnd"), 127) or 127),
        root_note=_integer(layer.get("rootNote"), None),
        sample_start=int(_integer(slice_info.get("Start", layer.get("sampleStart")), 0) or 0),
        sample_end=_integer(slice_info.get("End", layer.get("sampleEnd")), None),
        loop_enabled=_boolean(layer.get("loop")),
        loop_start=_integer(layer.get("loopStart"), None),
        loop_end=_integer(layer.get("loopEnd"), None),
    )


def _json_model(path: Path, role_overrides: dict[str, str] | None = None) -> ProgramModel:
    raw = gzip.decompress(path.read_bytes())
    start = raw.find(b"{")
    if not raw.startswith(b"ACVS\n") or start < 0:
        raise ValueError(f"unsupported compressed MPC program: {path}")
    data = json.loads(raw[start:]).get("data", {})
    kind_value = data.get("type")
    if kind_value not in {0, 1}:
        raise ValueError(f"unsupported compressed program type: {kind_value!r}")
    kind: ProgramKind = "drum" if kind_value == 0 else "keygroup"
    drum = data.get("drum", {})
    instruments = drum.get("instruments", []) if isinstance(drum, dict) else []
    if kind == "keygroup":
        instruments = instruments[1:]
    pad_settings = data.get("programPads", {})
    colors = pad_settings.get("pads", {}) if isinstance(pad_settings, dict) else {}
    zones = []
    for index, instrument in enumerate(instruments, 1):
        if not isinstance(instrument, dict):
            continue
        layers = tuple(
            value
            for layer in instrument.get("layersv", [])
            if isinstance(layer, dict) and (value := _json_layer(layer))
        )
        if not layers:
            continue
        trigger_mode = int(_integer(instrument.get("triggerMode"), 1) or 0)
        zones.append(
            Zone(
                index=index,
                pad=index if kind == "drum" else None,
                low_note=_integer(instrument.get("lowNote"), None),
                high_note=_integer(instrument.get("highNote"), None),
                role=(
                    infer_role(layers[0].sample, role_overrides)
                    if kind == "drum"
                    else "melodic.instrument"
                ),
                color=colors.get(f"value{index - 1}"),
                layers=layers,
                playback_mode="one-shot" if trigger_mode == 0 else f"trigger-mode-{trigger_mode}",
                mute_group=int(_integer(instrument.get("whichMuteGroup"), 0) or 0),
                polyphony=int(_integer(instrument.get("polyphony"), 1) or 1),
                monophonic=_boolean(instrument.get("monophonic")),
            )
        )
    return ProgramModel(1, str(data.get("name", "")), kind, tuple(zones), "gzip-json", str(path.resolve()))


def from_xpm(path: Path, role_overrides: dict[str, str] | None = None) -> ProgramModel:
    return (
        _json_model(path, role_overrides)
        if path.read_bytes()[:2] == b"\x1f\x8b"
        else _xml_model(path, role_overrides)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--source-type", choices=("auto", "xpm", "manifest"), default="auto")
    parser.add_argument("--source-root", type=Path, help="optional WAV root for manifest validation")
    parser.add_argument("--roles", type=Path, help="TOML file with explicit [roles] overrides")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    source = args.source.expanduser().resolve()
    source_type = args.source_type
    if source_type == "auto":
        source_type = "manifest" if source.suffix.casefold() == ".toml" else "xpm"
    role_overrides = (
        load_role_overrides(args.roles.expanduser().resolve()) if args.roles else None
    )
    program = (
        from_drum_manifest(
            source,
            args.source_root.expanduser().resolve() if args.source_root else None,
            role_overrides,
        )
        if source_type == "manifest"
        else from_xpm(source, role_overrides)
    )
    report = {"program": program.to_dict(), "validation": program.validate()}
    rendered = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Wrote: {args.output}")
    else:
        print(rendered, end="")
    return 2 if report["validation"]["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
