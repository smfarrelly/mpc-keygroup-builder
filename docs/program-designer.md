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

## Keygroup viewer

The same command detects a Keygroup automatically. Instead of Drum banks it
shows a movable 37-note viewport centered on the program's sample roots or key
ranges. Each note indicates whether a zone is active. Note and zone selection
shows key range, playback behavior, polyphony, sample layers, velocity regions,
roots, bounds, and loop state.

The viewport is an inspectable 37-note window, not a claim about the MPC's
current octave-transpose setting. The octave buttons move it through MIDI
0–127 without changing the program.

## Machine-readable output

Use `--format json` with an `.json` output path to write the complete viewer
payload without HTML. It contains normalized zones, layers, banks, device
metadata, summaries, and findings for future UI or comparison tools.

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
changes the displayed bank, selected pad/note, or 37-note viewport.

## Real-data proof — August 27, 2026

- `FG Vinyl Layered Banks 03`: 64 pads across Banks A–D, 256 sample layers,
  seven mute groups, all audio resolved, and only the expected informational
  absence of an explicit manifest PadNoteMap.
- Scratchpad Wurli: MPC 3 compressed Keygroup, 73 zones/layers, all ProgramData
  audio resolved, no findings, and a working 37-note movable viewport.
- Browser interaction verified Bank D selection, D01's four velocity regions,
  physical pad ordering, octave movement, zone selection, and zero console
  errors on both viewers.

Generated HTML/JSON belongs under ignored `work/` storage. Licensed audio and
generated XPMs remain outside Git.
