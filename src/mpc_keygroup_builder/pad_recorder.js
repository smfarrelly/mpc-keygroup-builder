"use strict";
(() => {
  const $ = id => document.getElementById(id);
  const {layout, samples, initial} = JSON.parse($("payload").textContent);
  const pads = new Map(layout.pads.map(pad => [pad.pad, pad]));
  const shortcuts = "ZXCVASDFQWER1234";
  const first = "ABCDEFGH".indexOf(layout.bank) * 16 + 1;
  const buttons = new Map(), buffers = new Map(), voices = new Set();
  const skipCycle = new WeakMap();
  const history = [];
  let take = structuredClone(initial);
  let ctx, ready, timer, start, cursor, recording = false, frame;
  let hasEdits = false;
  function report(text) { $("status").textContent = text; }
  const length = () => take.bars * 1920;
  const seconds = () => 60 / take.tempo / 480;
  const active = () => timer !== undefined;
  function remember() {
    history.push(structuredClone(take));
    if (history.length > 20) history.shift();
  }
  function refresh() {
    $("count").textContent = take.events.length + (take.events.length === 1 ? " hit" : " hits");
    $("record").setAttribute("aria-pressed", String(recording));
    $("record").textContent = recording ? "Finish overdub" : "Record";
    $("play").disabled = active();
    $("stop").disabled = !active();
    $("tempo").disabled = $("bars").disabled = active();
    $("undo").disabled = active() || !history.length;
    $("clear").disabled = active() || !take.events.length;
    $("name").value = take.name;
    $("bars").value = take.bars;
    $("tempo").value = take.tempo;
  }
  async function audio() {
    if (!ctx) ctx = new AudioContext();
    await ctx.resume();
    if (!ready) {
      ready = Promise.all(Object.entries(samples).map(async ([id, data]) => {
        const bytes = Uint8Array.from(atob(data), ch => ch.charCodeAt(0));
        buffers.set(id, await ctx.decodeAudioData(bytes.buffer));
      })).then(() => { $("enable").textContent = "Audio enabled"; $("enable").disabled = true; })
        .catch(error => { ready = undefined; throw error; });
    }
    await ready;
  }
  function safely(fn) {
    return (...args) => Promise.resolve().then(() => fn(...args)).catch(error => report(error.message));
  }
  function voice(pad, velocity, when, duration) {
    const layer = pad.layers.find(l => l.low <= velocity && velocity <= l.high);
    const source = ctx.createBufferSource(), gain = ctx.createGain();
    source.buffer = buffers.get(layer.audio);
    source.playbackRate.value = 2 ** (layer.pitch / 12);
    gain.gain.value = velocity / 127;
    source.connect(gain).connect(ctx.destination);
    const item = {source, pad, when, end: when + source.buffer.duration / source.playbackRate.value};
    if (!pad.oneShot) item.end = Math.min(item.end, when + duration * seconds());
    for (const other of voices) {
      if (!(pad.mono && other.pad?.pad === pad.pad) && !(pad.group && other.pad?.group === pad.group)) continue;
      if (other.when <= when && other.end > when) {
        other.end = when;
        other.source.stop(when);
      } else if (other.when > when) {
        item.end = Math.min(item.end, other.when);
      }
    }
    source.onended = () => { voices.delete(item); gain.disconnect(); source.disconnect(); };
    voices.add(item);
    source.start(when);
    source.stop(item.end);
  }
  function metronome(when, downbeat) {
    const oscillator = ctx.createOscillator(), gain = ctx.createGain();
    oscillator.frequency.value = downbeat ? 1300 : 850;
    gain.gain.setValueAtTime(.1, when);
    gain.gain.exponentialRampToValueAtTime(.0001, when + .035);
    oscillator.connect(gain).connect(ctx.destination);
    const item = {source: oscillator, when, end: when + .04};
    voices.add(item);
    oscillator.onended = () => { voices.delete(item); gain.disconnect(); oscillator.disconnect(); };
    oscillator.start(when);
    oscillator.stop(item.end);
  }
  function schedule() {
    const now = ctx.currentTime;
    const from = Math.max(cursor, (now - start) / seconds(), 0);
    const to = (now + .075 - start) / seconds();
    if (to <= from) return;
    const end = length();
    for (let cycle = Math.floor(from / end); cycle <= Math.floor(to / end); cycle++) {
      for (const hit of take.events) {
        const at = cycle * end + hit.tick;
        if (at >= from && at < to && skipCycle.get(hit) !== cycle)
          voice(pads.get(hit.pad), hit.velocity, start + at * seconds(), hit.duration_ticks);
      }
    }
    if ($("click").checked) {
      for (let beat = Math.ceil(from / 480); beat * 480 < to; beat++)
        metronome(start + beat * 480 * seconds(), beat % 4 === 0);
    }
    cursor = to;
  }
  function position() {
    const beat = Math.floor(Math.max(0, ctx.currentTime - start) / (seconds() * 480)) % (4 * take.bars);
    $("position").value = (Math.floor(beat / 4) + 1) + "." + (beat % 4 + 1);
    frame = requestAnimationFrame(position);
  }
  async function transport(arm) {
    await audio();
    if (active() && !arm) return;
    if (arm && !recording) remember();
    recording = arm && !recording;
    if (!active()) {
      start = ctx.currentTime + .045;
      cursor = 0;
      timer = setInterval(schedule, 20);
      schedule();
      position();
    }
    report(recording ? "Recording into the loop. Press Stop when ready." : "Playing the loop.");
    refresh();
  }
  function stop() {
    clearInterval(timer);
    timer = undefined;
    cancelAnimationFrame(frame);
    for (const item of voices) item.source.stop();
    voices.clear();
    recording = false;
    $("position").value = "1.1";
    refresh();
  }
  async function strike(pad, velocity, receivedTime) {
    await audio();
    const now = ctx.currentTime;
    voice(pad, velocity, now, 60);
    const button = buttons.get(pad.pad);
    button.classList.add("active");
    setTimeout(() => button.classList.remove("active"), 110);
    if (!recording) return;
    const hitTime = receivedTime ?? now;
    const raw = Math.max(0, (hitTime - start) / seconds());
    const grid = Number($("snap").value) || 1;
    const absolute = Math.round(raw / grid) * grid;
    const tick = absolute % length();
    const hit = {tick, pad: pad.pad, velocity, duration_ticks: Math.min(60, length() - tick)};
    take.events = take.events.filter(e => e.tick !== tick || e.pad !== pad.pad);
    take.events.push(hit);
    take.events.sort((a, b) => a.tick - b.tick);
    skipCycle.set(hit, Math.floor(absolute / length()));
    hasEdits = true;
    refresh();
  }
  function validate(t) {
    const integer = (n, a, b) => Number.isInteger(n) && n >= a && n <= b;
    if (t?.kind !== "mpc-pad-take" || t.version !== 1 || t.ppq !== 480)
      throw Error("Choose a version 1 MPC pad take.");
    if (t.fingerprint !== layout.fingerprint || t.bank !== layout.bank || t.program !== layout.program)
      throw Error("This take belongs to a different kit, sample set or bank.");
    if (!integer(t.bars, 1, 64) || !Number.isFinite(t.tempo) || t.tempo < 20 || t.tempo > 300 ||
      !integer(t.channel, 1, 16) || typeof t.name !== "string" || !t.name.trim() ||
      t.name.length > 120 || !Array.isArray(t.events)) throw Error("Invalid take settings.");
    for (const e of t.events)
      if (!e || !pads.has(e.pad) || !integer(e.tick, 0, t.bars * 1920 - 1) ||
        !integer(e.duration_ticks, 1, t.bars * 1920 - e.tick) || !integer(e.velocity, 1, 127))
        throw Error("Take contains an invalid pad, velocity, tick or duration.");
  }
  function midi() {
    const name = Array.from(new TextEncoder().encode(take.name + " seed 0")).slice(0,127);
    const tempo = Math.round(60000000 / take.tempo);
    const end = [length(), 9, [255,47,0]];
    const conductor = [[0,0,[255,3,9,...new TextEncoder().encode("Conductor")]],
      [0,1,[255,81,3,tempo >> 16,(tempo >> 8) & 255,tempo & 255]], [0,2,[255,88,4,4,2,24,8]], end];
    const notes = [[0,0,[255,3,name.length,...name]], end];
    for (const e of take.events) {
      const note = pads.get(e.pad).note, channel = take.channel - 1;
      notes.push([e.tick,2,[144 + channel,note,e.velocity]], [e.tick + e.duration_ticks,1,[128 + channel,note,0]]);
    }
    function chunk(events) {
      events.sort((a,b) => a[0]-b[0] || a[1]-b[1] || a[2][1]-b[2][1] || a[2][2]-b[2][2]);
      let last = 0;
      const data = [];
      for (const [tick,, message] of events) {
        let delta = tick - last;
        const bytes = [delta & 127];
        while ((delta >>= 7) > 0) bytes.unshift(128 | (delta & 127));
        data.push(...bytes,...message);
        last = tick;
      }
      const n = data.length;
      return [77,84,114,107,n >>> 24,n >>> 16 & 255,n >>> 8 & 255,n & 255,...data];
    }
    return Uint8Array.from([77,84,104,100,0,0,0,6,0,1,0,2,1,224,...chunk(conductor),...chunk(notes)]);
  }
  function download(data, type, ext) {
    const url = URL.createObjectURL(new Blob([data], {type}));
    const a = document.createElement("a");
    a.href = url;
    a.download = (take.name.replace(/[^\p{L}\p{N} _-]+/gu,"").trim() || "Drum take") + ext;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  for (const row of [3,2,1,0]) for (let col = 0; col < 4; col++) {
    const slot = row * 4 + col, pad = pads.get(first + slot);
    const button = document.createElement("button");
    button.className = "pad";
    const label = document.createElement("span"), role = document.createElement("strong");
    label.textContent = layout.bank + String(slot + 1).padStart(2,"0") + " · " + shortcuts[slot];
    role.textContent = pad?.role.replaceAll("_"," ") || "Empty";
    button.append(label, role);
    if (pad) {
      button.title = "MIDI note " + pad.note + "\n" + pad.layers.map(l => l.low + "–" + l.high + " " + l.sample).join("\n");
      if (Number.isInteger(pad.color)) button.style.setProperty("--pad","#" + (pad.color & 0xffffff).toString(16).padStart(6,"0"));
      button.onpointerdown = safely(e => { if (e.button === 0) return strike(pad,e.shiftKey ? 40 : +$("velocity").value); });
      button.onclick = safely(e => { if (e.detail === 0) return strike(pad,+$("velocity").value); });
      buttons.set(pad.pad, button);
    } else button.disabled = true;
    $("pads").appendChild(button);
  }
  document.addEventListener("keydown", safely(e => {
    if (e.repeat || e.ctrlKey || e.metaKey || e.altKey || /INPUT|SELECT|TEXTAREA/.test(e.target.tagName)) return;
    const key = e.code.replace(/^(Key|Digit)/,"");
    const index = key.length === 1 ? shortcuts.indexOf(key) : -1;
    if (index >= 0 && pads.has(first + index)) return strike(pads.get(first + index), e.shiftKey ? 40 : +$("velocity").value);
  }));
  let access, input;
  const inputNotes = new Map();
  for (const pad of pads.values()) {
    const sameNote = inputNotes.get(pad.note) || [];
    sameNote.push(pad);
    inputNotes.set(pad.note, sameNote);
  }
  function midiStatus(text) { $("midi-status").textContent = text; }
  function midiHit(event) {
    const [status, note, velocity] = event.data;
    if ((status & 0xf0) !== 0x90 || !velocity) return;
    const channel = (status & 15) + 1;
    const filter = Number($("midi-channel").value);
    if (filter && channel !== filter) return;
    const matches = inputNotes.get(note) || [];
    if (matches.length !== 1) {
      midiStatus(matches.length ? "Note " + note + " matches several pads in this bank." :
                 "Note " + note + " is outside bank " + layout.bank + ". Hover over a pad for its MIDI note.");
      return;
    }
    const pad = matches[0];
    const arrival = ctx.currentTime - Math.max(0, performance.now() - event.timeStamp) / 1000;
    midiStatus("Channel " + channel + " · note " + note + " · velocity " + velocity);
    strike(pad, velocity, arrival).catch(error => midiStatus(error.message));
  }
  function releaseInput() {
    if (input) {
      input.onmidimessage = null;
      input.close().catch(error => midiStatus(error.message));
      input = undefined;
    }
  }
  function listInputs() {
    const ports = Array.from(access.inputs.values()).filter(port => port.state === "connected");
    if (input && !ports.includes(input)) {
      releaseInput();
      midiStatus("Input disconnected. Choose a connected input to resume.");
    }
    $("midi-port").replaceChildren(new Option("Off",""));
    for (const p of ports) $("midi-port").add(new Option(p.name || p.manufacturer || p.id,p.id));
    $("midi-port").value = input?.id || "";
    if (!ports.length) midiStatus("No connected MIDI inputs. Connect a controller or use the computer keyboard.");
  }
  for (let n = 1; n <= 16; n++) $("midi-channel").add(new Option(String(n),String(n)));
  $("connect-midi").onclick = async () => {
    try {
      if (!navigator.requestMIDIAccess) throw Error("MIDI input is unavailable in this browser. Use the on-screen pads or keyboard.");
      if (!access) access = await navigator.requestMIDIAccess({sysex:false});
      await audio();
      access.onstatechange = listInputs;
      midiStatus("Choose an input to play this bank.");
      listInputs();
    } catch (error) { midiStatus(error.message); }
  };
  $("midi-port").onchange = () => {
    const id = $("midi-port").value;
    releaseInput();
    input = access?.inputs.get(id);
    if (input) input.onmidimessage = midiHit;
    midiStatus(input ? "Listening to " + (input.name || input.id) : "MIDI input off.");
  };
  $("enable").onclick = safely(async () => { await audio(); report("Ready to play."); });
  $("play").onclick = safely(() => transport(false));
  $("record").onclick = safely(() => transport(true));
  $("stop").onclick = () => { stop(); report("Stopped."); };
  $("name").onchange = () => { const name = $("name").value.trim(); if (name) { take.name = name; hasEdits = true; } refresh(); };
  for (const id of ["tempo","bars"]) $(id).onchange = safely(() => {
    const updated = {...take, [id]: Number($(id).value)};
    try { validate(updated); } catch { refresh(); throw Error("Choose a valid tempo and enough bars to keep all recorded hits."); }
    remember(); take = updated; hasEdits = true; refresh();
  });
  $("open").onclick = () => $("file").click();
  $("file").onchange = safely(async () => {
    const file = $("file").files[0];
    $("file").value = "";
    if (!file) return;
    const next = JSON.parse(await file.text());
    validate(next);
    stop(); remember(); take = next; hasEdits = false; refresh(); report("Opened " + file.name);
  });
  $("undo").onclick = () => { if (history.length) { take = history.pop(); hasEdits = true; refresh(); report("Undid last change."); } };
  $("clear").onclick = () => { remember(); take.events = []; hasEdits = true; refresh(); report("Cleared hits. Undo restores them."); };
  $("save").onclick = () => { download(JSON.stringify(take,null,2)+"\n","application/json",".take.json"); hasEdits = false; report("Saved editable take."); };
  $("midi").onclick = () => { download(midi(),"audio/midi",".mid"); report("Saved MIDI."); };
  window.addEventListener("beforeunload", e => { if (hasEdits) { e.preventDefault(); e.returnValue = ""; } });
  refresh();
})();
