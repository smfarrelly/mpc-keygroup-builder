# Role-addressed Drum Ideas

The drum-idea engine creates small, deterministic patterns without coupling a
recipe to one kit's pad numbers. A recipe asks for sound identities such as
`kick`, `snare`, `hihat.closed`, `tom`, `percussion`, or `fx`. The active Drum
Program and optional layout resolve those identities to pads, and the XPM's own
`PadNoteMap` supplies the MIDI notes.

Generate JSON provenance plus an importable format-0 Standard MIDI file:

```bash
uv run mpc-drum-idea recipes/drums/dusty-pocket.toml \
  --program "/path/to/Drum Program.xpm" \
  --seed 37 \
  --tempo 91 \
  --output-prefix work/ideas/dusty-pocket
```

Resolve the identical recipe and seed through a planned layout:

```bash
uv run mpc-drum-idea recipes/drums/dusty-pocket.toml \
  --program "/path/to/Drum Program.xpm" \
  --preset layouts/classic-mpc.toml \
  --device devices/mpc-key-37.toml \
  --seed 37 \
  --tempo 91 \
  --output-prefix work/ideas/dusty-pocket-classic
```

Both runs preserve pattern intent. MIDI notes change only when the selected
semantic sound occupies a different destination pad. `--density` scales event
probabilities from 0 to 2 without changing the saved recipe. `--force` is
required to replace either output.

## Recipe format

```toml
schema_version = 1
id = "example"
name = "Example"
bars = 2
steps_per_bar = 16
swing = 0.57
gate = 0.45
channel = 10

[[events]]
role = "kick"
steps = [0, 7, 10, 16, 23, 26]
velocity = 112
humanize_velocity = 5

[[events]]
role = "snare"
steps = [4, 12, 20, 28]
velocity = 108
selection = "cycle"
```

`selection` may be `first`, `cycle`, or `random` when several zones match a
role. Every random decision comes from the recorded seed. Missing roles or
missing/invalid pad-note mappings are errors rather than guessed notes.

The starter recipes are:

- `recipes/drums/dusty-pocket.toml`
- `recipes/drums/electro-grid.toml`
- `recipes/drums/sparse-weird.toml`

## Current real-data proof

Against `Vinyl SP From Mars 01`, `dusty-pocket` seed 37 at 91 BPM produces 28
events in both the source and Classic layouts. Linux identifies both outputs as
format-0 Standard MIDI with one track at 480 PPQ. Steps and randomized
velocities remain identical; the snare note changes to follow its Classic
destination pad.

MIDI syntax and deterministic layout resolution are locally proven. Import,
track assignment, sound correspondence, and groove feel remain MPC hardware
tests.
