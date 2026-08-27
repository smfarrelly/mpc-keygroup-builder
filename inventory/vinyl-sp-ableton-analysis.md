# Vinyl SP Ableton source analysis

## Reproducible inventory — August 27, 2026

```bash
uv run mpc-ableton inventory \
  "/path/to/Vinyl SP From Mars/Presets/Ableton/Vinyl SP From Mars" \
  --json work/ableton-vinyl-sp-inventory.json
```

The owned pack contains 23 readable Ableton files: two `.als` sets, one
individual-hits `.adg`, and 20 kit `.adg` racks. All 23 parse without issues.
Across preset instances the reports expose 2,884 zones, 2,040 referenced sample
names, and 209 named macro instances. Those totals deliberately count shared
material again when it appears in multiple presets.

The conservative translation suggestions are two **B — Close** sets and 21
**C — Template** racks. The two sets preserve readable sample maps but include
macro/effect intent that needs MPC-native substitution. Each prepared kit rack
contains a Drum Rack plus per-pad instrument/effect branches, so a Drum Program
can preserve the 16-hit selection while exact rack processing belongs in a
program/project template rather than a blind XPM rewrite.

The individual-hits rack is a catalog source rather than a single performance
program: it exposes 1,122 zone instances and 700 referenced sample names across
16 instrument branches. The prepared 16-hit kit racks are therefore the safer
first translation targets. This supports the existing bank-composer approach:
preserve source kit membership and sample choice, then use explicit MPC pad
colors, mute groups, and intentionally selected program-level effects.

## Next manual checks

- Confirm macro target ranges and per-pad choke/voice settings in Ableton's
  visible Rack/Chain views when Ableton is available.
- Pair the source-side rules below with a known-good MPC-authored effects save
  before automating processing parameters.

## Five-preset source review

The individual-hits catalog, 808 Standard, Acoustic Hybrid, Old Tape, and Flux
reports were reviewed against their raw gzip XML. Independent tag counts match
the analyzer exactly: 1,122 zones for Individual Hits and 16 zones for each
prepared kit.

The four prepared kits share the same source topology: one Drum Rack, 16
Simpler instruments, full 1–127 velocity zones, no warping, inactive sustain
loops, release-mode playback through each sample endpoint, and the Tune,
Decay, Drive, Cutoff, Comp, Reverb, and Reverb Decay vocabulary. They differ
primarily in their curated sample names:

- **808 Standard:** cohesive machine kit and the baseline original-machine
  translation.
- **Acoustic Hybrid:** acoustic drums mixed with machine/processed percussion;
  useful as a complete contrasting bank.
- **Old Tape:** tape/sub/glitch selections with longer character tails; preserve
  tails and avoid aggressive normalization.
- **Flux:** stabs, vocals, reverses, and tonal FX mixed with drums; better as an
  alternate character bank than the universal main kit.
- **Individual Hits:** 700 referenced sample names selected through 16 rack
  branches; use as catalog input and one-shot source, not one literal program.

## Pilot translation specification v1

1. Treat each prepared 16-hit kit rack as one source-native MPC bank. Preserve
   kit membership and source order once Drum Rack note assignments are
   extracted; do not interpret each Simpler's full key range as a chromatic
   instrument.
2. Use one full-velocity one-shot layer per prepared-kit pad. Preserve sample
   endpoints and natural tails. Add velocity layers only through an explicit
   curated recipe, never by inferring layers from these racks.
3. Infer semantic pad colors from the selected sample, then preserve explicit
   hat mute groups from an MPC-authored template or verified source choke data.
4. Translate Tune, Decay, Drive, Cutoff, and Comp into a restrained common MPC
   performance vocabulary only after target parameters are captured. Treat
   Reverb and Reverb Decay as shared-send/project intent rather than baking 16
   duplicate effects into every generated XPM.
5. Label the result **C — Template** when claiming rack-level fidelity. The
   underlying 16-hit sample selection can still produce a valid Drum Program;
   rack processing and macros require a companion MPC program/project design.
6. Validate sample identity, pad count, one-shot behavior, endpoints, colors,
   mute groups, save/reload, and a short groove on hardware. Never claim exact
   Ableton-effect equivalence from XML names alone.

This specification explains the already generated banks: 808 Standard,
Acoustic Hybrid, and Old Tape are direct source-kit choices inside `FG Vinyl
Kit Banks 01`; Flux remains available for a future character/FX bank or shots
program.
