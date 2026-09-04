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

For plugin mapping, the first five-page performance batch is software-complete.
Regenerate its worksheets from the SD content and saved startup project with:

```bash
uv run mpc-plugin-map compile midi/plugins/*.toml \
  --synth-root "/media/steve-farrelly/3561-6538/Synths" \
  --project "/media/steve-farrelly/3561-6538/Projects/Boot.xpj" \
  --output work/midi-control/plugin-performance-wave-01
```

The generated `HARDWARE_CHECKLIST.md` starts with one probe per plugin before
asking for a full Learn pass. Slots 7–11 and channels 11–15 are reserved for
Iona, Flavor Pro, Trigger FX, Multitap Delay, and Vintage Filter. This work does
not depend on the Volca MIDI splitter.

Historical plans and test detail remain in `docs/` and `inventory/`; they are
reference material, not prerequisites for resuming work.
