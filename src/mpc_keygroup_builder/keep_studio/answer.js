// Compose in seconds so the player's microtiming survives conversion to take ticks.
"use strict";
function answerTrack(seed, tracks, variation, capture) {
  const { track, events, seconds, beat } = seed;
  const notes = capture.notes(events).map((n) => ({
    key: n.key,
    velocity: n.velocity,
    at: (n.start * seconds) / capture.END,
    end: (n.end * seconds) / capture.END,
  }));
  if (!notes.length) throw Error("Play at least one note for Answer Track.");
  const attacks = [];
  for (const n of notes) {
    const last = attacks.at(-1);
    if (last && n.at - last.at < 0.045) {
      last.keys.push(n.key);
      last.end = Math.max(last.end, n.end);
      last.velocity = Math.max(last.velocity, n.velocity);
    } else
      attacks.push({
        at: n.at,
        end: n.end,
        keys: [n.key],
        velocity: n.velocity,
      });
  }
  const drum = tracks[track].drum;
  const chord = attacks.some((a) => a.keys.length > 1);
  const bass = /bass|sub smooth/i.test(track);
  const preference = drum
    ? ["Pluck Bass", "Wurli"]
    : bass
      ? ["Wurli", "Main Drums"]
      : chord
        ? ["Pluck Bass", "Main Drums"]
        : ["Main Drums", "Pluck Bass"];
  const target = preference.find((n) => n !== track && tracks[n]?.zones.length);
  if (!target)
    throw Error("The Scratchpad needs another playable answer instrument.");
  const kit = tracks[target].drum;
  const accent = attacks.reduce((a, b) => (a.velocity > b.velocity ? a : b));
  const longest = attacks.reduce((a, b) =>
    a.end - a.at >= b.end - b.at ? a : b,
  );
  const reading = variation % 3;
  // Busy parts invite space. Keep the accent even if it lands late.
  const ranked = [...attacks].sort((a, b) => b.velocity - a.velocity);
  const limit = attacks.length > 7 ? 3 : 5;
  let motif =
    attacks.length > limit
      ? [...new Set([accent, ...ranked.slice(0, limit - 1)])].sort(
          (a, b) => a.at - b.at,
        )
      : attacks.slice();
  const stop = Math.max(beat * 1.5, seconds);
  let description = "Echoes the accents";
  if (reading === 1) {
    description = "Answers in the gaps";
    let occupied = 0;
    const gaps = [];
    for (const a of attacks) {
      if (a.at - occupied >= beat * 0.2)
        gaps.push({
          at: occupied + (a.at - occupied) * 0.5,
          width: a.at - occupied,
          ref: a,
        });
      occupied = Math.max(occupied, drum ? a.at + beat * 0.16 : a.end);
    }
    const tail = Math.max(stop, occupied + beat * 0.8);
    gaps.push({
      at: occupied + beat * 0.25,
      width: tail - occupied,
      ref: accent,
    });
    motif = gaps
      .sort((a, b) => b.width - a.width)
      .slice(0, 3)
      .sort((a, b) => a.at - b.at)
      .map((g) => ({ ...g.ref, at: g.at }));
  } else if (reading === 2) {
    description = "Turns the phrase around";
    motif = motif.map((a, i, all) => ({
      ...all[all.length - 1 - i],
      at: Math.max(0, all.at(-1).at - all[all.length - 1 - i].at) + beat * 0.25,
    }));
  } else if (chord && attacks.length === 1) {
    description = "Moves through your chord";
    motif = [0, 0.5, 1.25].map((b) => ({ ...longest, at: b * beat }));
  }
  const tones = [...new Set(notes.map((n) => n.key))];
  const result = [];
  for (const [i, a] of motif.entries()) {
    const velocity = Math.max(
      30,
      Math.min(115, Math.round(a.velocity * (reading === 1 ? 0.72 : 0.86))),
    );
    const zones = tracks[target].zones.filter(
      (z) => velocity >= z.low && velocity <= z.high,
    );
    let key;
    if (kit) {
      const role =
        a === longest || motif.length === 1
          ? "kick.primary"
          : a.velocity >= accent.velocity
            ? "snare.primary"
            : i % 2
              ? "hihat.closed"
              : "kick.primary";
      key = (
        zones.find((z) => z.role === role) ??
        zones.find((z) => z.role === "kick.primary") ??
        zones[0]
      )?.root;
    } else {
      const base = target === "Pluck Bass" ? 36 : 60;
      const pitch = drum
        ? [0, 7, 3][(i + reading + (a === accent ? 1 : 0)) % 3]
        : chord
          ? tones[(i + reading) % tones.length] % 12
          : a.keys[0] % 12;
      const desired = base + pitch;
      const playable = Array.from({ length: 128 }, (_, n) => n).filter(
        (n) => n % 12 === pitch && zones.some((z) => z.lo <= n && n <= z.hi),
      );
      key = playable.sort(
        (a, b) => Math.abs(a - desired) - Math.abs(b - desired),
      )[0];
    }
    if (key === undefined) continue;
    const duration = Math.min(
      kit ? 0.12 : beat * 0.75,
      Math.max(0.05, (motif[i + 1]?.at ?? a.at + beat) - a.at - 0.015),
    );
    result.push({ at: a.at, key, velocity, duration });
  }
  if (!result.length)
    throw Error("The answer falls outside this instrument's playable range.");
  return { target, notes: result, description };
}

// Put the original MIDI and the auditioned answer on one shared loop timeline.
function answerPair(seed, reply, offset, capture) {
  const end =
    Math.max(
      seed.seconds,
      offset + Math.max(...reply.notes.map((n) => n.at + n.duration)),
    ) +
    seed.beat * 0.5;
  const bar = seed.beat * 4,
    seconds = Math.ceil(end / bar) * bar;
  if (seconds > 120)
    throw Error(
      "Try a shorter phrase so the conversation fits a two-minute take.",
    );
  const tick = (t) => Math.round((t / seconds) * capture.END);
  const original = seed.events.map(([t, ...msg]) => [
    tick((t / capture.END) * seed.seconds),
    ...msg,
  ]);
  const events = [];
  for (const n of reply.notes) {
    const start = tick(offset + n.at);
    events.push(
      [start, 144, n.key, n.velocity],
      [Math.max(start + 1, tick(offset + n.at + n.duration)), 128, n.key, 0],
    );
  }
  events.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  return {
    seconds,
    layers: [
      { track: seed.track, events: original },
      { track: reply.target, events },
    ],
  };
}
if (typeof module !== "undefined") module.exports = { answerTrack, answerPair };
