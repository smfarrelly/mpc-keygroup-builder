"""Compose selected 16-pad banks from existing MPC Drum Programs."""

from __future__ import annotations

import argparse
import json
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .drum_builder import DrumManifest, PadSpec, build_drum_program
from .drum_map import build_map


BANKS = "ABCDEFGH"


@dataclass(frozen=True)
class BankSpec:
    target: str
    source: str
    bank: str
    label: str


@dataclass(frozen=True)
class BankRecipe:
    name: str
    banks: tuple[BankSpec, ...]


def load_recipe(path: Path) -> BankRecipe:
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("bank recipe name must be a non-empty string")
    raw_banks = data.get("banks")
    if not isinstance(raw_banks, list) or not raw_banks:
        raise ValueError("bank recipe must contain [[banks]] tables")
    banks = []
    targets: set[str] = set()
    for index, raw in enumerate(raw_banks, 1):
        if not isinstance(raw, dict):
            raise ValueError(f"banks entry {index} must be a table")
        target = raw.get("target")
        source = raw.get("source")
        bank = raw.get("bank")
        label = raw.get("label")
        if not isinstance(target, str) or target.upper() not in BANKS:
            raise ValueError(f"banks entry {index} has invalid target {target!r}")
        target = target.upper()
        if target in targets:
            raise ValueError(f"duplicate target bank {target}")
        if not isinstance(source, str) or not source.strip() or Path(source).name != source:
            raise ValueError(f"banks entry {index} source must be an XPM basename")
        if not isinstance(bank, str) or bank.upper() not in BANKS:
            raise ValueError(f"banks entry {index} has invalid source bank {bank!r}")
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"banks entry {index} label must be a non-empty string")
        targets.add(target)
        banks.append(BankSpec(target, source, bank.upper(), label.strip()))
    return BankRecipe(name.strip(), tuple(sorted(banks, key=lambda item: BANKS.index(item.target))))


def _audio_index(root: Path) -> tuple[dict[str, list[Path]], dict[str, list[Path]]]:
    by_name: dict[str, list[Path]] = {}
    by_stem: dict[str, list[Path]] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.casefold() != ".wav":
            continue
        by_name.setdefault(path.name.casefold(), []).append(path)
        by_stem.setdefault(path.stem.casefold(), []).append(path)
    return by_name, by_stem


def _resolve_audio(
    reference: str,
    by_name: dict[str, list[Path]],
    by_stem: dict[str, list[Path]],
) -> Path:
    value = Path(reference).name
    candidates = by_name.get(value.casefold(), []) if Path(value).suffix else by_stem.get(value.casefold(), [])
    if not candidates:
        raise FileNotFoundError(f"source sample not found: {reference}")
    if len(candidates) > 1:
        options = ", ".join(str(path) for path in candidates)
        raise ValueError(f"ambiguous source sample {reference!r}: {options}")
    return candidates[0]


def compose_recipe(recipe: BankRecipe, source_root: Path) -> DrumManifest:
    by_name, by_stem = _audio_index(source_root)
    pads = []
    seen_samples: dict[str, Path] = {}
    for bank_spec in recipe.banks:
        program_path = source_root / bank_spec.source
        if not program_path.is_file():
            raise FileNotFoundError(f"source Drum Program not found: {program_path}")
        report = build_map(program_path)
        source_pads = [pad for pad in report["pads"] if pad["bank"] == bank_spec.bank]
        positions = {(int(pad["pad"]) - 1) % 16 + 1 for pad in source_pads}
        if len(source_pads) != 16 or positions != set(range(1, 17)):
            raise ValueError(
                f"{bank_spec.source} bank {bank_spec.bank} must contain exactly pads 1 through 16"
            )
        groups = {int(pad["mute_group"]) for pad in source_pads if int(pad["mute_group"]) > 0}
        if len(groups) > 1:
            raise ValueError(
                f"{bank_spec.source} bank {bank_spec.bank} has multiple mute groups; "
                "automatic bank rebasing would merge them"
            )
        target_offset = BANKS.index(bank_spec.target) * 16
        target_group = BANKS.index(bank_spec.target) + 1
        for source_pad in sorted(source_pads, key=lambda item: int(item["pad"])):
            position = (int(source_pad["pad"]) - 1) % 16 + 1
            audio = _resolve_audio(str(source_pad["sample"]), by_name, by_stem)
            key = audio.name.casefold()
            previous = seen_samples.get(key)
            if previous is not None and previous != audio:
                raise ValueError(f"selected samples collide when flattened: {previous} and {audio}")
            seen_samples[key] = audio
            pads.append(
                PadSpec(
                    pad=target_offset + position,
                    sample=audio.name,
                    mute_group=target_group if int(source_pad["mute_group"]) > 0 else 0,
                )
            )
    return DrumManifest(recipe.name, tuple(pads))


def render_manifest(recipe: BankRecipe, manifest: DrumManifest) -> str:
    specs = {spec.pad: spec for spec in manifest.pads}
    lines = [f"name = {json.dumps(manifest.name)}", ""]
    for bank_spec in recipe.banks:
        lines.append(
            f"# Bank {bank_spec.target}: {bank_spec.label}; "
            f"source {bank_spec.source} bank {bank_spec.bank}."
        )
        offset = BANKS.index(bank_spec.target) * 16
        for position in range(1, 17):
            spec = specs[offset + position]
            lines.extend(
                [
                    "[[pads]]",
                    f"pad = {spec.pad}",
                    f"sample = {json.dumps(spec.sample)}",
                ]
            )
            if spec.mute_group:
                lines.append(f"mute_group = {spec.mute_group}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipe", type=Path)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--manifest-output", type=Path, required=True)
    parser.add_argument("--template", type=Path)
    parser.add_argument("--package-output", type=Path)
    args = parser.parse_args()
    if (args.template is None) != (args.package_output is None):
        parser.error("--template and --package-output must be supplied together")
    recipe = load_recipe(args.recipe.expanduser().resolve())
    source_root = args.source_root.expanduser().resolve()
    manifest = compose_recipe(recipe, source_root)
    manifest_output = args.manifest_output.expanduser().resolve()
    if manifest_output.exists():
        raise FileExistsError(f"manifest output already exists: {manifest_output}")
    manifest_output.parent.mkdir(parents=True, exist_ok=True)
    manifest_output.write_text(render_manifest(recipe, manifest), encoding="utf-8")
    print(f"Wrote: {manifest_output}")
    print(f"Banks: {len(recipe.banks)}; pads: {len(manifest.pads)}")
    if args.template is not None and args.package_output is not None:
        destination = build_drum_program(
            manifest,
            args.template.expanduser().resolve(),
            source_root,
            args.package_output.expanduser().resolve(),
        )
        print(f"Wrote: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
