# Volca Direct 1-2-3 MPC project test

This is the shortest project that matches the September 3 Launch Control
captures. It deliberately uses the Volca Drum's **single-channel** mode.

## Intended project

1. `VOLCA KEYS` — MIDI Track 1, output channel 1.
2. `VOLCA BASS` — MIDI Track 2, output channel 2.
3. `VOLCA DRUM` — MIDI Track 3, output channel 3.

The two Launch Control modes named `Volca Drum 1-3` and `Volca Drum 4-6` are
parameter pages, not separate MIDI output channels. Both captured exports send
their drum controls on channel 3.

## MPC setup

1. Start a new empty project and delete any automatically added factory tracks.
2. Add three MIDI tracks in the order above.
3. Set every track's output port to the physical port feeding the Volcas. Start
   with `MPC MIDI Out`; if the confirmed USB-to-DIN bridge is used instead,
   select the Launch Control `To DIN Out 1` port on all three tracks.
4. Set output channels to 1, 2, and 3 respectively.
5. Keep track monitoring on `Auto`. Select one track at a time for the first
   isolation pass.
6. In MIDI/Sync preferences, send MIDI Clock and transport from the selected
   output port. Avoid enabling two clock outputs that reach the same Volcas.
7. Set Volca Keys receive to channel 1, Volca Bass to channel 2, and Volca Drum
   to single-channel mode on channel 3. Enable short-message reception.
8. On `VOLCA DRUM`, use Pad Perform Custom notes A01-A06 as 60, 62, 64, 65, 67,
   and 69—the pad map already proven on this hardware.
9. Save as `FG Volca Direct 123.xpj` on the SD card.

## Ordered acceptance pass

- [ ] Track 1 keys play only Volca Keys.
- [ ] Track 2 keys play only Volca Bass.
- [ ] Track 3 pads A01-A06 play Drum parts 1-6.
- [ ] Launch Control `Volca Keys` changes only Keys parameters.
- [ ] Launch Control `Volca Bass` changes only Bass parameters.
- [ ] Both Drum pages change the intended Drum parts while remaining on ch3.
- [ ] MPC Play starts all connected Volcas once, with no doubled clock or notes.
- [ ] Record one bar per track, save, reload, and replay it.
- [ ] Confirm track names, output port, channels, Pad Perform map, tempo, and
  Launch Control behavior survive reload.

## Capture after the test

Put the MPC into Controller Mode and preserve both:

- `SD Card / Projects / FG Volca Direct 123.xpj`
- `SD Card / Projects / FG Volca Direct 123_[ProjectData]/`

Then run `mpc-xpj inspect` and `mpc-xpj midi-learn` against the saved project.
Do not use XPJ comparison to infer a single setting unless the before/after
projects differ by only that setting.
