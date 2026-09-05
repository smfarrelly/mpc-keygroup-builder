"""Manifest-driven batch inspection, build, validation, and installation."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import shutil
import sys
import tempfile
import tomllib
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .cli import (
    all_samples,
    build_program,
    copy_file_durable,
    discover_samples,
    place_sample_groups,
    validate_written_program,
    write_program,
)


@dataclass(frozen=True)
class Settings:
    library_root: Path
    mpc_root: Path
    template: Path
    artifacts_root: Path


@dataclass(frozen=True)
class Instrument:
    name: str
    category: str
    source: Path
    velocity_preset: Path | None
    install_mode: str
    centralized: Path | None
    vendor_programs_checked: bool
    include: tuple[str, ...] = ("*.wav",)
    exclude: tuple[str, ...] = ()
    root_shift: int = 0
    root_target: tuple[int, int] | None = None


@dataclass(frozen=True)
class Batch:
    manifest_path: Path
    library: str
    destination: Path
    instruments: tuple[Instrument, ...]


def _configured_path(value: str, *, base: Path) -> Path:
    path = Path(value).expanduser()
    return (path if path.is_absolute() else base / path).resolve()


def _relative_path(root: Path, value: str, label: str) -> Path:
    relative = Path(value)
    if relative.is_absolute():
        raise ValueError(f"{label} must be relative: {value}")
    target = (root / relative).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"{label} escapes its configured root: {value}") from error
    return target


def load_settings(path: Path) -> Settings:
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    base = path.parent.resolve()
    required = ("library_root", "mpc_root", "template", "artifacts_root")
    missing = [key for key in required if not isinstance(data.get(key), str)]
    if missing:
        raise ValueError(f"missing string config keys: {', '.join(missing)}")
    return Settings(*(_configured_path(data[key], base=base) for key in required))


def load_batch(manifest_path: Path, settings: Settings) -> Batch:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if data.get("version") != 1:
        raise ValueError("manifest version must be 1")
    library = data.get("library")
    if not isinstance(library, str) or not library:
        raise ValueError("manifest library must be a non-empty string")
    source_root_value = data.get("source_root")
    destination_value = data.get("destination")
    entries = data.get("instruments")
    if not isinstance(source_root_value, str) or not isinstance(destination_value, str):
        raise ValueError("manifest source_root and destination must be strings")
    if not isinstance(entries, list) or not entries:
        raise ValueError("manifest instruments must be a non-empty list")
    source_root = _relative_path(settings.library_root, source_root_value, "source_root")
    destination = _relative_path(settings.mpc_root, destination_value, "destination")
    centralized_root_value = data.get("centralized_root")
    centralized_root = (
        _relative_path(settings.mpc_root, centralized_root_value, "centralized_root")
        if isinstance(centralized_root_value, str)
        else None
    )
    instruments: list[Instrument] = []
    identities: set[tuple[str, str]] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"instrument {index} must be an object")
        name = entry.get("name")
        source_value = entry.get("source")
        category = entry.get("category", "")
        if not all(isinstance(value, str) for value in (name, source_value, category)):
            raise ValueError(f"instrument {index} name/source/category must be strings")
        identity = (category, name)
        if identity in identities:
            raise ValueError(f"duplicate instrument destination: {category}/{name}")
        identities.add(identity)
        velocity_value = entry.get("velocity_preset")
        velocity = (
            _relative_path(settings.library_root, velocity_value, "velocity_preset")
            if isinstance(velocity_value, str)
            else None
        )
        mode = entry.get("install", "copy")
        if mode not in {"copy", "relocate", "replace_corrupt"}:
            raise ValueError(f"invalid install mode for {name}: {mode}")
        selection = entry.get("sample_selection")
        include = ("*.wav",)
        exclude: tuple[str, ...] = ()
        if selection is not None:
            if not isinstance(selection, dict) or set(selection) - {"include", "exclude"}:
                raise ValueError(f"{name} sample_selection has invalid keys")
            raw_include = selection.get("include", ["*.wav"])
            raw_exclude = selection.get("exclude", [])
            if (
                not isinstance(raw_include, list)
                or not raw_include
                or not all(isinstance(pattern, str) and pattern for pattern in raw_include)
                or not isinstance(raw_exclude, list)
                or not all(isinstance(pattern, str) and pattern for pattern in raw_exclude)
            ):
                raise ValueError(f"{name} sample_selection patterns must be strings")
            include = tuple(raw_include)
            exclude = tuple(raw_exclude)
            if mode != "copy":
                raise ValueError(f"{name} sample_selection requires install=copy")
        centralized_value = entry.get("centralized")
        centralized = None
        if centralized_value is not None:
            if centralized_root is None or not isinstance(centralized_value, str):
                raise ValueError(f"{name} centralized path requires centralized_root")
            centralized = _relative_path(
                centralized_root, centralized_value, f"{name} centralized"
            )
        if mode != "copy" and centralized is None:
            raise ValueError(f"{name} install mode {mode} requires centralized")
        root_shift = entry.get("root_shift", 0)
        if isinstance(root_shift, bool) or not isinstance(root_shift, int):
            raise ValueError(f"{name} root_shift must be an integer")
        root_target_value = entry.get("root_target")
        root_target = None
        if root_target_value is not None:
            if "root_shift" in entry:
                raise ValueError(f"{name} root_shift and root_target are mutually exclusive")
            if (
                not isinstance(root_target_value, list)
                or len(root_target_value) != 2
                or any(
                    isinstance(note, bool) or not isinstance(note, int)
                    for note in root_target_value
                )
            ):
                raise ValueError(f"{name} root_target must be [LOW, HIGH] MIDI integers")
            low, high = root_target_value
            if not 0 <= low <= high <= 127:
                raise ValueError(f"{name} root_target must satisfy 0 <= LOW <= HIGH <= 127")
            root_target = (low, high)
        instruments.append(
            Instrument(
                name=name,
                category=category,
                source=_relative_path(source_root, source_value, f"{name} source"),
                velocity_preset=velocity,
                install_mode=mode,
                centralized=centralized,
                vendor_programs_checked=entry.get("vendor_programs_checked") is True,
                include=include,
                exclude=exclude,
                root_shift=root_shift,
                root_target=root_target,
            )
        )
    return Batch(manifest_path.resolve(), library, destination, tuple(instruments))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wav_map(path: Path) -> dict[str, Path]:
    return {item.name: item for item in path.glob("*.wav") if item.is_file()}


def selected_wav_map(instrument: Instrument) -> dict[str, Path]:
    available = wav_map(instrument.source)
    selected = {
        name: path
        for name, path in available.items()
        if any(fnmatch.fnmatchcase(name, pattern) for pattern in instrument.include)
        and not any(fnmatch.fnmatchcase(name, pattern) for pattern in instrument.exclude)
    }
    if not selected:
        raise ValueError(f"{instrument.name}: sample_selection selected no WAVs")
    return selected


def compare_wav_maps(
    left: dict[str, Path], right: dict[str, Path]
) -> tuple[bool, str]:
    if set(left) != set(right):
        missing = sorted(set(left) - set(right))
        extra = sorted(set(right) - set(left))
        return False, f"file-set mismatch missing={missing[:3]} extra={extra[:3]}"
    for name in sorted(left):
        if left[name].stat().st_size == 0 or right[name].stat().st_size == 0:
            return False, f"zero-byte WAV: {name}"
        if sha256(left[name]) != sha256(right[name]):
            return False, f"checksum mismatch: {name}"
    return True, f"{len(left)} checksums match"


def compare_wavs(expected: Path, actual: Path) -> tuple[bool, str]:
    return compare_wav_maps(wav_map(expected), wav_map(actual))


def artifact_paths(settings: Settings, batch: Batch, instrument: Instrument) -> tuple[Path, Path]:
    parent = settings.artifacts_root / batch.library / instrument.category
    program = parent / f"{instrument.name}.xpm"
    return program, parent / f"{instrument.name}_[ProgramData]"


def installed_paths(batch: Batch, instrument: Instrument) -> tuple[Path, Path]:
    parent = batch.destination / instrument.category
    program = parent / f"{instrument.name}.xpm"
    return program, parent / f"{instrument.name}_[ProgramData]"


def _validate_copy(program: Path, data: Path, expected: dict[str, Path]) -> dict[str, int]:
    if data != program.with_name(f"{program.stem}_[ProgramData]"):
        raise ValueError(f"nonstandard ProgramData path for {program}")
    counts = validate_written_program(program)
    okay, reason = compare_wav_maps(expected, wav_map(data))
    if not okay:
        raise ValueError(f"{program}: {reason}")
    if counts["samples"] != len(expected):
        raise ValueError(f"{program}: XPM/selected sample count mismatch")
    return counts


def inspect_batch_report(settings: Settings, batch: Batch) -> dict[str, Any]:
    hashes: dict[str, list[str]] = {}
    programs = []
    for instrument in batch.instruments:
        try:
            selected = selected_wav_map(instrument)
            groups, placement = place_sample_groups(
                discover_samples(
                    instrument.source, instrument.velocity_preset, set(selected)
                ),
                root_shift=instrument.root_shift,
                root_target=instrument.root_target,
            )
            samples = all_samples(groups)
            discovered = {sample.path.name for sample in samples}
            available = set(selected)
            if discovered != available:
                ignored = sorted(available - discovered)
                missing = sorted(discovered - available)
                raise ValueError(
                    f"sample discovery mismatch ignored={ignored[:3]} missing={missing[:3]}"
                )
            for sample in samples:
                hashes.setdefault(sha256(sample.path), []).append(
                    f"{instrument.category}/{instrument.name}/{sample.path.name}"
                )
            central = "none"
            if instrument.centralized is not None:
                files = wav_map(instrument.centralized)
                zeros = sum(path.stat().st_size == 0 for path in files.values())
                central = f"{len(files)} WAVs, {zeros} zero-byte"
            programs.append({
                "name": instrument.name, "category": instrument.category, "status": "pass",
                "source": str(instrument.source), "keygroups": len(groups), "samples": len(samples),
                "selected_bytes": sum(sample.path.stat().st_size for sample in samples),
                "excluded_samples": len(wav_map(instrument.source)) - len(selected),
                "centralized": central,
                "root_shift": placement.shift if placement is not None else instrument.root_shift,
                "root_target": list(instrument.root_target) if instrument.root_target is not None else None,
            })
        except (FileNotFoundError, KeyError, ValueError, wave.Error) as error:
            programs.append({
                "name": instrument.name, "category": instrument.category, "status": "fail",
                "source": str(instrument.source), "error": str(error),
            })
    duplicates = [sorted(paths) for paths in hashes.values() if len(paths) > 1]
    failures = sum(item["status"] == "fail" for item in programs)
    return {
        "schema_version": 1, "kind": "mpc-keygroup-batch-inspection",
        "library": batch.library, "manifest": str(batch.manifest_path),
        "summary": {
            "instruments": len(batch.instruments), "passed": len(batch.instruments) - failures,
            "failures": failures, "keygroups": sum(item.get("keygroups", 0) for item in programs),
            "samples": sum(item.get("samples", 0) for item in programs),
            "selected_bytes": sum(item.get("selected_bytes", 0) for item in programs),
            "unique_audio": len(hashes), "duplicate_groups": len(duplicates),
        },
        "programs": programs, "duplicate_audio_groups": sorted(duplicates),
    }


def inspect_batch(settings: Settings, batch: Batch, report_path: Path | None = None, *, force_report: bool = False) -> int:
    report = inspect_batch_report(settings, batch)
    for item in report["programs"]:
        identity = f"{item['category']}/{item['name']}"
        if item["status"] == "fail":
            print(f"FAIL\t{identity}\t{item['error']}")
            continue
        print(
            f"PASS\t{identity}\tkeygroups={item['keygroups']}\tsamples={item['samples']}"
            f"\tbytes={item['selected_bytes']}\tcentral={item['centralized']}"
            f"\texcluded={item['excluded_samples']}\troot_shift={item['root_shift']:+d}"
            f"\troot_target={tuple(item['root_target']) if item['root_target'] is not None else 'none'}"
        )
    summary = report["summary"]
    print(
        f"SUMMARY\tinstruments={summary['instruments']}\tfailures={summary['failures']}\t"
        f"keygroups={summary['keygroups']}\tsamples={summary['samples']}\tbytes={summary['selected_bytes']}\t"
        f"unique_audio={summary['unique_audio']}\tduplicate_groups={summary['duplicate_groups']}"
    )
    for paths in report["duplicate_audio_groups"]:
        print("DUPLICATE\t" + "\t".join(paths))
    if report_path is not None:
        destination = report_path.expanduser().resolve()
        if destination.exists() and not force_report:
            raise FileExistsError(f"inspection report exists; pass --force-report to replace: {destination}")
        _write_json_atomic(destination, report)
        print(f"REPORT\t{destination}")
    return 1 if summary["failures"] or summary["duplicate_groups"] else 0


def build_batch(settings: Settings, batch: Batch, *, force: bool) -> None:
    for index, instrument in enumerate(batch.instruments, 1):
        selected = selected_wav_map(instrument)
        groups, _ = place_sample_groups(
            discover_samples(
                instrument.source, instrument.velocity_preset, set(selected)
            ),
            root_shift=instrument.root_shift,
            root_target=instrument.root_target,
        )
        program_path, data_path = artifact_paths(settings, batch, instrument)
        if force:
            program_path.unlink(missing_ok=True)
            if data_path.exists():
                shutil.rmtree(data_path)
        header, program = build_program(settings.template, groups, instrument.name)
        write_program(header, program, groups, program_path, force=force)
        print(f"BUILT\t{index}/{len(batch.instruments)}\t{instrument.category}/{instrument.name}")


def validate_batch(settings: Settings, batch: Batch, *, location: str) -> None:
    seen: dict[str, list[str]] = {}
    total = 0
    for instrument in batch.instruments:
        program, data = (
            artifact_paths(settings, batch, instrument)
            if location == "artifacts"
            else installed_paths(batch, instrument)
        )
        counts = _validate_copy(program, data, selected_wav_map(instrument))
        total += counts["samples"]
        for name, path in wav_map(data).items():
            seen.setdefault(sha256(path), []).append(
                f"{instrument.category}/{instrument.name}/{name}"
            )
        print(
            f"VALID\t{instrument.category}/{instrument.name}\t"
            f"keygroups={counts['keygroups']}\tsamples={counts['samples']}"
        )
    duplicates = [paths for paths in seen.values() if len(paths) > 1]
    if duplicates:
        raise ValueError(f"batch contains {len(duplicates)} duplicate audio groups")
    print(
        f"SUMMARY\tlocation={location}\tprograms={len(batch.instruments)}\t"
        f"samples={total}\tunique_audio={len(seen)}"
    )


def _write_json_atomic(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.",
            delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _copy_data_resumable(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    expected = wav_map(source)
    existing = wav_map(destination)
    extra = set(existing) - set(expected)
    if extra:
        raise ValueError(f"unexpected files in partial ProgramData: {sorted(extra)[:3]}")
    for name, source_file in expected.items():
        target = destination / name
        if target.is_file() and target.stat().st_size > 0:
            if sha256(source_file) == sha256(target):
                continue
        copy_file_durable(source_file, target)


def _central_preflight(instrument: Instrument) -> None:
    if instrument.install_mode == "copy":
        return
    if not instrument.vendor_programs_checked:
        raise ValueError(
            f"{instrument.name}: relocation/removal requires vendor_programs_checked=true"
        )
    assert instrument.centralized is not None
    if not instrument.centralized.is_dir():
        raise FileNotFoundError(instrument.centralized)
    vendor_files = [
        path for path in instrument.centralized.rglob("*")
        if path.is_file() and path.suffix.lower() in {".xpm", ".xpn"}
    ]
    if vendor_files:
        raise ValueError(f"{instrument.name}: vendor program inside centralized folder")


def _remove_empty_parents(path: Path, stop: Path) -> None:
    current = path.parent
    while current != stop and current.is_relative_to(stop):
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


def install_batch(settings: Settings, batch: Batch, *, execute: bool) -> None:
    if not execute:
        for instrument in batch.instruments:
            program, _ = installed_paths(batch, instrument)
            print(
                f"PLAN\t{instrument.install_mode}\t{instrument.category}/"
                f"{instrument.name}\t{program}"
            )
        print("Dry install plan only; pass --execute to modify MPC media.")
        return

    # Complete all artifact and central preflight checks before modifying media.
    for instrument in batch.instruments:
        program, data = artifact_paths(settings, batch, instrument)
        _validate_copy(program, data, selected_wav_map(instrument))
        target_program, target_data = installed_paths(batch, instrument)
        if target_program.is_file() and target_data.is_dir():
            _validate_copy(target_program, target_data, selected_wav_map(instrument))
            continue
        if target_data.is_dir() and instrument.install_mode == "relocate":
            okay, reason = compare_wavs(instrument.source, target_data)
            if not okay:
                raise ValueError(f"{instrument.name} partial ProgramData: {reason}")
            continue
        _central_preflight(instrument)

    state_path = (
        settings.artifacts_root / ".install-state" / f"{batch.manifest_path.stem}.json"
    )
    completed: list[str] = []
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        completed = list(state.get("completed", []))

    for index, instrument in enumerate(batch.instruments, 1):
        identity = f"{instrument.category}/{instrument.name}"
        artifact_program, artifact_data = artifact_paths(settings, batch, instrument)
        target_program, target_data = installed_paths(batch, instrument)
        if target_program.is_file() and target_data.is_dir():
            _validate_copy(target_program, target_data, selected_wav_map(instrument))
            if identity not in completed:
                completed.append(identity)
                _write_json_atomic(state_path, {"completed": completed})
            print(f"SKIP_VALID\t{index}/{len(batch.instruments)}\t{identity}")
            continue
        if target_program.exists():
            raise ValueError(f"partial install has XPM without valid ProgramData: {target_program}")
        target_program.parent.mkdir(parents=True, exist_ok=True)
        if instrument.install_mode == "relocate":
            assert instrument.centralized is not None
            if target_data.exists():
                okay, reason = compare_wavs(instrument.source, target_data)
                if not okay:
                    raise ValueError(f"{instrument.name} partial ProgramData: {reason}")
            else:
                okay, reason = compare_wavs(instrument.source, instrument.centralized)
                if not okay:
                    raise ValueError(f"{instrument.name} centralized: {reason}")
                os.replace(instrument.centralized, target_data)
        else:
            _copy_data_resumable(artifact_data, target_data)
        copy_file_durable(artifact_program, target_program)
        _validate_copy(target_program, target_data, selected_wav_map(instrument))
        if instrument.install_mode == "replace_corrupt":
            assert instrument.centralized is not None
            central_files = wav_map(instrument.centralized)
            if not central_files or any(path.stat().st_size != 0 for path in central_files.values()):
                raise ValueError(
                    f"{instrument.name}: refusing to remove non-empty centralized data"
                )
            shutil.rmtree(instrument.centralized)
        if identity not in completed:
            completed.append(identity)
        _write_json_atomic(state_path, {"completed": completed})
        print(f"INSTALLED\t{index}/{len(batch.instruments)}\t{identity}")
    validate_batch(settings, batch, location="installed")


def clean_batch(settings: Settings, batch: Batch, *, execute: bool) -> None:
    """Remove only generated artifacts named by the manifest."""
    targets: list[Path] = []
    for instrument in batch.instruments:
        targets.extend(artifact_paths(settings, batch, instrument))
    for target in targets:
        print(f"{'REMOVE' if execute else 'PLAN_REMOVE'}\t{target}")
        if not execute:
            continue
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
    state_path = (
        settings.artifacts_root / ".install-state" / f"{batch.manifest_path.stem}.json"
    )
    if execute and state_path.exists():
        state_path.unlink()
    if not execute:
        print("Dry cleanup plan only; pass --execute to remove generated artifacts.")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("config.local.toml"))
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("inspect", "build", "validate", "install", "clean"):
        child = subparsers.add_parser(command)
        child.add_argument("manifest", type=Path)
        if command == "build":
            child.add_argument("--force", action="store_true")
        elif command == "validate":
            child.add_argument(
                "--location", choices=("artifacts", "installed"), default="artifacts"
            )
        elif command == "install":
            child.add_argument("--execute", action="store_true")
        elif command == "inspect":
            child.add_argument("--report", type=Path, help="write a machine-readable preflight report")
            child.add_argument("--force-report", action="store_true", help="replace the named report")
        elif command == "clean":
            child.add_argument("--execute", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    settings = load_settings(args.config.resolve())
    batch = load_batch(args.manifest.resolve(), settings)
    if args.command == "inspect":
        return inspect_batch(settings, batch, args.report, force_report=args.force_report)
    if args.command == "build":
        build_batch(settings, batch, force=args.force)
    elif args.command == "validate":
        validate_batch(settings, batch, location=args.location)
    elif args.command == "install":
        install_batch(settings, batch, execute=args.execute)
    elif args.command == "clean":
        clean_batch(settings, batch, execute=args.execute)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, FileExistsError, KeyError, ValueError, wave.Error) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2)
