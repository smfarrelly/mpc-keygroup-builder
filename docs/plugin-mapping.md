# Declarative plugin performance pages

`mpc-plugin-map` converts small, reviewable TOML profiles into Launch Control
XL 3 Components worksheets and MPC MIDI Learn worksheets. It is the bridge
between the read-only plugin parameter catalog and the one-time hardware Learn
operation.

The profiles describe musical roles such as tone, movement, space, and
character. They pin every choice to the exact control name and UI parameter
found in the installed MPC plugin content. Compilation fails if installed
metadata has drifted, a parameter is missing, an endpoint is duplicated, or a
Custom Mode slot is reused.

## First performance-page batch

- `midi/plugins/iona-performance.toml`: slot 7, channel 11, source mix,
  envelopes, filtering, movement, space, and arpeggiator controls.
- `midi/plugins/flavor-pro-performance.toml`: slot 8, channel 12, global and
  per-engine depth plus pitch, distortion, digital, vinyl, and timbre gestures.
- `midi/plugins/trigger-fx-performance.toml`: slot 9, channel 13, time,
  modulation, filter, granular, Lo-Fi, and reverb controls.
- `midi/plugins/multitap-delay-performance.toml`: slot 10, channel 14, master
  delay and five tap timing, level, pan, and enable controls.
- `midi/plugins/vintage-filter-performance.toml`: slot 11, channel 15, a
  compact cutoff, resonance, drive, envelope, and LFO page.

These pages are additive. They do not alter the captured OPx-4 mode in slot 1
on channel 9 or Jura mode in slot 2 on channel 10. Channels 1–3 remain available
to the current Volca routing plan, and channel 16 remains the control/mixer
channel.

## Validate before touching hardware

Use the SD card's readable plugin content and, when available, an MPC-authored
project containing MIDI Learn evidence:

```bash
uv run mpc-plugin-map check midi/plugins/*.toml \
  --synth-root "/media/user/CARD/Synths" \
  --project "/media/user/CARD/Projects/Boot.xpj"
```

An empty `errors` list means each named control still exists. It does not mean
the mapping has passed on hardware.

## Compile the setup packet

```bash
uv run mpc-plugin-map compile midi/plugins/*.toml \
  --synth-root "/media/user/CARD/Synths" \
  --project "/media/user/CARD/Projects/Boot.xpj" \
  --capture "work/hardware-captures/launch-control-xl3/1 - OPX.syx" \
  --capture "work/hardware-captures/launch-control-xl3/2 - Jura.syx" \
  --output work/midi-control/plugin-performance-wave-01
```

The output contains one folder per plugin, combined Components and MPC Learn
CSVs, a control-layout review for each page, an ordered hardware checklist, a
machine-readable manifest, and both summary- and control-level comparisons with
the supplied real Components captures. Existing `.syx` and `.xpj` inputs are
read only. Use `--force` only to replace the named generated output directory.

## Memorize-once CC convention

- Top encoders: CC20–27.
- Middle encoders: CC28–35.
- Bottom encoders: CC36–43.
- Faders: CC44–51.
- Upper buttons: CC52–59.
- Lower buttons: CC60–67.

Each page uses the same physical-to-CC relationship on its own MIDI channel.
This keeps Components entry predictable and allows the MPC Learn target—not
the controller number—to carry the plugin-specific meaning.

## Minimal hardware verification

Do not learn a full page first. Load one plugin on a dedicated track, create its
Components mode, and learn only the first `core` control named in the generated
`HARDWARE_CHECKLIST.md`. Verify minimum, midpoint, maximum, pickup behavior, and
that no unrelated control moves. Save/reload a small MPC project, inspect the
XPJ, and only then learn the rest of that page.

The UI metadata exposes exact names and parameter numbers, but it does not prove
the MPC's saved parameter ID. The catalog labels a `+4096` relationship as a
hypothesis until a same-plugin MPC-authored XPJ confirms it. The Learn workflow
remains the supported write path; this project does not synthesize XPJ or
Components SysEx files.
