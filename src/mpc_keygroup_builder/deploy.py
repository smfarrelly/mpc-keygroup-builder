"""Plan or apply an additive, checksum-verified MPC SD-card deployment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .candidates import load_manifest


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _program_data(program: Path) -> list[Path]:
    prefix = "".join(c for c in program.stem.casefold() if c.isalnum())
    matches = []
    for item in program.parent.iterdir():
        normalized = "".join(c for c in item.name.casefold() if c.isalnum())
        if item.is_dir() and normalized.startswith(prefix) and "programdata" in normalized:
            for path in item.rglob("*"):
                if path.is_symlink():
                    raise ValueError(
                        f"companion ProgramData may not contain symbolic links: {path}"
                    )
                if path.is_file():
                    matches.append(path)
    return sorted(matches)


def _contained_path(
    root: Path, value: object, label: str, *, reject_symlinks: bool = False
) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a nonempty relative path")
    relative = Path(value)
    if relative.is_absolute():
        raise ValueError(f"{label} must be a relative path: {value!r}")
    root = root.expanduser().resolve()
    unresolved = root / relative
    if reject_symlinks:
        current = root
        for part in relative.parts:
            current /= part
            if current.is_symlink():
                raise ValueError(f"{label} may not contain symbolic links: {value!r}")
    path = unresolved.resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ValueError(f"{label} escapes its root: {value!r}") from error
    return path


def build_plan(
    manifest: Path, local_root: Path, target_root: Path, *, include_audio: bool = False
) -> list[dict[str, object]]:
    document = load_manifest(manifest)
    local_root = local_root.expanduser().resolve()
    target_root = target_root.expanduser().resolve()
    plan: list[dict[str, object]] = []
    for candidate in document["candidates"]:
        relative = candidate["sd_path"]
        source = _contained_path(local_root, relative, "candidate sd_path")
        target = _contained_path(target_root, relative, "candidate sd_path")
        if not source.is_file():
            raise FileNotFoundError(f"local program is missing: {source}")
        files = [source]
        if include_audio:
            files.extend(_program_data(source))
        for item in files:
            item_relative = (
                Path(relative)
                if item == source
                else Path(relative).parent / item.relative_to(source.parent)
            )
            item_target = (
                target
                if item == source
                else _contained_path(
                    target_root, item_relative.as_posix(), "companion audio path"
                )
            )
            source_hash = sha256(item)
            target_hash = sha256(item_target) if item_target.is_file() else None
            action = "unchanged" if source_hash == target_hash else ("replace" if target_hash else "create")
            plan.append({
                "candidate": candidate["id"],
                "kind": "program" if item == source else "audio",
                "source": str(item.resolve()),
                "target": str(item_target),
                "relative": str(item_relative),
                "local_root": str(local_root),
                "target_root": str(target_root),
                "bytes": item.stat().st_size,
                "source_sha256": source_hash,
                "target_sha256_before": target_hash,
                "action": action,
            })
    return plan


def apply_plan(plan: list[dict[str, object]], backup_dir: Path | None = None) -> None:
    replacements = [item for item in plan if item["action"] == "replace"]
    if replacements and backup_dir is None:
        raise ValueError("--backup-dir is required when deployment would replace files")
    for item in plan:
        if item["action"] == "unchanged":
            continue
        relative = item["relative"]
        source = _contained_path(
            Path(str(item["local_root"])),
            relative,
            "planned source path",
            reject_symlinks=True,
        )
        target = _contained_path(
            Path(str(item["target_root"])), relative, "planned target path"
        )
        if item["action"] == "replace":
            target = _contained_path(
                Path(str(item["target_root"])), relative, "replacement target path"
            )
            backup = backup_dir / str(item["relative"])
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup)
            if sha256(backup) != item["target_sha256_before"]:
                raise OSError(f"backup verification failed: {target}")
        target = _contained_path(
            Path(str(item["target_root"])), relative, "deployment target path"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target = _contained_path(
            Path(str(item["target_root"])), relative, "deployment target path"
        )
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}-", dir=target.parent)
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            shutil.copy2(source, temporary)
            if sha256(temporary) != item["source_sha256"]:
                raise OSError(f"copy verification failed: {source}")
            target = _contained_path(
                Path(str(item["target_root"])), relative, "deployment target path"
            )
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        target = _contained_path(
            Path(str(item["target_root"])), relative, "deployment target path"
        )
        if sha256(target) != item["source_sha256"]:
            raise OSError(f"target verification failed: {target}")


def deployment_report(plan: list[dict[str, object]], applied: bool) -> dict[str, object]:
    return {
        "format": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "applied": applied,
        "deletes": 0,
        "files": plan,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--local-root", type=Path, required=True)
    parser.add_argument("--target-root", type=Path, required=True)
    parser.add_argument("--include-audio", action="store_true", help="include companion ProgramData files")
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    plan = build_plan(args.manifest, args.local_root, args.target_root, include_audio=args.include_audio)
    if args.apply:
        apply_plan(plan, args.backup_dir)
    report = deployment_report(plan, args.apply)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for item in plan:
        print(f"{str(item['action']).upper():9} {item['relative']}")
    print("Applied and verified." if args.apply else "Dry run only; no files changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
