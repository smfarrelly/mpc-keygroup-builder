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
  --json work/ableton-pack.json
```

Inventory scans `.adg` and `.als`, skips AppleDouble and `__MACOSX` metadata,
keeps parse errors visible, and emits compact per-preset summaries. Licensed
samples and preset XML are never copied into the repository.

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

These heuristics intentionally leave false confidence on the table. A future
translator must also compare representative reports with Ableton's visible
behavior and use MPC-authored templates as target-format ground truth.

## Current boundary

The inspector identifies device/effect types but does not yet normalize every
device parameter or macro target. Choke groups, voice limits, modulation
routing, and exact per-device semantics require representative source studies
before they become exporter inputs.
