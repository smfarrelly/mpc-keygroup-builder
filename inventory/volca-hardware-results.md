# Key 37 and Volca hardware results

## Individual MIDI routing — August 26, 2026

Tested sequentially from the MPC Key 37 physical MIDI output because a MIDI
thru/splitter was not yet available:

- Volca Bass: `pass` on MIDI channel 1.
- Volca Keys: `pass` on MIDI channel 2.
- Volca Drum: `pass` in single-channel mode on MIDI channel 10.

The positive route to each device was confirmed individually. Cross-device
leakage with all three connected remains pending until the thru/splitter is
available.

## Confirmed distribution hardware

A CME MIDI Thru5 WC has been ordered. Planned wiring:

- MPC Key 37 physical MIDI Out → Thru5 MIDI In.
- Thru5 Out 1 → Volca Bass MIDI In, channel 1.
- Thru5 Out 2 → Volca Keys MIDI In, channel 2.
- Thru5 Out 3 → Volca Drum MIDI In, single-channel mode channel 10.
- Thru5 USB-C → stable 5V power.

Outputs 4 and 5 remain intentionally unused for future expansion. The Thru5 is
a one-input distributor, not a merger or independently addressable MIDI
interface; the MPC continues to use its one physical MIDI output and the
Volcas perform channel filtering.

## Volca Drum pad map

The Volca Drum MIDI track uses Pad Perform → Custom with this Bank A map:

- A01: C3 → Part 1
- A02: D3 → Part 2
- A03: E3 → Part 3
- A04: F3 → Part 4
- A05: G3 → Part 5
- A06: A3 → Part 6

All six physical MPC pads triggered their intended Volca Drum parts. A short
MPC MIDI sequence also played the Volca successfully.

## Clock and sequencing

MPC MIDI output `Track` and `Sync` were enabled, Sync Send was set to `MIDI
Clock`, and transport was enabled. The Volca Drum followed MPC start, stop, and
tempo: `pass`.

When the Volca also contained a local pattern, MPC Play started both the local
Volca sequencer and the MPC-recorded MIDI sequence. This is expected but can
double or overlap notes. The preferred reusable posture is MPC-master
sequencing: use an empty Volca pattern, keep clock/transport enabled, and store
the note sequence in the MPC project. Alternatively, use a Volca-local pattern
and do not duplicate its notes on the MPC track.

## Pending

- Repeat clock/transport testing on Volca Keys and Volca Bass.
- Connect all three through the ordered CME MIDI Thru5 WC and test channel isolation,
  simultaneous start/stop, and drift.
- Record practical audio routing and gain settings.
- Save, power-cycle, and confirm the custom Drum pad map, ports, channels,
  clock, and track names return.
- Perform the ten-minute jam and count touchscreen interruptions.
