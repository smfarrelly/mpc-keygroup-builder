const assert = require("node:assert/strict");
const {
  History,
  notes,
  aligned,
  window4,
  END,
} = require("../src/mpc_keygroup_builder/keep_studio/capture.js");
const h = new History();
for (const e of [
  [0, 144, 60, 51],
  [0.25, 176, 64, 101],
  [0.4, 128, 60, 27],
  [0.75, 144, 64, 82],
  [2, 176, 64, 0],
  [2.75, 128, 64, 40],
  [3.5, 144, 67, 100],
  [5.5, 128, 67, 20],
])
  h.add(e);
h.prune(0.9);
const phrase = h.slice(1, 5);
assert.deepEqual(phrase.slice(0, 4), [
  [0, 176, 64, 101],
  [0, 144, 60, 51],
  [0, 128, 60, 0],
  [0, 144, 64, 82],
]);
assert.deepEqual(notes(phrase), [
  { start: 0, end: 3840, key: 60, velocity: 51 },
  { start: 0, end: 6720, key: 64, velocity: 82 },
  { start: 9600, end: END, key: 67, velocity: 100 },
]);
assert.deepEqual(window4(8.9, 120), [0, 8]);
const drums = new History();
for (const [t, key] of [
  [1, 36],
  [2.1, 38],
  [4.1, 40],
  [8.1, 42],
]) {
  drums.add([t, 144, key, 90]);
  drums.add([t + 0.1, 128, key, 0]);
}
assert.deepEqual(
  notes(aligned(drums, 2, 10, 0, true)).map((n) => n.key),
  [42, 38, 40],
);
assert.equal(notes(drums.slice(2, 10, true)).length, 3);
const held = new History();
held.add([0, 144, 60, 100]);
held.add([5, 128, 60, 20]);
assert.deepEqual(held.phrase(6), [0, 5.06]);
held.add([9, 144, 66, 70]);
held.add([9.5, 128, 66, 0]);
assert.deepEqual(held.phrase(10), [9, 9.56]);
const taps = [
  [80, 144, 70, 97],
  [290, 128, 70, 0],
];
assert.deepEqual(notes(taps, 1), [
  { start: 0, end: 210, key: 70, velocity: 97 },
]);
assert.equal(taps[0][0], 80);
