# Declarative MIDI control for MPC Key 37, Launch Control XL 3, and Volcas

This design separates musical intent from one-off menu operations. Device MIDI
implementations live in `midi/devices/`; a complete controller and routing plan
lives in `midi/maps/`; `mpc-midi-control` validates the references and compiles
human- and machine-readable setup artifacts.

## What can be declarative now

- Exact Launch Control endpoint, message type, channel, CC/note number, range,
  behavior, label, color, output, and Custom Mode slot.
- Exact Volca receive channel and every mapped parameter/note, checked against
  a reusable official-chart-backed device definition.
- Exact MPC input/output port roles and per-track input/output route.
- Exact project-scoped MPC MIDI Learn source CC and intended target.
- Topology checks, including refusal to treat a passive thru box as a merger.
- CSV worksheets for Novation Components and MPC MIDI Learn, plus normalized
  JSON suitable for later editor or project-capture tooling.
- An ordered hardware checklist and TOML results ledger in every compiled map.
- A semantic map comparison that reports topology, mode-output, route, and
  control-assignment differences without relying on line-oriented TOML diffs.

## What remains evidence-gated

Novation Components can download and upload Custom Modes as `.syx`, but the
official Programmer's Reference does not publish the Custom Mode serialization
format. The project therefore does not write `.syx`. Its read-only capture
inspector understands the envelope, control slots, labels, encoded channels,
and controller numbers observed in real XL 3 exports while retaining every
unproven field as raw bytes. Button channels are clearly marked as an inference
from the same mode's encoder section.

Akai saves MIDI Learn assignments inside a project, but does not document a
supported standalone mapping-file or XPJ writer. The generated worksheet makes
the one-time Learn pass deterministic. A future writer remains gated on paired
MPC-authored baseline/changed XPJ captures and preservation tests.

## Cross-referenced control modes

### Slot 1 — MPC Mix, channel 16, USB

- Faders: tracks 1–8 volume, CC20–27.
- Top encoders: each strip's primary tone control, CC28–35.
- Middle encoders: movement/delay control, CC36–43.
- Bottom encoders: reverb/space control, CC44–51.
- Upper buttons: mute, CC52–59 toggle.
- Lower buttons: CC60–67 reserved for one consistent performance action. The
  exact target remains explicitly unverified.

Channel 16 isolates the control surface from the Volcas on channels 1, 2, and
10. Akai documents mixer volume, pan, and mute plus track-, pad-, and
effect-dependent targets. The project must retain **Global**, **Control**, and
**Track** for the Launch Control input; MIDI Learn mappings save with it.

### Slot 2 — Volca Bass, channel 1

The mode exposes all documented CC parameters: Slide Time (5), Expression
(11), Octave (40), LFO Rate/Intensity (41/42), three oscillator pitches
(43–45), envelope attack and decay/release (46/47), Cutoff EG Intensity (48),
and Gate Time (49). Slide Time, Expression, and Gate Time are MIDI-only controls
in Korg's implementation chart.

### Slot 3 — Volca Keys, channel 2

The mode exposes Portamento (5), Expression (11), Voice through LFO Pitch
Intensity (40–47), LFO Cutoff Intensity through Sustain (48–51), and Delay
Time/Feedback (52/53).

### Slot 4 — Volca Drum single-channel mode, channel 10

- Upper buttons 1–6 send the hardware-confirmed notes C3, D3, E3, F3, G3, A3
  (60, 62, 64, 65, 67, 69).
- Faders 1–6 control part levels.
- Encoder columns 1–6 control each part's layer select, modulation amount, and
  modulation rate.
- The remaining four assigned encoders control waveguide model, decay, body,
  and tune (CC116–119).

The six-note trigger layout is labeled `hardware-confirmed`, not `official`,
because Korg's single-channel chart documents part note reception but not this
practical note arrangement.

## Current topology: no new hardware assumption

```text
Launch Control XL 3 USB
          │ channels 16 / 1 / 2 / 10
          ▼
      MPC Key 37 ── physical MIDI Out ── CME Thru5 ── Bass / Keys / Drum
          │
          ├─ MPC Mix: project MIDI Learn consumes channel 16
          └─ Volca modes: three monitored MIDI tracks pass channels 1/2/10
```

The Thru5 distributes the MPC's one output and relies on the distinct receive
channels for device isolation. It cannot combine an independent Launch Control
DIN stream with MPC DIN output.

## Lower-click alternative to test later

The Launch Control XL 3 is also a USB MIDI interface with two host-visible DIN
outputs, and Novation documents that host USB data and surface-generated data
can share a DIN output. A potentially cleaner topology is:

```text
Launch Control XL 3 USB ↔ MPC Key 37
Launch Control XL 3 DIN Out 1 ── CME Thru5 ── Bass / Keys / Drum
```

In that topology, MPC Volca tracks target the Launch Control's `To DIN Out 1`
USB port while Volca Custom Modes send directly to DIN 1. MPC Mix remains USB
only. This avoids three MIDI pass-through tracks for surface controls and does
not require a separate merger. It is a research recommendation, not the
default, until the Key 37 confirms that it enumerates the Launch Control's
virtual DIN output and simultaneous sequencer/surface traffic produces neither
dropped nor doubled messages.

That alternative is already expressed without duplicating the 110 base
assignments. `fg-key37-lcxl3-volcas-bridge.toml` inherits the standard map and
overrides only topology, three track outputs, and three Custom Mode outputs:

```bash
uv run mpc-midi-control compile \
  midi/maps/fg-key37-lcxl3-volcas-bridge.toml \
  work/midi-control/fg-key37-lcxl3-volcas-bridge
```

## Build and restore workflow

```bash
uv run mpc-midi-control check midi/maps/fg-key37-lcxl3-volcas.toml
uv run mpc-midi-control compile midi/maps/fg-key37-lcxl3-volcas.toml \
  work/midi-control/fg-key37-lcxl3-volcas

uv run mpc-midi-control compare \
  midi/maps/fg-key37-lcxl3-volcas.toml \
  midi/maps/fg-key37-lcxl3-volcas-bridge.toml \
  work/midi-control/conservative-vs-bridge
```

Edit TOML, recompile, and review the diff in CSV/JSON. On the first hardware
pass, enter the four Custom Modes in Components, export their `.syx` files,
perform the MPC Mix MIDI Learn pass, and save the baseline project. Subsequent
changes begin in TOML rather than rediscovering channels and CCs from menus.
The current comparison proves that the bridge experiment changes three Custom
Mode outputs, three MPC routes, and topology metadata while changing **zero**
endpoint/message/channel/number/target assignments. This isolates the physical
routing question from the musical mapping question.

## Inspect real Components and MPC captures

Keep `.syx`, `.xpj`, ProjectData, and licensed samples in the ignored `work/`
tree. Inspect one or more Components exports:

```bash
uv run mpc-launch-control inspect work/hardware-captures/launch-control-xl3/*.syx \
  --output work/hardware-captures/launch-control-xl3/components.json
```

Cross-check their captured channel/controller pairs against the MIDI Learn
assignments saved in an MPC 3 project:

```bash
uv run mpc-launch-control audit "/media/user/CARD/Projects/Boot.xpj" \
  work/hardware-captures/launch-control-xl3/*.syx \
  --output work/hardware-captures/launch-control-xl3/boot-audit.json
```

An unmatched control is evidence, not automatically a failure: direct Volca
controls should bypass MPC MIDI Learn. The audit never rewrites either input.

## Primary sources

- [Akai MIDI Learn](https://support.akaipro.com/en/support/solutions/articles/69000858700-mpc-series-mapping-plugin-parameters-in-mpc-standalone-and-mpc-2-0-mpc-beats)
- [Akai Multi-MIDI routing](https://support.akaipro.com/en/support/solutions/articles/69000804431-akai-pro-mpc-series-configuring-midi-ports-for-multi-midi-control)
- [Novation XL 3 hardware and port behavior](https://userguides.novationmusic.com/hc/en-gb/articles/26190543883538-Launch-Control-XL-3-hardware-overview)
- [Novation XL 3 outside a DAW](https://userguides.novationmusic.com/hc/en-gb/articles/26190491669650-Using-Launch-Control-XL-3-outside-of-a-DAW)
- [Novation XL 3 Components guide](https://support.novationmusic.com/hc/en-gb/articles/27203903097362-Launch-Control-XL-3-Components-guide)
- [Novation Programmer's Reference](https://fael-downloads-prod.focusrite.com/customer/prod/downloads/launch_control_xl_3_programmer_s_reference_guide-pdf_en.pdf)
- [Korg Volca Bass implementation](https://cdn.korg.com/us/support/download/files/5b722ac465bb10f1907528e571968f4e.pdf)
- [Korg Volca Keys implementation](https://cdn.korg.com/us/support/download/files/d9a276cdfce7ff88c32a38ba6f3ba8aa.pdf)
- [Korg Volca Drum single-channel implementation](https://cdn.korg.com/us/support/download/files/68ae4f439b41bcb2cdc8350874a84cec.pdf)
