# Role-addressed Drum Ideas

The drum-idea engine creates small, deterministic patterns without coupling a
recipe to one kit's pad numbers. A recipe asks for sound identities such as
`kick`, `snare`, `hihat.closed`, `tom`, `percussion`, or `fx`. The active Drum
Program and optional layout resolve those identities to pads, and the XPM's own
`PadNoteMap` supplies the MIDI notes.

Generate JSON provenance plus an MPC-targeted format-1 Standard MIDI file:

```bash
uv run mpc-drum-idea recipes/drums/dusty-pocket.toml \
  --program "/path/to/Drum Program.xpm" \
  --seed 37 \
  --tempo 91 \
  --output-prefix work/ideas/dusty-pocket
```

JSON and MIDI destinations are preflighted together before either is written.
They cannot replace recipe/program/configuration inputs or follow symbolic
links; both files are published atomically, and replacement requires `--force`.

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
required to replace either output. Format 1 is the default because MPC 3.9.1.2
standalone did not create a sequence from the original format-0 hardware-test
files. Use `--midi-format 0` only when a destination specifically requires the
single-track legacy form.

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
events in both the source and Classic layouts. The MPC-targeted outputs are
format-1 Standard MIDI with a conductor track, a note track, and 480 PPQ.
Steps and randomized velocities remain identical; the snare note changes to
follow its Classic destination pad.

MIDI syntax and deterministic layout resolution are locally proven. The first
format-0 files were visible in the MPC Browser but only flickered when loaded;
they created no new sequence on MPC 3.9.1.2. The format-1 replacements import
and play on hardware, and the source/Classic pair is musically close enough to
accept. Because the source contains varied one-shots, that listening result is
not an isolated measurement of every velocity or swing offset.

## Hear the pattern with the kit you chose

After generating a Drum Idea, render its JSON to a loop-length WAV. Use the matching XML Drum Program and a different output stem so the audition receipt and idea can sit together.

```bash
uv run mpc-program-audition "/path/to/Drum Program.xpm" \
  --drum-idea work/ideas/dusty-pocket.json --output work/ideas/dusty-pocket-listen.wav
```

The preview uses the idea’s saved tempo, swing timing and velocities. Each pad selects its matching velocity layer. A later hit in a shared mute group cuts the earlier hit, which makes closed/open hat interactions audible. The renderer sums to mono, applies sample trim and pitch, and ends at the bar boundary for looping. The adjacent JSON records each actual sample, start frame and played length. For a remapped idea, use the XPM with the corresponding pad and MIDI-note layout.

## Compare grooves in one browser tab

```bash
uv run mpc-drum-session "work/SDK Drum Synth Kit/SDK Drum Synth Kit.xpm" \
  recipes/drums/dusty-pocket.toml recipes/drums/funk-machine.toml \
  recipes/drums/house-foundation.toml recipes/drums/electro-grid.toml \
  --tempo 96 --seed 37 --output work/drum-session-01
```

Open `work/drum-session-01/index.html`. Each player loops the audition at the selected tempo. Starting a different player pauses the previous one. Each pattern has its own format-1 MIDI download and exact sample timing record. The same command works with another XML drum kit that covers the recipes’ requested roles. A missing role identifies the pattern build that needs attention. The generated folder is self-contained for listening. Use the corresponding XPM and its samples when taking the MIDI to the MPC.
