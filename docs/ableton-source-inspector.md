# Ableton source inspection

`mpc-ableton` reads the XML inside Ableton `.adg` racks and `.als` sets as a
description of musical intent. It does not launch Ableton, modify the source,
or claim that every Live device has an MPC equivalent.

## Inspect one preset

```bash
uv run mpc-ableton inspect "/path/to/Preset.adg" \
  --json work/ableton-preset.json
```

The report preserves source/version metadata and extracts readable device and
branch types, user names, non-default macro names, multisample references,
key/velocity ranges, roots, detune, level/pan, sample endpoints, sustain and
release loops, and warp state. Full zone detail remains available for later
normalized-model import rather than being reduced to summary counts.

## Inventory a pack

```bash
uv run mpc-ableton inventory "/path/to/Ableton pack" \
  --jobs 4 --json work/ableton-pack.json
```

Inventory scans `.adg` and `.als`, skips AppleDouble and `__MACOSX` metadata,
keeps parse errors visible, and emits compact per-preset summaries. `--jobs`
uses bounded process workers while preserving the same deterministic ordering
as the serial scan. Licensed samples and preset XML are never copied into the
repository.

## Inventory tempo-named loops

```bash
uv run mpc-loop-inventory "/path/to/loop pack" \
  --json work/loops.json --csv work/loops.csv
```

The source must be an existing directory, and JSON and CSV must name distinct
regular output files. Output symlinks are refused. Individual unreadable or
poorly named WAVs remain visible as issues without hiding valid loops.

## Build a coverage-aware backlog

```bash
uv run mpc-ableton-backlog work/ableton-pack.json \
  --catalog work/program-catalog.json \
  --json work/ableton-mpc-backlog.json \
  --markdown inventory/ableton-mpc-backlog.md
```

The planner assigns Drum, Keygroup, Clip, project, or Reference-only targets.
Prepared reusable racks rank above full Live sets and demos; giant
individual-hit racks remain catalog sources; existing Drum/Keygroup coverage
reduces duplicate work. Scores are transparent triage signals, not musical
quality judgments, and every entry retains its reasons and source fidelity.

## Translate prepared Drum Racks

`mpc-ableton-drum` reads each `DrumBranchPreset` in document order, resolves its
sample zones below a declared pack root, and carries receiving-note provenance,
velocity layers, and choke groups into a Drum Program manifest. Batch recipes
use paths relative to the owned library root and preflight the entire set before
creating any output package.

```bash
uv run mpc-ableton-drum plan inventory/ableton-drum-wave-01.toml \
  --library-root "/path/to/Samples From Mars" \
  --report work/ableton-drum-plan.json
```

The plan explicitly reports sampler or device behavior that is not yet
serialized. A generated program therefore preserves the raw sample instrument
topology but does not claim to reproduce Ableton Rack effects or macros.

## Produce an explicit translation contract

`mpc-ableton-fidelity` expands the coarse A–D suggestion into feature-level
evidence. It records whether samples, key and velocity ranges, roots, Drum
notes, choke groups, endpoints, tuning, loops, warp, macros, and devices are
direct, template-level, review-required, reference-only, or absent.

```bash
mpc-ableton-fidelity \
  "/path/to/Kit.adg" "/path/to/Instrument.adg" \
  --source-root "/path/to/Samples From Mars" \
  --output work/fidelity-review
```

The JSON retains normalized zone/pad evidence; the Markdown is a short review
view. The destination is transactional and must not already exist. Missing root
notes, Ableton warp, plug-ins, effects, or macro intent stay visible instead of
being silently treated as converted.

## Plan and build a diverse Drum wave

`mpc-ableton-wave` turns a coverage backlog into a bounded test batch. It
excludes prior recipes and exact duplicates, distributes choices across packs,
resolves every referenced sample, and runs the Drum converter in preflight
before publishing a recipe:

```bash
mpc-ableton-wave plan work/samples-from-mars-mpc-backlog.json \
  --source-root "/path/to/Samples From Mars" \
  --exclude-recipe inventory/ableton-drum-wave-01.toml \
  --count 24 --max-per-pack 2 \
  --output work/ableton-drum-wave-02-plan
```

Build that recipe with a generated structural target template:

```bash
mpc-ableton-wave build \
  work/ableton-drum-wave-02-plan/ableton-drum-wave-02.toml \
  --source-root "/path/to/Samples From Mars" \
  --output work/hardware-candidates/sfm-ableton-wave-02
```

The build is all-or-nothing, locally simulates every XPM, removes machine-local
paths from its reports, writes checksums, and creates an MPC hardware checklist.
It copies licensed source audio into ignored local output only; never commit or
redistribute that output. The maintained Wave 02 selection metadata lives in
`inventory/ableton-drum-wave-02.toml`. Run `mpc-bundle-verify PATH-TO-WAVE`
after moving the private bundle to confirm that every licensed local file still
matches its receipt.

### Prioritize translation risks

Raw converter diagnostics can be repetitive—for example, one gain difference
may appear once per pad. Convert a wave's build report into a compact,
per-program review queue:

```bash
mpc-ableton-risk work/hardware-candidates/sfm-ableton-wave-02/build-report.json \
  --output work/hardware-candidates/sfm-ableton-wave-02-risk-review
```

The transactional output contains JSON for automation, CSV for sorting, and
`TRANSLATION_REVIEW.md` for the hardware session. It groups warnings into
timing/warp, sample-start, looping, pitch, gain, stereo, device, and macro
risks; preserves affected pad numbers; and orders programs by the most severe
difference. A risk level prioritizes listening—it is not a hardware verdict.

## Fidelity suggestions

The labels are conservative routing suggestions, not automated conversion
claims:

- **A — direct:** readable sample zones and no detected multi-branch or plug-in
  dependency; likely representable in one MPC program.
- **B — close:** the sample map is readable, while macros or additional devices
  need deliberate MPC-native effects or Q-Link substitutions.
- **C — template:** Drum Rack, MIDI-effect, or multiple instrument branches
  imply multiple pads, programs, tracks, or routing.
- **D — reference-only:** a plug-in dependency or missing sample-zone data
  prevents a defensible automatic translation.

These heuristics intentionally leave false confidence on the table. The
feature-level contract provides the source-side comparison surface, while MPC
hardware results and MPC-authored target templates remain the ground truth.

## Current boundary

The inspector identifies device/effect types but does not yet decode every
device parameter or macro target. The current Drum exporter preserves sample
topology, velocity layers, and choke groups; voice limits, modulation routing,
effects, warp, and exact per-device semantics still require representative
source studies before they become exporter inputs.
