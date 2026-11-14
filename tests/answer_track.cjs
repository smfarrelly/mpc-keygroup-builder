const assert = require("node:assert/strict");
const C = require("../src/mpc_keygroup_builder/keep_studio/capture.js");
const {
  answerTrack,
  answerPair,
} = require("../src/mpc_keygroup_builder/keep_studio/answer.js");
const melodic = { drum: false, zones: [{ lo: 24, hi: 96, low: 0, high: 127 }] };
const tracks = {
  Wurli: melodic,
  "Pluck Bass": melodic,
  "Dark FM": melodic,
  "Main Drums": {
    drum: true,
    zones: ["kick.primary", "snare.primary", "hihat.closed"].map((role, i) => ({
      role,
      root: 44 + i,
      low: 0,
      high: 127,
    })),
  },
};
function seed(track, notes) {
  return {
    track,
    seconds: 1,
    beat: 0.5,
    events: notes
      .flatMap(([k, t, len, v]) => [
        [t, 144, k, v],
        [t + len, 128, k, 0],
      ])
      .sort((a, b) => a[0] - b[0]),
  };
}
const chord = seed(
  "Wurli",
  [60, 63, 67].map((k) => [k, 0, 15000, 90]),
);
const notes = seed("Pluck Bass", [
  [42, 0, 2000, 76],
  [40, 10000, 3500, 98],
]);
const taps = seed("Main Drums", [
  [44, 0, 250, 40],
  [44, 4800, 400, 65],
  [44, 10643, 270, 124],
]);
for (const [source, target] of [
  [chord, "Pluck Bass"],
  [notes, "Wurli"],
  [taps, "Pluck Bass"],
]) {
  const original = JSON.stringify(source);
  const replies = [0, 1, 2].map((i) => answerTrack(source, tracks, i, C));
  assert.equal(replies[0].target, target);
  assert.equal(new Set(replies.map((r) => JSON.stringify(r.notes))).size, 3);
  for (const r of replies) {
    const pair = answerPair(source, r, 1.3, C);
    assert.equal(pair.layers.length, 2);
    const kept = C.notes(pair.layers[1].events);
    assert.equal(kept.length, r.notes.length);
    kept.forEach((n, i) => {
      assert.equal(n.key, r.notes[i].key);
      assert.equal(n.velocity, r.notes[i].velocity);
      assert.ok(
        Math.abs((n.start / C.END) * pair.seconds - r.notes[i].at - 1.3) <
          0.001,
      );
    });
  }
  assert.equal(JSON.stringify(source), original);
}
const bass = answerTrack(chord, tracks, 0, C);
assert.deepEqual(
  bass.notes.map((n) => n.key),
  [36, 39, 43],
);
const drumBass = answerTrack(taps, tracks, 0, C).notes;
assert(drumBass[2].velocity > drumBass[1].velocity);
assert(Math.abs(drumBass[2].at - 10643 / C.END) < 0.0001);
const gaps = answerTrack(notes, tracks, 1, C);
assert(gaps.notes.some((n) => n.at > 2000 / C.END && n.at < 10000 / C.END));
assert.equal(
  answerTrack({ ...notes, track: "Dark FM" }, tracks, 0, C).target,
  "Main Drums",
);
