# Resume here

## Current focus — software hardening, hardware deferred

Updated October 30, 2026. No new hardware acceptance session is required now.

PRs #62–#85 are merged into `main`. Start with one musical task rather than
reconstructing that development history:

```bash
uv run mpc-tools start
uv run mpc-tools resume --offline
```

The SD handoff is complete: the seven Scratchpad entry points pass bounded
sample-reference checks, and the optional twelve-candidate MIDI/synthetic wave
is deployed without replacing existing instruments or projects. Use
[SD navigation](docs/sd-navigation.md) for full loading paths. No new listening
verdicts were recorded. Laptop library reconciliation, safer capture/restore and
package publication, bounded XPM inspection, and contextual storage errors are
available on current `main`; they are newer than the pinned v0.1.0 release.

For a personal browser landing page, use [the local home guide](docs/local-home.md).
It combines your explicit favorites ledger, verified local archives, and selected
bundle checks. A saved `*.local.toml` input selection keeps the command short;
choose a new output filename each time. No drive is discovered automatically.

New creative waves record build-time recipe fingerprints. Use
`mpc-tools check --bundle PATH --recipe-root recipes` to distinguish intact
files from current recipe inputs. Older bundles remain freshness-unknown.
Existing archives with extra inspection reports should be preserved, not
silently relabeled as verified exact archives. Capture a clean copy into a new
folder when needed, keeping the historical source and reports untouched.

For everyday music making, keep using the existing Scratchpad instruments.
The colored vendor drum copies are under
`Samples/Samples From Mars/<collection>/<original name> FG COLORS.xpm`, beside
their WAVs. The Cassette color-only pilot passed; the broader batch is only
software/deployment-verified. Do not turn that into an assumed listening pass.

The SD cleanup removed failed relocated colored copies and abandoned staging
trees with local recovery records. No further SD cleanup, sync, or project
rewrite is required to continue the software work.

For continued development, favor tests, capture integrity, and useful experiment
comparison over generating another hardware audition backlog. For controller
work, prioritize MPC internal mixing and buried plugin parameters; prefer the
Volcas' and external effects' native controls for hands-on performance.

## Check the retained project checkpoint

Run this first after time away:

```bash
uv run mpc-tools resume --offline
```

## Retained hardware plan — deferred

The direct Launch Control XL 3, MPC Key 37, and Volca plan below is retained
for a future hardware session, not the immediate next task. Its target routing
is a plan, not a claim that the currently loaded MPC project matches it.

The current MPC-authored starting point is `Projects/Volca/Base.xpj`. The next
saved target is `Projects/FG Volca Direct 123.xpj`, with exactly these MIDI
tracks:

1. `VOLCA KEYS` — channel 1
2. `VOLCA BASS` — channel 2
3. `VOLCA DRUM` — channel 3, with the Volca Drum in single-channel mode

Both Launch Control Drum pages use channel 3. They divide the controls into
parts 1–3 and 4–6; they are not separate MIDI channels.

For plugin mapping, all nine performance pages are software-complete. Regenerate
the combined worksheets from the SD content and saved startup project with:

```bash
uv run mpc-plugin-map compile midi/plugins/*.toml \
  --synth-root "/media/steve-farrelly/3561-6538/Synths" \
  --project "/media/steve-farrelly/3561-6538/Projects/Boot.xpj" \
  --output work/midi-control/plugin-performance-all
```

The generated `HARDWARE_CHECKLIST.md` starts with one probe per page before
asking for a full Learn pass. Slots 7–15 cover Iona, Flavor Pro, Trigger FX,
Multitap Delay, Vintage Filter, Chorus, Expander, Color Compressor, and a
three-effect Analog Wear Rack. This work does not depend on the Volca MIDI
splitter.

For the no-CLI hardware session, open
`site/plugin-mapping-companion.html`. It presents the same exact mappings as a
visual XL3 surface, keeps progress and notes locally in the browser, and exports
JSON or CSV results. Start with the Vintage Filter cutoff probe if you want the
shortest possible end-to-end check.

The durable pending ledger is `inventory/plugin-control-status.csv`. After a
session, export JSON from the companion and import it with
`mpc-plugin-results`; the importer refuses stale fingerprints and mismatched
targets before changing that ledger. The full controller capacity report is
generated from `midi/controller-capacity.toml` and currently leaves only MIDI
channel 8 unreserved.

Historical plans and test detail remain in `docs/` and `inventory/`; they are
reference material, not prerequisites for resuming work.
