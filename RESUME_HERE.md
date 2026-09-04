# Resume here

Run this first after time away:

```bash
uv run mpc-tools resume --sd-root /media/steve-farrelly/3561-6538
```

Current objective: finish the direct Launch Control XL 3, MPC Key 37, and Volca
project without reconstructing the project history.

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
