# Creative MIDI generators

The creative MIDI tools build deterministic musical starting points without
requiring an MPC project file or licensed audio. Every run writes a Standard
MIDI file and a JSON evidence file. Reusing the same recipe, seed, tempo, and
tool version recreates the same events.

## Chords and bass

Generate two named MIDI tracks plus a conductor track:

```bash
uv run mpc-harmony-idea recipes/harmony/dusty-dorian.toml \
  --seed 37 --tempo 92 \
  --output-prefix work/ideas/dusty-dorian-37
```

The recipe declares key, scale, scale-degree progression, harmonic rhythm,
three- or four-note chords, bass rhythm, velocities, MIDI channels, and strict
MIDI note ranges. Chord voicings are chosen with deterministic nearest-voice
movement. Bass pitches follow each chord root and the recipe's semitone pattern.
If a requested pitch class or chord cannot fit its declared range, generation
fails rather than silently placing an unusable note.

Bundled starting recipes are:

- `dusty-dorian`: seventh chords and a moving eighth-note bass line.
- `ambient-minor`: held seventh chords with restrained roots.
- `electro-minor`: triads and a gated octave/fifth bass figure.

The output defaults to format-1 MIDI at 480 PPQ: conductor, Chords, and Bass.
Use `--midi-format 0` only when testing a legacy importer. The JSON includes
each chosen voicing, scale degree, beat position, range, note, duration, and
velocity. Hardware import remains a separate acceptance gate.

## Semantic drums

`mpc-drum-idea` remains the drum counterpart. It addresses roles such as
`kick`, `snare`, and `hihat.closed`, resolves them through the active layout,
and writes MIDI plus JSON. Its MIDI rendering now shares the same tested writer
as the harmony generator, without changing its command or output contract.
