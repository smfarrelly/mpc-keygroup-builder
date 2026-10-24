# Resume here

## Current focus — software hardening, hardware deferred

Updated October 23, 2026. No new hardware acceptance session is required now.

The next development action is to review the open changes below, address any
feedback, and integrate them only after review. They are separate PRs, not
features already merged into `main`:

- [#62: colocated XML drum coloring](https://github.com/smfarrelly/mpc-keygroup-builder/pull/62)
  preserves sample fields and avoids relocating sample-dependent programs.
- [#63: safer rebuilds and local hardlink staging](https://github.com/smfarrelly/mpc-keygroup-builder/pull/63)
  validates replacements before publishing and protects previous instruments.
- [#64: focused Ableton conversion plans](https://github.com/smfarrelly/mpc-keygroup-builder/pull/64)
  exposes conversion losses and rejects output-name collisions.
- [#65: musical idea snapshots](https://github.com/smfarrelly/mpc-keygroup-builder/pull/65)
  captures named projects with notes, verifies archives offline, and compares
  saved takes without editing them.

For everyday music making, keep using the existing Scratchpad instruments.
The colored vendor drum copies are under
`Samples/Samples From Mars/<collection>/<original name> FG COLORS.xpm`, beside
their WAVs. The Cassette color-only pilot passed; the broader batch is only
software/deployment-verified. Do not turn that into an assumed listening pass.

The SD cleanup removed failed relocated colored copies and abandoned staging
trees with local recovery records. No further SD cleanup, sync, or project
rewrite is required to continue the software work.

After these reviews, favor tests, capture integrity, and useful experiment
comparison over generating another hardware audition backlog. For controller
work, prioritize MPC internal mixing and buried plugin parameters; prefer the
Volcas' and external effects' native controls for hands-on performance.

## Check the retained project checkpoint

Run this first after time away:

```bash
uv run mpc-tools resume --sd-root /media/steve-farrelly/3561-6538
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
