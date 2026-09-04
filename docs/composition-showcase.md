# Six-composition showcase

`mpc-showcase` builds a redistributable proof of the creative workflow without
requiring commercial samples, an MPC, or a repository checkout. It generates
six contrasting four-part ideas—dusty, ambient, electro, funk, house, and
weird—from fixed seeds.
Each composition contains Drums, Bass, Chords, and Melody plus Main, Main B,
Breakdown, Build, and Outro sequence candidates.

```bash
mpc-showcase --output my-mpc-showcase
```

Build a subset or override one family seed without changing the maintained
defaults:

```bash
mpc-showcase --family house --family weird --seed house=999 \
  --output house-and-weird
mpc-showcase --all --output all-six
```

Open `my-mpc-showcase/README.md` first. The bundle contains:

- a 16-pad Drum Program and deterministic CC0 WAV fixtures;
- one complete format-1 MIDI idea per composition;
- five separately importable arrangement MIDI files per composition;
- the exact Drum, harmony, Melody, and workstation recipes;
- JSON provenance, event counts, component seeds, and transformations;
- content checksums and a hardware checklist.

The maintained Scratchpad sounds appear as suggested assignments. They are
labels only; no commercial audio or plugin content is copied. Any compatible
local instrument can replace them.

## Reproducibility contract

Two builds from the same release produce byte-identical files and the same
composition digests regardless of output directory. The command refuses an
existing destination rather than merging or deleting user files. The build is
assembled in a sibling staging directory and promoted only after every
composition and checksum has been written.

The root `showcase.json` records software status as `pass` and hardware status
as `deferred`. Generated MIDI and structural evidence are not presented as a
finished song or a listening result. Completing the accompanying MPC checklist
is a separate human decision.

## Editing the recipes

The output's `Recipes/` directory is editable. Validate revised source recipes
before regenerating individual ideas:

```bash
mpc-schema validate drum-recipe Recipes/drums/*.toml
mpc-schema validate harmony-recipe Recipes/harmony/*.toml
mpc-schema validate melody-recipe Recipes/melody/*.toml
mpc-schema validate workstation-recipe Recipes/workstation/*.toml
```

Developers may pass `--recipe-root` to test repository recipe edits. The normal
installed command uses packaged copies, and CI verifies those copies have not
drifted from the maintained sources.
