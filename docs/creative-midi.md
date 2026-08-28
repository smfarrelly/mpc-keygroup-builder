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

## Melody motifs

Generate a scale-safe motif with controlled repetition and variation:

```bash
uv run mpc-melody-idea recipes/melody/dusty-answer.toml \
  --seed 37 --tempo 92 \
  --output-prefix work/ideas/dusty-answer-37
```

The motif declares an onset rhythm and a contour in scale steps. The first pass
is literal; later repetitions can substitute neighboring scale tones, move a
note by an octave, or leave a deliberate rest. All decisions are seeded and
recorded as `repeat`, `neighbor`, `octave`, or a combination in JSON. The
declared note range is a hard boundary. `dusty-answer`, `ambient-drift`, and
`electro-hook` provide matching counterparts to the harmony recipe families.

## Semantic drums

`mpc-drum-idea` remains the drum counterpart. It addresses roles such as
`kick`, `snare`, and `hihat.closed`, resolves them through the active layout,
and writes MIDI plus JSON. Its MIDI rendering now shares the same tested writer
as the harmony generator, without changing its command or output contract.

## Four-part workstation bundles

Combine a semantic Drum Program with a matched drum, harmony, and melody recipe:

```bash
uv run mpc-workstation-idea recipes/workstation/dusty-scratchpad.toml \
  --program "/full/path/to/Vinyl SP From Mars 01.xpm" \
  --seed 37 --tempo 92 \
  --output-prefix work/ideas/dusty-scratchpad-37
```

The bundle contains one format-1 MIDI file with named Drums, Bass, Chords, and
Melody tracks, one complete JSON reproduction record, and one concise Markdown
MPC loading guide. Short drum recipes repeat exactly to the harmonic length.
The root seed deterministically derives separate drum, harmony, and melody
seeds. The record fingerprints the source Drum Program and identifies any
layout used, so a future result can be traced to its exact note map.

The bundled `dusty-scratchpad`, `ambient-scratchpad`, and
`electro-scratchpad` recipes suggest programs from the current Key 37 palette.
The expanded family adds `funk-scratchpad`, `house-scratchpad`, and
`weird-scratchpad`, each with its own semantic drum pattern, progression, bass
figure, and motif rather than a cosmetic preset rename.
These are musical starting points rather than claims of MPC project-file
generation; import and listening remain explicit hardware gates.
