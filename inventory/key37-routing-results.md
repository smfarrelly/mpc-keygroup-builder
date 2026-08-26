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

- Captured and hash-verified locally from the SD card without modifying the
  originals.
- Baseline: `Key37-routing-baseline.xpj`.
- Changed: `Key37-routing-Drumsplit1.xpj`.
- Capture directory:
  `work/key37-routing-captures/2026-08-26-drumsplit/` (Git-ignored).
- Intended single action: Key Ranges → Drum Split.
- XPJ inspection confirms that Drum Split changed both tracks' note filters.
  It also replaced the Drum Program's custom pad-note map with an identity map
  (`pad 0 → note 0` through `pad 127 → note 127`). The programs, two-track
  order, record-arm state, and sample sets remained intact.

## Dedicated track input ports and MPC Pads Global off — August 26, 2026

Starting from the baseline, the following routing was tested with Drum Split
off, Rec Arm Behaviour `Multi`, and both musical tracks armed:

- Wurli MIDI Input: `MPC Keyboard`.
- Vinyl SP MIDI Input: `MPC Pads`.
- MPC Pads `Global`: off in the device MIDI preferences.
- Drum track selected when saved.

Observed on hardware:

- With the Drum track selected, physical pads play Vinyl SP and physical keys
  play Wurli. This is the closest known-good working posture.
- With Wurli selected, the physical pads still follow the selected Wurli
  context instead of remaining a fully independent Drum surface. Bank A can
  sound notes, other banks do not provide useful drum access, and the Drum
  Program's pad colors are not displayed.
- Disabling the MPC Pads `Global` preference did not make all eight physical
  pad banks remain dedicated to the Drum Program while Wurli was selected.

Verdict: `warn`, closest known-good. Leave the Drum track selected during a
jam to retain Bank A drum behavior and Drum Program colors while the keyboard
routes to Wurli. Switching the selected track remains a limitation.

Capture and XPJ findings:

- Changed project: `Key37-routing-Noglobal.xpj`.
- Capture directory:
  `work/key37-routing-captures/2026-08-26-noglobal/` (Git-ignored).
- The XPJ persists exactly two meaningful track-input changes: Wurli from `All
  Ports` to `MPC Keyboard`, and Vinyl SP from `All Ports` to `MPC Pads`.
- The device-level MPC Pads `Global` toggle does not appear in the XPJ. It must
  be treated as a machine preference and checked separately after reload or on
  another MPC.
- The remaining raw comparison is save-time normalization and context: Main
  Mode versus Track View, Q-Link/scene bindings for the selected Drum Program,
  reordered-but-identical sample sets, floating-point metadata rounding, and
  loop-crossfade sentinel normalization. It is not evidence of a third routing
  change.

## Baseline project structure

All three XPJs report MPC 3 firmware header `3.9.1.2`, schema version 28, 120
BPM, no saved sequences, and exactly two musical tracks:

1. `Wurli` — Keygroup, record-armed.
2. `Vinyl SP From Mars 01 FG COLORS` — Drum, record-armed and selected.

The inspector also reports 28 system mixer tracks (16 outputs, four returns,
and eight submixes). Those are normal project infrastructure, not extra musical
tracks.

Next isolated experiment: reload `Key37-routing-Noglobal.xpj`, verify the two
track inputs persisted, then independently verify the MPC Pads `Global` device
preference. Keep the Drum track selected and test all pad banks plus the full
keyboard range before attempting the larger Scratchpad project.
