"""Render a self-contained, read-only MPC Program Designer viewer."""

from __future__ import annotations

import argparse
import html
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median
from typing import Any

from .device import DeviceProfile, load_device
from .model import ProgramModel, Zone, from_drum_manifest, from_xpm
from .roles import load_role_overrides


AUDIO_SUFFIXES = {".wav", ".aif", ".aiff"}
SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


@dataclass(frozen=True)
class DesignerIssue:
    severity: str
    code: str
    message: str
    zone: int | None = None


def _color(value: int | None) -> str | None:
    return f"#{value & 0xFFFFFF:06X}" if value is not None else None


def _compact_ranges(values: list[int]) -> str:
    if not values:
        return ""
    ranges: list[str] = []
    start = previous = values[0]
    for value in values[1:]:
        if value == previous + 1:
            previous = value
            continue
        ranges.append(str(start) if start == previous else f"{start}-{previous}")
        start = previous = value
    ranges.append(str(start) if start == previous else f"{start}-{previous}")
    return ", ".join(ranges)


def _audio_index(root: Path | None) -> tuple[dict[str, list[Path]], dict[str, list[Path]]] | None:
    if root is None or not root.is_dir():
        return None
    by_name: dict[str, list[Path]] = {}
    by_stem: dict[str, list[Path]] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.casefold() not in AUDIO_SUFFIXES:
            continue
        by_name.setdefault(path.name.casefold(), []).append(path)
        by_stem.setdefault(path.stem.casefold(), []).append(path)
    return by_name, by_stem


def _sample_status(
    sample: str,
    index: tuple[dict[str, list[Path]], dict[str, list[Path]]] | None,
) -> tuple[str, int]:
    if index is None:
        return "unchecked", 0
    name = Path(sample).name
    by_name, by_stem = index
    matches = (
        by_name.get(name.casefold(), [])
        if Path(name).suffix
        else by_stem.get(Path(name).stem.casefold(), [])
    )
    if not matches:
        return "missing", 0
    if len(matches) > 1:
        return "ambiguous", len(matches)
    return "found", 1


def infer_sample_root(program: ProgramModel, source_root: Path | None = None) -> Path | None:
    if source_root is not None:
        return source_root.resolve()
    if not program.source_path or program.source_format == "drum-manifest-toml":
        return None
    source = Path(program.source_path)
    if program.source_format == "gzip-json":
        program_data = source.with_name(f"{source.stem}_[ProgramData]")
        if program_data.is_dir():
            return program_data.resolve()
    return source.parent.resolve() if source.parent.is_dir() else None


def analyse_program(
    program: ProgramModel,
    device: DeviceProfile,
    sample_root: Path | None = None,
) -> tuple[list[DesignerIssue], dict[int, list[dict[str, Any]]]]:
    issues: list[DesignerIssue] = []
    validation = program.validate()
    issues.extend(DesignerIssue("error", "model_validation", value) for value in validation["errors"])
    issues.extend(
        DesignerIssue("warning", "model_validation", value)
        for value in validation["warnings"]
    )
    audio = _audio_index(sample_root)
    layer_status: dict[int, list[dict[str, Any]]] = {}
    for zone in program.zones:
        statuses = []
        coverage = [0] * 128
        for layer in zone.layers:
            status, matches = _sample_status(layer.sample, audio)
            statuses.append({"status": status, "matches": matches})
            if status == "missing":
                issues.append(
                    DesignerIssue(
                        "error",
                        "missing_sample",
                        f"Sample not found below the selected sample root: {layer.sample}",
                        zone.index,
                    )
                )
            elif status == "ambiguous":
                issues.append(
                    DesignerIssue(
                        "error",
                        "ambiguous_sample",
                        f"Sample resolves to {matches} files: {layer.sample}",
                        zone.index,
                    )
                )
            for velocity in range(max(0, layer.velocity_start), min(127, layer.velocity_end) + 1):
                coverage[velocity] += 1
            if layer.sample_end is not None and layer.sample_end < layer.sample_start:
                issues.append(
                    DesignerIssue(
                        "error",
                        "invalid_sample_bounds",
                        f"Sample end {layer.sample_end} precedes start {layer.sample_start}",
                        zone.index,
                    )
                )
            if layer.loop_enabled and (layer.loop_start is None or layer.loop_end is None):
                issues.append(
                    DesignerIssue(
                        "warning",
                        "incomplete_loop",
                        f"Loop is enabled without complete bounds: {layer.sample}",
                        zone.index,
                    )
                )
        gaps = [velocity for velocity, count in enumerate(coverage) if count == 0]
        stacks = [velocity for velocity, count in enumerate(coverage) if count > 1]
        if gaps:
            issues.append(
                DesignerIssue(
                    "error",
                    "dead_velocity_range",
                    f"No layer triggers at velocities {_compact_ranges(gaps)}",
                    zone.index,
                )
            )
        if stacks:
            issues.append(
                DesignerIssue(
                    "warning",
                    "stacked_velocity_range",
                    f"Multiple layers trigger at velocities {_compact_ranges(stacks)}",
                    zone.index,
                )
            )
        layer_status[zone.index] = statuses

    if program.kind == "drum":
        outside = [zone.index for zone in program.zones if zone.pad and zone.pad > device.capacity]
        if outside:
            issues.append(
                DesignerIssue(
                    "error",
                    "device_capacity",
                    f"{len(outside)} populated pads exceed {device.name}'s {device.capacity}-slot capacity",
                )
            )
        groups: dict[int, list[Zone]] = {}
        for zone in program.zones:
            if zone.mute_group:
                groups.setdefault(zone.mute_group, []).append(zone)
        for group, zones in groups.items():
            if len(zones) == 1:
                issues.append(
                    DesignerIssue(
                        "warning",
                        "singleton_mute_group",
                        f"Mute Group {group} contains only one populated pad",
                        zones[0].index,
                    )
                )
        ungrouped_hats = [
            zone for zone in program.zones if zone.role.startswith("hihat.") and not zone.mute_group
        ]
        if ungrouped_hats:
            issues.append(
                DesignerIssue(
                    "warning",
                    "ungrouped_hats",
                    f"{len(ungrouped_hats)} hat pads have no mute group",
                )
            )
        missing_colors = sum(zone.color is None for zone in program.zones)
        if missing_colors:
            issues.append(
                DesignerIssue(
                    "info",
                    "missing_colors",
                    f"{missing_colors} populated pads have no explicit color",
                )
            )
        if not program.pad_note_map and all(zone.midi_note is None for zone in program.zones):
            issues.append(
                DesignerIssue(
                    "info",
                    "midi_map_unavailable",
                    "No explicit Drum PadNoteMap is available in the normalized source",
                )
            )
    return sorted(
        issues,
        key=lambda value: (SEVERITY_ORDER.get(value.severity, 9), value.zone or 0, value.code),
    ), layer_status


def _zone_payload(
    zone: Zone,
    program: ProgramModel,
    statuses: list[dict[str, Any]],
) -> dict[str, Any]:
    midi_note = zone.midi_note
    if midi_note is None and zone.pad is not None:
        midi_note = program.pad_note_map.get(zone.pad)
    return {
        "index": zone.index,
        "pad": zone.pad,
        "midi_note": midi_note,
        "low_note": zone.low_note,
        "high_note": zone.high_note,
        "role": zone.role,
        "color": zone.color,
        "color_hex": _color(zone.color),
        "playback_mode": zone.playback_mode,
        "mute_group": zone.mute_group,
        "polyphony": zone.polyphony,
        "monophonic": zone.monophonic,
        "locked": zone.locked,
        "layers": [
            {
                **asdict(layer),
                "sample_status": statuses[index]["status"],
                "sample_matches": statuses[index]["matches"],
            }
            for index, layer in enumerate(zone.layers)
        ],
    }


def build_view_data(
    program: ProgramModel,
    device: DeviceProfile,
    sample_root: Path | None = None,
) -> dict[str, Any]:
    issues, statuses = analyse_program(program, device, sample_root)
    zones = [
        _zone_payload(zone, program, statuses.get(zone.index, [])) for zone in program.zones
    ]
    role_counts = Counter(zone.role for zone in program.zones)
    populated_banks: list[str] = []
    banks: dict[str, list[dict[str, Any] | None]] = {}
    zones_by_pad = {zone["pad"]: zone for zone in zones if zone["pad"] is not None}
    for bank_index, bank in enumerate(device.banks):
        offset = bank_index * device.pads_per_bank
        slots = [zones_by_pad.get(offset + position) for position in range(1, device.pads_per_bank + 1)]
        banks[bank] = slots
        if any(slots):
            populated_banks.append(bank)
    roots = [
        layer.root_note
        for zone in program.zones
        for layer in zone.layers
        if layer.root_note is not None
    ]
    ranges = [
        note
        for zone in program.zones
        for note in (zone.low_note, zone.high_note)
        if note is not None
    ]
    focus_notes = roots or ranges or [60]
    key_start = max(0, min(128 - max(1, device.keys), round(median(focus_notes)) - device.keys // 2))
    severity_counts = Counter(issue.severity for issue in issues)
    mute_groups: dict[str, list[str]] = {}
    for zone in program.zones:
        if zone.mute_group and zone.pad:
            mute_groups.setdefault(str(zone.mute_group), []).append(device.label(zone.pad))
    return {
        "schema_version": 1,
        "read_only": True,
        "program": {
            "name": program.name,
            "kind": program.kind,
            "source_format": program.source_format,
            "source_path": program.source_path,
            "zones": zones,
        },
        "device": {
            **asdict(device),
            "pads_per_bank": device.pads_per_bank,
            "capacity": device.capacity,
        },
        "summary": {
            "zones": len(program.zones),
            "layers": sum(len(zone.layers) for zone in program.zones),
            "populated_banks": populated_banks,
            "roles": dict(sorted(role_counts.items())),
            "mute_groups": mute_groups,
            "issues": dict(severity_counts),
            "sample_root": str(sample_root) if sample_root else None,
        },
        "banks": banks,
        "keyboard": {
            "keys": device.keys,
            "default_start": key_start,
            "minimum": 0,
            "maximum_start": max(0, 128 - max(1, device.keys)),
        },
        "issues": [asdict(issue) for issue in issues],
    }


HTML_TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__TITLE__ — MPC Program Designer</title>
  <style>
    :root { color-scheme: dark; --bg:#0d1014; --panel:#171b21; --panel2:#20262e; --line:#343c47; --text:#f4f6f8; --muted:#9aa5b1; --accent:#f3b33d; --danger:#ff6b6b; --warn:#f6c85f; --info:#61b8ff; }
    * { box-sizing:border-box; }
    body { margin:0; font:15px/1.45 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:radial-gradient(circle at top left,#1a2029 0,#0d1014 42rem); color:var(--text); }
    button { font:inherit; }
    .shell { max-width:1440px; margin:auto; padding:28px; }
    header { display:flex; justify-content:space-between; gap:24px; align-items:flex-start; margin-bottom:22px; }
    .eyebrow { color:var(--accent); text-transform:uppercase; letter-spacing:.14em; font-size:12px; font-weight:800; }
    h1 { margin:4px 0 6px; font-size:clamp(28px,4vw,48px); line-height:1.05; }
    .source { color:var(--muted); max-width:900px; overflow-wrap:anywhere; }
    .readonly { border:1px solid #725b26; background:#2b2414; color:#ffd77d; padding:7px 11px; border-radius:999px; white-space:nowrap; font-weight:700; }
    .chips { display:flex; flex-wrap:wrap; gap:9px; margin:0 0 22px; }
    .chip { padding:7px 10px; border:1px solid var(--line); border-radius:999px; background:#12161b; color:#dbe1e7; }
    .layout { display:grid; grid-template-columns:minmax(0,1.35fr) minmax(320px,.65fr); gap:20px; align-items:start; }
    .panel { background:linear-gradient(180deg,rgba(32,38,46,.96),rgba(21,25,31,.98)); border:1px solid var(--line); border-radius:18px; box-shadow:0 18px 50px rgba(0,0,0,.26); }
    .panel-head { padding:18px 20px; border-bottom:1px solid var(--line); display:flex; align-items:center; justify-content:space-between; gap:12px; }
    .panel-head h2 { margin:0; font-size:18px; }
    .panel-body { padding:20px; }
    .banks { display:flex; flex-wrap:wrap; gap:8px; }
    .bank { min-width:42px; padding:8px 12px; border-radius:10px; border:1px solid var(--line); color:var(--text); background:#11151a; cursor:pointer; }
    .bank.active { border-color:var(--accent); background:#352a16; color:#ffd579; }
    .bank.empty { opacity:.46; }
    .pad-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; max-width:760px; margin:18px auto 8px; }
    .pad { position:relative; min-height:128px; padding:12px; border:2px solid rgba(255,255,255,.18); border-radius:14px; cursor:pointer; text-align:left; background:#303740; color:white; overflow:hidden; transition:transform .12s ease,border-color .12s ease,box-shadow .12s ease; }
    .pad:hover,.pad:focus-visible { transform:translateY(-2px); border-color:white; box-shadow:0 10px 28px rgba(0,0,0,.35); outline:none; }
    .pad.selected { border-color:var(--accent); box-shadow:0 0 0 3px rgba(243,179,61,.22); }
    .pad.empty { cursor:default; opacity:.28; background:#222830!important; }
    .pad-label { font-weight:900; letter-spacing:.06em; }
    .pad-role { display:block; margin-top:22px; font-size:13px; font-weight:750; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .pad-sample { display:block; margin-top:4px; font-size:11px; opacity:.82; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .badges { display:flex; gap:5px; position:absolute; right:8px; top:8px; }
    .badge { border-radius:999px; padding:2px 6px; font-size:10px; font-weight:850; background:rgba(0,0,0,.45); color:white; }
    .detail-empty { color:var(--muted); padding:16px 0; }
    .kv { display:grid; grid-template-columns:120px 1fr; gap:7px 14px; margin:0 0 18px; }
    .kv dt { color:var(--muted); }
    .kv dd { margin:0; overflow-wrap:anywhere; }
    .layer { padding:12px; border:1px solid var(--line); background:#12161b; border-radius:12px; margin-top:10px; }
    .layer-top { display:flex; justify-content:space-between; gap:10px; }
    .layer-sample { font-weight:750; overflow-wrap:anywhere; }
    .status { font-size:11px; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); }
    .status.found { color:#72d69b; } .status.missing,.status.ambiguous { color:var(--danger); }
    .velocity { position:relative; height:8px; margin-top:10px; background:#303741; border-radius:999px; overflow:hidden; }
    .velocity span { position:absolute; top:0; bottom:0; background:linear-gradient(90deg,#df8c2d,#f2d36c); border-radius:999px; }
    .issues { margin-top:20px; }
    .issue { border-left:4px solid var(--line); background:#12161b; padding:11px 12px; margin-top:8px; border-radius:0 10px 10px 0; }
    .issue.error { border-color:var(--danger); } .issue.warning { border-color:var(--warn); } .issue.info { border-color:var(--info); }
    .issue strong { text-transform:uppercase; font-size:11px; letter-spacing:.09em; }
    .issue p { margin:3px 0 0; color:#d8dee5; }
    .issue code { color:var(--muted); }
    .key-controls { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
    .key-controls button { color:var(--text); border:1px solid var(--line); background:#11151a; border-radius:9px; padding:7px 10px; cursor:pointer; }
    .keybed-wrap { overflow-x:auto; padding:8px 0 12px; }
    .keybed { display:grid; grid-template-columns:repeat(var(--keys),minmax(30px,1fr)); min-width:1000px; gap:3px; align-items:start; }
    .key { height:150px; border:1px solid #89929c; border-radius:0 0 7px 7px; background:#e9edf1; color:#111; padding:8px 2px; display:flex; align-items:flex-end; justify-content:center; cursor:pointer; font-size:10px; white-space:pre-line; }
    .key.black { height:98px; background:#171a1f; color:white; border-color:#050607; z-index:2; }
    .key.active { box-shadow:inset 0 -8px 0 var(--accent); }
    .key.selected { outline:3px solid var(--info); outline-offset:2px; }
    .zone-list { display:grid; gap:10px; }
    .zone-card { border:1px solid var(--line); background:#12161b; border-radius:12px; padding:12px; cursor:pointer; }
    .zone-card:hover { border-color:#687483; }
    .zone-card strong { display:block; }
    .zone-card span { color:var(--muted); }
    .hidden { display:none!important; }
    footer { color:var(--muted); margin:22px 2px; font-size:13px; }
    @media (max-width:900px) { .layout { grid-template-columns:1fr; } .shell { padding:18px; } header { flex-direction:column; } .pad { min-height:108px; } }
    @media (max-width:520px) { .pad-grid { gap:7px; } .pad { min-height:94px; padding:8px; } .pad-role { margin-top:15px; font-size:11px; } .pad-sample { display:none; } .kv { grid-template-columns:90px 1fr; } }
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div><div class="eyebrow">MPC Program Designer · v0.3 read-only</div><h1 id="title"></h1><div class="source" id="source"></div></div>
      <div class="readonly">Read only · source unchanged</div>
    </header>
    <div class="chips" id="chips"></div>
    <div class="layout">
      <main class="panel">
        <div class="panel-head"><h2 id="surface-title">Performance surface</h2><div class="banks" id="banks"></div><div class="key-controls hidden" id="key-controls"><button id="oct-down">− octave</button><strong id="key-window"></strong><button id="oct-up">+ octave</button></div></div>
        <div class="panel-body"><div id="drum-surface"><div class="pad-grid" id="pad-grid"></div></div><div class="hidden" id="keygroup-surface"><div class="keybed-wrap"><div class="keybed" id="keybed"></div></div><div class="zone-list" id="zone-list"></div></div></div>
      </main>
      <aside>
        <section class="panel"><div class="panel-head"><h2>Selection</h2></div><div class="panel-body" id="detail"><div class="detail-empty">Select a populated pad or key.</div></div></section>
        <section class="panel issues"><div class="panel-head"><h2>Validation</h2><span id="issue-total"></span></div><div class="panel-body" id="issues"></div></section>
      </aside>
    </div>
    <footer>Generated locally from the normalized Program Model. This viewer contains metadata only and has no editing or export controls.</footer>
  </div>
  <script>const DATA=__DATA__;
  const $=id=>document.getElementById(id);
  const el=(tag,cls,text)=>{const node=document.createElement(tag);if(cls)node.className=cls;if(text!==undefined)node.textContent=text;return node;};
  const basename=value=>String(value||'').split(/[\\/]/).pop();
  const noteName=n=>['C','C♯','D','D♯','E','F','F♯','G','G♯','A','A♯','B'][n%12]+(Math.floor(n/12)-1);
  const isBlack=n=>[1,3,6,8,10].includes(n%12);
  function addChip(text){$('chips').append(el('span','chip',text));}
  function contrast(hex){if(!hex)return '#fff';const n=parseInt(hex.slice(1),16),r=n>>16,g=n>>8&255,b=n&255;return (.299*r+.587*g+.114*b)>155?'#111':'#fff';}
  function renderHeader(){const p=DATA.program,s=DATA.summary;$('title').textContent=p.name||'Unnamed program';$('source').textContent=`${p.kind} · ${p.source_format} · ${p.source_path||'in-memory source'}`;addChip(`${s.zones} zones`);addChip(`${s.layers} layers`);addChip(DATA.device.name);if(p.kind==='drum')addChip(`${s.populated_banks.length}/${DATA.device.banks.length} populated banks`);Object.entries(s.issues).forEach(([kind,count])=>addChip(`${count} ${kind}${count===1?'':'s'}`));}
  function renderIssues(){const box=$('issues');box.replaceChildren();$('issue-total').textContent=DATA.issues.length?`${DATA.issues.length} findings`:'clear';if(!DATA.issues.length){box.append(el('div','detail-empty','No model, sample, velocity, or mute-group findings.'));return;}DATA.issues.forEach(issue=>{const card=el('div',`issue ${issue.severity}`);const top=el('strong','',`${issue.severity} · ${issue.code}`);card.append(top);card.append(el('p','',`${issue.zone?`Zone ${issue.zone}: `:''}${issue.message}`));box.append(card);});}
  function layerNode(layer){const card=el('div','layer');const top=el('div','layer-top');top.append(el('span','layer-sample',basename(layer.sample)));top.append(el('span',`status ${layer.sample_status}`,layer.sample_status));card.append(top);card.append(el('div','source',`Velocity ${layer.velocity_start}–${layer.velocity_end}${layer.root_note!==null?` · root MIDI ${layer.root_note}`:''}${layer.loop_enabled?' · loop':''}`));const velocity=el('div','velocity');const fill=el('span');fill.style.left=`${layer.velocity_start/128*100}%`;fill.style.width=`${(layer.velocity_end-layer.velocity_start+1)/128*100}%`;velocity.append(fill);card.append(velocity);return card;}
  function renderZone(zone,label){const box=$('detail');box.replaceChildren();const rows=[['Location',label],['Role',zone.role]];if(zone.low_note!==null&&zone.high_note!==null)rows.push(['Key range',`${noteName(zone.low_note)}–${noteName(zone.high_note)} · MIDI ${zone.low_note}–${zone.high_note}`]);if(zone.midi_note!==null)rows.push(['MIDI note',`${zone.midi_note} (${noteName(zone.midi_note)})`]);rows.push(['Playback',zone.playback_mode],['Mute group',zone.mute_group||'none'],['Polyphony',zone.polyphony],['Monophonic',zone.monophonic?'yes':'no'],['Color',zone.color_hex||'not declared'],['Locked',zone.locked?'yes':'no']);const dl=el('dl','kv');rows.forEach(([k,v])=>{dl.append(el('dt','',k));dl.append(el('dd','',String(v)));});box.append(dl);box.append(el('h3','',`Layers · ${zone.layers.length}`));zone.layers.forEach(layer=>box.append(layerNode(layer)));}
  let selectedPad=null;
  function renderBank(bank){document.querySelectorAll('.bank').forEach(node=>node.classList.toggle('active',node.dataset.bank===bank));const grid=$('pad-grid');grid.replaceChildren();const slots=DATA.banks[bank],cols=DATA.device.pad_columns,rows=DATA.device.pad_rows;for(let row=rows-1;row>=0;row--){for(let col=0;col<cols;col++){const position=row*cols+col,zone=slots[position],label=`${bank}${String(position+1).padStart(2,'0')}`;const button=el('button',`pad${zone?'':' empty'}`);button.type='button';button.dataset.label=label;button.append(el('span','pad-label',label));if(zone){button.style.background=zone.color_hex||'#39424d';button.style.color=contrast(zone.color_hex);const badges=el('span','badges');if(zone.layers.length>1)badges.append(el('span','badge',`${zone.layers.length}L`));if(zone.mute_group)badges.append(el('span','badge',`M${zone.mute_group}`));button.append(badges);button.append(el('span','pad-role',zone.role));button.append(el('span','pad-sample',basename(zone.layers[0]?.sample)));button.addEventListener('click',()=>{document.querySelectorAll('.pad').forEach(n=>n.classList.remove('selected'));button.classList.add('selected');selectedPad=label;renderZone(zone,label);});}else{button.disabled=true;button.append(el('span','pad-role','Empty'));}grid.append(button);}}const first=grid.querySelector('.pad:not(.empty)');if(first&&(!selectedPad||!selectedPad.startsWith(bank)))first.click();}
  function renderDrums(){DATA.device.banks.forEach(bank=>{const populated=DATA.banks[bank].some(Boolean),button=el('button',`bank${populated?'':' empty'}`,bank);button.type='button';button.dataset.bank=bank;button.disabled=!populated;button.addEventListener('click',()=>renderBank(bank));$('banks').append(button);});renderBank(DATA.summary.populated_banks[0]||DATA.device.banks[0]);}
  let keyStart=DATA.keyboard.default_start,selectedNote=null;
  function activeZones(note){return DATA.program.zones.filter(zone=>zone.low_note!==null&&zone.high_note!==null&&zone.low_note<=note&&note<=zone.high_note);}
  function renderNote(note){selectedNote=note;document.querySelectorAll('.key').forEach(node=>node.classList.toggle('selected',Number(node.dataset.note)===note));const zones=activeZones(note);if(!zones.length){$('detail').replaceChildren(el('div','detail-empty',`${noteName(note)} · MIDI ${note} has no mapped zone.`));return;}renderZone(zones[0],`${noteName(note)} · MIDI ${note}`);}
  function renderKeybed(){const bed=$('keybed');bed.replaceChildren();bed.style.setProperty('--keys',DATA.keyboard.keys);$('key-window').textContent=`${noteName(keyStart)}–${noteName(keyStart+DATA.keyboard.keys-1)} · MIDI ${keyStart}–${keyStart+DATA.keyboard.keys-1}`;for(let note=keyStart;note<keyStart+DATA.keyboard.keys;note++){const zones=activeZones(note),key=el('button',`key ${isBlack(note)?'black':'white'}${zones.length?' active':''}`,`${noteName(note)}\n${note}`);key.type='button';key.dataset.note=String(note);key.title=zones.length?zones.map(z=>`${z.index}: ${basename(z.layers[0]?.sample)}`).join('\n'):'Unmapped';key.addEventListener('click',()=>renderNote(note));bed.append(key);}if(selectedNote===null||selectedNote<keyStart||selectedNote>=keyStart+DATA.keyboard.keys)renderNote(keyStart+Math.floor(DATA.keyboard.keys/2));else renderNote(selectedNote);}
  function renderKeygroups(){$('drum-surface').classList.add('hidden');$('keygroup-surface').classList.remove('hidden');$('banks').classList.add('hidden');$('key-controls').classList.remove('hidden');$('surface-title').textContent='37-note keybed viewport';$('oct-down').addEventListener('click',()=>{keyStart=Math.max(DATA.keyboard.minimum,keyStart-12);renderKeybed();});$('oct-up').addEventListener('click',()=>{keyStart=Math.min(DATA.keyboard.maximum_start,keyStart+12);renderKeybed();});const list=$('zone-list');DATA.program.zones.forEach(zone=>{const card=el('button','zone-card');card.type='button';card.append(el('strong','',`Zone ${zone.index} · MIDI ${zone.low_note}–${zone.high_note}`));card.append(el('span','',`${zone.layers.length} layer${zone.layers.length===1?'':'s'} · ${basename(zone.layers[0]?.sample)}`));card.addEventListener('click',()=>renderZone(zone,`Zone ${zone.index} · MIDI ${zone.low_note}–${zone.high_note}`));list.append(card);});renderKeybed();}
  renderHeader();renderIssues();if(DATA.program.kind==='drum')renderDrums();else renderKeygroups();
  </script>
</body>
</html>
'''


def render_html(data: dict[str, Any]) -> str:
    title = html.escape(str(data["program"]["name"] or "Unnamed program"), quote=True)
    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    payload = payload.replace("&", "\\u0026").replace("<", "\\u003C").replace(">", "\\u003E")
    return HTML_TEMPLATE.replace("__TITLE__", title).replace("__DATA__", payload)


def load_program(
    source: Path,
    source_type: str = "auto",
    source_root: Path | None = None,
    roles: Path | None = None,
) -> ProgramModel:
    resolved_type = source_type
    if resolved_type == "auto":
        resolved_type = "manifest" if source.suffix.casefold() == ".toml" else "xpm"
    overrides = load_role_overrides(roles) if roles else None
    return (
        from_drum_manifest(source, source_root, overrides)
        if resolved_type == "manifest"
        else from_xpm(source, overrides)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--source-type", choices=("auto", "xpm", "manifest"), default="auto")
    parser.add_argument("--source-root", type=Path, help="optional WAV root for manifest validation")
    parser.add_argument("--roles", type=Path, help="TOML file with explicit [roles] overrides")
    parser.add_argument("--device", type=Path, required=True)
    parser.add_argument("--format", choices=("html", "json"), default="html")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true", help="replace an existing viewer output")
    args = parser.parse_args()
    source = args.source.expanduser().resolve()
    source_root = args.source_root.expanduser().resolve() if args.source_root else None
    roles = args.roles.expanduser().resolve() if args.roles else None
    output = args.output.expanduser().resolve()
    if output == source:
        parser.error("viewer output cannot replace the source program")
    if output.exists() and not args.force:
        parser.error(f"viewer output exists; use --force to replace it: {output}")
    program = load_program(source, args.source_type, source_root, roles)
    device = load_device(args.device.expanduser().resolve())
    sample_root = infer_sample_root(program, source_root)
    data = build_view_data(program, device, sample_root)
    rendered = json.dumps(data, indent=2) + "\n" if args.format == "json" else render_html(data)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    counts = data["summary"]["issues"]
    print(f"Wrote: {output}")
    print(
        f"Program: {program.name} ({program.kind}); zones={len(program.zones)}; "
        f"issues={sum(counts.values())}"
    )
    return 2 if counts.get("error", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
