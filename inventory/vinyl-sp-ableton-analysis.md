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

- Compare five representative reports with Ableton's visible Rack/Chain views.
- Confirm how per-pad choke, playback, filter/envelope, and macro targets are
  encoded in one standard kit and one deliberately effected kit.
- Write the pilot translation specification only after those source fields are
  paired with known-good MPC Drum Program and project settings.
