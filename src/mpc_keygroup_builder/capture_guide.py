"""Join saved controller assignments to preset and native Q-Link evidence."""

from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path
from string import Template
from typing import Any
from urllib.parse import quote


def enrich_control(
    source: dict[str, Any], target: str, audit: dict[str, Any], catalog: dict[str, Any] | None,
) -> dict[str, Any]:
    """Only attribute native controls after matching the Learn row, track, ID and name."""
    evidence = {"status": "older-audit", "plugin": None, "track": None, "preset": None,
                "preset_edited": None, "parameter": None, "q_links": []}
    if "learned_rows" not in source:
        return evidence
    matches = [r for r in source["learned_rows"] if r.get("name") == target]
    if len(matches) != 1 or matches[0].get("target_count") != 1:
        return {**evidence, "status": "ambiguous-target" if matches else "no-target"}
    match = matches[0]
    parameter = match.get("parameter")
    track = match.get("track")
    if type(parameter) is not int or not isinstance(track, str):
        return {**evidence, "status": "incomplete-target"}
    evidence.update(track=track, parameter=parameter)
    tracks = [r for r in audit.get("plugin_tracks", []) if r["track"] == track]
    if len(tracks) != 1:
        return {**evidence, "status": "unresolved-track"}
    evidence.update({key: tracks[0].get(key) for key in ("plugin", "preset", "preset_edited")})
    plugins = [p for p in (catalog or {}).get("plugins", []) if p.get("plugin") == evidence["plugin"]]
    if len(plugins) != 1:
        return {**evidence, "status": "catalog-ambiguous" if plugins else "catalog-unavailable"}
    prefix = f"{track} ("
    if not (target.startswith(prefix) and target.endswith(")")):
        return {**evidence, "status": "catalog-unmatched"}
    name = target[len(prefix):-1]
    controls = [r for r in plugins[0].get("controls", [])
                if type(r.get("mpc_parameter")) is int and r["mpc_parameter"] == parameter
                and name in (r.get("name"), *r.get("aliases", []))]
    if len(controls) != 1:
        return {**evidence, "status": "catalog-ambiguous" if controls else "catalog-unmatched"}
    links = controls[0].get("q_links")
    if not isinstance(links, list) or not all(isinstance(item, str) for item in links):
        links = []
    return {**evidence, "status": "skin-match", "q_links": links}


_STATUS = {
    "older-audit": "Regenerate the Learn audit to see preset and parameter evidence.",
    "ambiguous-target": "Multiple saved targets. Native placement is unresolved.",
    "no-target": "Expected Learn target missing.",
    "incomplete-target": "Saved target lacks a track or parameter ID.",
    "unresolved-track": "Saved track could not be uniquely identified.",
    "catalog-unavailable": "No matching plugin skin in the supplied catalog.",
    "catalog-ambiguous": "More than one catalog entry matches.",
    "catalog-unmatched": "Skin name and parameter ID could not be matched.",
}
_GROUPS = (
    ("top-encoder", "Top encoders"), ("middle-encoder", "Middle encoders"),
    ("bottom-encoder", "Bottom encoders"), ("fader", "Persistent MPC mix faders"),
    ("upper-button", "Upper buttons"), ("lower-button", "Lower buttons"),
)


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def note_manifest(report: dict) -> dict | None:
    """Bind listening notes to the exact XPJ, controller modes and selected controls."""
    project_hash = report.get("project_sha256")
    if not isinstance(project_hash, str) or not re.fullmatch("[0-9a-f]{64}", project_hash):
        return None
    controls = []
    for core in report["cores"]:
        capture_hash = (core["source_capture"] or {}).get("sha256")
        if core["errors"] or not isinstance(capture_hash, str) or not re.fullmatch("[0-9a-f]{64}", capture_hash):
            return None
        for row in core["selected_controls"]:
            evidence = row.get("evidence") or {}
            controls.append({
                "key": f'{core["id"]}-{row["endpoint"]}', "mode": core["capture_name"],
                "mode_sha256": capture_hash, "endpoint": row["endpoint"],
                "target": row["expected_target"], "channel": row["channel"], "cc": row["cc"],
                "plugin": evidence.get("plugin"), "preset": evidence.get("preset"),
            })
    identity = {"project_sha256": project_hash, "controls": sorted(controls, key=lambda r: r["key"])}
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return {**identity, "fingerprint": digest, "project": report.get("project_name")}


def _card(core: dict, row: dict, position: int, mix: bool) -> str:
    label = row["label"] if mix else row["expected_label"]
    evidence = row.get("evidence", {})
    targets = row["learned_targets"]
    destinations = "".join(f"<li>{esc(item)}</li>" for item in targets)
    target_html = f"<ul>{destinations}</ul>" if targets else "<p>No saved Learn target</p>"
    placement = ""
    if evidence:
        links = evidence["q_links"]
        if links:
            placement = "<p>Plugin skin<br>" + "<br>".join(esc(link) for link in links) + "</p>"
        else:
            placement = f'<p>{esc(_STATUS.get(evidence["status"], "Skin contains no native Q-Link placement."))}</p>'
        if evidence["parameter"] is not None:
            placement = f'<p>XPJ parameter {esc(evidence["parameter"])}</p>' + placement
    source = row["channel_source"]
    channel_note = "" if source == "encoded" else f" · {esc(source or 'unknown source')}"
    element_id = esc(f'{core["id"]}-{row["endpoint"]}')
    return (f'<div class="card {"mix" if mix else "plugin"}" id="{element_id}"><small>{position}</small>'
            f'<strong>{esc(label)}</strong><p>Ch {esc(row["channel"])} · CC {esc(row["cc"])}{channel_note}</p>'
            f'{target_html}{placement}</div>')


def render_html(report: dict[str, Any]) -> str:
    """Write a self-contained page with deep links, useful with scripts disabled."""
    sections, nav = [], []
    for core in report["cores"]:
        core_id = esc(core["id"])
        nav.append(f'<a href="#{quote(core["id"], safe="")}">{esc(core["name"])}</a>')
        selected = {r["endpoint"]: r for r in core["selected_controls"]}
        faders = {r["endpoint"]: r for r in core["persistent_mix_faders"]}
        other = set(core.get("other_enabled_endpoints", []))
        groups = []
        for prefix, title in _GROUPS:
            entries = []
            if not any(k.startswith(prefix + "-") for k in (*selected, *faders)):
                continue
            for i in range(1, 9):
                key = f"{prefix}-{i}"
                row = selected.get(key) or faders.get(key)
                if row:
                    entries.append(_card(core, row, i, key in faders))
                else:
                    note = "Outside core" if key in other else "No captured assignment"
                    entries.append(f'<div class="blank"><small>{i}</small>{note}</div>')
            groups.append(f'<section><h3>{title}</h3><div class="strip">{"".join(entries)}</div></section>')
        presets = []
        for row in selected.values():
            e = row.get("evidence") or {}
            if e.get("plugin"):
                edited = " (edited)" if e["preset_edited"] is True else ""
                text = f'{e["plugin"]} · {e["track"]} · {e.get("preset") or "Preset unknown"}{edited}'
                if text not in presets:
                    presets.append(text)
        source = core.get("source_capture") or {}
        details = "".join(f"<li>{esc(x)}</li>" for x in (*core["errors"], *core["warnings"]))
        diagnostics = f"<details><summary>Mapping findings</summary><ul>{details}</ul></details>" if details else ""
        sections.append(
            f'<article id="{core_id}"><h2>{esc(core["name"])}</h2><p>{esc(" / ".join(presets))}</p>'
            f'<p>Components mode <b>{esc(core["capture_name"])}</b> · {len(selected)} selected controls</p>'
            + ("<p>Listen to each macro on the saved preset to identify its musical effect.</p>"
               if any(r["role"] == "macro" for r in selected.values()) else "")
            + "".join(groups) + diagnostics +
            f'<details><summary>Capture identification</summary><p>Components SHA-256 <code>{esc(source.get("sha256") or "unavailable")}</code></p></details></article>')
    project = report.get("project_name") or "Project name unavailable"
    firmware = report.get("project_firmware") or "unknown"
    template = Path(__file__).with_name("capture_guide.html").read_text(encoding="utf-8")
    # Substitute once so literal tokens in a user-supplied label survive.
    manifest = note_manifest(report)
    note_ui = ""
    script = ""
    if manifest:
        note_ui = ('<section id="notebook" hidden><h2>Preset listening notes</h2>'
                   '<form><label>Physical control <select id="gesture"></select></label>'
                   '<label>What changes as you turn or press it?'
                   '<textarea id="observation" rows="3" maxlength="2000"></textarea></label></form>'
                   '<button type="button" id="save-notes">Download notes</button> '
                   '<label class="import">Restore notes <input type="file" id="restore-notes" accept=".json,application/json"></label>'
                   '<p id="note-status" role="status"></p></section>')
        payload = json.dumps(manifest, ensure_ascii=True).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
        javascript = Path(__file__).with_name("capture_notes.js").read_text(encoding="utf-8")
        script = f'<script type="application/json" id="note-manifest">{payload}</script><script>{javascript}</script>'
    return Template(template).substitute(nav=" ".join(nav), sections="".join(sections),
                                         project=esc(project), firmware=esc(firmware),
                                         notebook=note_ui, scripts=script)
