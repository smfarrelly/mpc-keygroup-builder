"""Generate an offline, interactive plugin-mapping hardware companion."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from . import plugin_map, plugin_params


GROUPS = (
    ("top-encoder", "Top encoders"),
    ("middle-encoder", "Middle encoders"),
    ("bottom-encoder", "Bottom encoders"),
    ("fader", "Faders"),
    ("upper-button", "Upper buttons"),
    ("lower-button", "Lower buttons"),
)


def companion_data(profiles: list[dict[str, Any]], catalog: dict[str, Any]) -> dict[str, Any]:
    validation = plugin_map.validate_batch(profiles, catalog)
    if validation["errors"]:
        raise ValueError("invalid plugin companion: " + "; ".join(validation["errors"]))
    pages = []
    for result in validation["profiles"]:
        profile = result["profile"]
        controls = []
        by_endpoint = {item["control"]: item for item in result["controls"]}
        for group, _ in GROUPS:
            for position in range(1, 9):
                endpoint = f"{group}-{position}"
                item = by_endpoint.get(endpoint)
                if item:
                    controls.append(
                        {
                            key: item[key]
                            for key in (
                                "control", "cc", "label", "role", "priority", "behavior",
                                "plugin", "name", "ui_parameter", "mpc_parameter", "evidence",
                                "q_links", "control_type",
                            )
                        }
                    )
        pages.append(
            {
                "id": profile["id"],
                "name": profile["name"],
                "description": profile["description"],
                "slot": profile["slot"],
                "channel": profile["channel"],
                "plugins": plugin_map.profile_plugins(profile),
                "probe": profile.get("probe"),
                "controls": controls,
            }
        )
    pages.sort(key=lambda item: item["slot"])
    identity = [
        {
            "id": page["id"],
            "slot": page["slot"],
            "channel": page["channel"],
            "controls": [
                (control["control"], control["plugin"], control["ui_parameter"], control["cc"])
                for control in page["controls"]
            ],
        }
        for page in pages
    ]
    fingerprint = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    return {
        "schema_version": 1,
        "title": "MPC Plugin Mapping Companion",
        "fingerprint": fingerprint,
        "pages": pages,
        "groups": [{"id": group, "name": name} for group, name in GROUPS],
        "evidence_boundary": (
            "UI metadata is software evidence. Pass/warn/fail remains pending until a person "
            "moves the control on MPC hardware and saves/reloads the project."
        ),
    }


def render_html(data: dict[str, Any]) -> str:
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    return HTML_TEMPLATE.replace("__DATA__", payload)


def build_companion(
    profile_paths: list[Path],
    synth_root: Path,
    output: Path,
    *,
    project: Path | None = None,
    force: bool = False,
) -> Path:
    output = output.expanduser()
    if output.is_symlink():
        raise ValueError(f"plugin companion output may not be a symbolic link: {output}")
    output = output.resolve()
    if output.exists() and not force:
        raise FileExistsError(f"plugin companion exists: {output}")
    profiles = sorted(
        (plugin_map.load_profile(path) for path in profile_paths),
        key=lambda item: item["slot"],
    )
    catalog = plugin_params.catalog(synth_root.expanduser().resolve(), project)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_html(companion_data(profiles, catalog)), encoding="utf-8")
    return output


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profiles", type=Path, nargs="+")
    parser.add_argument("--synth-root", type=Path, required=True)
    parser.add_argument("--project", type=Path, help="optional MPC XPJ evidence")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true", help="replace only the named HTML output")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    output = build_companion(
        args.profiles,
        args.synth_root,
        args.output,
        project=args.project,
        force=args.force,
    )
    print(f"Wrote: {output}")
    print("Browser capabilities: guided Learn steps, local progress, notes, JSON/CSV export")
    print("No XPJ, SysEx, plugin content, or SD-card data is written.")
    return 0


HTML_TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="dark">
  <title>MPC Plugin Mapping Companion</title>
  <style>
    :root{color-scheme:dark;font-family:Inter,ui-sans-serif,system-ui,sans-serif;--bg:#0d1110;--panel:#151b18;--line:#2b3730;--text:#edf4ee;--muted:#9eada3;--green:#9de7b0;--amber:#f0c86b;--red:#ff817a;--blue:#8fc8ff;--shadow:0 18px 55px #0007}
    *{box-sizing:border-box} body{margin:0;background:radial-gradient(circle at 12% 0,#18251d 0,transparent 34rem),var(--bg);color:var(--text)}
    button,input,textarea{font:inherit} button{color:inherit} .shell{display:grid;grid-template-columns:285px 1fr;min-height:100vh}
    aside{border-right:1px solid var(--line);padding:26px 18px;position:sticky;top:0;height:100vh;overflow:auto;background:#0f1412ee}
    .eyebrow{font-size:.72rem;letter-spacing:.14em;text-transform:uppercase;color:var(--green);font-weight:800}.brand{font-size:1.25rem;font-weight:790;line-height:1.1;margin:9px 0 24px}
    .page-list{display:grid;gap:7px}.page-tab{width:100%;text-align:left;border:1px solid transparent;background:transparent;border-radius:12px;padding:11px;cursor:pointer}.page-tab:hover{background:#19211d}.page-tab.active{border-color:#557261;background:#1b2720}
    .tab-top{display:flex;justify-content:space-between;gap:8px;font-weight:720}.tab-meta{font-size:.78rem;color:var(--muted);margin-top:5px}.mini-progress{height:3px;background:#303a34;border-radius:9px;margin-top:8px;overflow:hidden}.mini-progress i{display:block;height:100%;background:var(--green)}
    .side-actions{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:20px}.side-actions button,.file-label{border:1px solid var(--line);background:#17201b;border-radius:10px;padding:8px 9px;font-size:.78rem;text-align:center;cursor:pointer}.file-label input{display:none}
    main{padding:34px clamp(20px,4vw,58px) 80px;max-width:1500px;width:100%}.hero{display:flex;align-items:flex-start;justify-content:space-between;gap:22px}.hero h1{font-size:clamp(2rem,5vw,4.3rem);line-height:.98;letter-spacing:-.045em;margin:10px 0}.lede{color:var(--muted);max-width:720px;line-height:1.55}.chips{display:flex;flex-wrap:wrap;gap:7px;margin-top:16px}.chip{border:1px solid var(--line);border-radius:999px;padding:6px 10px;font-size:.78rem;color:#c8d4cc;background:#121815}.score{text-align:right;min-width:125px}.score strong{display:block;font-size:2rem}.score span{color:var(--muted);font-size:.8rem}
    .steps{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:28px 0}.step{border:1px solid var(--line);background:var(--panel);border-radius:14px;padding:13px;display:flex;gap:10px;align-items:flex-start}.step input{accent-color:#82d49a;margin-top:3px}.step b{display:block;font-size:.9rem}.step small{color:var(--muted);line-height:1.35;display:block;margin-top:3px}
    .workspace{display:grid;grid-template-columns:minmax(540px,1.25fr) minmax(300px,.75fr);gap:18px}.card{border:1px solid var(--line);background:#121815d9;border-radius:18px;padding:18px;box-shadow:var(--shadow)}.card-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:15px}.card h2{font-size:1rem;margin:0}.legend{font-size:.76rem;color:var(--muted)}
    .controller{background:linear-gradient(145deg,#222a26,#151a17);border:1px solid #3d4a42;border-radius:18px;padding:18px;display:grid;gap:14px}.control-row{display:grid;grid-template-columns:90px repeat(8,minmax(44px,1fr));gap:8px;align-items:center}.row-name{font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;color:#8e9c93}.control{aspect-ratio:1;border:1px solid #3a463f;background:#101512;border-radius:50%;cursor:pointer;padding:5px;font-size:.68rem;line-height:1.05;overflow:hidden;display:grid;place-items:center;text-align:center}.control.fader{aspect-ratio:.55;border-radius:9px}.control.button{aspect-ratio:2.1;border-radius:8px}.control.empty{opacity:.22;cursor:default}.control.assigned{border-color:#60786a;background:#1c2821}.control.core{box-shadow:inset 0 0 0 2px #82d49a55}.control.selected{outline:2px solid var(--blue);outline-offset:2px}.control.pass{background:#193a25;border-color:var(--green)}.control.warn{background:#40351c;border-color:var(--amber)}.control.fail{background:#45201e;border-color:var(--red)}
    .detail-empty{color:var(--muted);line-height:1.6;padding:25px 4px}.detail h3{font-size:1.35rem;margin:3px 0}.route{color:var(--green);font-size:.9rem;margin:7px 0 14px}.facts{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:14px 0}.fact{background:#0e1311;border-radius:10px;padding:9px}.fact span{display:block;color:var(--muted);font-size:.7rem;text-transform:uppercase;letter-spacing:.08em}.fact b{font-size:.88rem}.status{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin:16px 0}.status button{border:1px solid var(--line);background:#171e1a;border-radius:9px;padding:8px 3px;cursor:pointer;font-size:.78rem}.status button.active{border-color:var(--blue);background:#203247}.notes-label{font-size:.76rem;color:var(--muted)}textarea{width:100%;min-height:95px;resize:vertical;border:1px solid var(--line);border-radius:10px;background:#0d1210;color:var(--text);padding:10px;margin-top:6px}.nav-controls{display:flex;justify-content:space-between;gap:8px;margin-top:12px}.nav-controls button{border:1px solid var(--line);background:#17201b;border-radius:9px;padding:8px 12px;cursor:pointer}.boundary{margin-top:18px;color:#849188;font-size:.8rem;line-height:1.5}
    .toast{position:fixed;right:22px;bottom:22px;background:#e5f4e9;color:#102015;border-radius:11px;padding:11px 15px;box-shadow:var(--shadow);opacity:0;transform:translateY(8px);transition:.2s;pointer-events:none}.toast.show{opacity:1;transform:none}
    .print-pages{display:none}
    @media(max-width:980px){.shell{display:block}aside{position:static;height:auto;border-right:0;border-bottom:1px solid var(--line)}.page-list{display:flex;overflow:auto}.page-tab{min-width:190px}.workspace{grid-template-columns:1fr}.control-row{grid-template-columns:75px repeat(8,minmax(38px,1fr))}}
    @media(max-width:650px){main{padding:24px 12px 70px}.hero{display:block}.score{text-align:left;margin-top:15px}.steps{grid-template-columns:1fr}.controller{overflow:auto}.control-row{min-width:620px}.card{padding:12px}}
    @media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;transition:none!important}}
    @media print{body{background:#fff;color:#111}.shell,.toast{display:none}.print-pages{display:block}.print-card{page-break-after:always;padding:10mm;font-family:Arial,sans-serif}.print-card:last-child{page-break-after:auto}.print-card h1{font-size:22pt;margin:0 0 4mm}.print-meta{font-size:10pt;margin-bottom:5mm}.print-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:3mm 8mm}.print-group{break-inside:avoid}.print-group h2{font-size:11pt;border-bottom:1px solid #333;margin:0 0 2mm;padding-bottom:1mm}.print-row{display:grid;grid-template-columns:28mm 1fr 16mm;gap:2mm;font-size:8.5pt;padding:1.2mm 0;border-bottom:1px solid #ddd}.print-note{font-size:8pt;margin-top:5mm;color:#333}}
  </style>
</head>
<body>
  <div class="shell">
    <aside>
      <div class="eyebrow">Offline · local only</div><div class="brand">Plugin Mapping Companion</div>
      <nav class="page-list" id="page-list" aria-label="Plugin pages"></nav>
      <div class="side-actions">
        <button id="export-json" type="button">Export JSON</button><button id="export-csv" type="button">Export CSV</button>
        <label class="file-label">Import JSON<input id="import-json" type="file" accept="application/json,.json"></label><button id="print" type="button">Print mode cards</button>
        <button id="reset" type="button">Reset progress</button>
      </div>
      <p class="boundary">Progress and notes remain in this browser. Exports contain observations only—never plugin state, audio, XPJ, or SysEx.</p>
    </aside>
    <main>
      <header class="hero"><div><div class="eyebrow" id="slot"></div><h1 id="title"></h1><div class="lede" id="description"></div><div class="chips" id="chips"></div></div><div class="score"><strong id="score">0%</strong><span id="score-label">0 of 0 tested</span></div></header>
      <section class="steps" id="steps"></section>
      <div class="workspace">
        <section class="card"><div class="card-head"><h2>Launch Control XL 3</h2><div class="legend">outlined = core · color = result</div></div><div class="controller" id="controller"></div></section>
        <section class="card"><div class="card-head"><h2>Selected control</h2><div class="legend" id="position"></div></div><div id="detail"></div></section>
      </div>
      <p class="boundary" id="evidence"></p>
    </main>
  </div>
  <section class="print-pages" id="print-pages" aria-hidden="true"></section>
  <div class="toast" id="toast" role="status" aria-live="polite"></div>
  <script>
  const DATA=__DATA__,STATUSES=['pending','pass','warn','fail'],STORAGE=`mpc-plugin-companion:${DATA.fingerprint}`;
  const $=id=>document.getElementById(id);let pageIndex=0,selected=null,state=loadState();
  function emptyState(){const pages={};DATA.pages.forEach(p=>{const controls={};p.controls.forEach(c=>controls[c.control]={status:'pending',notes:''});pages[p.id]={steps:{mode:false,probe:false,reload:false},controls}});return{schema_version:1,fingerprint:DATA.fingerprint,pages}}
  function loadState(){try{const saved=JSON.parse(localStorage.getItem(STORAGE));if(saved&&saved.fingerprint===DATA.fingerprint)return mergeState(saved)}catch(e){}return emptyState()}
  function mergeState(saved){const fresh=emptyState();DATA.pages.forEach(p=>{const old=saved.pages?.[p.id];if(!old)return;Object.keys(fresh.pages[p.id].steps).forEach(k=>fresh.pages[p.id].steps[k]=old.steps?.[k]===true);p.controls.forEach(c=>{const source=old.controls?.[c.control];if(!source)return;fresh.pages[p.id].controls[c.control]={status:STATUSES.includes(source.status)?source.status:'pending',notes:typeof source.notes==='string'?source.notes:''}})});return fresh}
  function save(){localStorage.setItem(STORAGE,JSON.stringify(state))}
  function page(){return DATA.pages[pageIndex]}function pageState(){return state.pages[page().id]}
  function progress(p){const values=Object.values(state.pages[p.id].controls),tested=values.filter(v=>v.status!=='pending').length;return{tested,total:values.length,pct:values.length?Math.round(tested/values.length*100):0}}
  function render(){renderTabs();const p=page(),s=pageState(),pr=progress(p);$('slot').textContent=`Custom Mode ${p.slot} · MIDI channel ${p.channel} · USB`;$('title').textContent=p.name;$('description').textContent=p.description;$('chips').replaceChildren();[...p.plugins,`${p.controls.length} controls`,`${p.controls.filter(c=>c.priority==='core').length} core`].forEach(addChip);$('score').textContent=`${pr.pct}%`;$('score-label').textContent=`${pr.tested} of ${pr.total} tested`;$('evidence').textContent=DATA.evidence_boundary;renderSteps(p,s);renderController(p,s);renderDetail(p,s)}
  function addChip(text){const el=document.createElement('span');el.className='chip';el.textContent=text;$('chips').append(el)}
  function renderTabs(){$('page-list').replaceChildren();DATA.pages.forEach((p,i)=>{const pr=progress(p),b=document.createElement('button');b.type='button';b.className=`page-tab ${i===pageIndex?'active':''}`;b.innerHTML=`<div class="tab-top"><span>${esc(p.name)}</span><span>${pr.pct}%</span></div><div class="tab-meta">Slot ${p.slot} · Ch ${p.channel}</div><div class="mini-progress"><i style="width:${pr.pct}%"></i></div>`;b.onclick=()=>{pageIndex=i;selected=p.probe||p.controls[0]?.control||null;render()};$('page-list').append(b)})}
  function renderSteps(p,s){const probe=p.controls.find(c=>c.control===p.probe),items=[['mode','Create mode',`Slot ${p.slot}, channel ${p.channel}, USB output`],['probe','Verify one probe',probe?`${probe.control} · CC ${probe.cc} → ${probe.plugin} ${probe.name}`:'Use the first core control'],['reload','Save and reload','Confirm the learned assignment persists in the MPC project']];$('steps').replaceChildren();items.forEach(([id,title,copy])=>{const label=document.createElement('label');label.className='step';label.innerHTML=`<input type="checkbox" ${s.steps[id]?'checked':''}><span><b>${esc(title)}</b><small>${esc(copy)}</small></span>`;label.querySelector('input').onchange=e=>{s.steps[id]=e.target.checked;save();renderTabs()};$('steps').append(label)})}
  function renderController(p,s){const by=new Map(p.controls.map(c=>[c.control,c]));$('controller').replaceChildren();DATA.groups.forEach(g=>{const row=document.createElement('div');row.className='control-row';const name=document.createElement('div');name.className='row-name';name.textContent=g.name;row.append(name);for(let i=1;i<=8;i++){const id=`${g.id}-${i}`,c=by.get(id),b=document.createElement('button');b.type='button';b.className=`control ${g.id.includes('fader')?'fader':g.id.includes('button')?'button':''} ${c?'assigned':'empty'} ${c?.priority==='core'?'core':''} ${c?s.controls[id].status:''} ${id===selected?'selected':''}`;b.disabled=!c;b.setAttribute('aria-label',c?`${id}: ${c.label}`:`${id}: unassigned`);b.textContent=c?c.label:'—';if(c)b.onclick=()=>{selected=id;renderController(p,s);renderDetail(p,s)};row.append(b)}$('controller').append(row)})}
  function renderDetail(p,s){const c=p.controls.find(x=>x.control===selected)||p.controls.find(x=>x.control===p.probe)||p.controls[0];if(!c){$('detail').innerHTML='<div class="detail-empty">No mapped controls on this page.</div>';return}selected=c.control;const v=s.controls[c.control];$('position').textContent=c.control;$('detail').innerHTML=`<div class="detail"><div class="eyebrow">${esc(c.priority)} · ${esc(c.role)}</div><h3>${esc(c.label)}</h3><div class="route">${esc(c.plugin)} → ${esc(c.name)}</div><div class="facts"><div class="fact"><span>Send</span><b>Ch ${p.channel} · CC ${c.cc}</b></div><div class="fact"><span>Behavior</span><b>${esc(c.behavior)}</b></div><div class="fact"><span>UI parameter</span><b>${c.ui_parameter}</b></div><div class="fact"><span>MPC candidate</span><b>${c.mpc_parameter} · ${esc(c.evidence)}</b></div></div><div class="status" role="group" aria-label="Hardware result">${STATUSES.map(x=>`<button type="button" data-status="${x}" class="${v.status===x?'active':''}">${x}</button>`).join('')}</div><label class="notes-label">Listening and behavior notes<textarea id="notes" placeholder="What moved? Range, pickup, unexpected targets, musical usefulness…">${esc(v.notes)}</textarea></label><div class="nav-controls"><button id="prev" type="button">← Previous</button><button id="next" type="button">Next →</button></div></div>`;$('detail').querySelectorAll('[data-status]').forEach(b=>b.onclick=()=>{v.status=b.dataset.status;save();render()});$('notes').oninput=e=>{v.notes=e.target.value;save()};$('prev').onclick=()=>move(-1);$('next').onclick=()=>move(1)}
  function move(delta){const controls=page().controls,i=Math.max(0,controls.findIndex(c=>c.control===selected)),next=(i+delta+controls.length)%controls.length;selected=controls[next].control;renderController(page(),pageState());renderDetail(page(),pageState())}
  function renderPrint(){const root=$('print-pages');root.replaceChildren();DATA.pages.forEach(p=>{const card=document.createElement('article');card.className='print-card';const groups=DATA.groups.map(g=>{const controls=p.controls.filter(c=>c.control.startsWith(g.id));if(!controls.length)return'';return`<section class="print-group"><h2>${esc(g.name)}</h2>${controls.map(c=>`<div class="print-row"><b>${esc(c.control)}</b><span>${esc(c.label)} · ${esc(c.plugin)} → ${esc(c.name)}</span><span>CC ${c.cc}</span></div>`).join('')}</section>`}).join('');card.innerHTML=`<h1>${esc(p.name)}</h1><div class="print-meta">Custom Mode ${p.slot} · MIDI channel ${p.channel} · USB · Probe ${esc(p.probe||'first core control')}</div><div class="print-grid">${groups}</div><div class="print-note">Hardware result: □ pass □ warn □ fail &nbsp; Notes: ________________________________________________</div>`;root.append(card)})}
  function resultPayload(){return{schema_version:1,kind:'mpc-plugin-mapping-results',fingerprint:DATA.fingerprint,exported_at:new Date().toISOString(),pages:DATA.pages.map(p=>({id:p.id,name:p.name,slot:p.slot,channel:p.channel,steps:state.pages[p.id].steps,controls:p.controls.map(c=>({control:c.control,plugin:c.plugin,target:c.name,status:state.pages[p.id].controls[c.control].status,notes:state.pages[p.id].controls[c.control].notes}))}))}}
  function download(name,type,text){const url=URL.createObjectURL(new Blob([text],{type})),a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),0);toast(`Downloaded ${name}`)}
  function csv(){const rows=[['profile','slot','channel','control','plugin','target','status','notes']];resultPayload().pages.forEach(p=>p.controls.forEach(c=>rows.push([p.id,p.slot,p.channel,c.control,c.plugin,c.target,c.status,c.notes])));return rows.map(r=>r.map(x=>`"${String(x).replaceAll('"','""')}"`).join(',')).join('\n')+'\n'}
  $('export-json').onclick=()=>download('mpc-plugin-mapping-results.json','application/json',JSON.stringify(resultPayload(),null,2)+'\n');$('export-csv').onclick=()=>download('mpc-plugin-mapping-results.csv','text/csv',csv());$('print').onclick=()=>window.print();$('import-json').onchange=async e=>{try{const file=e.target.files?.[0];if(!file)return;const parsed=JSON.parse(await file.text());if(parsed.schema_version!==1||parsed.kind!=='mpc-plugin-mapping-results'||parsed.fingerprint!==DATA.fingerprint||!Array.isArray(parsed.pages))throw Error('This result file does not match the current mapping set.');const incoming={fingerprint:parsed.fingerprint,pages:{}};parsed.pages.forEach(p=>{if(!p||!Array.isArray(p.controls))return;incoming.pages[p.id]={steps:p.steps,controls:Object.fromEntries(p.controls.filter(c=>c&&typeof c.control==='string').map(c=>[c.control,{status:c.status,notes:c.notes}]))}});state=mergeState(incoming);save();render();toast('Imported matching results')}catch(err){alert(`Import failed: ${err.message}`)}e.target.value=''};$('reset').onclick=()=>{if(confirm('Reset all local progress and notes for this mapping set?')){state=emptyState();save();render();toast('Progress reset')}};
  function toast(message){$('toast').textContent=message;$('toast').classList.add('show');setTimeout(()=>$('toast').classList.remove('show'),1800)}function esc(value){return String(value??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
  selected=DATA.pages[0]?.probe||DATA.pages[0]?.controls[0]?.control||null;render();renderPrint();
  </script>
</body>
</html>
'''


if __name__ == "__main__":
    raise SystemExit(main())
