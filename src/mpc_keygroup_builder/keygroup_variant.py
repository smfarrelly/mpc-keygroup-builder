"""Create preservation-first variants of MPC 3 compressed Keygroup Programs."""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
import os
import re
import shutil
import tempfile
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .testing import ProgramTest, test_gzip_json


_ENVELOPE_PARAMETERS = {
    "amp_attack": ("ampEnvelope", "Attack"),
    "amp_decay": ("ampEnvelope", "Decay"),
    "amp_sustain": ("ampEnvelope", "Sustain"),
    "amp_release": ("ampEnvelope", "Release"),
    "filter_attack": ("filterEnvelope", "Attack"),
    "filter_decay": ("filterEnvelope", "Decay"),
    "filter_sustain": ("filterEnvelope", "Sustain"),
    "filter_release": ("filterEnvelope", "Release"),
}
_FILTER_PARAMETERS = {
    "filter_cutoff": "filterCutoff",
    "filter_resonance": "filterResonance",
    "filter_envelope_amount": "filterEnvelopeAmount",
}
_NORMALIZED_PARAMETERS = set(_ENVELOPE_PARAMETERS) | {
    "filter_cutoff",
    "filter_resonance",
}
_PARAMETERS = {"transpose", *_ENVELOPE_PARAMETERS, *_FILTER_PARAMETERS}
_QLINK_NAMES = {
    "amp_attack": "attack",
    "filter_cutoff": "cutoff",
    "filter_attack": "filter attack",
}


@dataclass(frozen=True)
class VariantSpec:
    schema_version: int
    id: str
    name: str
    description: str
    parameters: dict[str, int | float]


@dataclass(frozen=True)
class VariantReport:
    source: str
    output: str
    source_name: str
    output_name: str
    variant: str
    changed_paths: tuple[str, ...]
    instrument_records: int
    sample_layers: int
    sample_registry_entries: int
    program_data_files: int
    program_data_bytes: int
    document_preserved_except_allowlist: bool
    program_data_checksums_match: bool


def _safe_filename(value: str) -> str:
    clean = re.sub(r"[\\/:*?\"<>|\x00-\x1f]+", " ", value)
    clean = " ".join(clean.split()).strip(" .")
    if not clean:
        raise ValueError("variant output name has no filesystem-safe characters")
    return clean


def _overlap(left: Path, right: Path) -> bool:
    left = left.resolve()
    right = right.resolve()
    return left == right or left.is_relative_to(right) or right.is_relative_to(left)


def _read_program(path: Path) -> tuple[bytes, dict[str, Any]]:
    if path.read_bytes()[:2] != b"\x1f\x8b":
        raise ValueError(
            f"expressive variants currently require an MPC 3 compressed Keygroup: {path}"
        )
    try:
        raw = gzip.decompress(path.read_bytes())
    except gzip.BadGzipFile as error:
        raise ValueError(f"invalid compressed MPC program: {path}") from error
    start = raw.find(b"{")
    if not raw.startswith(b"ACVS\n") or start < 0:
        raise ValueError(f"unsupported compressed MPC program: {path}")
    try:
        document = json.loads(raw[start:])
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid MPC JSON document: {path}") from error
    data = document.get("data")
    if not isinstance(data, dict) or data.get("type") != 1:
        raise ValueError(f"not a compressed Keygroup Program: {path}")
    return raw[:start], document


def load_variant(path: Path) -> VariantSpec:
    with path.open("rb") as stream:
        raw = tomllib.load(stream)
    allowed = {"schema_version", "id", "name", "description", "parameters"}
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"unknown variant fields: {', '.join(unknown)}")
    if raw.get("schema_version") != 1:
        raise ValueError("variant requires schema_version=1")
    identifier = raw.get("id")
    name = raw.get("name")
    description = raw.get("description", "")
    parameters = raw.get("parameters", {})
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("variant id must be a non-empty string")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("variant name must be a non-empty string")
    if not isinstance(description, str):
        raise ValueError("variant description must be a string")
    if not isinstance(parameters, dict):
        raise ValueError("variant parameters must be a table")
    extra = sorted(set(parameters) - _PARAMETERS)
    if extra:
        raise ValueError(f"unsupported variant parameters: {', '.join(extra)}")
    clean: dict[str, int | float] = {}
    for key, value in parameters.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{key} must be numeric")
        if key == "transpose":
            if not isinstance(value, int) or not -24 <= value <= 24:
                raise ValueError("transpose must be an integer from -24 to 24")
            clean[key] = value
        elif key in _NORMALIZED_PARAMETERS:
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"{key} must be from 0.0 to 1.0")
            clean[key] = float(value)
        else:
            if not -1.0 <= float(value) <= 1.0:
                raise ValueError(f"{key} must be from -1.0 to 1.0")
            clean[key] = float(value)
    return VariantSpec(1, identifier.strip(), name.strip(), description.strip(), clean)


def _require_dict(parent: dict[str, Any], key: str, context: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"source lacks required {context}.{key} object")
    return value


def _set_value(
    parent: dict[str, Any], key: str, value: int | float, path: str, changed: list[str]
) -> None:
    if key not in parent:
        raise ValueError(f"source lacks required parameter {path}")
    if parent[key] != value:
        parent[key] = value
        changed.append(path)


def _update_qlink(
    data: dict[str, Any], parameter: str, value: float, changed: list[str]
) -> None:
    expected_name = _QLINK_NAMES.get(parameter)
    if expected_name is None:
        return
    qlinks = data.get("customQLinks")
    if not isinstance(qlinks, list):
        raise ValueError("source lacks required customQLinks array")
    matches = [
        (index, item)
        for index, item in enumerate(qlinks)
        if isinstance(item, dict) and str(item.get("name", "")).casefold() == expected_name
    ]
    if len(matches) != 1:
        raise ValueError(f"source requires exactly one {expected_name!r} custom Q-Link")
    index, item = matches[0]
    _set_value(item, "controlValue", value, f"data.customQLinks[{index}].controlValue", changed)


def _apply(
    document: dict[str, Any], spec: VariantSpec, output_name: str
) -> tuple[str, ...]:
    data = _require_dict(document, "data", "document")
    changed: list[str] = []
    _set_value(data, "name", output_name, "data.name", changed)
    keygroup = _require_dict(data, "keygroup", "data")
    synth = _require_dict(keygroup, "synthSection", "data.keygroup")
    for parameter, value in spec.parameters.items():
        if parameter == "transpose":
            _set_value(data, "transpose", value, "data.transpose", changed)
            _set_value(keygroup, "transpose", value, "data.keygroup.transpose", changed)
            continue
        if parameter in _ENVELOPE_PARAMETERS:
            envelope_name, field_name = _ENVELOPE_PARAMETERS[parameter]
            envelope = _require_dict(synth, envelope_name, "data.keygroup.synthSection")
            field = _require_dict(
                envelope,
                field_name,
                f"data.keygroup.synthSection.{envelope_name}",
            )
            _set_value(
                field,
                "value0",
                value,
                f"data.keygroup.synthSection.{envelope_name}.{field_name}.value0",
                changed,
            )
            _update_qlink(data, parameter, float(value), changed)
            continue
        field_name = _FILTER_PARAMETERS[parameter]
        filter_data = _require_dict(synth, "filterData", "data.keygroup.synthSection")
        active_filter = _require_dict(
            filter_data, "value0", "data.keygroup.synthSection.filterData"
        )
        _set_value(
            active_filter,
            field_name,
            value,
            f"data.keygroup.synthSection.filterData.value0.{field_name}",
            changed,
        )
        _update_qlink(data, parameter, float(value), changed)
    return tuple(changed)


def _program_counts(document: dict[str, Any]) -> tuple[int, int, int]:
    data = _require_dict(document, "data", "document")
    drum = _require_dict(data, "drum", "data")
    instruments = drum.get("instruments")
    if not isinstance(instruments, list):
        raise ValueError("source lacks required data.drum.instruments array")
    layers = sum(
        1
        for instrument in instruments
        if isinstance(instrument, dict)
        for layer in instrument.get("layersv", [])
        if isinstance(layer, dict) and (layer.get("sampleFile") or layer.get("sampleName"))
    )
    samples = data.get("samples", [])
    if not isinstance(samples, list):
        raise ValueError("source lacks required data.samples array")
    return len(instruments), layers, len(samples)


def _semantic_result(
    result: ProgramTest, source_issues: set[tuple[str, str, str]]
) -> dict[str, Any]:
    issues = [asdict(issue) for issue in result.issues]
    new_issues = [
        issue
        for issue in issues
        if (issue["severity"], issue["code"], issue["message"]) not in source_issues
    ]
    return {
        "verdict": result.verdict,
        "playable_notes": result.playable_notes,
        "dead_trigger_cells": result.dead_trigger_cells,
        "stacked_trigger_cells": result.stacked_trigger_cells,
        "issues": issues,
        "new_issues": new_issues,
    }


def _tree_checksums(path: Path) -> dict[str, tuple[int, str]]:
    result: dict[str, tuple[int, str]] = {}
    if not path.is_dir():
        return result
    for item in sorted(value for value in path.rglob("*") if value.is_file()):
        digest = hashlib.sha256()
        with item.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        result[item.relative_to(path).as_posix()] = (item.stat().st_size, digest.hexdigest())
    return result


def verify_variant(
    source: Path,
    output: Path,
    spec: VariantSpec,
    *,
    name: str | None = None,
    require_program_data: bool = True,
) -> VariantReport:
    source_prefix, source_document = _read_program(source)
    output_prefix, output_document = _read_program(output)
    if output_prefix != source_prefix:
        raise ValueError("MPC serialization prefix changed")
    source_name = str(source_document["data"].get("name", ""))
    output_name = name or f"{source_name} {spec.name}"
    expected = copy.deepcopy(source_document)
    changed = _apply(expected, spec, output_name)
    if output_document != expected:
        raise ValueError("output document changed outside the variant allowlist")
    source_data = source.with_name(f"{source.stem}_[ProgramData]")
    output_data = output.with_name(f"{output.stem}_[ProgramData]")
    source_checksums = _tree_checksums(source_data)
    output_checksums = _tree_checksums(output_data)
    if require_program_data and not source_checksums:
        raise ValueError(f"source ProgramData folder is missing or empty: {source_data}")
    if require_program_data and output_checksums != source_checksums:
        raise ValueError("output ProgramData file set or checksums changed")
    instruments, layers, samples = _program_counts(output_document)
    return VariantReport(
        str(source.resolve()),
        str(output.resolve()),
        source_name,
        output_name,
        spec.id,
        changed,
        instruments,
        layers,
        samples,
        len(output_checksums),
        sum(value[0] for value in output_checksums.values()),
        True,
        output_checksums == source_checksums,
    )


def _write_atomic(path: Path, payload: bytes) -> None:
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
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def export_variant(
    source: Path,
    output: Path,
    spec: VariantSpec,
    *,
    name: str | None = None,
    force: bool = False,
    copy_program_data: bool = True,
) -> VariantReport:
    if source.resolve() == output.resolve():
        raise ValueError("in-place Keygroup variant export is not allowed")
    prefix, document = _read_program(source)
    source_name = str(document["data"].get("name", ""))
    output_name = name or f"{source_name} {spec.name}"
    _apply(document, spec, output_name)
    source_data = source.with_name(f"{source.stem}_[ProgramData]")
    output_data = output.with_name(f"{output.stem}_[ProgramData]")
    if copy_program_data and _overlap(source_data, output_data):
        raise ValueError("source and output ProgramData paths must not overlap")
    if output.is_dir():
        raise ValueError(f"XPM output path is a directory: {output}")
    targets = [output, *([output_data] if copy_program_data else [])]
    existing = [str(path) for path in targets if path.exists()]
    if existing and not force:
        raise FileExistsError(f"output exists; pass --force to replace it: {', '.join(existing)}")
    if copy_program_data and not _tree_checksums(source_data):
        raise ValueError(f"source ProgramData folder is missing or empty: {source_data}")
    output.parent.mkdir(parents=True, exist_ok=True)
    if force:
        output.unlink(missing_ok=True)
        if copy_program_data and output_data.exists():
            shutil.rmtree(output_data)
    if copy_program_data:
        with tempfile.TemporaryDirectory(
            dir=output.parent, prefix=f".{output.stem}.data."
        ) as root:
            staged = Path(root) / output_data.name
            shutil.copytree(source_data, staged)
            os.replace(staged, output_data)
    payload = gzip.compress(
        prefix + json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode(),
        compresslevel=9,
        mtime=0,
    )
    _write_atomic(output, payload)
    return verify_variant(
        source,
        output,
        spec,
        name=output_name,
        require_program_data=copy_program_data,
    )


def build_variant_package(
    source: Path,
    specs: list[VariantSpec],
    output: Path,
    *,
    name_prefix: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    if len(specs) < 1:
        raise ValueError("a variant package requires at least one specification")
    identifiers = [spec.id.casefold() for spec in specs]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("variant package ids must be unique")
    _, document = _read_program(source)
    source_name = str(document["data"].get("name", ""))
    prefix = _safe_filename(name_prefix or source_name)
    filenames = [f"{prefix} {_safe_filename(spec.name)}.xpm" for spec in specs]
    if len({name.casefold() for name in filenames}) != len(filenames):
        raise ValueError("variant package output filenames must be unique")
    source_test = test_gzip_json(source, source.name)
    if source_test.verdict == "fail":
        codes = ", ".join(sorted({issue.code for issue in source_test.issues}))
        raise ValueError(f"source semantic validation failed: {codes}")
    source_issue_set = {
        (issue.severity, issue.code, issue.message) for issue in source_test.issues
    }
    source_data = source.with_name(f"{source.stem}_[ProgramData]")
    if _overlap(output, source) or _overlap(output, source_data):
        raise ValueError("variant package output must not overlap its source")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        if not force:
            raise FileExistsError(f"output exists; pass --force to replace it: {output}")
        if output.is_dir():
            shutil.rmtree(output)
        else:
            output.unlink()
    with tempfile.TemporaryDirectory(
        dir=output.parent, prefix=f".{output.name}.package."
    ) as temporary:
        staging = Path(temporary) / output.name
        staging.mkdir()
        variants: list[dict[str, Any]] = []
        for index, (spec, filename) in enumerate(zip(specs, filenames), 1):
            target = staging / filename
            report = export_variant(
                source,
                target,
                spec,
                name=f"{prefix} {spec.name}",
            )
            semantic = _semantic_result(
                test_gzip_json(target, filename), source_issue_set
            )
            if semantic["verdict"] == "fail" or semantic["new_issues"]:
                codes = ", ".join(
                    sorted({issue["code"] for issue in semantic["new_issues"]})
                ) or "semantic failure"
                raise ValueError(f"variant {spec.id} introduced validation issues: {codes}")
            variants.append(
                {
                    "order": index,
                    "id": spec.id,
                    "name": spec.name,
                    "description": spec.description,
                    "program": filename,
                    "program_data": f"{Path(filename).stem}_[ProgramData]",
                    "parameters": spec.parameters,
                    "changed_paths": list(report.changed_paths),
                    "instrument_records": report.instrument_records,
                    "sample_layers": report.sample_layers,
                    "sample_registry_entries": report.sample_registry_entries,
                    "program_data_files": report.program_data_files,
                    "program_data_bytes": report.program_data_bytes,
                    "preservation_verdict": "pass",
                    "semantic": semantic,
                }
            )
        verdicts = [item["semantic"]["verdict"] for item in variants]
        semantic_verdict = (
            "fail" if "fail" in verdicts else "warn" if "warn" in verdicts else "pass"
        )
        manifest = {
            "schema_version": 1,
            "kind": "mpc-keygroup-variant-package",
            "source": str(source.resolve()),
            "source_name": source_name,
            "name_prefix": prefix,
            "variant_count": len(variants),
            "source_semantic": _semantic_result(source_test, source_issue_set),
            "variants": variants,
            "preservation_verdict": "pass",
            "semantic_verdict": semantic_verdict,
            "semantic_new_issue_count": sum(
                len(item["semantic"]["new_issues"]) for item in variants
            ),
            "hardware_verdict": "pending",
        }
        _write_atomic(
            staging / "manifest.json",
            (json.dumps(manifest, indent=2) + "\n").encode(),
        )
        lines = [
            f"# {prefix} expressive Keygroup candidates",
            "",
            "Each XPM is self-contained with a checksum-verified ProgramData copy.",
            "Preservation verification proves that only the declared parameters",
            "and matching Q-Link control values changed. Semantic warnings are",
            "recorded separately and compared with the source; neither check proves",
            "musical fit.",
            "",
            "Hardware listening order:",
            "",
        ]
        lines.extend(
            f"{item['order']}. `{item['program']}` — {item['description']}"
            for item in variants
        )
        lines.extend(
            [
                "",
                "For each candidate, compare level, attack/release behavior, filter",
                "character, playable range, Q-Link pickup, and save/reload persistence.",
                "Record pass/warn/fail plus listening notes before promoting a preset.",
                "",
            ]
        )
        _write_atomic(staging / "README.md", "\n".join(lines).encode())
        os.replace(staging, output)
    for spec, filename in zip(specs, filenames):
        verify_variant(
            source,
            output / filename,
            spec,
            name=f"{prefix} {spec.name}",
        )
    return manifest


def inspect_program(source: Path) -> dict[str, Any]:
    _, document = _read_program(source)
    data = document["data"]
    keygroup = _require_dict(data, "keygroup", "data")
    synth = _require_dict(keygroup, "synthSection", "data.keygroup")
    parameters: dict[str, int | float] = {
        "transpose": int(data["transpose"]),
    }
    for parameter, (envelope_name, field_name) in _ENVELOPE_PARAMETERS.items():
        parameters[parameter] = float(synth[envelope_name][field_name]["value0"])
    for parameter, field_name in _FILTER_PARAMETERS.items():
        parameters[parameter] = float(synth["filterData"]["value0"][field_name])
    instruments, layers, samples = _program_counts(document)
    program_data = source.with_name(f"{source.stem}_[ProgramData]")
    checksums = _tree_checksums(program_data)
    return {
        "source": str(source.resolve()),
        "name": data.get("name", ""),
        "format": "gzip-json",
        "instrument_records": instruments,
        "sample_layers": layers,
        "sample_registry_entries": samples,
        "program_data_files": len(checksums),
        "parameters": parameters,
        "supported_parameters": sorted(_PARAMETERS),
    }


def _print(value: Any) -> None:
    print(json.dumps(asdict(value) if hasattr(value, "__dataclass_fields__") else value, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect, export, and verify preservation-first MPC Keygroup variants"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="show supported source parameters")
    inspect.add_argument("source", type=Path)
    export = commands.add_parser("export", help="write a self-contained Keygroup variant")
    export.add_argument("source", type=Path)
    export.add_argument("--spec", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)
    export.add_argument("--name")
    export.add_argument("--force", action="store_true")
    export.add_argument("--xpm-only", action="store_true")
    package = commands.add_parser(
        "package", help="build a self-contained multi-variant hardware package"
    )
    package.add_argument("source", type=Path)
    package.add_argument("--spec", type=Path, action="append", required=True)
    package.add_argument("--output", type=Path, required=True)
    package.add_argument("--name-prefix")
    package.add_argument("--force", action="store_true")
    verify = commands.add_parser("verify", help="verify an exported Keygroup variant")
    verify.add_argument("source", type=Path)
    verify.add_argument("output", type=Path)
    verify.add_argument("--spec", type=Path, required=True)
    verify.add_argument("--name")
    verify.add_argument("--xpm-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            _print(inspect_program(args.source))
        elif args.command == "export":
            _print(
                export_variant(
                    args.source,
                    args.output,
                    load_variant(args.spec),
                    name=args.name,
                    force=args.force,
                    copy_program_data=not args.xpm_only,
                )
            )
        elif args.command == "verify":
            _print(
                verify_variant(
                    args.source,
                    args.output,
                    load_variant(args.spec),
                    name=args.name,
                    require_program_data=not args.xpm_only,
                )
            )
        else:
            _print(
                build_variant_package(
                    args.source,
                    [load_variant(path) for path in args.spec],
                    args.output,
                    name_prefix=args.name_prefix,
                    force=args.force,
                )
            )
    except (FileExistsError, FileNotFoundError, OSError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
