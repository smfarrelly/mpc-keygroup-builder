"""Cross-reference plugin metadata, controller captures, and core recipes."""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import shutil
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any

from . import capture_core


PRIORITIES = {"P0", "P1", "P2", "P3"}


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _contained(root: Path, relative: str, label: str) -> Path:
    path = Path(relative)
    if path.is_absolute():
        raise ValueError(f"{label} must be relative: {relative}")
    target = (root / path).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"{label} escapes target directory: {relative}") from error
    return target


def load_targets(path: Path) -> dict[str, Any]:
    path = path.expanduser().resolve()
    with path.open("rb") as stream:
        document = tomllib.load(stream)
    if document.get("schema_version") != 1:
        raise ValueError(f"{path}: plugin evidence targets require schema_version=1")
    if not isinstance(document.get("name"), str) or not document["name"].strip():
        raise ValueError(f"{path}: targets require name")
    plugins = document.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        raise ValueError(f"{path}: targets require [[plugins]]")
    ids = []
    for index, row in enumerate(plugins, 1):
        context = f"{path}: plugin {index}"
        if not isinstance(row, dict):
            raise ValueError(f"{context} must be a table")
        for field in ("id", "name", "purpose"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f"{context} requires {field}")
        ids.append(row["id"])
        aliases = row.get("aliases")
        captures = row.get("capture_names")
        if not isinstance(aliases, list) or not aliases or not all(isinstance(item, str) and item for item in aliases):
            raise ValueError(f"{context} requires string aliases")
        if not isinstance(captures, list) or not all(isinstance(item, str) and item for item in captures):
            raise ValueError(f"{context} capture_names must be a string list")
        if row.get("priority") not in PRIORITIES:
            raise ValueError(f"{context} priority must be one of: {', '.join(sorted(PRIORITIES))}")
        recipe = row.get("core_recipe")
        if recipe is not None and (not isinstance(recipe, str) or not recipe.strip()):
            raise ValueError(f"{context} core_recipe must be a relative path")
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path}: plugin ids must be unique")
    document["source_path"] = str(path)
    return document


def _load_json_list(path: Path, key: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    document = json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))
    rows = document.get(key)
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"{path}: requires {key} list")
    return document, rows


def analyze(targets: dict[str, Any], catalog_path: Path, audit_path: Path) -> dict[str, Any]:
    catalog, plugins = _load_json_list(catalog_path, "plugins")
    audit, captures = _load_json_list(audit_path, "captures")
    catalog_index: dict[str, list[dict[str, Any]]] = {}
    for plugin in plugins:
        name = plugin.get("plugin")
        if isinstance(name, str):
            catalog_index.setdefault(_normalized(name), []).append(plugin)
    capture_index = {
        row.get("name"): row for row in captures if isinstance(row.get("name"), str)
    }
    root = Path(targets["source_path"]).parent
    results = []
    for target in targets["plugins"]:
        aliases = {_normalized(target["name"]), *(_normalized(item) for item in target["aliases"])}
        catalog_matches = []
        for alias in aliases:
            catalog_matches.extend(catalog_index.get(alias, []))
        unique_catalog = {str(item.get("plugin")): item for item in catalog_matches}
        capture_matches = [
            capture_index[name] for name in target["capture_names"] if name in capture_index
        ]
        learned = sum(
            bool(control.get("learned_targets"))
            for capture in capture_matches
            for control in capture.get("controls", [])
            if isinstance(control, dict)
        )
        recipe_report = None
        recipe_error = None
        if target.get("core_recipe"):
            try:
                recipe = capture_core.load_recipe(
                    _contained(root, target["core_recipe"], f"{target['id']} core_recipe")
                )
                recipe_report = {
                    "id": recipe["id"], "capture_name": recipe["capture_name"],
                    "controls": len(recipe["controls"]),
                    "preserve_mix_faders": recipe["preserve_mix_faders"],
                }
                if recipe["capture_name"] not in target["capture_names"]:
                    recipe_error = "core recipe capture is not declared by target"
            except (FileNotFoundError, ValueError, tomllib.TOMLDecodeError) as error:
                recipe_error = str(error)
        has_catalog = bool(unique_catalog)
        has_capture = bool(capture_matches)
        has_learn = learned > 0
        has_recipe = recipe_report is not None and recipe_error is None
        if has_capture and has_learn and has_recipe:
            status = "captured-core-ready" if not has_catalog else "full-evidence-core-ready"
            next_action = "run the compact-versus-full live comparison and record a hardware verdict"
        elif has_capture and has_learn:
            status = "capture-ready"
            next_action = "curate a compact core recipe from the verified captured targets"
        elif has_catalog:
            status = "catalog-ready"
            next_action = "map one useful probe, export the Components mode, and save paired MPC Learn evidence"
        else:
            status = "evidence-missing"
            next_action = "load the plugin, export a named Components mode, learn one useful probe, and save/copy the MPC project capture"
        if recipe_error:
            status = "recipe-invalid"
            next_action = f"repair core recipe: {recipe_error}"
        results.append({
            **target,
            "catalog_plugins": sorted(unique_catalog),
            "catalog_control_count": sum(int(item.get("control_count", 0)) for item in unique_catalog.values()),
            "captures": [item.get("name") for item in capture_matches],
            "captured_enabled_controls": sum(int(item.get("enabled_count", 0)) for item in capture_matches),
            "learned_controls": learned,
            "core_recipe_evidence": recipe_report,
            "recipe_error": recipe_error,
            "status": status, "next_action": next_action,
        })
    counts: dict[str, int] = {}
    for row in results:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    return {
        "schema_version": 1, "kind": "mpc-plugin-evidence-readiness",
        "name": targets["name"], "target_path": targets["source_path"],
        "catalog_path": str(catalog_path.expanduser().resolve()),
        "audit_path": str(audit_path.expanduser().resolve()),
        "catalog_source_root": catalog.get("source_root"),
        "project": audit.get("project"),
        "summary": {"targets": len(results), "statuses": dict(sorted(counts.items()))},
        "plugins": sorted(results, key=lambda item: (item["priority"], item["name"].casefold())),
        "boundary": "Missing local metadata is an evidence gap, not evidence that a plugin is uninstalled or unavailable on the MPC.",
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [f"# {report['name']}", "", report["boundary"], "", "## Readiness", ""]
    for row in report["plugins"]:
        catalog = ", ".join(row["catalog_plugins"]) or "none"
        captures = ", ".join(row["captures"]) or "none"
        recipe = row["core_recipe_evidence"]
        recipe_text = f"{recipe['id']} ({recipe['controls']} controls)" if recipe else "none"
        lines.extend((
            f"### {row['priority']} — {row['name']} — {row['status']}", "",
            row["purpose"], "",
            f"- Catalog: {catalog}; {row['catalog_control_count']} controls.",
            f"- Captures: {captures}; {row['captured_enabled_controls']} enabled controls; {row['learned_controls']} with saved targets.",
            f"- Core recipe: {recipe_text}.",
            f"- Next: {row['next_action']}.", "",
        ))
    return "\n".join(lines)


def render_csv(report: dict[str, Any]) -> str:
    fields = (
        "priority", "id", "name", "status", "catalog_control_count",
        "captured_enabled_controls", "learned_controls", "next_action",
    )
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(report["plugins"])
    return stream.getvalue()


def write_report(
    report: dict[str, Any], output: Path, *, force: bool = False,
    protected_paths: tuple[Path, ...] = (),
) -> Path:
    output = output.expanduser().absolute()
    if output.is_symlink():
        raise ValueError(f"refusing symbolic-link plugin evidence output: {output}")
    resolved_output = output.resolve(strict=False)
    for source in protected_paths:
        source = source.expanduser().resolve()
        if source == resolved_output or source.is_relative_to(resolved_output):
            raise ValueError(f"plugin evidence output must not contain input: {source}")
    if output.exists() and not force:
        raise FileExistsError(f"plugin evidence output already exists: {output}")
    if output.exists():
        receipt = output / "plugin-evidence.json"
        if not output.is_dir() or receipt.is_symlink() or not receipt.is_file():
            raise ValueError(f"refusing to replace unrecognized plugin evidence output: {output}")
        previous = json.loads(receipt.read_text(encoding="utf-8"))
        if previous.get("kind") != "mpc-plugin-evidence-readiness":
            raise ValueError(f"refusing to replace unrecognized plugin evidence output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        (staging / "plugin-evidence.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        (staging / "PLUGIN_EVIDENCE.md").write_text(render_markdown(report), encoding="utf-8")
        (staging / "plugin-evidence.csv").write_text(render_csv(report), encoding="utf-8")
        if output.exists():
            shutil.rmtree(output)
        os.replace(staging, output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("targets", type=Path)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--capture-audit", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv or sys.argv[1:])
    report = analyze(load_targets(args.targets), args.catalog, args.capture_audit)
    write_report(
        report, args.output, force=args.force,
        protected_paths=(args.targets, args.catalog, args.capture_audit),
    )
    print(f"Wrote: {args.output.resolve()}")
    print("; ".join(f"{status}={count}" for status, count in report["summary"]["statuses"].items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
