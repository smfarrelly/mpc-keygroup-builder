const assert = require("node:assert/strict");
const P = require("../src/mpc_keygroup_builder/keep_studio/pad-melody.js");
const C = require("../src/mpc_keygroup_builder/keep_studio/capture.js");
const pitches = P.pitches("C2, Eb2 G2");
assert.deepEqual(pitches, [36, 39, 43]);
assert.deepEqual(P.pitches("0, C#3 Bb3 G9"), [0, 49, 58, 127]);
for (const bad of ["", "Ab", "128", "G#9", "C2 ".repeat(17)])
  assert.throws(() => P.pitches(bad));
const hits = [
  { time: 1, velocity: 89 },
  { time: 1.123, velocity: 32 },
  { time: 1.36, velocity: 119 },
  { time: 1.9, velocity: 70 },
];
const line = P.line(hits, pitches, 0.5);
assert.deepEqual(
  line.map((n) => n.key),
  [36, 36, 39, 43],
);
const notes = C.notes(P.events(line, 1, 2, C.END));
assert.deepEqual(
  notes.map((n) => n.velocity),
  hits.map((h) => h.velocity),
);
assert.equal(notes[0].end, notes[1].start);
assert(notes[1].end - notes[1].start < notes[2].end - notes[2].start);
assert.deepEqual(
  notes.map((n) => n.start),
  hits.map((h) => Math.round(((h.time - 1) * C.END) / 2)),
);
const revoiced = P.line(hits, [50, 55], 0.5);
assert.deepEqual(
  revoiced.map((n) => n.key),
  [50, 50, 55, 50],
);
const original = P.events(line, 1, 2, C.END);
const moved = C.notes(P.moveHit(original, C.END - 200, C));
assert.equal(moved.at(-1).start, C.END - 200);
assert.equal(moved.at(-1).key, 36);
assert.deepEqual(C.notes(original), notes);
