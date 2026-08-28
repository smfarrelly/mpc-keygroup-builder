# MPC Program Designer

`mpc-program-designer` creates a self-contained, source-safe HTML workspace from
the normalized Program Model. It does not run a server, load remote assets, or
modify the source program. Drum layout changes remain an in-memory draft until
a later export step is explicitly requested.

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
  --layout layouts/right-handed-performance.toml \
  --layout layouts/left-handed-performance.toml \
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

## Layout draft workspace

Repeat `--layout` to bundle any reusable layout presets that should appear in
the editor. Drum Programs then expose a source-safe draft workspace with:

- native pad drag/swap plus a click-based Move/Swap workflow that can cross
  banks;
- per-zone position locks that block moves, replacement, and mirror swaps;
- a selected-pad color picker;
- current-bank horizontal mirroring;
- Classic, right-handed, left-handed, full-library, or custom semantic presets;
- a bounded 50-step undo history, redo, reset-bank, and reset-all;
- a current-bank source-versus-draft comparison; and
- deterministic JSON assignment preview containing slot, source zone, full
  layer metadata, role, color, lock state, source SHA-256, and normalized model
  fingerprint; and
- a deterministic `Download draft JSON` action.

Drafts are isolated by program and device profile and survive source/device
switching while the HTML page remains open. The editor never writes to disk,
embeds no licensed audio, and only downloads a portable JSON draft when asked.
It never writes an XPM in the browser.

## MIDI groove heat and ergonomic suggestions

Pass one or more Standard MIDI files to aggregate their note-on usage. Format 0
and format 1 files, including running status, are supported:

```bash
uv run mpc-program-designer "/path/to/Kit.xpm" \
  --device devices/mpc-key-37.toml \
  --layout layouts/right-handed-performance.toml \
  --groove work/ideas/dusty-pocket-source.mid \
  --groove work/ideas/second-pattern.mid \
  --output work/program-designer/kit-groove.html
```

The viewer maps MIDI notes through each Drum Program's explicit zone notes or
PadNoteMap. Heated pads show hit counts; selection detail shows average velocity
and share of mapped events. The summary retains every MIDI source's path,
SHA-256, format, track count, PPQ, and event count, plus all unmapped notes. A
missing PadNoteMap therefore produces visible unmapped events instead of a
guessed Classic MPC mapping.

Right- and left-hand suggestions rank used sounds by hit count and average
velocity, then place them toward the lower dominant-hand corner, Bank A first.
This is an explicit repeatable reach heuristic, not an ergonomic or musical
truth. Source locks and locks added in the current draft stay fixed; unused
sounds retain their original locations when possible. Applying a suggestion is
a normal undoable draft action, so it can be compared, edited, downloaded, and
validated through the same source-safe export path.

## Validate and export a layout draft

Treat the downloaded JSON as a proposal, not an instrument. The separate CLI
requires the exact source file and device profile before it will write any
artifact:

```bash
uv run mpc-layout-draft inspect downloaded-layout-draft.json \
  --source "/exact/path/to/Source.xpm" \
  --device devices/mpc-key-37.toml
```

Validation requires matching source-file and normalized-model SHA-256 hashes,
program and device identity, a complete one-to-one source-zone assignment,
correct device slot labels, and unchanged source metadata for every zone.
Duplicate, missing, out-of-range, stale, or tampered assignments are refused.
If the viewer was generated with `--roles`, pass that same overrides file to
`mpc-layout-draft --roles` so the normalized fingerprints remain identical.

Export a reusable Drum builder manifest from either a source manifest or XPM:

```bash
uv run mpc-layout-draft manifest downloaded-layout-draft.json \
  --source inventory/source-kit.toml \
  --device devices/mpc-key-37.toml \
  --output work/layouts/source-kit-right-handed.toml \
  --name "Source Kit Right Handed"
```

The builder manifest preserves placement, sample layers, velocity ranges, and
mute groups. The current manifest schema does not encode pad colors or editor
locks, so those remain recorded in the draft JSON.

Only an exact XPM source can produce an XPM export:

```bash
uv run mpc-layout-draft xpm downloaded-layout-draft.json \
  --source "/exact/path/to/Source.xpm" \
  --device devices/mpc-key-37.toml \
  --output work/layouts/Source-Kit-Right-Handed.xpm \
  --name "Source Kit Right Handed"
```

This command delegates to the tested record-permutation exporter. Its
independent post-write verifier requires a complete instrument-record
bijection, unchanged sample-layer count and global settings, the requested
name, exact placement, and only the explicitly declared color edits. In-place
source modification and accidental output replacement are refused.

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
payload without HTML. Schema v3 contains the source/device/groove inventory, every
normalized rendered view, and deterministic pairwise comparisons including
changed fields and summary deltas.

Existing output is refused unless `--force` is supplied. The output path can
never equal an input program or MIDI groove path.

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

## Source-safety guarantee

Every source is parsed before the workspace output is created. The CLI refuses
input/output identity, refuses replacement by default, and embeds no audio.
Layout actions mutate only the page's isolated draft model; the browser's only
write action is an explicit draft-JSON download. Program, MIDI, and normalized
comparison data remain unchanged.

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
- The 64-pad layered program passed cross-bank swaps, colors, locks,
  lock-preserving mirror, right-handed semantic layout, undo/redo, reset, and
  per-device draft-isolation checks. Assignment count remained 64 and the
  original manifest remained byte-identical.
- The same 64-pad program produced a deterministic, fingerprinted download
  payload after a swap and recolor with zero browser warnings. Draft validation,
  manifest re-import, XML XPM record permutation, explicit color override, and
  stale/tampered-source rejection are covered by automated tests.
- The hardware-tested 28-note `dusty-pocket-source.mid` groove mapped all 28
  events onto seven sounds in the real 64-pad layered XPM. Browser checks passed
  heat toggling, hit/velocity/share detail, a 94.2% modeled right-hand reach
  improvement, current-draft lock preservation, 64-zone uniqueness, exact undo,
  and zero console warnings.

Generated HTML/JSON belongs under ignored `work/` storage. Licensed audio and
generated XPMs remain outside Git.
