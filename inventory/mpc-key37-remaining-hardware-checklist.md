# MPC Key 37 remaining hardware master checklist

**Snapshot:** August 27, 2026
**Scope:** Every explicitly planned MPC hardware gate that is not already
closed. This is the active project queue, not a requirement to audition every
untested entry in the 750-program catalog.

For file-loading instructions, every path begins at **Browser > Places > SD
Card**. After loading a Drum Program, leave the Browser before judging pad
colors.

Record program results as:

`Program — pass/warn/fail — favorite/provisional/no — reload pass/fail — notes`

For pad-specific problems include bank and pad, for example:

`808 Distorted Kit — warn — provisional — reload pass — A07 much louder; hats choke correctly`

## 1. Do now: close the Vinyl Scratchpad program tests

### FG Vinyl Shots 04 Eight Bank

**Hardware result — August 27, 2026:** `pass`, selected/favorite Track 2 Shots
program. All Banks A–H and every acceptance item below passed.

Load:

`SD Card / 00 FG Scratchpad / 02 Vinyl Shots / FG Vinyl Shots 04 Eight Bank.xpm`

- [x] Confirm all 16 pads trigger exactly once in every Bank A–H.
- [x] Confirm Banks A and C are useful percussion banks.
- [x] Confirm Bank B contains FX, stabs, and vocal fragments.
- [x] Confirm Bank D contains character and transition hits.
- [x] Confirm Bank E contains claps, snaps, rims, and textured snares.
- [x] Confirm Bank F contains toms, metallic cymbals, and resonant percussion.
- [x] Confirm Bank G has kicks on G01–G08 and snares on G09–G16.
- [x] Confirm Bank H has closed hats on H01–H08 and the matching open hats on
  H09–H16.
- [x] Confirm every matched Bank H closed/open pair chokes correctly.
- [x] Confirm semantic colors remain visible after leaving Browser.
- [x] Record a two-bar fill, save/reload, and confirm colors, samples, sequence,
  and choke behavior return.
- [x] Keep as the selected Track 2 program; no pad replacement requested.

### FG Vinyl Kit Banks 01

**Hardware result — August 27, 2026:** `pass`, retained as a provisional Drum
alternate. Core loading, all-bank playback, named-family character, and choke
behavior work as expected. The same pattern recorded successfully on Banks A,
B, C, and G, and the multi-kit performance concept was reported as very
impressive. Save/reload also restores colors, samples, and mute behavior as
expected. A stricter normalized same-role layout is not necessary. Hardware
acceptance is complete.

Load:

`SD Card / 01 FG Favorites / 04 Drum Alternates / 03 FG Vinyl Kit Banks 01 / FG Vinyl Kit Banks 01.xpm`

- [x] Test all 16 pads in every Bank A–H.
- [x] Confirm A=808, B=909, C=Machinedrum, D=CR78, E=LM1, F=Acoustic Vinyl,
  G=Old Tape, and H=Acoustic Hybrid.
- [x] Confirm closed/open hats choke within each bank without choking unrelated
  banks.
- [x] Record the same pattern with Banks A, B, C, and G; all four worked and
  made a strong musical impression.
- [x] Save/reload and confirm colors, samples, and mute groups persist.
- [x] Compare against Shots 04: Kit Banks succeeds as a complete-groove bank
  family while Shots remains the selected accent/unusual-hit program.
- [x] Retain the source-native layouts; a stricter normalized variant is not
  necessary.

### FG Vinyl Layered Kit 01

**Initial hardware result — August 27, 2026:** strong provisional success. The
velocity-layered-pad concept was reported as excellent and worth developing
further. Hat choking was difficult to hear and may not be working, so retain a
`warn` until the velocity-specific test below passes. Full pad, boundary, groove,
and reload acceptance remain open.

Load:

`SD Card / 01 FG Favorites / 04 Drum Alternates / 04 FG Vinyl Layered Kit 01 / FG Vinyl Layered Kit 01.xpm`

- [ ] Confirm only Bank A is populated.
- [ ] Strike A01–A16 softly, medium-soft, medium-hard, and hard.
- [ ] Listen around velocity boundaries 31/32, 63/64, and 95/96 for disruptive
  pitch, volume, or character jumps.
- [ ] Confirm every velocity produces one sound with no silent band.
- [ ] Confirm A09/A10 and A11/A12 are two independent hat-choke pairs. The XPM
  contains Mute Groups 1 and 2, but the first hardware audition was
  inconclusive. For the clearest test, turn Full Level off, strike A12 at
  velocity 32–63 to select its 1.60-second LM1 open-hat layer, then strike A11;
  the A12 tail should stop abruptly. Cross-test A12 followed by A09; that must
  not choke.
- [ ] Record a two-bar groove without Full Level and judge whether normal playing
  reaches all four timbres naturally.
- [ ] Repeat with Full Level and confirm the hardest layer is predictable.
- [ ] Save/reload and repeat A01, A03, A09, A10, A13, and A15.
- [x] Velocity morphing is an excellent concept and merits further development.

### Close the selected main-kit behavior checks

Load:

`SD Card / 00 FG Scratchpad / 01 Main Drums / Vinyl SP From Mars 01 FG COLORS.xpm`

- [ ] Alternate closed/open hats and confirm choking feels correct.
- [ ] Play fast repeated kicks and snares; listen for unwanted cutting or overlap.
- [ ] Check perceived pad levels at a fixed master volume.
- [ ] Save, switch programs, reload, and confirm colors and sound persist.

## 2. Do now: Ableton Wave 01 — 32 programs

Common root:

`SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01`

For every Keygroup, test low/middle/high ranges, neighboring semitones,
soft/hard velocity, held notes, and reload. For every Drum Program, test every
occupied pad, semantic colors, velocity layers, choke behavior, relative
levels, and reload. Ableton effects/macros and Rack gain are not reproduced;
judge raw-sample playability and mapping.

### Five SP-1200 Keygroups

- [x] Chromatic Analog Tom — `warn`; loads, but requires transposing the Key 37
  down several octaves before notes trigger. Source roots are MIDI 27–42;
  investigate why the MPC does not honor the generated outer extrapolation.
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 01 Keygroups / SP-1200 From Mars / Chromatic Percussion / Chromatic Analog Tom.xpm`
- [x] Chromatic Chimes — `warn`; same behavior as Chromatic Analog Tom: notes
  require transposing down several octaves before they trigger. Source roots
  are MIDI 35–50; include in the Keygroup range-remapping investigation.
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 01 Keygroups / SP-1200 From Mars / Chromatic Percussion / Chromatic Chimes.xpm`
- [x] Chromatic Cowbell — `warn`; repeats the same octave-down-only trigger
  behavior. Source roots are MIDI 29–44; include in the corrected remap batch.
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 01 Keygroups / SP-1200 From Mars / Chromatic Percussion / Chromatic Cowbell.xpm`
- [x] Chromatic Tom — `warn`; repeats the same octave-down-only trigger
  behavior. Source roots are MIDI 25–40; include in the corrected remap batch.
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 01 Keygroups / SP-1200 From Mars / Chromatic Percussion / Chromatic Tom.xpm`
- [x] Chromatic Tone — `warn`; repeats the same octave-down-only trigger
  behavior. Source roots are MIDI 33–48; include in the corrected remap batch.
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 01 Keygroups / SP-1200 From Mars / Chromatic Percussion / Chromatic Tone.xpm`

**Five-program verdict:** all five load, but all require transposing down
several octaves before triggering. The software model's claimed outer-note
coverage is not honored by the MPC. Rebuild a comparison batch with the 16
source roots explicitly shifted into the normal Key 37 register; do not promote
these versions as finished instruments.

### Vinyl and SP-1200 Drum Programs

- [x] Vinyl Drums — Big Break Kit — `pass`; all 16 source pads work as
  expected.
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 02 Drum Programs / Vinyl Drums / Big Break Kit / Big Break Kit.xpm`
- [x] Vinyl Drums — Hand Break Kit — `pass`; all 16 source pads work as
  expected.
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 02 Drum Programs / Vinyl Drums / Hand Break Kit / Hand Break Kit.xpm`
- [x] SP-1200 — Factory Kit 1 — `pass`; its 12 populated pads are intentional,
  with A13–A16 empty by source design.
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 02 Drum Programs / SP-1200 / Factory Kit 1 / Factory Kit 1.xpm`
- [x] SP-1200 — Factory Kit 2 — `pass`; its 12 populated pads are intentional,
  with A13–A16 empty by source design.
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 02 Drum Programs / SP-1200 / Factory Kit 2 / Factory Kit 2.xpm`

### Roland-style Drum Programs

**Batch verdict — August 27, 2026:** most of the remaining Drum Programs were
auditioned without blocking problems, and the complete Drum wave was accepted
as done. Ordinary programs below are recorded `pass (batch accepted)`. The two
pre-existing source-choke anomalies remain accepted `warn`.

- [x] 505 — Clean Kit — `pass (batch accepted)`
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 02 Drum Programs / 505 / Clean Kit / Clean Kit.xpm`
- [x] 505 — SP-1200 Glitch Kit — `pass (batch accepted)`
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 02 Drum Programs / 505 / SP-1200 Glitch Kit / SP-1200 Glitch Kit.xpm`
- [x] 606 — Blender Kit — `pass (batch accepted)`
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 02 Drum Programs / 606 / Blender Kit / Blender Kit.xpm`
- [x] 606 — Clean Kit — `pass (batch accepted)`
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 02 Drum Programs / 606 / Clean Kit / Clean Kit.xpm`
- [x] 626 — Clean Kit 1 — `pass (batch accepted)`
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 02 Drum Programs / 626 / Clean Kit 1 / Clean Kit 1.xpm`
- [x] 626 — Color Kit 1 — `pass (batch accepted)`
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 02 Drum Programs / 626 / Color Kit 1 / Color Kit 1.xpm`
- [x] 707 — Mod Combo Kit — `pass (batch accepted)`
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 02 Drum Programs / 707 / Mod Combo Kit / Mod Combo Kit.xpm`
- [x] 707 — SP-1200 Dark Kit — `pass (batch accepted)`
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 02 Drum Programs / 707 / SP-1200 Dark Kit / SP-1200 Dark Kit.xpm`
- [x] 808 — Clean Kit 01 — `pass (batch accepted)`
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 02 Drum Programs / 808 / Clean Kit 01 / Clean Kit 01.xpm`
- [x] 808 — Distorted Kit — `pass (batch accepted)`
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 02 Drum Programs / 808 / Distorted Kit / Distorted Kit.xpm`
- [x] 909 — Clean Kit — `pass (batch accepted)`
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 02 Drum Programs / 909 / Clean Kit / Clean Kit.xpm`
- [x] 909 — Dirt Kit — `pass (batch accepted)`
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 02 Drum Programs / 909 / Dirt Kit / Dirt Kit.xpm`
- [x] CR-78 — Kit 1 — `pass (batch accepted)`
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 02 Drum Programs / CR-78 / Kit 1 / Kit 1.xpm`
- [x] CR-78 — Kit 2 — `pass (batch accepted)`
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 02 Drum Programs / CR-78 / Kit 2 / Kit 2.xpm`

### Other classic Drum Programs

- [x] DMX — Clean Kit 01 — `pass (batch accepted)`
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 02 Drum Programs / DMX / Clean Kit 01 / Clean Kit 01.xpm`
- [x] DMX — S612 Boogie Kit — `pass (batch accepted)`
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 02 Drum Programs / DMX / S612 Boogie Kit / S612 Boogie Kit.xpm`
- [x] Drumtrax — Kit 1 — `pass (batch accepted)`
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 02 Drum Programs / Drumtrax / Kit 1 / Kit 1.xpm`
- [x] Drumulator — Clean Kit — `pass (batch accepted)`
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 02 Drum Programs / Drumulator / Clean Kit / Clean Kit.xpm`
- [x] LM-1 — Computer Love Kit — `pass (batch accepted)`
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 02 Drum Programs / LM-1 / Computer Love Kit / Computer Love Kit.xpm`

### Character Drum Programs

- [x] Found Sounds — Body Kit — `pass (batch accepted)`; accepted as a 32-pad
  Banks A–B program.
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 02 Drum Programs / Found Sounds / Body Kit / Body Kit.xpm`
- [x] Modern Oddities — Hardware Glitch Kit — accepted `warn`; retain its source
  behavior where the lone closed-hat-labelled pad has no open partner or choke
  assignment.
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 02 Drum Programs / Modern Oddities / Hardware Glitch Kit / Hardware Glitch Kit.xpm`
- [x] S950 Snacks — Club 8 Kit — `pass (batch accepted)`
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 02 Drum Programs / S950 Snacks / Club 8 Kit / Club 8 Kit.xpm`
- [x] S950 Snacks — Hard Glitch Kit — accepted `warn`; retain its source
  behavior where the open-hat-labelled pad sits outside the main choke group.
  `SD Card / 00 FG Hardware Tests / SFM Ableton Wave 01 / 02 Drum Programs / S950 Snacks / Hard Glitch Kit / Hard Glitch Kit.xpm`

Known source behavior to verify rather than automatically fail:

- Hardware Glitch's lone closed-hat-labelled pad has no open partner or source
  choke assignment.
- S950 Hard Glitch's open-hat-labelled pad is outside the source rack's main
  choke group.

## 3. Do now: build and accept the revised Scratchpad project

Create a new project from the known-good dedicated-input routing posture. Do
not overwrite the earlier protected master.

Load the selected programs from these complete paths:

- Track 1 Main Drums:
  `SD Card / 00 FG Scratchpad / 01 Main Drums / Vinyl SP From Mars 01 FG COLORS.xpm`
- Track 2 Shots:
  `SD Card / 00 FG Scratchpad / 02 Vinyl Shots / FG Vinyl Shots 04 Eight Bank.xpm`
- Track 3 Bass:
  `SD Card / 00 FG Scratchpad / 03 Bass / Pluck Bass.xpm`
- Track 4 Keys:
  `SD Card / 00 FG Scratchpad / 04 Keys / Wurli.xpm`
- Track 5 Lead:
  `SD Card / 00 FG Scratchpad / 05 Lead / Dark FM.xpm`
- Track 6 Pad:
  `SD Card / 00 FG Scratchpad / 06 Pad / Glass Howl.xpm`
- Track 7 Bass Pad:
  `SD Card / 00 FG Scratchpad / 07 Bass Pad / Sub Smooth.xpm`

Then create Track 8 as an empty reserved Clip track and Track 9 as an Audio
capture/transition track.

- [ ] Preserve the closest known-good routing: melodic tracks use `MPC
  Keyboard`, Drum tracks use `MPC Pads`, Rec Arm Behaviour is `Multi`, and the
  active Drum track remains selected when independent pads/keys are needed.
- [ ] Balance useful starting levels without mastering.
- [ ] Record four bars containing Main Drums, Shots, Pluck Bass, Wurli, and at
  least one actual Dark FM lead phrase. The prior capture had no lead events.
- [ ] Add Glass Howl and Sub Smooth only if they improve the idea; their track
  existence and reload still need confirmation even if no notes are recorded.
- [ ] Save the protected master as:
  `SD Card / Projects / FG Scratchpad / FG Vinyl Scratchpad v0.2 Master.xpj`
- [ ] Save a disposable copy as:
  `SD Card / Projects / FG Scratchpad / FG Vinyl Scratchpad v0.2 Jam.xpj`
- [ ] Power-cycle/reload the Master and confirm programs, colors, track names,
  inputs, record-arm state, and sequence return.
- [ ] Time a cold start from power-on to the first recorded drum-and-keys idea;
  target under one minute.

## 4. Do now: create the minimal Clip reference

This is an on-device format capture, not a musical loop-library test. It is
blocked only if no suitable short Vinyl Breaks WAV is currently on the SD.

- [ ] Start an empty disposable project and create one Clip track/program.
- [ ] Assign one short Vinyl Breaks WAV to A01.
- [ ] Set one-bar launch quantization and tempo/warp synchronization if exposed.
- [ ] Save the baseline as:
  `SD Card / Projects / FG Clip Reference / Key37_Clip_Reference_01.xpj`
- [ ] Save/export the Clip Program, if the MPC offers it, as:
  `SD Card / Projects / FG Clip Reference / Key37_Clip_Reference_01.xpm`
- [ ] Change exactly one Clip behavior and write down the setting name and old/new
  values.
- [ ] Save the changed copy as:
  `SD Card / Projects / FG Clip Reference / Key37_Clip_Reference_02.xpj`
- [ ] Save/export the changed XPM, if available, as:
  `SD Card / Projects / FG Clip Reference / Key37_Clip_Reference_02.xpm`
- [ ] Return the SD card to Ubuntu so both XPJs, available XPMs, and companion
  ProjectData folders can be copied without modification and compared.

## 5. Optional now: finish the curated comparison bracket

The core choices are already closed. These tests are optional and should not
delay Scratchpad acceptance.

### Bass alternatives

- [ ] Junos Dusty Pluck
  `SD Card / Programs / Keygroups / Samples From Mars / Junos From Mars / Bass / Dusty Pluck.xpm`
- [ ] Mini Mama Bass
  `SD Card / Programs / Keygroups / Samples From Mars / Mini From Mars / Bass / Mama Bass.xpm`
- [ ] Mirage Melodic Bass
  `SD Card / Programs / Keygroups / Samples From Mars / Mirage From Mars / Bass / Melodic Bass.xpm`

Use the same saved Pluck Bass sequence, octave, level, and effects for all
three comparisons.

### Keys alternatives

- [ ] Emulator Drift Keys
  `SD Card / Programs / Keygroups / Samples From Mars / Emulator From Mars / Keys / Drift Keys.xpm`
- [ ] OB Warble Chords
  `SD Card / Programs / Keygroups / Samples From Mars / OB From Mars / Keys / Warble Chords.xpm`

### Lead/pad alternatives

- [ ] 2600 BuildAShimmerPad
  `SD Card / Programs / Keygroups / Samples From Mars / 2600 From Mars / Pads / BuildAShimmerPad.xpm`
- [ ] Emulator Resonant Glass
  `SD Card / Programs / Keygroups / Samples From Mars / Emulator From Mars / Pads / Resonant Glass.xpm`
- [ ] Mini Sharp Lead
  `SD Card / Programs / Keygroups / Samples From Mars / Mini From Mars / Leads / Sharp Lead.xpm`

For each optional Keygroup test normal octave, octave down/up, velocity,
sustain, pitch bend, modulation, useful range, relative level, and reload.

## 6. Plugin installation and persistence audit

These are selected from an MPC Plugin track, not loaded as SD files.

- [ ] Confirm **Iona** appears, creates a playable Plugin track, and survives
  save/power-cycle/reload.
- [ ] Confirm **OPx-4** appears, creates a playable Plugin track, and survives
  save/power-cycle/reload.
- [ ] Confirm **AIR Flavor Pro** appears and can be inserted, heard, saved, and
  restored.
- [ ] Confirm installation state for **Jura**.
- [ ] Confirm installation state for **Mini D**.
- [ ] Confirm installation state for **Studio Strings**.
- [ ] Confirm installation state for **Fabric / Fabric Collection**.
- [ ] For every newly purchased/downloaded plugin, record: installed location,
  version if shown, preset load, basic playability, save/reload, and whether it
  deserves a Scratchpad role.

The earlier filesystem audit found Iona, OPx-4, and AIR Flavor Pro content under
the SD `Synths` folder. It did not find the other four there, but they may be
installed in MPC internal storage.

## 7. Needs one more SD transfer before testing

These local packages are generated and validated but were not part of the most
recent SD deployment. Do not search for them on the MPC until Ubuntu deploys
them.

### Layout comparison package

Planned MPC paths after deployment:

- [ ] Classic:
  `SD Card / 00 FG Hardware Tests / Layout Trial v2 / 01-classic-mpc / FGVS03 Classic.xpm`
- [ ] Right-handed:
  `SD Card / 00 FG Hardware Tests / Layout Trial v2 / 02-right-handed-performance / FGVS03 Right.xpm`
- [ ] Left-handed:
  `SD Card / 00 FG Hardware Tests / Layout Trial v2 / 03-left-handed-performance / FGVS03 Left.xpm`
- [ ] Full-library source order:
  `SD Card / 00 FG Hardware Tests / Layout Trial v2 / 04-full-library / FGVS03 Full.xpm`

After deployment:

- [ ] Load Classic and Right first and leave Browser so colors appear.
- [ ] Trigger all 96 populated pads in Banks A–F.
- [ ] Record the same pattern without looking at the screen; count wrong-pad
  strikes and judge one-handed comfort.
- [ ] Compare Left only if it offers a plausible advantage.
- [ ] Save/reload at least Classic and the best handed candidate.
- [ ] Confirm samples, colors, choke, and playback behavior persist.
- [ ] Choose Classic, a handed layout, or full-library source order.

### Semantic MIDI comparison

Planned MPC paths after deployment:

- [ ] Source-layout MIDI:
  `SD Card / 00 FG Hardware Tests / MIDI / dusty-pocket-source.mid`
- [ ] Classic-layout MIDI:
  `SD Card / 00 FG Hardware Tests / MIDI / dusty-pocket-classic.mid`

After deployment, import the source MIDI onto the original Vinyl SP program
and Classic MIDI onto `FGVS03 Classic`. Confirm both express the same
kick/snare/hat intent, and that tempo 91 BPM, swing, velocities, and loop length
survive import and project reload.

### Clip reference audio

If no Vinyl Breaks WAV is already accessible on the SD, Ubuntu must deploy one
short legal source WAV to this planned path before Section 4:

`SD Card / 00 FG Hardware Tests / Clip Reference / Vinyl Breaks Test.wav`

## 8. Waiting on or using external hardware

### Volca Jam

Already passed: Bass channel 1 individually, Keys channel 2 individually, Drum
channel 10 individually, Drum custom A01–A06 mapping, and Drum clock/start/stop.

The prior Volca XPJ was archived off the SD during cleanup. Restore or create
the next protected project at:

`SD Card / Projects / FG Volca Jam / FG Volca Jam v0.2 Master.xpj`

- [ ] Record and play an actual MPC-authored Volca Drum sequence using an empty
  Volca pattern.
- [ ] Record short MPC-authored patterns for Volca Bass and Volca Keys.
- [ ] Confirm Volca Bass and Keys individually follow MPC clock and transport.
- [ ] After the CME MIDI Thru5 WC is available, connect all three and confirm
  each MIDI track reaches only its intended device.
- [ ] Confirm all three receive predictable start/stop and remain in sync.
- [ ] Check doubled notes, stuck notes, unwanted program changes, and ten-minute
  clock drift.
- [ ] Record practical audio monitoring/capture gain settings.
- [ ] Switch keyboard/pads among internal and external tracks.
- [ ] Save, power-cycle/reload, and confirm ports, channels, clock, pad map, and
  track names return.
- [ ] Perform a ten-minute jam and count touchscreen interruptions.

### Launch Control XL 3

No SD file should be loaded until the mapping is created and saved on hardware.

- [ ] Check/update Launch Control XL 3 firmware with Novation Components.
- [ ] Confirm standalone USB connection to the Key 37.
- [ ] Verify all intended faders, encoders, and buttons send distinct messages.
- [ ] Map faders 1–8 to track volume 1–8.
- [ ] Map top encoders to tone/brightness.
- [ ] Map middle encoders to delay/movement.
- [ ] Map bottom encoders to reverb/space.
- [ ] Map upper buttons to track mute.
- [ ] Try lower buttons as record arm; keep only if safe and useful.
- [ ] Check for disruptive value jumps when first touching each control.
- [ ] Save the controller custom mode and MPC project.
- [ ] Power-cycle both devices and confirm persistence.
- [ ] Clone the Scratchpad project and confirm Universal Mix meanings persist.
- [ ] Perform a ten-minute jam with minimal touchscreen navigation.

## 9. Optional routing research; core workflow already passes

The closest known-good posture is proven: keep the Drum track selected, use
dedicated `MPC Pads`/`MPC Keyboard` inputs, and use Multi record arm. Drum Split
is not a physical pads-versus-keyboard split.

Only continue this section if understanding the remaining device behavior is
worth the session time:

- [ ] Test Internal Keyboard Routing `Global` in isolation.
- [ ] Restore baseline, then test `Tracks` in isolation.
- [ ] Restore baseline, then test `Global and Tracks` in isolation.
- [ ] For each, record exactly what the keys trigger, what pads trigger, whether
  anything cross-triggers, and whether it survives reload.
- [ ] Reload the dedicated-input project and verify the device-level MPC Pads
  `Global` preference separately because it is not stored in the XPJ.

The old routing projects were intentionally removed from the SD and remain in
the verified Ubuntu/external-drive capture. They need redeployment before this
optional section can use file-based baselines.

## 10. Completion gates

- [x] Shots 04 accepted as the selected/favorite Track 2 program.
- [x] Kit Banks passes and is retained as a provisional Drum alternate; its
  four-bank pattern comparison and save/reload persistence also pass.
- [ ] Layered Kit concept accepted; complete pad/boundary/reload tests and
  resolve the hardware choke warning.
- [x] All 32 Ableton Wave 01 programs have results: five Keygroup range warnings,
  25 Drum passes, and two accepted source-choke Drum warnings.
- [ ] Revised Scratchpad Master saves/reloads with a recorded lead phrase.
- [ ] Cold-start idea captured in under one minute.
- [ ] Minimal Clip reference pair returned to Ubuntu for inspection.
- [ ] Layout and semantic MIDI packages deployed and tested.
- [ ] Plugin installation/persistence audit complete.
- [ ] Actual MPC-authored Volca sequences survive reload.
- [ ] Three-Volca isolation/sync passes after the CME distributor arrives.
- [ ] Launch Control Universal Mix mapping survives power-cycle and project clone.

## Already closed — do not repeat unless behavior regresses

- Original seven Scratchpad candidates all received hardware results.
- Main drums selected: Vinyl SP From Mars 01.
- Primary bass selected: Mirage Pluck Bass.
- Keys selected: Mirage Wurli.
- Lead selected: Emulator Dark FM.
- Pad selected: Kawaii Dreams Glass Howl.
- Bass Pad selected: Juno Sub Smooth.
- Minimal Scratchpad core recorded drums, bass, and keys and survived reload.
- Routing baseline, Drum Split, and dedicated-input behavior were captured and
  inspected.
- Individual Volca Bass, Keys, and Drum MIDI routing passed.
- Volca Drum pad mapping and clock/start/stop passed.
- SD write repair, sustained write probe, and verified program deployments
  passed.
