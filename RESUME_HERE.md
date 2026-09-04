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

For plugin mapping, generate a ranked OPx-4 parameter list from the SD content
and the saved startup project:

```bash
uv run mpc-plugin-params "/media/steve-farrelly/3561-6538/Synths" \
  --plugin OPx-4 \
  --project "/media/steve-farrelly/3561-6538/Projects/Boot.xpj" \
  --recommended
```

Historical plans and test detail remain in `docs/` and `inventory/`; they are
reference material, not prerequisites for resuming work.
