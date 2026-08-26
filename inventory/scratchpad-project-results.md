# Scratchpad and Volca project capture results

## August 26, 2026 captures

The four SD-card projects and their companion ProjectData folders were copied
read-only and verified against the mounted originals. The ignored local capture
directory is:

`work/project-captures/2026-08-26-scratchpad-volca/`

All four XPJs report MPC firmware `3.9.1.2` and project schema 28.

### Scratchpad protected master

`FG-scratchpad-v0-1-test.xpj` has no sequence and contains four musical tracks:

1. Wurli — Keygroup, input `MPC Keyboard`, armed.
2. Vinyl SP From Mars 01 FG COLORS — Drum, input `MPC Pads`, armed and selected.
3. Pluck Bass — Keygroup, input `MPC Keyboard`, disarmed.
4. OneFiftySeven — Keygroup, input `MPC Keyboard`, disarmed.

The matching jam copy contains one looped four-bar sequence at 120 BPM. Saved
events are present on Vinyl SP (77 events), Pluck Bass (16 notes), and Wurli
(16 notes). OneFiftySeven has no saved note events. The jam therefore proves
drums, bass, and keys in a real sequence; it does not yet prove a recorded lead
part.

Verdict: Scratchpad save/reload persistence is `pass` based on the hardware
reload and the captured project state. Pluck Bass has stronger favorite
evidence than the ledger's earlier isolated audition alone implied.

### Volca protected master and jam

Both Volca projects contain three MIDI tracks routed to the physical
`MPC Key 37 MPC MIDI Port A` output:

- Bass — MIDI channel 1, input `MPC Keyboard`.
- Keys — MIDI channel 2, input `MPC Keyboard`.
- Drum — MIDI channel 10, input `MPC Pads`.

The jam copy renames these tracks `Volca Bass`, `Volca Keys`, and `Volca Drum`.
Its Volca Drum custom pad map persists A01–A06 as C3, D3, E3, F3, G3, and A3.
The saved four-bar sequence is approximately 135.75 BPM, but every MIDI track's
event list is empty. The pattern heard after pressing MPC Play was therefore
the Volca's local sequence following MPC clock and transport, not recorded MPC
note playback.

Verdict: channel routing, Drum pad mapping, track names, clock, and transport
are preserved. Recording and reloading an actual MPC-authored Volca note
sequence remains pending.
