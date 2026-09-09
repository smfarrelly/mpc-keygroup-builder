"""Compile compact plugin cores from Launch Control and MPC Learn evidence."""

from __future__ import annotations

import argparse
import csv
import html
import io
import json
import os
import shutil
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any


def load_recipe(path: Path) -> dict[str, Any]:
    path = path.expanduser().resolve()
    with path.open("rb") as stream:
        document = tomllib.load(stream)
    if document.get("schema_version") != 1:
        raise ValueError(f"{path}: capture core recipe requires schema_version=1")
    for field in ("id", "name", "capture_name", "description", "friction_removed"):
        if not isinstance(document.get(field), str) or not document[field].strip():
            raise ValueError(f"{path}: recipe requires {field}")
    if type(document.get("preserve_mix_faders")) is not bool:
        raise ValueError(f"{path}: preserve_mix_faders must be true or false")
    controls = document.get("controls")
    if not isinstance(controls, list) or not 1 <= len(controls) <= 8:
        raise ValueError(f"{path}: recipe requires 1..8 [[controls]] entries")
    endpoints = []
    for index, row in enumerate(controls, 1):
        if not isinstance(row, dict):
            raise ValueError(f"{path}: control {index} must be a table")
        for field in ("endpoint", "expected_label", "expected_target", "role", "reason"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f"{path}: control {index} requires {field}")
        endpoints.append(row["endpoint"])
    if len(endpoints) != len(set(endpoints)):
        raise ValueError(f"{path}: control endpoints must be unique")
    document["source_path"] = str(path)
    return document


def load_audit(path: Path) -> dict[str, Any]:
    path = path.expanduser().resolve()
    document = json.loads(path.read_text(encoding="utf-8"))
    captures = document.get("captures")
    if not isinstance(captures, list):
        raise ValueError(f"{path}: audit requires captures list")
    for index, capture in enumerate(captures, 1):
        if not isinstance(capture, dict) or not isinstance(capture.get("name"), str):
            raise ValueError(f"{path}: capture {index} requires a name")
        if not isinstance(capture.get("controls"), list):
            raise ValueError(f"{path}: capture {index} requires controls")
    document["source_path"] = str(path)
    return document


def analyze(audit: dict[str, Any], recipes: list[dict[str, Any]]) -> dict[str, Any]:
    if not recipes:
        raise ValueError("at least one capture core recipe is required")
    capture_index = {item["name"]: item for item in audit["captures"]}
    if len(capture_index) != len(audit["captures"]):
        raise ValueError("audit capture names must be unique")
    ids = [recipe["id"] for recipe in recipes]
    if len(ids) != len(set(ids)):
        raise ValueError("capture core recipe ids must be unique")
    results = []
    all_errors: list[str] = []
    all_warnings: list[str] = []
    for recipe in recipes:
        errors: list[str] = []
        warnings: list[str] = []
        capture = capture_index.get(recipe["capture_name"])
        if capture is None:
            errors.append(f"capture not found: {recipe['capture_name']}")
            controls: list[dict[str, Any]] = []
            mix_faders: list[dict[str, Any]] = []
            source_capture = None
        else:
            source_capture = {
                "name": capture["name"], "path": capture.get("path"),
                "sha256": capture.get("sha256"),
                "enabled_count": capture.get("enabled_count"),
                "matched_control_count": capture.get("matched_control_count"),
            }
            by_endpoint = {
                row.get("control"): row
                for row in capture["controls"] if isinstance(row, dict)
            }
            controls = []
            for declared in recipe["controls"]:
                source = by_endpoint.get(declared["endpoint"])
                if source is None:
                    errors.append(f"{declared['endpoint']}: endpoint missing from capture")
                    continue
                if source.get("label") != declared["expected_label"]:
                    errors.append(
                        f"{declared['endpoint']}: label changed from "
                        f"{declared['expected_label']!r} to {source.get('label')!r}"
                    )
                targets = source.get("learned_targets", [])
                if declared["expected_target"] not in targets:
                    errors.append(
                        f"{declared['endpoint']}: expected learned target missing: "
                        f"{declared['expected_target']}"
                    )
                if source.get("channel_source") != "encoded":
                    warnings.append(
                        f"{declared['endpoint']}: channel is {source.get('channel_source')}, "
                        "not directly encoded"
                    )
                channel, cc = source.get("channel"), source.get("number")
                if type(channel) is not int or not 1 <= channel <= 16:
                    errors.append(f"{declared['endpoint']}: invalid captured channel {channel!r}")
                if type(cc) is not int or not 0 <= cc <= 127:
                    errors.append(f"{declared['endpoint']}: invalid captured CC {cc!r}")
                controls.append({
                    **declared,
                    "channel": channel, "cc": cc,
                    "channel_source": source.get("channel_source"),
                    "learned_targets": targets,
                })
            mix_faders = []
            if recipe["preserve_mix_faders"]:
                mix_faders = [
                    {
                        "endpoint": row.get("control"), "label": row.get("label"),
                        "channel": row.get("channel"), "cc": row.get("number"),
                        "channel_source": row.get("channel_source"),
                        "learned_targets": row.get("learned_targets", []),
                    }
                    for row in capture["controls"]
                    if isinstance(row, dict) and str(row.get("control", "")).startswith("fader-")
                ]
                if len(mix_faders) != 8:
                    errors.append(f"persistent mix requires 8 captured faders, found {len(mix_faders)}")
                for row in mix_faders:
                    if type(row["channel"]) is not int or not 1 <= row["channel"] <= 16:
                        errors.append(f"{row['endpoint']}: invalid captured channel {row['channel']!r}")
                    if type(row["cc"]) is not int or not 0 <= row["cc"] <= 127:
                        errors.append(f"{row['endpoint']}: invalid captured CC {row['cc']!r}")
                fader_channels = {row["channel"] for row in mix_faders}
                if len(fader_channels) != 1:
                    errors.append("persistent mix faders must use one channel")
                plugin_channels = {row["channel"] for row in controls}
                if fader_channels & plugin_channels:
                    errors.append("persistent mix faders must be isolated from plugin controls")
                unmatched = [row["endpoint"] for row in mix_faders if not row["learned_targets"]]
                if unmatched:
                    warnings.append(
                        "mix faders without saved Learn targets: " + ", ".join(unmatched)
                    )
            retained_endpoints = {
                *(row["endpoint"] for row in controls),
                *(row["endpoint"] for row in mix_faders),
            }
            omitted_controls = [
                {
                    "endpoint": row.get("control"), "label": row.get("label"),
                    "channel": row.get("channel"), "cc": row.get("number"),
                    "channel_source": row.get("channel_source"),
                    "learned_targets": row.get("learned_targets", []),
                }
                for row in capture["controls"]
                if isinstance(row, dict) and row.get("control") not in retained_endpoints
            ]
        if capture is None:
            omitted_controls = []
        result = {
            "id": recipe["id"], "name": recipe["name"],
            "description": recipe["description"],
            "friction_removed": recipe["friction_removed"],
            "capture_name": recipe["capture_name"],
            "source_capture": source_capture,
            "selected_controls": controls,
            "persistent_mix_faders": mix_faders,
            "omitted_controls": omitted_controls,
            "omitted_enabled_controls": len(omitted_controls) if capture is not None else None,
            "errors": sorted(set(errors)), "warnings": sorted(set(warnings)),
            "hardware_status": "pending",
        }
        all_errors.extend(f"{recipe['id']}: {item}" for item in errors)
        all_warnings.extend(f"{recipe['id']}: {item}" for item in warnings)
        results.append(result)
    return {
        "schema_version": 1, "kind": "mpc-captured-plugin-cores",
        "audit_path": audit["source_path"],
        "summary": {
            "cores": len(results), "errors": len(set(all_errors)),
            "warnings": len(set(all_warnings)),
            "plugin_controls": sum(len(item["selected_controls"]) for item in results),
            "persistent_mix_faders": sum(len(item["persistent_mix_faders"]) for item in results),
        },
        "cores": results,
        "errors": sorted(set(all_errors)), "warnings": sorted(set(all_warnings)),
        "boundary": "The report preserves captured CC and MIDI Learn evidence. It does not write SysEx, alter an MPC project, or prove musical value.",
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Captured plugin performance cores", "",
        f"Cores: {summary['cores']}; selected plugin controls: {summary['plugin_controls']}; "
        f"persistent mix faders: {summary['persistent_mix_faders']}; errors: "
        f"{summary['errors']}; warnings: {summary['warnings']}.", "",
    ]
    for core in report["cores"]:
        lines.extend((f"## {core['name']}", "", core["description"], "", f"Friction removed: {core['friction_removed']}", ""))
        for row in core["selected_controls"]:
            lines.append(
                f"- `{row['endpoint']}` — {row['expected_label']} → "
                f"{row['expected_target']} (ch {row['channel']}, CC {row['cc']}, "
                f"{row['role']}): {row['reason']}"
            )
        lines.extend(("", f"Persistent mix faders: {len(core['persistent_mix_faders'])}; omitted captured controls: {core['omitted_enabled_controls']}.", ""))
        for warning in core["warnings"]:
            lines.append(f"- Warning: {warning}")
        for error in core["errors"]:
            lines.append(f"- Error: {error}")
        lines.append("")
    lines.extend(("## Evidence boundary", "", report["boundary"], ""))
    return "\n".join(lines)


def render_csv(report: dict[str, Any]) -> str:
    fields = ("core", "purpose", "endpoint", "label", "channel", "cc", "target", "role", "evidence")
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for core in report["cores"]:
        for row in core["selected_controls"]:
            writer.writerow({
                "core": core["id"], "purpose": "plugin-core",
                "endpoint": row["endpoint"], "label": row["expected_label"],
                "channel": row["channel"], "cc": row["cc"],
                "target": row["expected_target"], "role": row["role"],
                "evidence": row["channel_source"],
            })
        for row in core["persistent_mix_faders"]:
            writer.writerow({
                "core": core["id"], "purpose": "persistent-mpc-mix",
                "endpoint": row["endpoint"], "label": row["label"],
                "channel": row["channel"], "cc": row["cc"],
                "target": "; ".join(row["learned_targets"]), "role": "mix",
                "evidence": row["channel_source"],
            })
    return stream.getvalue()


def render_edit_csv(report: dict[str, Any]) -> str:
    fields = (
        "core", "action", "endpoint", "current_label", "channel", "cc",
        "target", "role", "channel_evidence",
    )
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for core in report["cores"]:
        for row in core["selected_controls"]:
            writer.writerow({
                "core": core["id"], "action": "keep-plugin-core",
                "endpoint": row["endpoint"], "current_label": row["expected_label"],
                "channel": row["channel"], "cc": row["cc"],
                "target": row["expected_target"], "role": row["role"],
                "channel_evidence": row["channel_source"],
            })
        for row in core["persistent_mix_faders"]:
            writer.writerow({
                "core": core["id"], "action": "keep-mpc-mix",
                "endpoint": row["endpoint"], "current_label": row["label"],
                "channel": row["channel"], "cc": row["cc"],
                "target": "; ".join(row["learned_targets"]), "role": "mix",
                "channel_evidence": row["channel_source"],
            })
        for row in core["omitted_controls"]:
            writer.writerow({
                "core": core["id"], "action": "omit-from-core",
                "endpoint": row["endpoint"], "current_label": row["label"],
                "channel": row["channel"], "cc": row["cc"],
                "target": "; ".join(row["learned_targets"]), "role": "reference",
                "channel_evidence": row["channel_source"],
            })
    return stream.getvalue()


def render_checklist(report: dict[str, Any]) -> str:
    lines = ["# Captured core hardware checklist", ""]
    for core in report["cores"]:
        lines.extend((
            f"## {core['name']}", "",
            "- [ ] Preserve/export the original Components mode before editing.",
            "- [ ] Confirm all eight faders still balance the intended MPC mix targets.",
            "- [ ] Compare the compact controls with the original page during a played-in loop jam.",
            "- [ ] Confirm pickup/range behavior and that no unrelated target moves.",
            "- [ ] Save/reload the project and record pass, warn, or fail with listening notes.",
            "",
        ))
    return "\n".join(lines)


def render_html(report: dict[str, Any]) -> str:
    sections = []
    groups = (
        ("top-encoder", "Top encoders"),
        ("middle-encoder", "Middle encoders"),
        ("bottom-encoder", "Bottom encoders"),
        ("fader", "Persistent MPC mix faders"),
        ("upper-button", "Upper buttons"),
        ("lower-button", "Lower buttons"),
    )
    for core in report["cores"]:
        plugin = {row["endpoint"]: row for row in core["selected_controls"]}
        mix = {row["endpoint"]: row for row in core["persistent_mix_faders"]}
        reference = {row["endpoint"]: row for row in core["omitted_controls"]}
        rows = []
        for prefix, title in groups:
            cells = []
            for position in range(1, 9):
                endpoint = f"{prefix}-{position}"
                item = plugin.get(endpoint) or mix.get(endpoint) or reference.get(endpoint)
                if item is None:
                    cells.append(f'<div class="control empty"><b>{html.escape(endpoint)}</b><span>unassigned</span></div>')
                    continue
                is_mix = endpoint in mix
                is_reference = endpoint in reference
                label = item.get("expected_label", item.get("label", ""))
                target = item.get("expected_target") or "; ".join(item.get("learned_targets", [])) or "Learn pending"
                css = "reference" if is_reference else "mix" if is_mix else "plugin"
                cells.append(
                    f'<div class="control {css}"><b>{html.escape(endpoint)}</b>'
                    f'<strong>{html.escape(str(label))}</strong>'
                    f'<span>ch {item.get("channel")} · CC {item.get("cc")}</span>'
                    f'<small>{html.escape(str(target))}</small></div>'
                )
            rows.append(
                f'<section class="row"><h3>{html.escape(title)}</h3>'
                f'<div class="controls">{"".join(cells)}</div></section>'
            )
        warnings = "".join(f"<li>{html.escape(item)}</li>" for item in core["warnings"])
        sections.append(
            f'<article><header><div><p class="eyebrow">Hardware pending · captured evidence</p>'
            f'<h2>{html.escape(core["name"])}</h2><p>{html.escape(core["description"])}</p></div>'
            f'<div class="counts"><b>{len(plugin)}</b> plugin controls<br><b>{len(mix)}</b> mix faders</div></header>'
            f'{"".join(rows)}<p class="friction"><b>Friction removed:</b> {html.escape(core["friction_removed"])}</p>'
            f'{f"<details><summary>{len(core["warnings"])} evidence warnings</summary><ul>{warnings}</ul></details>" if warnings else ""}'
            f'</article>'
        )
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark"><title>Captured Plugin Cores</title><style>
:root{{font-family:Inter,system-ui,sans-serif;color-scheme:dark;--bg:#0d1110;--panel:#161d19;--line:#334038;--text:#edf4ee;--muted:#9caaa1;--plugin:#284b38;--mix:#3c375d}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at 10% 0,#183324,transparent 30rem),var(--bg);color:var(--text)}}main{{max-width:1400px;margin:auto;padding:36px 22px 80px}}h1{{font-size:clamp(2.2rem,6vw,5rem);letter-spacing:-.05em;margin:.2em 0}}.intro{{color:var(--muted);max-width:760px;line-height:1.55}}article{{margin-top:28px;padding:22px;border:1px solid var(--line);border-radius:20px;background:#121815dd}}header{{display:flex;justify-content:space-between;gap:20px;align-items:start}}h2{{font-size:1.8rem;margin:.2em 0}}.eyebrow{{text-transform:uppercase;letter-spacing:.12em;font-size:.7rem;color:#9ee6b1;font-weight:800}}.counts{{text-align:right;color:var(--muted);white-space:nowrap}}.counts b{{color:var(--text);font-size:1.3rem}}.row{{margin-top:18px}}h3{{font-size:.78rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}}.controls{{display:grid;grid-template-columns:repeat(8,minmax(90px,1fr));gap:8px;overflow:auto}}.control{{min-height:118px;border:1px solid var(--line);border-radius:12px;padding:10px;display:flex;flex-direction:column;gap:6px}}.control.plugin{{background:var(--plugin);border-color:#598469}}.control.mix{{background:var(--mix);border-color:#7770a5}}.control.reference{{opacity:.46;border-style:dashed}}.control.empty{{opacity:.18}}.control b{{font-size:.7rem;color:var(--muted)}}.control strong{{font-size:.86rem}}.control span,.control small{{font-size:.72rem;line-height:1.3}}.control small{{color:#c0cbc4}}.friction{{margin-top:20px}}details{{color:#f1cf78}}footer{{margin-top:28px;color:var(--muted);font-size:.82rem}}@media(max-width:850px){{header{{display:block}}.counts{{text-align:left}}.controls{{grid-template-columns:repeat(8,105px)}}}}
</style></head><body><main><p class="eyebrow">Offline · read-only review</p><h1>Captured plugin cores</h1>
<p class="intro">Green controls are the compact plugin surface. Purple faders preserve the MPC internal mix on its isolated channel. Dim controls show captured assignments intentionally omitted from the core; empty cells were not enabled in the capture.</p>
{"".join(sections)}<footer>{html.escape(report["boundary"])}</footer></main></body></html>'''


def write_report(
    report: dict[str, Any], output: Path, *, force: bool = False,
    protected_paths: tuple[Path, ...] = (),
) -> Path:
    output = output.expanduser().absolute()
    if output.is_symlink():
        raise ValueError(f"refusing symbolic-link captured core output: {output}")
    resolved_output = output.resolve(strict=False)
    for protected in protected_paths:
        protected = protected.expanduser().resolve()
        if protected == resolved_output or protected.is_relative_to(resolved_output):
            raise ValueError(f"captured core output must not contain input: {protected}")
    if output.exists() and not force:
        raise FileExistsError(f"captured core output already exists: {output}")
    if output.exists():
        receipt = output / "captured-plugin-cores.json"
        if output.is_symlink() or not output.is_dir() or receipt.is_symlink() or not receipt.is_file():
            raise ValueError(f"refusing to replace unrecognized captured core output: {output}")
        previous = json.loads(receipt.read_text(encoding="utf-8"))
        if previous.get("kind") != "mpc-captured-plugin-cores":
            raise ValueError(f"refusing to replace unrecognized captured core output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        (staging / "captured-plugin-cores.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        (staging / "CAPTURED_CORES.md").write_text(render_markdown(report), encoding="utf-8")
        (staging / "captured-controls.csv").write_text(render_csv(report), encoding="utf-8")
        (staging / "COMPONENTS_EDIT_PLAN.csv").write_text(render_edit_csv(report), encoding="utf-8")
        (staging / "HARDWARE_CHECKLIST.md").write_text(render_checklist(report), encoding="utf-8")
        (staging / "CORE_COMPANION.html").write_text(render_html(report), encoding="utf-8")
        if output.exists():
            shutil.rmtree(output)
        os.replace(staging, output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit", type=Path)
    parser.add_argument("recipes", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv or sys.argv[1:])
    report = analyze(load_audit(args.audit), [load_recipe(path) for path in args.recipes])
    write_report(
        report, args.output, force=args.force,
        protected_paths=(args.audit, *args.recipes),
    )
    summary = report["summary"]
    print(f"Wrote: {args.output.resolve()}")
    print(
        f"Cores: {summary['cores']}; plugin controls: {summary['plugin_controls']}; "
        f"mix faders: {summary['persistent_mix_faders']}; errors: {summary['errors']}; "
        f"warnings: {summary['warnings']}"
    )
    return 2 if summary["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
