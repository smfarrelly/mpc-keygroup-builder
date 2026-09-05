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

## Compact-effects batch

- `midi/plugins/air-chorus-performance.toml`: slot 12, channel 4, all seven
  Chorus controls.
- `midi/plugins/air-expander-performance.toml`: slot 13, channel 5, all six
  Expander controls.
- `midi/plugins/color-compressor-performance.toml`: slot 14, channel 6, all six
  Color Compressor controls.
- `midi/plugins/analog-wear-rack-performance.toml`: slot 15, channel 7, one
  coordinated page for Tape Emulator, Vintage, and Vinyl Emulator.

The rack profile demonstrates the plural `plugins` form: every control names
its target plugin explicitly, and compilation validates it against that
plugin's own UI metadata. This supports a useful insert chain without pretending
the three effects are one plugin. Channel 8 remains unreserved.

Together, the nine generated pages contain 178 role-selected assignments and
cover every plugin/effect with readable SD metadata except OPx-4, whose real
Components capture already exists.

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
  --output work/midi-control/plugin-performance-all
```

The output contains one folder per profile, combined Components and MPC Learn
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

For a focused compact-effects packet, compile the four matching profile paths
instead of the wildcard. For one complete current packet, compile all nine with
`midi/plugins/*.toml`; profiles are ordered by slot regardless of shell path
order.

## Browser companion

`mpc-plugin-companion` packages the validated profiles as one offline HTML
workflow. It draws the controller by physical row, highlights core controls,
opens each exact MIDI Learn target, remembers results and notes locally, and
exports JSON or CSV without needing a server:

```bash
uv run mpc-plugin-companion midi/plugins/*.toml \
  --synth-root "/media/user/CARD/Synths" \
  --project "/media/user/CARD/Projects/Boot.xpj" \
  --output plugin-mapping-companion.html
```

Open the generated file in any current browser. The committed offline copy is
linked from `site/index.html`. Local progress is separated by a deterministic
mapping fingerprint; importing results from a different revision is rejected.
The page performs no network requests and cannot modify the MPC, SD card,
Components modes, XPJ files, or SysEx captures.

Use **Print mode cards** to produce one compact reference sheet per Custom Mode.
The print view includes physical control positions, target plugins and
parameters, CC numbers, the page channel, and a handwritten result area.

## Durable results ledger

Initialize a complete pending ledger from the same validated mapping set:

```bash
uv run mpc-plugin-results init midi/plugins/*.toml \
  --synth-root "/media/user/CARD/Synths" \
  --project "/media/user/CARD/Projects/Boot.xpj" \
  --ledger inventory/plugin-control-status.csv \
  --report inventory/plugin-control-status.md
```

After testing, export JSON from the companion and import it with:

```bash
uv run mpc-plugin-results import mpc-plugin-mapping-results.json \
  midi/plugins/*.toml \
  --synth-root "/media/user/CARD/Synths" \
  --project "/media/user/CARD/Projects/Boot.xpj" \
  --ledger inventory/plugin-control-status.csv \
  --report inventory/plugin-control-status.md \
  --force
```

The importer recomputes the mapping fingerprint and validates every page,
control, plugin, target, status, and note before atomically replacing the named
ledger. Missing, duplicated, unknown, tampered, or stale results are refused.
`--force` applies only to the named ledger and report outputs.

## Generate a new profile seed

When new readable plugin content appears, generate a review-required draft
instead of beginning with an empty controller page:

```bash
uv run mpc-plugin-seed "New Plugin" \
  --synth-root "/media/user/CARD/Synths" \
  --slot 15 --channel 7 --limit 40 \
  --output new-plugin-performance.toml

uv run mpc-plugin-map check new-plugin-performance.toml \
  --synth-root "/media/user/CARD/Synths"
```

The generator ranks useful and Q-Link-visible controls, separates buttons from
continuous controls, infers broad musical roles, and groups tone, motion,
texture, envelope, source, and global controls consistently. Its output is
explicitly a draft: review labels, roles, layout, slot/channel replacement, and
musical value before hardware use.

## Measure mapping coverage

Profiles intentionally select a small performance surface, but omission should
be deliberate. Compare every current profile with installed UI metadata and an
optional MPC-authored XPJ:

```bash
mpc-plugin-coverage midi/plugins/*.toml \
  --synth-root "/media/user/CARD/Synths" \
  --project "/media/user/CARD/Projects/Boot.xpj" \
  --output work/plugin-mapping-coverage
```

The transactional directory contains JSON, CSV, and a readable review. It
reports unique planned controls, independently learned controls, their union,
musical-role and parameter-evidence coverage, accidentally redundant targets,
and the highest-ranked useful controls that remain omitted. Installed plugins
without a profile remain visible instead of disappearing from the plan.

Coverage is not a goal of mapping every parameter. It makes the tradeoff
explicit: a compact page can be accepted when the omitted list contains only
low-value controls, while a missing filter, envelope, mix, or performance macro
becomes an actionable profile revision.
