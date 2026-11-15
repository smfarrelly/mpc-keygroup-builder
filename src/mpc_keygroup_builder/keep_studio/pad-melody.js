"use strict";
const PadMelody = (() => {
  const names = [
    "C",
    "C#",
    "D",
    "D#",
    "E",
    "F",
    "F#",
    "G",
    "G#",
    "A",
    "A#",
    "B",
  ];
  const label = (n) => names[n % 12] + (Math.floor(n / 12) - 1);
  function pitches(value) {
    const tokens = value.trim().split(/[\s,]+/);
    if (tokens.length > 16) throw Error("Choose up to 16 pitches.");
    return tokens.map((token) => {
      const m = /^([a-g])([#b]?)(-?\d)$/i.exec(token);
      const n = m
        ? (Number(m[3]) + 1) * 12 +
          names.indexOf(m[1].toUpperCase()) +
          (m[2] === "#" ? 1 : m[2] === "b" ? -1 : 0)
        : /^\d{1,3}$/.test(token)
          ? Number(token)
          : -1;
      if (n < 0 || n > 127)
        throw Error("Enter note names such as C2 Eb2 G2, or MIDI notes 0–127.");
      return n;
    });
  }
  function line(
    hits,
    pitches,
    beat,
    cursor = { step: 0, previous: pitches[0] },
  ) {
    return hits.map((hit) => advance(cursor, hit, pitches, beat));
  }
  function advance(cursor, hit, pitches, beat) {
    const ghost = hit.velocity < 50;
    const key = ghost
      ? cursor.previous
      : pitches[cursor.step++ % pitches.length];
    cursor.previous = key;
    return { ...hit, key, duration: beat * (ghost ? 0.14 : 0.62) };
  }
  function events(notes, start, seconds, end) {
    const result = [];
    for (const [i, n] of notes.entries()) {
      const tick = Math.min(
        end - 1,
        Math.max(0, Math.round(((n.time - start) / seconds) * end)),
      );
      const until = Math.min(
        n.time + n.duration,
        notes[i + 1]?.time ?? Infinity,
        start + seconds,
      );
      if (until <= n.time) continue;
      const off = Math.min(
        end,
        Math.max(tick + 1, Math.round(((until - start) / seconds) * end)),
      );
      result.push([tick, 144, n.key, n.velocity], [off, 128, n.key, 0]);
    }
    return result.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  }
  function moveHit(original, tick, capture) {
    const notes = capture.notes(original);
    if (!notes.length) throw Error("The melody is empty.");
    const distance = (n) => {
      const d = Math.abs(tick - n.start);
      return Math.min(d, capture.END - d);
    };
    const closest = notes.reduce((a, b) =>
      distance(a) <= distance(b) ? a : b,
    );
    const shifted = notes
      .map((n) => ({
        time: n === closest ? tick : n.start,
        key: n.key,
        velocity: n.velocity,
        duration: n.end - n.start,
      }))
      .sort((a, b) => a.time - b.time);
    return events(shifted, 0, capture.END, capture.END);
  }
  return { label, pitches, line, advance, events, moveHit };
})();
if (typeof module !== "undefined") module.exports = PadMelody;
