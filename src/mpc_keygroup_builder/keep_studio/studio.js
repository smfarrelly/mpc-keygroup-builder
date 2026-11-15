"use strict";
(async () => {
  const $ = (id) => document.getElementById(id),
    msg = (text) => ($("status").textContent = text);
  const tracks = await (await fetch("/catalog")).json();
  for (const name of Object.keys(tracks))
    $("track").add(new Option(name, name));
  $("track").value = tracks.Wurli ? "Wurli" : Object.keys(tracks)[0];
  const keys = "awsedftgyhujkolp",
    buffers = new Map(),
    live = new Map(),
    sustained = new Set(),
    sources = new Set(),
    histories = new Map(),
    pressed = new Map();
  let listening = false,
    firstNote = null,
    lastInput = 0,
    answerSeed = null,
    answerOffset = 0,
    followingChord = false,
    lastReply = null,
    variation = 0,
    pair = null,
    audition = null;
  let clickOrigin = 0;
  let ctx,
    running = false,
    origin = 0,
    anchor = null,
    beatIndex = 0,
    nextLayer = [],
    clockTimer,
    lastPhrase = null,
    pedal = false,
    loading = false,
    epoch = 0;
  let idea = {
    format: "keep-that-take/1",
    name: "My idea",
    seconds: 8,
    layers: [],
  };
  const current = () => $("track").value;
  const now = () => ctx.currentTime - origin;
  function history(name) {
    if (!histories.has(name)) histories.set(name, new Capture.History());
    return histories.get(name);
  }
  async function buffer(id) {
    if (!buffers.has(id))
      buffers.set(
        id,
        (async () => {
          const response = await fetch("/sample/" + id);
          if (!response.ok)
            throw Error("Could not load the instrument sample.");
          return ctx.decodeAudioData(await response.arrayBuffer());
        })().catch((e) => {
          buffers.delete(id);
          throw e;
        }),
      );
    return buffers.get(id);
  }
  function init() {
    if (!ctx) ctx = new AudioContext({ sampleRate: 44100 });
    return ctx.resume();
  }
  function stopVoice(v, t) {
    if (!v || v.releaseAt <= t) return;
    v.releaseAt = t;
    const when = Math.max(ctx.currentTime, t);
    v.gain.gain.cancelScheduledValues(when);
    v.gain.gain.setTargetAtTime(0, when, 0.006);
    v.source.stop(when + 0.045);
  }
  function silence() {
    ++epoch;
    for (const v of sources) {
      try {
        v.source.stop();
      } catch {}
    }
    live.clear();
    sustained.clear();
    pressed.clear();
    pedal = false;
    for (const b of $("surface").children) b.classList.remove("down");
  }
  function zone(name, n, v) {
    return tracks[name].zones.find(
      (z) => n >= z.lo && n <= z.hi && v >= z.low && v <= z.high,
    );
  }
  async function sound(name, n, vel, when, duration, token, groupScope) {
    const z = zone(name, n, vel);
    if (!z) return;
    const generation = epoch,
      audio = await buffer(z.id);
    if (generation !== epoch || token?.cancel) return;
    const start = Math.max(when, ctx.currentTime);
    const source = ctx.createBufferSource(),
      gain = ctx.createGain();
    const rate = 2 ** (((tracks[name].drum ? 0 : n - z.root) + z.tune) / 12);
    source.buffer = audio;
    source.playbackRate.value = rate;
    gain.gain.value = (vel / 127) * 0.68;
    source.connect(gain).connect(ctx.destination);
    const v = {
      source,
      gain,
      name,
      group: z.group,
      pad: z.pad,
      groupScope,
      start,
    };
    if (z.group || z.mono)
      for (const old of sources)
        if (
          ((z.group && old.group === z.group) ||
            (z.mono && old.pad === z.pad)) &&
          old.name === name &&
          old.groupScope === groupScope &&
          old.start <= start
        )
          stopVoice(old, start);
    sources.add(v);
    if (token) token.voice = v;
    source.onended = () => {
      sources.delete(v);
      gain.disconnect();
      source.disconnect();
    };
    const offset = Math.min(audio.duration, z.start / (z.rate || 44100));
    const end = Math.min(audio.duration, (z.end + 1) / (z.rate || 44100));
    if (end <= offset) {
      sources.delete(v);
      return;
    }
    source.start(start, offset, end - offset);
    if (!tracks[name].drum && duration !== null) stopVoice(v, start + duration);
  }
  function safe(fn) {
    return (...args) =>
      Promise.resolve()
        .then(() => fn(...args))
        .catch((e) => msg(e.message));
  }
  function record(status, k, v, received = performance.now()) {
    if (!running) return;
    const name = current(),
      hist = history(name),
      t = Math.max(
        0,
        hist.events.at(-1)?.[0] ?? 0,
        now() - Math.max(0, performance.now() - received) / 1000,
      );
    if (followingChord && status === 144) finishChord(t);
    hist.add([t, status, k, v]);
    hist.prune(t - 121);
    if (listening) {
      if (status === 144 && firstNote === null) firstNote = t;
      if (firstNote !== null) lastInput = t;
    }
    if (status === 176) {
      pedal = v >= 64;
      if (!pedal) {
        for (const token of sustained) release(token);
        sustained.clear();
      }
      return;
    }
    if (status === 144) {
      if (live.has(k)) release(live.get(k));
      for (const token of sustained)
        if (token.note === k) {
          release(token);
          sustained.delete(token);
        }
      const token = { note: k, drum: tracks[name].drum };
      live.set(k, token);
      const when = ctx.currentTime;
      padStrike(k, v, t, when);
      sound(name, k, v, when, null, token, "live").catch((e) => msg(e.message));
    } else if (live.has(k)) {
      if (groove?.down.delete(k)) groove.drums.add([t, 128, k, 0]);
      const token = live.get(k);
      live.delete(k);
      if (pedal && !token.drum) sustained.add(token);
      else release(token);
    }
    const b = $("surface").querySelector('[data-note="' + k + '"]');
    b?.classList.toggle("down", status === 144);
  }
  function release(token) {
    if (token.drum) return;
    token.cancel = true;
    stopVoice(token.voice, ctx.currentTime);
  }
  function closeInput() {
    if (!running) return;
    for (const k of [...live.keys()]) record(128, k, 0);
    record(176, 64, 0);
    pressed.clear();
  }
  let activeName = current();
  function surface() {
    const t = tracks[current()];
    $("octave").disabled = t.drum;
    const notes = t.drum
      ? [...new Set(t.zones.map((z) => z.root))].slice(0, 16)
      : Array.from(
          { length: 16 },
          (_, i) => 60 + 12 * Number($("octave").value) + i,
        );
    const root = $("surface");
    root.replaceChildren();
    notes.forEach((n, i) => {
      const b = document.createElement("button");
      b.dataset.note = n;
      b.textContent = t.drum
        ? "Pad " + (i + 1)
        : ["C", "C♯", "D", "D♯", "E", "F", "F♯", "G", "G♯", "A", "A♯", "B"][
            n % 12
          ] +
          (Math.floor(n / 12) - 1);
      b.onpointerdown = (e) => {
        e.preventDefault();
        b.setPointerCapture(e.pointerId);
        record(144, n, e.shiftKey ? 38 : 96);
      };
      b.onpointerup = b.onpointercancel = () => record(128, n, 0);
      root.append(b);
    });
  }
  $("track").onchange = () => {
    const next = current();
    $("track").value = activeName;
    closeInput();
    $("track").value = next;
    clearAnswer();
    resetGroove();
    activeName = next;
    lastPhrase = null;
    surface();
    if (ctx) warm(next).catch((e) => msg(e.message));
  };
  $("octave").onchange = () => {
    closeInput();
    surface();
    if (ctx) warm(current()).catch((e) => msg(e.message));
  };
  async function warm(name) {
    const ids = [
      ...new Set(
        [...$("surface").children]
          .map((b) => zone(name, +b.dataset.note, 96)?.id)
          .filter((i) => i !== undefined),
      ),
    ];
    await Promise.all(ids.map(buffer));
  }
  for (const [name, t] of Object.entries(tracks))
    if (!t.drum) $("voice").add(new Option(name, name));
  if (tracks["Pluck Bass"]) $("voice").value = "Pluck Bass";
  let groove = null,
    grooveBusy = false,
    learning = false,
    learned = [],
    conductor = false,
    melodyVoice = null,
    groovePreview = null,
    moveUndo = null;
  let learnTrigger = false,
    triggerBinding = null,
    midiAccess = null;
  try {
    triggerBinding = JSON.parse(localStorage.getItem("pad-melody-trigger"));
  } catch {}
  function updateTrigger() {
    $("learnTrigger").textContent = learnTrigger
      ? "Cancel trigger learn"
      : "Learn MIDI kick trigger";
    $("forgetTrigger").disabled = !triggerBinding;
  }
  $("learnTrigger").onclick = safe(async () => {
    if (learnTrigger) {
      learnTrigger = false;
      updateTrigger();
      return;
    }
    closeInput();
    await connectMidi();
    learnTrigger = true;
    learning = false;
    $("learnPitches").textContent = "Play pitches on MIDI";
    updateTrigger();
    $("grooveStatus").textContent =
      "Strike the external pad you want to use as a kick.";
  });
  $("forgetTrigger").onclick = () => {
    closeInput();
    triggerBinding = null;
    learnTrigger = false;
    localStorage.removeItem("pad-melody-trigger");
    updateTrigger();
    $("grooveStatus").textContent = "Removed the MIDI kick assignment.";
  };
  function stopMelodyPreview() {
    if (!groovePreview) return;
    groovePreview.cancel = true;
    for (const v of sources)
      if (v.groupScope === groovePreview) v.source.stop();
    groovePreview = null;
  }
  function resetGroove() {
    stopMelodyPreview();
    groove = null;
    conductor = false;
    learning = false;
    learnTrigger = false;
    updateTrigger();
    $("learnPitches").textContent = "Play pitches on MIDI";
    if (melodyVoice) {
      melodyVoice.cancel = true;
      stopVoice(melodyVoice.voice, ctx.currentTime);
      melodyVoice = null;
    }
    $("grooveStatus").textContent =
      "Each strike plays a drum and the next pitch. Soft hits repeat the previous pitch.";
  }
  function grooveControls() {
    updateTrigger();
    const canMove = idea.layers.some((l) => l.padMelody === true);
    $("accompany").disabled =
      grooveBusy || loading || idea.layers.length > 126 || !$("voice").value;
    $("accompany").textContent = groove
      ? groove.playing
        ? "Finish playing"
        : "Resume playing"
      : "Play with pads";
    $("keepGroove").disabled = $("remelody").disabled =
      grooveBusy || !groove?.notes.length;
    $("voice").disabled = $("trigger").disabled = !!groove || grooveBusy;
    $("undoMove").disabled = !moveUndo || !idea.layers.includes(moveUndo.layer);
    $("conduct").disabled =
      !running || !!groove || !canMove || !tracks[current()].drum;
    $("conduct").textContent = conductor
      ? "Cancel kick move"
      : "Move a melody hit with next kick";
  }
  async function pitchBank() {
    const pitches = PadMelody.pitches($("pitches").value),
      name = $("voice").value;
    await init();
    const ids = new Set();
    for (const n of pitches) {
      const zones = tracks[name].zones.filter((z) => z.lo <= n && n <= z.hi);
      if (!zones.length)
        throw Error(name + " cannot play " + PadMelody.label(n) + ".");
      for (const z of zones) ids.add(z.id);
    }
    await Promise.all([...ids].map(buffer));
    return pitches;
  }
  function padStrike(n, velocity, time, when) {
    const z = zone(current(), n, velocity);
    if (!z) return;
    if (conductor && z.role === "kick.primary") {
      const layer = idea.layers.findLast((l) => l.padMelody === true);
      const phase =
        (((time - anchor) % idea.seconds) + idea.seconds) % idea.seconds;
      const tick = Math.min(
        Capture.END - 1,
        Math.round((phase / idea.seconds) * Capture.END),
      );
      moveUndo = { layer, events: layer.events };
      layer.events = PadMelody.moveHit(layer.events, tick, Capture);
      conductor = false;
      persist();
      refresh();
      $("grooveStatus").textContent =
        "Moved the nearest melody hit to this kick. Listen on the next loop.";
    }
    if (!groove || !groove.playing) return;
    if (groove.start === null) groove.start = time;
    const bar = 240 / +$("tempo").value;
    if (
      time - groove.start >= Math.floor(120 / bar) * bar ||
      groove.hits.length >= 8192
    ) {
      groove.playing = false;
      $("grooveStatus").textContent =
        "Capture full. Keep the groove or audition new pitches.";
      return;
    }
    if (groove.down.has(n)) groove.drums.add([time, 128, n, 0]);
    groove.down.add(n);
    groove.drums.add([time, 144, n, velocity]);
    // Drum one-shots need a release for MIDI playback, supplied by slice or actual key-up.
    if ($("trigger").value === "kick" && z.role !== "kick.primary") return;
    stopMelodyPreview();
    const hit = { time, velocity };
    groove.hits.push(hit);
    const note = PadMelody.advance(
      groove.cursor,
      hit,
      groove.pitches,
      60 / +$("tempo").value,
    );
    groove.notes.push(note);
    if (melodyVoice) {
      melodyVoice.cancel = true;
      stopVoice(melodyVoice.voice, when);
    }
    melodyVoice = {};
    sound(
      $("voice").value,
      note.key,
      velocity,
      when,
      note.duration,
      melodyVoice,
      "pad-melody",
    ).catch((e) => msg(e.message));
    $("grooveStatus").textContent =
      $("voice").value +
      " · " +
      PadMelody.label(note.key) +
      " · velocity " +
      velocity;
    grooveControls();
  }
  function groovePair() {
    const bar = 240 / +$("tempo").value,
      start = groove.start;
    const last = groove.notes.at(-1);
    const end = Math.max(
      last.time + last.duration,
      groove.drums.events.filter((e) => e[1] === 144).at(-1)[0] + 0.05,
    );
    if (idea.layers.length) {
      const seconds = idea.seconds;
      const melodic = new Capture.History();
      for (const [i, n] of groove.notes.entries()) {
        const off = Math.min(
          n.time + n.duration,
          groove.notes[i + 1]?.time ?? Infinity,
        );
        if (off <= n.time) continue;
        melodic.add([n.time, 144, n.key, n.velocity]);
        melodic.add([off, 128, n.key, 0]);
      }
      const layers = [
        {
          track: current(),
          events: Capture.aligned(
            groove.drums,
            end - seconds,
            end,
            anchor,
            true,
          ),
        },
        {
          track: $("voice").value,
          padMelody: true,
          events: Capture.aligned(melodic, end - seconds, end, anchor, false),
        },
      ];
      if (layers.some((l) => !l.events.some((e) => e[1] === 144)))
        throw Error("Play a trigger in the most recent loop before keeping.");
      return { seconds, layers };
    }
    const seconds =
      Math.min(Math.floor(120 / bar), Math.ceil((end - start) / bar)) * bar;
    return {
      seconds,
      layers: [
        {
          track: current(),
          events: groove.drums.slice(start, start + seconds, true),
        },
        {
          track: $("voice").value,
          events: PadMelody.events(groove.notes, start, seconds, Capture.END),
          padMelody: true,
        },
      ],
    };
  }
  $("accompany").onclick = safe(async () => {
    if (groove) {
      groove.playing = !groove.playing;
      $("grooveStatus").textContent = groove.playing
        ? "Listening to pads."
        : "Rhythm captured. Keep it or audition new pitches.";
      grooveControls();
      $("accompany").textContent = groove.playing
        ? "Finish playing"
        : "Resume playing";
      return;
    }
    grooveBusy = true;
    refresh();
    try {
      const drum = tracks[current()].drum
        ? current()
        : Object.keys(tracks).find((n) => tracks[n].drum);
      if (!drum) throw Error("Choose a Scratchpad with a drum track.");
      if (current() !== drum) {
        $("track").value = drum;
        $("track").onchange();
      }
      clearAnswer();
      conductor = false;
      if (!running) await startClock();
      const pitches = await pitchBank();
      if (!running || current() !== drum) return;
      groove = {
        playing: true,
        start: null,
        pitches,
        cursor: { step: 0, previous: pitches[0] },
        hits: [],
        notes: [],
        down: new Set(),
        drums: new Capture.History(),
      };
      $("grooveStatus").textContent =
        "Play a pad. The melody follows your hits.";
    } finally {
      grooveBusy = false;
      refresh();
    }
  });
  $("remelody").onclick = safe(async () => {
    const take = groove;
    grooveBusy = true;
    grooveControls();
    try {
      const pitches = await pitchBank();
      if (take !== groove) return;
      groove.pitches = pitches;
      groove.cursor = { step: 0, previous: pitches[0] };
      groove.notes = PadMelody.line(
        groove.hits,
        pitches,
        60 / +$("tempo").value,
        groove.cursor,
      );
      const preview = groovePair();
      stopMelodyPreview();
      groovePreview = {};
      const start = ctx.currentTime + 0.05;
      for (const l of preview.layers)
        playLayer(l, start, preview.seconds, groovePreview, 0, groovePreview);
      $("grooveStatus").textContent =
        "Same rhythm, new pitches. Keep groove saves this version.";
    } finally {
      grooveBusy = false;
      grooveControls();
    }
  });
  $("keepGroove").onclick = safe(() => {
    const chosen = groovePair();
    closeInput();
    resetGroove();
    clearAnswer();
    if (!idea.layers.length) {
      idea.seconds = chosen.seconds;
      idea.tempo = +$("tempo").value;
      idea.free = true;
      $("snap").value = 0;
      anchor = now() + 0.12;
      clickOrigin = anchor;
      beatIndex = 0;
    }
    const next =
      anchor +
      Math.max(0, Math.ceil((now() - anchor) / idea.seconds)) * idea.seconds;
    idea.layers.push(...chosen.layers);
    nextLayer.push(next, next);
    persist();
    refresh();
    $("grooveStatus").textContent =
      "Drums and melody kept. Arm a kick move to change the loop.";
  });
  $("undoMove").onclick = () => {
    if (!moveUndo || !idea.layers.includes(moveUndo.layer)) return;
    moveUndo.layer.events = moveUndo.events;
    moveUndo = null;
    conductor = false;
    persist();
    refresh();
    $("grooveStatus").textContent = "Restored the melody timing.";
  };
  $("conduct").onclick = () => {
    conductor = !conductor;
    grooveControls();
    $("grooveStatus").textContent = conductor
      ? "Play a kick where you want the nearest melody hit."
      : "Kick move cancelled.";
  };
  $("learnPitches").onclick = safe(async () => {
    if (!learning) {
      closeInput();
      await connectMidi();
      learnTrigger = false;
      updateTrigger();
      learned = [];
      learning = true;
    } else learning = false;
    $("learnPitches").textContent = learning
      ? "Finish pitch entry"
      : "Play pitches on MIDI";
    $("grooveStatus").textContent = learning
      ? "Play up to 16 MIDI notes, then finish pitch entry."
      : "Pitch order ready. Start playing or audition the new pitches.";
  });
  function refresh() {
    grooveControls();
    $("layers").replaceChildren(
      ...idea.layers.map((l, i) => {
        const li = document.createElement("li");
        li.textContent =
          l.track +
          " · " +
          l.events.filter((e) => e[1] === 144).length +
          " notes";
        if (tracks[l.track].drum) {
          const sel = document.createElement("select");
          sel.setAttribute(
            "aria-label",
            "Audition layer " + (i + 1) + " on kit",
          );
          for (const [name, t] of Object.entries(tracks))
            if (t.drum) sel.add(new Option(name, name));
          sel.value = l.audition || l.track;
          sel.onchange = () => {
            l.audition = sel.value;
            persist();
            msg(
              "Kit change applies on the next loop. Exports use the recorded instrument.",
            );
          };
          li.append(" ", sel);
        }
        return li;
      }),
    );
    $("undo").disabled = !idea.layers.length;
    $("answer").disabled =
      loading || grooveBusy || !!groove || !!idea.layers.length;
    $("answer").textContent = listening ? "Cancel answer" : "Answer";
    $("again").disabled = !pair || !running;
    $("both").disabled = !pair || !!idea.layers.length;
    $("keep").disabled = !running || !!groove;
    $("phrase").disabled = !!groove;
    $("start").disabled = running || loading;
    $("stop").disabled = !running;
    $("tempo").disabled = running || !!idea.layers.length;
    $("keep").textContent = idea.layers.length ? "Keep last loop" : "Keep 4";
    $("save").disabled = $("export").disabled = !idea.layers.length;
  }
  function persist() {
    idea.name = $("name").value.trim() || "My idea";
    idea.snap = +$("snap").value;
    idea.click = $("click").checked;
    try {
      localStorage.setItem("keep-take-v1", JSON.stringify(idea));
    } catch {
      msg("Browser storage is full. Use Save take to keep a copy.");
    }
  }
  function tick() {
    const t = now(),
      beat = 60 / Number($("tempo").value);
    while (clickOrigin + beatIndex * beat < t + 0.06) {
      const at = clickOrigin + beatIndex * beat;
      if ($("click").checked && at >= t - 0.05) {
        const o = ctx.createOscillator(),
          g = ctx.createGain(),
          w = Math.max(ctx.currentTime, origin + at);
        o.frequency.value = beatIndex % 4 === 0 ? 1200 : 830;
        g.gain.setValueAtTime(0.09, w);
        g.gain.exponentialRampToValueAtTime(0.0001, w + 0.035);
        o.connect(g).connect(ctx.destination);
        o.start(w);
        o.stop(w + 0.04);
      }
      beatIndex++;
    }
    for (let i = 0; i < idea.layers.length; i++) {
      if (anchor === null) continue;
      const l = idea.layers[i],
        dur = idea.seconds;
      let cursor = nextLayer[i] ?? anchor;
      while (cursor < t - 0.2) cursor += dur;
      if (cursor < t + 0.09) {
        playLayer(l, origin + cursor, dur, "layer" + i);
        cursor += dur;
      }
      nextLayer[i] = cursor;
    }
    if (
      followingChord &&
      ((!live.size && !sustained.size) || t - firstNote >= 55)
    )
      finishChord(t);
    const heldChord =
      !tracks[current()].drum &&
      live.size + sustained.size >= 2 &&
      t - lastInput >= Math.max(1, beat * 2);
    if (listening && firstNote !== null) {
      if (t - firstNote > 50) {
        clearAnswer();
        $("response").textContent = "Try a phrase under 50 seconds.";
      } else if (
        (heldChord ||
          tracks[current()].drum ||
          (!live.size && !sustained.size)) &&
        t - lastInput > Math.max(0.65, Math.min(1.2, beat * 1.5))
      ) {
        listening = false;
        followingChord = heldChord;
        const seconds = heldChord
          ? t - firstNote
          : Math.max(0.055, lastInput - firstNote + 0.004);
        answerSeed = {
          track: current(),
          events: history(current()).slice(
            firstNote,
            firstNote + seconds,
            tracks[current()].drum,
          ),
          seconds,
          beat,
        };
        auditionAnswer(false).catch(answerError);
      }
    }
    $("phase").textContent =
      "Bar " +
      (1 + Math.floor(Math.max(0, t - clickOrigin) / beat / 4)) +
      " · beat " +
      (1 + (Math.floor(Math.max(0, t - clickOrigin) / beat) % 4));
  }
  function playLayer(
    layer,
    start,
    duration,
    scope,
    snap = Number($("snap").value) / 100,
    token = null,
  ) {
    const target = layer.audition || layer.track;
    const srcPads = tracks[layer.track].zones,
      dstPads = tracks[target].zones;

    for (const n of Capture.notes(layer.events, snap)) {
      const k =
        target === layer.track
          ? n.key
          : dstPads.find(
              (z) => z.pad === srcPads.find((src) => src.root === n.key)?.pad,
            )?.root;
      if (k !== undefined)
        sound(
          target,
          k,
          n.velocity,
          start + (n.start / Capture.END) * duration,
          ((n.end - n.start) / Capture.END) * duration,
          token,
          scope,
        ).catch((e) => msg(e.message));
    }
  }
  function stop() {
    resetGroove();
    closeInput();
    clearAnswer();
    running = false;
    clearInterval(clockTimer);
    silence();
    lastPhrase = null;
    $("phase").textContent = "Clock stopped";
    refresh();
  }
  async function startClock() {
    loading = true;
    refresh();
    try {
      const bpm = Number($("tempo").value);
      if (!(bpm >= 20 && bpm <= 300))
        throw Error("Choose a tempo between 20 and 300 BPM.");
      await init();
      await warm(current());
      for (const l of idea.layers)
        await Promise.all(
          Capture.notes(l.events)
            .map((n) => zone(l.track, n.key, n.velocity))
            .filter(Boolean)
            .map((z) => buffer(z.id)),
        );
      origin = ctx.currentTime;
      running = true;
      histories.clear();
      anchor = idea.layers.length ? 0 : null;
      clickOrigin = 0;
      beatIndex = 0;
      nextLayer = [];
      tick();
      clockTimer = setInterval(tick, 25);
      msg("Listening. Play keys or pads.");
    } finally {
      loading = false;
      refresh();
    }
  }
  $("start").onclick = safe(startClock);
  $("stop").onclick = stop;

  function cancelAudition() {
    if (!audition) return;
    audition.cancel = true;
    for (const v of sources)
      if (v.groupScope === audition) {
        try {
          v.source.stop();
        } catch {}
      }
    audition = null;
  }
  function clearAnswer() {
    cancelAudition();
    listening = false;
    firstNote = null;
    answerSeed = null;
    followingChord = false;
    lastReply = null;
    pair = null;
    variation = 0;
    $("response").textContent = idea.layers.length
      ? "Start a new idea to try another exchange."
      : "Press Answer, play a short phrase, then leave a gap.";
    refresh();
  }
  function finishChord(t) {
    if (!followingChord) return;
    followingChord = false;
    const seconds = Math.max(answerSeed.seconds, t - firstNote + 0.001);
    answerSeed = {
      ...answerSeed,
      seconds,
      events: history(answerSeed.track).slice(firstNote, firstNote + seconds),
    };
    if (pair) pair = answerPair(answerSeed, lastReply, answerOffset, Capture);
  }
  function answerError(e) {
    clearAnswer();
    $("response").textContent = e.message;
  }
  async function auditionAnswer(replay) {
    cancelAudition();
    pair = null;
    refresh();
    const ticket = { cancel: false };
    audition = ticket;
    const reply = answerTrack(answerSeed, tracks, variation, Capture);
    lastReply = reply;
    $("response").textContent = "Loading " + reply.target + "…";
    const ids = reply.notes.map(
      (n) => zone(reply.target, n.key, n.velocity).id,
    );
    if (replay)
      for (const n of Capture.notes(answerSeed.events)) {
        const z = zone(answerSeed.track, n.key, n.velocity);
        if (z) ids.push(z.id);
      }
    await Promise.all([...new Set(ids)].map(buffer));
    if (ticket.cancel) return;
    if (!replay) answerOffset = Math.max(0, now() + 0.06 - firstNote);
    pair = answerPair(answerSeed, reply, answerOffset, Capture);
    const start = replay ? ctx.currentTime + 0.06 : origin + firstNote;
    if (replay)
      playLayer(pair.layers[0], start, pair.seconds, ticket, 0, ticket);
    playLayer(pair.layers[1], start, pair.seconds, ticket, 0, ticket);
    $("response").textContent = reply.target + " · " + reply.description + ".";
    refresh();
  }
  $("answer").onclick = safe(async () => {
    const wasListening = listening;
    clearAnswer();
    if (wasListening) return;
    if (!running) await startClock();
    listening = true;
    $("response").textContent =
      "Listening on " + current() + ". Play, then leave a gap.";
    refresh();
  });
  $("again").onclick = safe(async () => {
    finishChord(now());
    variation++;
    await auditionAnswer(true).catch(answerError);
  });
  $("both").onclick = () => {
    if (!pair || idea.layers.length) return;
    finishChord(now());
    const chosen = pair;
    closeInput();
    clearAnswer();
    idea.seconds = chosen.seconds;
    idea.tempo = +$("tempo").value;
    idea.free = true;
    $("snap").value = 0;
    idea.layers.push(...chosen.layers);
    anchor = now() + 0.12;
    clickOrigin = anchor;
    beatIndex = 0;
    nextLayer = [];
    persist();
    refresh();
    $("response").textContent =
      "Kept both parts. Choose an instrument to overdub.";
  };
  function keep(start, end, free) {
    if (!running) throw Error("Start the clock first.");
    if (start < -0.00001) throw Error("Play four complete bars first.");
    const hist = history(current()),
      events =
        idea.layers.length && !free
          ? Capture.aligned(hist, start, end, anchor, tracks[current()].drum)
          : hist.slice(Math.max(0, start), end, tracks[current()].drum);
    if (!events.some((e) => e[1] === 144))
      throw Error("No notes in that interval on " + current() + ".");
    if (!idea.layers.length) {
      idea.seconds = end - start;
      anchor = free
        ? now() + 0.12
        : ((Math.floor(now() / (240 / +$("tempo").value)) + 1) * 240) /
          +$("tempo").value;
      idea.tempo = +$("tempo").value;
      idea.free = free;
      if (free) {
        const bars = [...Array(150)]
          .map((_, i) => i + 1)
          .filter(
            (n) =>
              (240 * n) / idea.seconds >= 20 && (240 * n) / idea.seconds <= 300,
          )
          .sort((a, b) => Math.abs(a - 4) - Math.abs(b - 4))[0];
        if (bars) {
          idea.tempo = (240 * bars) / idea.seconds;
          $("tempo").value = idea.tempo;
        } else $("click").checked = false;
        clickOrigin = anchor;
        beatIndex = 0;
      }
    }
    if (idea.layers.length >= 128)
      throw Error("This idea already has 128 layers.");
    clearAnswer();
    idea.layers.push({ track: current(), events });
    nextLayer.push(
      anchor +
        Math.max(0, Math.ceil((now() - anchor) / idea.seconds)) * idea.seconds,
    );
    persist();
    refresh();
    msg("Kept " + current() + ". Choose another instrument and play along.");
  }
  $("keep").onclick = safe(() => {
    if (anchor === null) {
      const [s, e] = Capture.window4(now(), +$("tempo").value);
      keep(s, e, false);
    } else {
      const step = idea.free ? idea.seconds : idea.seconds / 4;
      const end = anchor + Math.floor((now() - anchor) / step) * step;
      if (end < anchor + idea.seconds - 0.00001)
        throw Error(
          "Let the first complete loop play before keeping an overdub.",
        );
      keep(end - idea.seconds, end, false);
    }
  });
  $("find").onclick = safe(() => {
    if (!running) throw Error("Start the clock and play a phrase first.");
    const h = history(current());
    h.prune(now() - 120);
    const [start, end] = h.phrase(now());
    lastPhrase = { track: current(), limit: now() };
    $("from").value = start.toFixed(3);
    $("to").value = Math.min(now(), Math.max(end, start + 0.05)).toFixed(3);
    msg("Adjust the start and end, then audition the phrase.");
  });
  function selection() {
    const a = Number($("from").value),
      b = Number($("to").value);
    if (
      !running ||
      lastPhrase?.track !== current() ||
      !(a >= 0 && b - a >= 0.05 && b - a <= 120 && b <= now() + 0.001)
    )
      throw Error(
        "Find a phrase and select 0.05–120 seconds of recent playing.",
      );
    return [a, b];
  }
  $("preview").onclick = safe(() => {
    const [a, b] = selection();
    playLayer(
      {
        track: current(),
        events: history(current()).slice(a, b, tracks[current()].drum),
      },
      ctx.currentTime + 0.05,
      b - a,
      "preview",
    );
  });
  $("phrase").onclick = safe(() => {
    const [a, b] = selection();
    if (idea.layers.length && Math.abs(b - a - idea.seconds) > 0.002)
      throw Error(
        "For overdubs use Keep last loop, or select the existing loop length.",
      );
    keep(a, b, true);
  });
  $("undo").onclick = () => {
    if (running) stop();
    idea.layers.pop();
    if (!idea.layers.length) anchor = null;
    persist();
    refresh();
  };
  $("fresh").onclick = () => {
    if (
      idea.layers.length &&
      !confirm("Start a new idea? Save a take file to keep this one.")
    )
      return;
    stop();
    idea.layers = [];
    anchor = null;
    $("name").value = "My idea";
    persist();
    refresh();
  };
  $("name").onchange = $("snap").onchange = $("click").onchange = persist;
  async function post(path, data) {
    const r = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!r.ok) throw Error(await r.text());
    return r.json();
  }
  function restore(data) {
    if (running) stop();
    idea = data;
    $("response").textContent =
      "Save this take and choose New idea to start an exchange.";
    $("name").value = data.name;
    $("tempo").value = data.tempo || 120;
    $("snap").value = data.snap || 0;
    $("click").checked = data.click ?? true;
    anchor = null;
    refresh();
  }
  $("save").onclick = safe(() => {
    persist();
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(idea)], { type: "application/json" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = idea.name + ".json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 3000);
  });
  $("open").onchange = safe(async () => {
    const f = $("open").files[0];
    if (!f) return;
    const data = JSON.parse(await f.text());
    await post("/validate", data);
    restore(data);
    persist();
    msg("Take reopened. Start the clock to play.");
    $("open").value = "";
  });
  $("export").onclick = safe(async () => {
    persist();
    const take = structuredClone(idea);
    $("export").disabled = true;
    msg("Writing project and companion samples…");
    try {
      msg("Saved project, MIDI and take to " + (await post("/export", take)));
    } finally {
      refresh();
    }
  });
  async function connectMidi() {
    if (!navigator.requestMIDIAccess)
      throw Error("Open in a Web MIDI compatible browser such as Chrome.");
    const access = (midiAccess ??= await navigator.requestMIDIAccess());
    const bind = () => {
      for (const input of access.inputs.values())
        input.onmidimessage = ({ data, timeStamp }) => {
          const [s, incoming, v] = data,
            status = s & 240;
          let k = incoming;
          if (learnTrigger) {
            if (status === 144 && v > 0) {
              triggerBinding = {
                port: input.id,
                channel: s & 15,
                note: incoming,
              };
              learnTrigger = false;
              updateTrigger();
              $("grooveStatus").textContent =
                "Learned MIDI note " +
                incoming +
                " on channel " +
                ((s & 15) + 1) +
                ". Play with pads to use it.";
              try {
                localStorage.setItem(
                  "pad-melody-trigger",
                  JSON.stringify(triggerBinding),
                );
              } catch {}
            }
            return;
          }
          if (
            !learning &&
            tracks[current()].drum &&
            (status === 144 || status === 128) &&
            triggerBinding?.port === input.id &&
            triggerBinding.channel === (s & 15) &&
            triggerBinding.note === incoming
          ) {
            k =
              tracks[current()].zones.find((z) => z.role === "kick.primary")
                ?.root ?? incoming;
          }
          if (learning) {
            if (status === 144 && v > 0 && learned.length < 16) {
              learned.push(k);
              $("pitches").value = learned.map(PadMelody.label).join(" ");
            }
            return;
          }
          if (status === 144) record(v ? 144 : 128, k, v, timeStamp);
          else if (status === 128 || (status === 176 && k === 64))
            record(status, k, v, timeStamp);
          else if (status === 176 && (k === 120 || k === 123)) closeInput();
        };
      msg(access.inputs.size + " MIDI inputs connected.");
    };
    bind();
    access.onstatechange = () => {
      closeInput();
      bind();
    };
  }
  $("midi").onclick = safe(connectMidi);
  window.addEventListener("keydown", (e) => {
    if (
      !running ||
      e.repeat ||
      e.ctrlKey ||
      e.metaKey ||
      e.altKey ||
      /INPUT|SELECT|TEXTAREA/.test(e.target.tagName)
    )
      return;
    const k = e.key.toLowerCase();
    if (k === " ") {
      e.preventDefault();
      record(176, 64, 127);
      return;
    }
    const button = $("surface").children[keys.indexOf(k)];
    if (button) {
      e.preventDefault();
      pressed.set(k, +button.dataset.note);
      record(144, +button.dataset.note, e.shiftKey ? 38 : 96);
    }
  });
  window.addEventListener("keyup", (e) => {
    const k = e.key.toLowerCase();
    if (k === " " && pedal) {
      e.preventDefault();
      record(176, 64, 0);
    }
    if (pressed.has(k)) {
      record(128, pressed.get(k), 0);
      pressed.delete(k);
    }
  });
  window.addEventListener("blur", closeInput);
  surface();
  refresh();
  try {
    const data = JSON.parse(localStorage.getItem("keep-take-v1"));
    if (data?.layers?.length) {
      await post("/validate", data);
      restore(data);
      msg("Restored your last idea. Start the clock to play.");
    }
  } catch {}
})().catch((e) => (document.getElementById("status").textContent = e.message));
