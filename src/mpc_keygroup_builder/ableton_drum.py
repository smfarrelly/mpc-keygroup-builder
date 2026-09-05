"""Translate prepared Ableton Drum Racks into MPC Drum Program packages."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path

from . import ableton
from .drum_builder import DrumManifest, LayerSpec, PadSpec, build_drum_program


@dataclass(frozen=True)
class ConversionPlan:
    name: str
    preset: Path
    pack_root: Path
    manifest: DrumManifest
    samples: dict[str, Path]
    receiving_notes: tuple[int, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class RecipeProgram:
    identifier: str
    name: str
    collection: str
    preset: Path
    pack_root: Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _contained(root: Path, value: str, label: str) -> Path:
    relative = Path(value)
    if relative.is_absolute():
        raise ValueError(f"{label} must be relative: {value}")
    target = (root / relative).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"{label} escapes its root: {value}") from error
    return target


def _velocity(zone: dict[str, object]) -> tuple[int, int]:
    raw = zone.get("velocity_range")
    if not isinstance(raw, dict):
        return 0, 127
    low = int(raw.get("min", 0))
    high = int(raw.get("max", 127))
    if low == 1:
        low = 0
    if not 0 <= low <= high <= 127:
        raise ValueError(f"invalid Ableton velocity range {low}..{high}")
    return low, high


def plan_conversion(
    preset: Path,
    pack_root: Path,
    *,
    name: str | None = None,
) -> ConversionPlan:
    preset = preset.expanduser().resolve()
    pack_root = pack_root.expanduser().resolve()
    if not pack_root.is_dir():
        raise NotADirectoryError(pack_root)
    report = ableton.inspect(preset)
    raw_pads = report.get("drum_pads", [])
    if not isinstance(raw_pads, list) or not raw_pads:
        raise ValueError(f"Ableton preset has no readable Drum Rack pads: {preset}")
    if len(raw_pads) > 128:
        raise ValueError(f"Ableton Drum Rack has {len(raw_pads)} pads; MPC supports 128")

    pads: list[PadSpec] = []
    samples: dict[str, Path] = {}
    receiving_notes: list[int] = []
    seen_notes: set[int] = set()
    warnings: set[str] = set()
    device_types = report.get("device_types", {})
    if isinstance(device_types, dict):
        structural = {
            "AudioBranchMixerDevice",
            "DrumGroupDevice",
            "InstrumentGroupDevice",
            "OriginalSimpler",
        }
        ignored = sorted(set(device_types) - structural)
        if ignored:
            warnings.add("Ableton device behavior is not serialized: " + ", ".join(ignored))
    if report.get("macros"):
        warnings.add("Ableton Rack macros are not serialized")
    for pad_number, raw_pad in enumerate(raw_pads, 1):
        if not isinstance(raw_pad, dict):
            raise TypeError(f"Ableton Drum Rack pad {pad_number} is not an object")
        receiving_note = raw_pad.get("receiving_note")
        if not isinstance(receiving_note, int) or not 0 <= receiving_note <= 127:
            raise ValueError(f"Ableton Drum Rack pad {pad_number} has no valid receiving note")
        if receiving_note in seen_notes:
            raise ValueError(f"duplicate Ableton receiving note {receiving_note}")
        seen_notes.add(receiving_note)
        receiving_notes.append(receiving_note)
        choke_group = raw_pad.get("choke_group", 0)
        if not isinstance(choke_group, int) or not 0 <= choke_group <= 32:
            raise ValueError(f"unsupported Ableton choke group {choke_group} on pad {pad_number}")

        raw_zones = raw_pad.get("zones", [])
        if not isinstance(raw_zones, list):
            raise TypeError(f"Ableton Drum Rack pad {pad_number} zones are not a list")
        zones = [zone for zone in raw_zones if zone.get("isactive") is not False]
        if not 1 <= len(zones) <= 4:
            raise ValueError(
                f"Ableton Drum Rack pad {pad_number} has {len(zones)} active zones; "
                "MPC Drum manifests support one through four"
            )
        layers: list[LayerSpec] = []
        for zone in zones:
            sample = zone.get("sample")
            if not isinstance(sample, dict):
                raise ValueError(f"Ableton Drum Rack pad {pad_number} has no sample reference")
            relative = sample.get("relative_path")
            filename = sample.get("name")
            if not isinstance(relative, str) or not isinstance(filename, str):
                raise ValueError(f"Ableton Drum Rack pad {pad_number} has an incomplete sample ref")
            source = _contained(pack_root, relative, "Ableton sample path")
            if not source.is_file():
                raise FileNotFoundError(source)
            if source.name != filename:
                raise ValueError(f"Ableton sample basename mismatch: {relative} != {filename}")
            prior = samples.get(filename.casefold())
            if prior is not None and prior != source:
                raise ValueError(f"flattened sample-name collision: {prior} and {source}")
            samples[filename.casefold()] = source
            low, high = _velocity(zone)
            layers.append(LayerSpec(filename, low, high))
            if zone.get("warped") is True:
                warnings.add(f"pad {pad_number} warp behavior is not serialized")
            for field, default in (
                ("detune", 0),
                ("volume", 1),
                ("panorama", 0),
                ("samplestart", 0),
            ):
                current = zone.get(field)
                if current is not None and current != default:
                    warnings.add(f"pad {pad_number} non-default {field}={current} is not serialized")
            sustain = zone.get("sustain_loop")
            if isinstance(sustain, dict) and sustain.get("mode", 0) not in {0, None}:
                warnings.add(f"pad {pad_number} sustain loop is not serialized")
        layers.sort(key=lambda item: item.velocity_start)
        if len(layers) == 1:
            pads.append(PadSpec(pad=pad_number, sample=layers[0].sample, mute_group=choke_group))
            continue
        expected = 0
        for layer in layers:
            if layer.velocity_start != expected:
                raise ValueError(
                    f"velocity gap or overlap on Ableton pad {pad_number}: expected {expected}, "
                    f"got {layer.velocity_start}"
                )
            expected = layer.velocity_end + 1
        if expected != 128:
            raise ValueError(f"velocity layers on Ableton pad {pad_number} do not end at 127")
        pads.append(PadSpec(pad=pad_number, mute_group=choke_group, layers=tuple(layers)))

    program_name = name or str(report.get("name") or preset.stem)
    manifest = DrumManifest(program_name, tuple(pads))
    return ConversionPlan(
        name=program_name,
        preset=preset,
        pack_root=pack_root,
        manifest=manifest,
        samples={path.name: path for path in samples.values()},
        receiving_notes=tuple(receiving_notes),
        warnings=tuple(sorted(warnings)),
    )


def render_manifest(plan: ConversionPlan) -> str:
    lines = [
        f"# Ableton source: {plan.preset}",
        f"# Source SHA-256: {_sha256(plan.preset)}",
        "# MPC pads follow Ableton DrumBranchPreset document order.",
        f"name = {json.dumps(plan.name)}",
        "",
    ]
    notes = dict(enumerate(plan.receiving_notes, 1))
    for spec in plan.manifest.pads:
        lines.extend(["[[pads]]", f"pad = {spec.pad}"])
        lines.append(f"# Ableton receiving note = {notes[spec.pad]}")
        if spec.mute_group:
            lines.append(f"mute_group = {spec.mute_group}")
        if spec.layers:
            for layer in spec.layers:
                lines.extend(
                    [
                        "[[pads.layers]]",
                        f"sample = {json.dumps(layer.sample)}",
                        f"velocity_start = {layer.velocity_start}",
                        f"velocity_end = {layer.velocity_end}",
                    ]
                )
        else:
            lines.append(f"sample = {json.dumps(spec.sample)}")
        lines.append("")
    return "\n".join(lines)


def build_conversion(plan: ConversionPlan, template: Path, output: Path) -> Path:
    with tempfile.TemporaryDirectory(prefix="mpc-ableton-drum-") as directory:
        staging = Path(directory)
        for filename, source in plan.samples.items():
            shutil.copy2(source, staging / filename)
        return build_drum_program(plan.manifest, template, staging, output)


def load_recipe(path: Path, library_root: Path) -> tuple[str, tuple[RecipeProgram, ...]]:
    path = path.expanduser().resolve()
    library_root = library_root.expanduser().resolve()
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    name = data.get("name")
    raw_programs = data.get("programs")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Ableton Drum batch name must be a non-empty string")
    if not isinstance(raw_programs, list) or not raw_programs:
        raise ValueError("Ableton Drum batch must contain [[programs]] tables")
    programs = []
    identifiers = set()
    destinations = set()
    for index, raw in enumerate(raw_programs, 1):
        if not isinstance(raw, dict):
            raise ValueError(f"Ableton Drum batch entry {index} is not a table")
        values = {key: raw.get(key) for key in ("id", "name", "collection", "preset", "pack_root")}
        if not all(isinstance(value, str) and value.strip() for value in values.values()):
            raise ValueError(f"Ableton Drum batch entry {index} has missing string fields")
        identifier = values["id"]
        destination = (values["collection"], values["name"])
        if identifier in identifiers or destination in destinations:
            raise ValueError(f"duplicate Ableton Drum batch entry {identifier}")
        identifiers.add(identifier)
        destinations.add(destination)
        programs.append(
            RecipeProgram(
                identifier=identifier,
                name=values["name"],
                collection=values["collection"],
                preset=_contained(library_root, values["preset"], "preset"),
                pack_root=_contained(library_root, values["pack_root"], "pack_root"),
            )
        )
    return name.strip(), tuple(programs)


def plan_batch(recipe: Path, library_root: Path) -> dict[str, object]:
    batch_name, programs = load_recipe(recipe, library_root)
    results = []
    for item in programs:
        plan = plan_conversion(item.preset, item.pack_root, name=item.name)
        results.append(
            {
                "id": item.identifier,
                "name": item.name,
                "collection": item.collection,
                "preset": str(item.preset),
                "preset_sha256": _sha256(item.preset),
                "pads": len(plan.manifest.pads),
                "samples": len(plan.samples),
                "receiving_notes": list(plan.receiving_notes),
                "translation_warnings": list(plan.warnings),
            }
        )
    return {"format": 1, "name": batch_name, "programs": results}


def build_batch(
    recipe: Path,
    library_root: Path,
    template: Path,
    output_root: Path,
    manifest_root: Path,
) -> dict[str, object]:
    batch_name, programs = load_recipe(recipe, library_root)
    output_root = output_root.expanduser().resolve()
    manifest_root = manifest_root.expanduser().resolve()
    template = template.expanduser().resolve()
    if output_root.exists() and any(output_root.iterdir()):
        raise FileExistsError(f"batch output is not empty: {output_root}")
    if manifest_root.exists() and any(manifest_root.iterdir()):
        raise FileExistsError(f"batch manifest output is not empty: {manifest_root}")
    prepared = []
    for item in programs:
        plan = plan_conversion(item.preset, item.pack_root, name=item.name)
        prepared.append((item, plan))
        print(
            f"PREFLIGHT\t{item.collection}/{item.name}\t"
            f"pads={len(plan.manifest.pads)}\tsamples={len(plan.samples)}"
        )
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_root.mkdir(parents=True, exist_ok=True)
    results = []
    for index, (item, plan) in enumerate(prepared, 1):
        manifest_path = manifest_root / f"{item.identifier}.toml"
        manifest_path.write_text(render_manifest(plan), encoding="utf-8")
        package = output_root / item.collection / item.name
        program = build_conversion(plan, template, package)
        result = {
            "id": item.identifier,
            "name": item.name,
            "collection": item.collection,
            "preset": str(item.preset),
            "preset_sha256": _sha256(item.preset),
            "program": str(program),
            "program_sha256": _sha256(program),
            "pads": len(plan.manifest.pads),
            "samples": len(plan.samples),
            "receiving_notes": list(plan.receiving_notes),
            "translation_warnings": list(plan.warnings),
        }
        results.append(result)
        print(
            f"BUILT\t{index}/{len(programs)}\t{item.collection}/{item.name}\t"
            f"pads={result['pads']}\tsamples={result['samples']}"
        )
    report = {"format": 1, "name": batch_name, "programs": results}
    report_path = manifest_root / "build-report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"SUMMARY\tprograms={len(results)}\treport={report_path}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("preset", type=Path)
    inspect_parser.add_argument("--pack-root", type=Path, required=True)
    inspect_parser.add_argument("--name")
    inspect_parser.add_argument("--manifest", type=Path)
    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("recipe", type=Path)
    plan_parser.add_argument("--library-root", type=Path, required=True)
    plan_parser.add_argument("--report", type=Path, required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("recipe", type=Path)
    build_parser.add_argument("--library-root", type=Path, required=True)
    build_parser.add_argument("--template", type=Path, required=True)
    build_parser.add_argument("--output-root", type=Path, required=True)
    build_parser.add_argument("--manifest-root", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "inspect":
        plan = plan_conversion(args.preset, args.pack_root, name=args.name)
        rendered = render_manifest(plan)
        if args.manifest:
            if args.manifest.exists():
                raise FileExistsError(args.manifest)
            args.manifest.parent.mkdir(parents=True, exist_ok=True)
            args.manifest.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        print(
            f"Pads: {len(plan.manifest.pads)}; samples: {len(plan.samples)}; "
            f"receiving notes: {min(plan.receiving_notes)}-{max(plan.receiving_notes)}"
        )
        for warning in plan.warnings:
            print(f"WARN: {warning}")
        return 0
    if args.command == "plan":
        report = plan_batch(args.recipe, args.library_root)
        if args.report.exists():
            raise FileExistsError(args.report)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        warnings = sum(bool(item["translation_warnings"]) for item in report["programs"])
        print(
            f"Programs: {len(report['programs'])}; programs with translation warnings: {warnings}; "
            f"report: {args.report}"
        )
        return 0
    build_batch(
        args.recipe,
        args.library_root,
        args.template,
        args.output_root,
        args.manifest_root,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
