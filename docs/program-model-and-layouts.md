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

JSON output is available with `--format json` for a future visual editor or XPM
exporter. The current layout command is intentionally read-only: it produces a
validated placement plan and does not rewrite an XPM. A generated XPM exporter
must preserve all non-layout settings and pass MPC hardware tests before these
presets can be called performance-ready.

## Current real-data proof

On August 26, 2026, the adapters and renderer were exercised against:

- `FG Vinyl Shots 03 Six Bank`: 96 Drum zones, no model errors or warnings;
- the MPC 3 Mirage Wurli XPM: 73 Keygroup zones, no model errors or warnings;
- all four stock layouts on the Key 37 profile: 96 assignments and zero
  unassigned zones per layout.

This proves normalized import and deterministic planning. It does not replace
the pending two-layout Key 37 load, color-reload, and playing comparison.
