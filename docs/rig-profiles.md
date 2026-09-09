# Reusable MPC rig profiles

Rig profiles describe musical intent independently of one MPC project file.
They preserve track roles, external device channels, clock policy, controller
semantics, and hardware acceptance tests in reviewable TOML.

## Included profiles

- `rigs/fg-vinyl-scratchpad.toml`: nine internal tracks for immediate idea
  generation, with the selected eight-bank FG Vinyl Shots Drum Program on
  Track 2, Dark FM lead on Track 5, Glass Howl pad on Track 6, Sub Smooth bass
  pad on Track 7, loops on Track 8, and capture on Track 9. The first eight
  tracks retain the reusable controller-strip vocabulary; nine is a project
  layout choice, not an MPC track limit.
- `rigs/fg-volca-jam.toml`: the same strip model with Volca Drum on strip 1,
  Volca Bass on strip 3, and Volca Keys on strip 4.
- `rigs/fg-volca-direct-123.toml`: minimal three-track hardware test matching
  the captured Custom Modes—Keys channel 1, Bass channel 2, and Drum
  single-channel mode on channel 3.
- `rigs/fg-launch-control-xl3.toml`: Universal Mix semantics for 8 faders,
  three encoder rows, and two button rows.

Validate or render a setup sheet:

```bash
uv run mpc-rig check rigs/fg-volca-jam.toml
uv run mpc-rig plan rigs/fg-launch-control-xl3.toml \
  --output work/launch-control-setup.md
```

Validation catches duplicate tracks, invalid track types or MIDI channels,
unknown devices, mismatched track/device channels, duplicate external routes,
and duplicate controller endpoints. Warnings deliberately retain work that
requires hardware: unselected programs and learn-mode controller messages.
Malformed `devices`, `tracks`, and `control_groups` structures are rejected at
load time with the section and entry number, before validation or rendering.

## Launch Control XL 3 strategy

The first custom mode is semantic, not effect-specific:

- Faders: track volume 1–8
- Top encoders: tone/brightness
- Middle encoders: delay/movement
- Bottom encoders: reverb/space
- Upper buttons: mute
- Lower buttons: record arm or one consistently chosen performance function

The semantic rig now has an exact, declarative companion at
`midi/maps/fg-key37-lcxl3-volcas.toml`. It assigns isolated channel 16 CCs for
the eight-strip MPC Mix mode and official Korg CCs on channels 1, 2, and 10 for
Volca Bass, Keys, and Drum modes. Validate and compile it with:

```bash
uv run mpc-midi-control check midi/maps/fg-key37-lcxl3-volcas.toml
uv run mpc-midi-control compile midi/maps/fg-key37-lcxl3-volcas.toml \
  work/midi-control/fg-key37-lcxl3-volcas
```

The generated folder contains a Novation Components worksheet, MPC MIDI Learn
worksheet, MPC track-routing sheet, complete device MIDI reference, normalized
JSON, and a setup guide. The current topology sends all surface MIDI over USB
to the MPC; three monitored MIDI tracks pass Volca channels to MPC MIDI Out and
the Thru5. This retains the current one-source passive-thru topology.

Novation currently provides an official user guide, Programmer's Reference,
and Components editor. Components supports editable custom modes and message
behavior, plus local SysEx export. Novation does not publish the Custom Mode
binary serialization, so the compiler deliberately does not invent `.syx`
files. Create each mode once from the worksheet, export the official `.syx`,
and retain that binary beside the declarative source.

Akai documents mixer, Drum-pad, track, and insert-effect MIDI Learn targets,
and saves mappings with each project. It does not provide a supported project
mapping-file writer, and transport cannot be MIDI-Learned. The compiler marks
the lower performance-button row unverified until one exact project target is
chosen on hardware; transport continues through MPC clock/MMC.
See the [official XL 3 downloads](https://downloads.novationmusic.com/novation/launch-control-xl-3/launch-control-xl-3)
and [official Components guide](https://support.novationmusic.com/hc/en-gb/articles/27203903097362-Launch-Control-XL-3-Components-guide).

See [Declarative MIDI control](declarative-midi-control.md) for the routing
cross-reference, per-device control choices, supported automation boundary,
and the optional inherited Launch Control USB-to-DIN bridge map.

## Volca acceptance order

1. Set and record unique receive channels on Bass, Keys, and Drum.
2. Confirm one MPC MIDI track reaches only its named device.
3. Enable MPC clock send and confirm transport/tempo behavior on each unit.
4. Record a short pattern per device and reload the project.
5. Measure practical audio-input gain and listen for latency or doubled notes.
6. Test switching the keyboard/pads between internal and external tracks.

### Key 37 hardware checkpoint — August 26, 2026

Individual DIN MIDI tests pass with Volca Bass on channel 1, Volca Keys on
channel 2, and Volca Drum in single-channel mode on channel 10. The Drum also
passes MPC clock/start/stop and uses a verified six-pad Custom Pad Perform map:
A01–A06 send C3, D3, E3, F3, G3, and A3 respectively.

A CME MIDI Thru5 WC is ordered as the permanent distributor. The planned
topology is MPC physical MIDI Out to Thru5 MIDI In, then Thru outputs 1–3 to
Volca Bass, Keys, and Drum respectively. The Thru5 copies all MIDI data to each
output; channel assignments 1, 2, and 10 provide device isolation while system
clock and transport reach all three.

Until it arrives, tests are performed one device at a time. Simultaneous
isolation, clock, drift, and ten-minute jam acceptance remain pending. See
`inventory/volca-hardware-results.md`.

The checked-in channel choices are starting values, not claims about factory
defaults. Anyone reusing the profile can edit the TOML before generating their
own setup sheet.

## Session report

Combine rig validation, candidate readiness, and optional deployment/routing
evidence into one JSON handoff:

```bash
uv run mpc-session-report inventory/scratchpad-candidates.toml \
  --ledger inventory/program-status.csv \
  --rig rigs/fg-vinyl-scratchpad.toml \
  --routing-report work/key37-routing-captures/session-001/routing-report.json \
  --deployment-report work/sd-deploy-applied.json \
  --output work/session-report.json
```

Optional evidence paths may be absent, in which case the report adds a next
action. Existing paths must be regular, non-symlink files containing JSON
objects; malformed evidence is rejected instead of being reported as missing.

Search the full program ledger without editing it:

```bash
uv run mpc-library inventory/program-status.csv --type Keygroup \
  --hardware pass --favorite yes --role bass
```
