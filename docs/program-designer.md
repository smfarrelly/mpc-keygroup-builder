# MPC Program Designer

`mpc-program-designer` creates a self-contained, read-only HTML viewer from the
normalized Program Model. It does not run a server, load remote assets, modify
the source program, or expose editing/export controls.

## Drum Program viewer

Inspect a legacy XML or MPC 3 compressed XPM:

```bash
uv run mpc-program-designer "/path/to/Kit.xpm" \
  --device devices/mpc-key-37.toml \
  --output work/program-designer/kit.html
```

The viewer provides:

- Bank A–H switching with empty banks disabled;
- the Key 37's physical 4-by-4 orientation, top row 13–16 through bottom row
  1–4;
- semantic pad colors and readable contrast;
- role, sample, PadNoteMap MIDI note when available, playback mode, mute group,
  polyphony, monophonic state, lock state, and explicit color;
- every sample layer with velocity region, root, loop state, and a graphical
  0–127 coverage bar;
- model, sample-resolution, velocity-coverage, device-capacity, and mute-group
  findings.

## Drum manifest viewer

Pass the owned sample directory when the manifest should verify referenced
audio:

```bash
uv run mpc-program-designer inventory/fg-vinyl-layered-banks-03.toml \
  --source-root "/path/to/Vinyl SP From Mars" \
  --device devices/mpc-key-37.toml \
  --output work/program-designer/fg-vinyl-layered-banks-03.html
```

Without `--source-root`, manifest samples are marked `unchecked`, not missing.
For XML XPMs, audio is resolved recursively beside the program. For MPC 3
compressed XPMs, the adjacent companion ProgramData directory is preferred.
Missing and multiply resolved samples are errors in the viewer report.

## Portable comparison bundle

Repeat `--compare` for additional programs and `--device` for additional
hardware profiles. Every source/device combination and every ordered program
comparison is generated once and embedded in the self-contained output:

```bash
uv run mpc-program-designer inventory/fg-vinyl-layered-banks-03.toml \
  --source-root "/path/to/Vinyl SP From Mars" \
  --compare inventory/fg-vinyl-layered-main-02.toml \
  --compare-source-root "/path/to/Vinyl SP From Mars" \
  --device devices/mpc-key-37.toml \
  --device devices/mpc-key-61.toml \
  --output work/program-designer/layered-comparison.html
```

The toolbar switches the inspected source and device without regenerating or
modifying anything. When a comparison source is selected, the lower panel
aligns Drum pads or Keygroup zones side by side, reports additions/removals and
zone/layer/finding deltas, and names the fields that changed. Drum comparisons
follow the currently displayed bank so large A–H programs remain readable.

`--compare-source-root` entries correspond by position to repeated `--compare`
arguments. XPM companion ProgramData directories are still inferred
automatically, so this option is mainly needed for manifest-based programs.

## Keygroup viewer

The same command detects a Keygroup automatically. Instead of Drum banks it
shows a movable device-sized viewport centered on the program's sample roots or
key ranges. Each note indicates whether a zone is active. Note and zone selection
shows key range, playback behavior, polyphony, sample layers, velocity regions,
roots, bounds, and loop state.

For the Key 37 profile, the viewport is an inspectable 37-note window, not a
claim about the MPC's current octave-transpose setting. The octave buttons move
it through MIDI 0–127 without changing the program.

## Machine-readable output

Use `--format json` with an `.json` output path to write the complete viewer
payload without HTML. Schema v2 contains the source/device inventory, every
normalized rendered view, and deterministic pairwise comparisons including
changed fields and summary deltas.

Existing output is refused unless `--force` is supplied. The output path can
never equal the input source path.

## Validation meanings

- `error`: invalid model data, missing/ambiguous samples, dead velocity ranges,
  invalid sample bounds, or zones beyond device capacity.
- `warning`: stacked velocity ranges, incomplete loop bounds, singleton mute
  groups, or ungrouped hats.
- `info`: useful metadata is unavailable, such as an explicit color or
  PadNoteMap in a manifest-derived model.

Velocity coverage is checked at every integer value from 0 through 127, not
only at a small set of representative velocities. A warning describes data
that deserves review; it is not automatically a hardware or musical failure.

## Read-only guarantee

The source is parsed before the viewer output is created. The CLI refuses
source/output identity, refuses replacement by default, embeds no audio, and
contains no browser-side file access or write path. HTML interaction only
changes the selected bundled source/device/comparison, displayed bank,
selected pad/note, or keybed viewport.

## Real-data proof — August 27, 2026

- `FG Vinyl Layered Banks 03`: 64 pads across Banks A–D, 256 sample layers,
  seven mute groups, all audio resolved, and only the expected informational
  absence of an explicit manifest PadNoteMap.
- Scratchpad Wurli: MPC 3 compressed Keygroup, 73 zones/layers, all ProgramData
  audio resolved, no findings, and a working 37-note movable viewport.
- Browser interaction verified Bank D selection, D01's four velocity regions,
  physical pad ordering, octave movement, zone selection, and zero console
  errors on both viewers.
- A two-source/two-device bundle compared `FG Vinyl Layered Banks 03` with
  `FG Vinyl Layered Main 02`: 16 Bank A locations were unchanged, 48 Bank B–D
  locations were additions, reversed selection inverted every delta, and the
  current-bank comparison counts remained aligned with the displayed pads.
- The same Wurli source switched between Key 37 and Key 61 profiles in place,
  rendering exactly 37 and 61 keys respectively with zero browser warnings.

Generated HTML/JSON belongs under ignored `work/` storage. Licensed audio and
generated XPMs remain outside Git.
