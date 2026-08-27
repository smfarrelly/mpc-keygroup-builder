# Program Model and Layout Planning

Program Model v1 is the format-independent layer between owned source material
and MPC serialization. It lets tools reason about a Drum Program or Keygroup
without depending on whether its XPM is legacy XML, MPC 3 compressed JSON, or a
repository Drum manifest.

The model records:

- program name, kind, source format, and source path;
- zones with pad or key range, semantic role, color, playback mode, mute group,
  polyphony, monophonic state, and locked placement;
- sample layers with velocity range, root note, sample bounds, and loop data.

Inspect an XPM or a Drum manifest and validate the normalized result:

```bash
uv run mpc-program-model "/path/to/program.xpm"

uv run mpc-program-model inventory/fg-vinyl-shots-six-bank.toml \
  --source-root "/path/to/Vinyl SP From Mars" \
  --output work/program-model.json
```

## Semantic roles and overrides

Roles are stable identities such as `kick.primary`, `snare.primary`,
`hihat.closed`, `tom.low`, `percussion.shaker`, `cymbal.ride`, and `fx.vocal`.
Filename classification supplies the default. An explicit filename or stem
override handles an unusual source without changing global inference:

```toml
[roles]
"Mystery Hit 07.wav" = "kick.primary"
"Odd Metallic Stem" = "cymbal.other"
```

Pass the file to either command with `--roles role-overrides.toml`. Names are
case-insensitive and match an exact basename first, then an exact stem. Unknown
roles are rejected.

## Declarative layouts and devices

`devices/mpc-key-37.toml` describes the 37 keys, 4-by-4 pad surface, Banks A–H,
and 128-slot capacity. Layout files are independent of that hardware profile:

- `layouts/classic-mpc.toml`
- `layouts/right-handed-performance.toml`
- `layouts/left-handed-performance.toml`
- `layouts/full-library.toml`

Role-first presets fill the first physical bank from a semantic priority list,
then preserve every remaining source zone in source order. The full-library
preset preserves source placement. A `locked` zone keeps its assigned pad and
cannot be displaced.

Render a map for review:

```bash
uv run mpc-layout inventory/fg-vinyl-shots-six-bank.toml \
  --source-root "/path/to/Vinyl SP From Mars" \
  --preset layouts/right-handed-performance.toml \
  --device devices/mpc-key-37.toml \
  --format markdown \
  --output work/right-handed-map.md
```

JSON output is available with `--format json` for a future visual editor.

## Non-destructive XPM export

Export writes a new Drum Program and refuses to modify the source in place:

```bash
uv run mpc-layout-export "/path/to/source.xpm" \
  --preset layouts/right-handed-performance.toml \
  --device devices/mpc-key-37.toml \
  --name "My Kit Right" \
  --output "/path/to/My Kit Right.xpm"
```

The exporter does not reconstruct sounds from a reduced schema. It permutes all
128 complete instrument records and moves each record's pad color with it.
Layers, mute groups, playback settings, unknown instrument fields, MIDI note
maps, sample registries, effects, and other global settings remain intact. XML
stays XML and MPC 3 compressed data stays compressed. Existing output is refused
unless `--force` is explicit.

Run the same invariant checks later without writing:

```bash
uv run mpc-layout-verify "/path/to/source.xpm" "/path/to/My Kit Right.xpm" \
  --preset layouts/right-handed-performance.toml \
  --device devices/mpc-key-37.toml \
  --name "My Kit Right"
```

An exported XPM still needs access to its licensed audio. Build a complete local
hardware-test handoff with one or more repeated `--preset` arguments:

```bash
uv run mpc-layout-package "/path/to/source.xpm" \
  --preset layouts/classic-mpc.toml \
  --preset layouts/right-handed-performance.toml \
  --device devices/mpc-key-37.toml \
  --name-prefix "TESTKIT" \
  --output work/testkit-layout-trial
```

Every variant is self-contained and receives an XPM, licensed audio copies, a
pad map, checksums, and semantic simulation results. Package output belongs in
ignored local storage and must never be committed.

## Current real-data proof

On August 26, 2026, the adapters and renderer were exercised against:

- `FG Vinyl Shots 03 Six Bank`: 96 Drum zones, no model errors or warnings;
- the MPC 3 Mirage Wurli XPM: 73 Keygroup zones, no model errors or warnings;
- all four stock layouts on the Key 37 profile: 96 assignments and zero
  unassigned zones per layout.
- four self-contained `FG Vinyl Shots 03` exports: 96 audio files per variant,
  all local simulations passing; 62, 61, 63, and 0 populated-pad moves for
  Classic, right-handed, left-handed, and full-library respectively.

The real Classic export independently preserves all 128 records, 96 sample
layers, pad colors, and global settings. Key 37 listening selects the
right-handed performance layout over Classic, although the advantage is modest
for this diverse one-shot collection rather than a compact conventional kit.
Both comparison programs save/reload correctly with samples, playback, and
semantic colors intact. The v0.2 layout hardware exit gate is closed.
