# Resume here

## Current focus — software hardening, hardware deferred

Updated October 30, 2026. No new hardware acceptance session is required now.

The current focus is instrument creation, organization, and reliable software
review. Start with the [instrument role guide](docs/instrument-role-guide.md)
and [software checkpoint](inventory/instrument-software-review-2026-10-30.md).
Use the existing Scratchpad for music; no new hardware session is required.

```bash
uv run mpc-tools resume --offline
uv run mpc-scratchpad-check inventory/scratchpad-current.toml \
  --ledger inventory/program-status.csv --require core
```

The current manifest covers the six selected ledger-backed instruments at their
actual SD locations. The original v0.1 shortlist is historical. Expanded shots
and expressive alternates remain documented separately. Add `--sd-root` only
when checking a mounted card; otherwise deployment is explicitly not checked.

The focused Layered Banks, Breaks Texture, and Wurli Clean/Warm/Pad hardware
review passed. New Found Transitions and Mechanical Layers candidates remain
hardware-pending; existing favorites are unchanged. The full reference audit
checked 1,306 XPMs and repaired three vendor spelling failures using two exact
WAV aliases, without changing any XPM or baseline project.

For software-only review, use Drum bank/velocity previews and optional PCM
verification, described in [testing](docs/testing-framework.md) and
[local readiness](docs/local-readiness.md). Thirty curated/new programs have
readable PCM and valid regions; Breaks Texture retains three vendor-padding
warnings. Software evidence does not promote hardware status. Current `main`
is newer than the pinned v0.1.0 release.

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
