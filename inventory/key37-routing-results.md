# MPC Key 37 routing results

## Drum Split — August 26, 2026

Project tracks:

- Track 1: Mirage Wurli Keygroup
- Track 2: Vinyl SP From Mars 01 FG COLORS Drum Program
- Rec Arm Behaviour: Multi; both tracks armed

Observed after enabling Key Ranges → Drum Split:

- Bank A physical pads trigger Vinyl SP.
- Other physical pad banks trigger low-octave Wurli notes.
- Low-octave physical keyboard keys trigger the Drum Program.
- Drum Split therefore separates MIDI note ranges, not the physical keyboard
  and pad input sources.

Verdict: `warn`, closest known-good. It provides immediate Bank A drums plus a
melodic keyboard range, but it sacrifices the low keyboard range and does not
keep Banks B–H dedicated to the Drum Program.

Capture status:

- `Key37_Routing_Baseline.xpj`: save/ingest confirmation pending.
- `Key37_Routing_Changed.xpj`: save/ingest confirmation pending.
- Intended single change: Key Ranges → Drum Split.

Next isolated experiment: if program tracks expose MIDI Input Port, restore the
baseline state and assign Wurli to `MPC Keyboard` and Vinyl SP to `MPC Pads`.
Save under a third, distinct filename; do not overwrite the controlled pair.
