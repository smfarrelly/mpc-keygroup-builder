# MPC Key 37 remaining hardware master checklist

**Snapshot:** August 27, 2026
**Scope:** Every explicitly planned MPC hardware gate that is not already
closed. This is the active project queue, not a requirement to audition every
untested entry in the 750-program catalog.

**Current posture:** Hardware acceptance sessions are deferred while software
and documentation continue. Unchecked items are preserved test designs, not an
immediate queue. Descriptive conclusions from completed tests live in
`docs/MPC_KEY37_FIELD_REVIEW.md`.

For file-loading instructions, every path begins at **Browser > Places > SD
Card**. After loading a Drum Program, leave the Browser before judging pad
colors.

Record program results as:

`Program — pass/warn/fail — favorite/provisional/no — reload pass/fail — notes`

For pad-specific problems include bank and pad, for example:

`808 Distorted Kit — warn — provisional — reload pass — A07 much louder; hats choke correctly`

## Deferred acceptance batch: expanded Drum banks 01

**Built, validated, and deployed — August 27, 2026; hardware acceptance
deferred.** These are the only new programs added by the cleanup/expansion
pass. A shallow on-card guide is at:

`SD Card / 01 FG Favorites / 04 Drum Alternates / 00 DRUM ALTERNATES INDEX.txt`

Full maps and technical results are in `inventory/fg-expanded-drum-banks-01.md`.

### 06 FG Classic Machines Banks 01

Load:

`SD Card / 01 FG Favorites / 04 Drum Alternates / 06 FG Classic Machines Banks 01 / FG Classic Machines Banks 01.xpm`

- [ ] Leave Browser and confirm colors.
- [ ] Test all pads: A=505, B=606, C=626, D=707, E=808, F=909, G=CR-78,
  H=DMX.
- [ ] Record one pattern on two contrasting banks.

### 07 FG Character Machines Banks 01

Load:

`SD Card / 01 FG Favorites / 04 Drum Alternates / 07 FG Character Machines Banks 01 / FG Character Machines Banks 01.xpm`

- [ ] Leave Browser and confirm colors.
- [ ] Test all pads: A=505 Glitch, B=606 Blender, C=626 Color, D=707 Dark,
  E=808 Distorted, F=909 Dirt, G=DMX S612, H=Hardware Glitch.
- [ ] Record one pattern on two contrasting banks.
- [ ] H10 has the accepted source program's missing-choke warning; judge it as
  source behavior, not a new composer failure.

### 08 FG Breaks Texture Banks 01

Load:

`SD Card / 01 FG Favorites / 04 Drum Alternates / 08 FG Breaks Texture Banks 01 / FG Breaks Texture Banks 01.xpm`

- [ ] Leave Browser and confirm colors.
- [ ] Test all pads: A=Big Break, B=Hand Break, C=Drumtrax, D=Drumulator,
  E=LM-1, F=Body Kit, G=S950 Club 8, H=S950 Hard Glitch.
- [ ] Record one pattern on two contrasting banks.
- [ ] H16 has the accepted source program's missing-choke warning; judge it as
  source behavior, not a new composer failure.

### 09 FG Vinyl Layered Banks 03

Load:

`SD Card / 01 FG Favorites / 04 Drum Alternates / 09 FG Vinyl Layered Banks 03 / FG Vinyl Layered Banks 03.xpm`

- [ ] Confirm Banks A-D are populated and E-H are intentionally empty.
- [ ] Play all pads in A-D at soft, medium-soft, medium-hard, and hard velocity.
- [ ] Check boundaries 31/32, 63/64, and 95/96 on each bank's kicks, snares,
  hats, cymbal, and FX pad.
- [ ] Test hat choke pairs A09/A10, A11/A12, B07/B08, B09/B10, C07/C08,
  C09/C10, and D07/D08. Cross-group hits must not choke.
- [ ] Save/reload the preferred new program and confirm colors, layers, samples,
  and mute groups persist.

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

**Hardware direction — August 27, 2026:** excellent and promoted to a
provisional main-drum candidate. Expand the velocity-layered-pad idea and test a
refined follow-up directly against the current Vinyl SP main-drums favorite.
Hat choking was difficult to hear and may not be working, so retain a technical
`warn` until the velocity-specific test below passes. Full pad, boundary,
groove, and reload acceptance remain open.

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
- [x] Velocity morphing is excellent; promote the concept to a provisional
  main-drum candidate and build a refined follow-up.

### Close the selected main-kit behavior checks

Load:

`SD Card / 00 FG Scratchpad / 01 Main Drums / Vinyl SP From Mars 01 FG COLORS.xpm`

- [ ] Alternate closed/open hats and confirm choking feels correct.
- [ ] Play fast repeated kicks and snares; listen for unwanted cutting or overlap.
- [ ] Check perceived pad levels at a fixed master volume.
- [ ] Save, switch programs, reload, and confirm colors and sound persist.

### FG Vinyl Layered Main 02 — refined main-kit comparison

**Built, validated, and deployed — August 27, 2026.** The second candidate uses
coherent drum families, four complete velocity regions on all 16 pads, and two
hat pairs whose open layers retain audible tails at every velocity.

**Musical result — August 27, 2026:** liked and accepted as an expressive Drum
alternate. Vinyl SP remains the Scratchpad main-drums favorite. The role choice
is final; the remaining checks below are technical acceptance, not another
main-kit contest.

Load:

`SD Card / 01 FG Favorites / 04 Drum Alternates / 05 FG Vinyl Layered Main 02 / FG Vinyl Layered Main 02.xpm`

- [ ] Confirm only Bank A is populated and all 16 pads show semantic colors.
- [ ] Test every pad across velocities 0–31, 32–63, 64–95, and 96–127.
- [ ] Check the 31/32, 63/64, and 95/96 boundaries.
- [ ] Strike A10 then A09 at each velocity; A10 must choke. A10 then A11 must
  not choke.
- [ ] Strike A12 then A11 at each velocity; A12 must choke. A12 then A09 must
  not choke.
- [x] Musical comparison closed: keep Vinyl SP as main and Layered Main 02 as
  the expressive alternate.
- [ ] Save/reload and confirm the expressive alternate persists correctly.

## 2. Do now: Ableton Wave 01 — 32 programs

**Cleanup note — August 27, 2026:** the completed source batch was removed from
the live SD after all 27 Drum results were accepted. It remains recoverable in
the external cleanup archive documented by `inventory/sd-cleanup-2026-08-27.md`.
Paths below are historical and require selective redeployment before any
optional retest.

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

### Normal-register comparison set

All five source instruments were rebuilt with their roots shifted up exactly
24 semitones. No audio was resampled or normalized. Common root:

`SD Card / 00 FG Hardware Tests / SFM Keygroup Register Fix 01 / Chromatic Percussion`

- [ ] Chromatic Analog Tom NR — `Chromatic Analog Tom NR.xpm`; roots 51–66.
- [ ] Chromatic Chimes NR — `Chromatic Chimes NR.xpm`; roots 59–74.
- [ ] Chromatic Cowbell NR — `Chromatic Cowbell NR.xpm`; roots 53–68.
- [ ] Chromatic Tom NR — `Chromatic Tom NR.xpm`; roots 49–64.
- [ ] Chromatic Tone NR — `Chromatic Tone NR.xpm`; roots 57–72.

Load each without octave transpose. Confirm the 16 source voices occur in the
normal keyboard register, test neighboring keys, and save/reload the best one.

**NR1 result — August 27, 2026:** close, but every program should move one more
octave to the right. Do not repeat this set unless directly comparing a boundary
with NR2.

### Normal-register 02 — warning; superseded by NR3

These shift the original roots up 36 semitones, one octave farther right than
NR1. The 85-file package was transactionally deployed and checksum-verified on
August 28, 2026. Its canonical recoverable copy is on the external drive under
`MPC Transfer / FG Software Candidates 2026-08-28 / SFM Keygroup Register Fix 02`.

Verified common root:

`SD Card / 00 FG Hardware Tests / SFM Keygroup Register Fix 02 / Chromatic Percussion`

- [ ] Chromatic Analog Tom NR2 — `Chromatic Analog Tom NR2.xpm`; roots 63–78.
- [ ] Chromatic Chimes NR2 — `Chromatic Chimes NR2.xpm`; roots 71–86.
- [ ] Chromatic Cowbell NR2 — `Chromatic Cowbell NR2.xpm`; roots 65–80.
- [ ] Chromatic Tom NR2 — `Chromatic Tom NR2.xpm`; roots 61–76.
- [ ] Chromatic Tone NR2 — `Chromatic Tone NR2.xpm`; roots 69–84.

**NR2 result — August 28, 2026:** all five remain too low for the desired
default-position workflow; seven keys are unavailable. Preserve NR2 as evidence
and move the complete family exactly one more octave upward.

### Normal-register 03 — built; SD deployment pending

NR3 uses an explicit +48-semitone shift from the original mappings, +12 above
NR2, without resampling or changing the 80 WAVs. All five programs pass batch
inspection, structural validation, and normalized-model loading.

Planned common root:

`SD Card / 00 FG Hardware Tests / SFM Keygroup Register Fix 03 / Chromatic Percussion`

- [ ] Chromatic Analog Tom NR3 — `Chromatic Analog Tom NR3.xpm`; roots 75–90.
- [ ] Chromatic Chimes NR3 — `Chromatic Chimes NR3.xpm`; roots 83–98.
- [ ] Chromatic Cowbell NR3 — `Chromatic Cowbell NR3.xpm`; roots 77–92.
- [ ] Chromatic Tom NR3 — `Chromatic Tom NR3.xpm`; roots 73–88.
- [ ] Chromatic Tone NR3 — `Chromatic Tone NR3.xpm`; roots 81–96.

The source package is checksum-verified on the external drive at
`MPC Transfer / FG Software Candidates 2026-08-28 / SFM Keygroup Register Fix 03`.
The SD card was removed immediately before deployment, and the transactional
deployer published no partial destination. Reinsert the card, deploy once, then
test all five without keyboard octave transpose.

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

**Captured structure — August 27, 2026:**
`FG Vinyl Scratchpad v02 Master.xpj` and its ProjectData folder were copied
read-only from the SD and hash-verified. The project contains the intended two
Drum tracks, six Keygroup tracks, and one Audio track, with all seven selected
programs present. It has no saved sequence. Track 8 is named `Clip` but is
actually a Keygroup track, and Track 9 is still named `Audio 001`.

Preserve this captured v02 Master. Make the corrections and musical acceptance
work in a new Jam copy rather than overwriting it.

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

Current track structure:

- [x] Tracks 1–2 are Drum tracks: Main Drums and Shots.
- [x] Tracks 3–7 are Keygroups: Pluck Bass, Wurli, Dark FM, Glass Howl, and Sub
  Smooth.
- [ ] Remove or repurpose Track 8, currently a Keygroup merely named `Clip`, in
  the Jam copy. Modern Clip Workflow is unavailable without Pro Pack and must
  not be represented by a renamed Keygroup.
- [x] Track 9 is an Audio track; rename `Audio 001` to `Capture` or `Audio
  Capture` in the Jam copy.

- [ ] Preserve the closest known-good routing: melodic tracks use `MPC
  Keyboard`, Drum tracks use `MPC Pads`, Rec Arm Behaviour is `Multi`, and the
  active Drum track remains selected when independent pads/keys are needed.
- [ ] Balance useful starting levels without mastering.
- [ ] Record four bars containing Main Drums, Shots, Pluck Bass, Wurli, and at
  least one actual Dark FM lead phrase. The prior capture had no lead events.
- [ ] Add Glass Howl and Sub Smooth only if they improve the idea; their track
  existence and reload still need confirmation even if no notes are recorded.
- [x] Preserve the captured protected master at:
  `SD Card / Projects / FG Scratchpad / FG Vinyl Scratchpad v02 Master.xpj`
- [ ] Save a disposable copy as:
  `SD Card / Projects / FG Scratchpad / FG Vinyl Scratchpad v0.2 Jam.xpj`
- [ ] Power-cycle/reload the Master and confirm programs, colors, track names,
  inputs, record-arm state, and sequence return.
- [x] Defer cold-start timing at the user's request; the under-one-minute target
  remains available when operational timing work resumes.

## 4. Deferred: create the minimal Clip reference

**Purchase-gated — August 27, 2026:** The MPC Key 37 does not own MPC Pro
Pack, so MPC 3 Clip Workflow and Clip Matrix are unavailable. This is an
optional paid-feature boundary, not a hardware or OS failure. Do not substitute
a Keygroup merely named `Clip`; resume this section only if Pro Pack is
purchased later.

This is an on-device format capture, not a musical loop-library test. The
reference audio was verified byte-for-byte, then removed from the live card
during cleanup. It is recoverable from the external archive at its former path:

`SD Card / 00 FG Hardware Tests / Clip Reference / 080 Black Phase Vinyl Breaks Clean.wav`

It is a stereo 44.1 kHz, 80 BPM, 12-second loop estimated at 16 beats/four
bars. The empty destination project folder was also removed from the live card.

- [ ] Start an empty disposable project and create one Clip track/program.
- [ ] Assign the exact deployed Vinyl Breaks WAV above to A01.
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

**Accepted without a dedicated persistence project — August 27, 2026:** The
user considers normal plugin save/reload behavior sufficiently established.
Reopen this gate only if a real project reports a missing plugin, preset, or
edited parameter after reload.

- [ ] Confirm **Iona** appears, creates a playable Plugin track, and survives
  save/power-cycle/reload.
- [ ] Confirm **OPx-4** appears, creates a playable Plugin track, and survives
  save/power-cycle/reload.
- [ ] Confirm **AIR Flavor Pro** appears and can be inserted, heard, saved, and
  restored.
- [x] **Jura** is installed on MPC internal storage.
- [ ] **Mini D** is not purchased; deferred rather than failed.
- [ ] **Studio Strings** is not purchased; deferred rather than failed.
- [x] **Fabric / Fabric Collection** is installed on MPC internal storage.
- [ ] For every newly purchased/downloaded plugin, record: installed location,
  version if shown, preset load, basic playability, save/reload, and whether it
  deserves a Scratchpad role.

The earlier filesystem audit found Iona, OPx-4, and AIR Flavor Pro content under
the SD `Synths` folder. The August 27 reusable audit now records 104 Iona
presets, 672 OPx-4 presets plus 68 content assets, and 101 AIR Flavor Pro
presets. It did not find plugin-content directories for Jura, Mini D, Studio
Strings, or Fabric/Fabric Collection. Jura-named factory oscillator assets are
not evidence of a Jura installation. Any plugin may still have its executable
or activation state in MPC internal storage, so hardware selection and
save/reload remain authoritative.

Fabric and Jura were subsequently confirmed on hardware in internal storage.
Their absence from the SD audit is therefore expected. Plugin persistence is
accepted by user judgment without constructing the disposable audit project;
Iona, OPx-4, and AIR Flavor Pro retain strong SD content evidence but no new
individual power-cycle result was claimed.

## 7. Deployed and ready: layout and semantic MIDI comparison

**Deployment verified — August 27, 2026:** all four layout packages and both
MIDI files are now on the SD. The four programs pass simulation directly from
the card with zero dead or stacked cells, and all 396 deployed files match the
local sources by relative path and SHA-256.

### Layout comparison package

**Layout decision — August 27, 2026:** select the right-handed performance
layout. The difference from Classic is modest because this 96-pad source is
dominated by varied one-shots rather than a small repeated
kick/snare/cymbal-style performance kit, but Right is still the preferred
default. Retain Classic, Left, and Full as reference variants.

**Persistence result — August 27, 2026:** save/reload, samples, playback, and
semantic pad colors all return correctly. The right-handed layout is accepted
and the layout-engine hardware gate is closed.

MPC paths:

- [x] Classic auditioned:
  `SD Card / 00 FG Hardware Tests / Layout Trial v2 / 01-classic-mpc / FGVS03 Classic.xpm`
- [x] Right-handed auditioned and selected:
  `SD Card / 00 FG Hardware Tests / Layout Trial v2 / 02-right-handed-performance / FGVS03 Right.xpm`
- [ ] Left-handed:
  `SD Card / 00 FG Hardware Tests / Layout Trial v2 / 03-left-handed-performance / FGVS03 Left.xpm`
- [ ] Full-library source order:
  `SD Card / 00 FG Hardware Tests / Layout Trial v2 / 04-full-library / FGVS03 Full.xpm`

After deployment:

- [x] Load Classic and Right first and leave Browser so colors appear.
- [ ] Trigger all 96 populated pads in Banks A–F.
- [ ] Record the same pattern without looking at the screen; count wrong-pad
  strikes and judge one-handed comfort.
- [ ] Compare Left only if it offers a plausible advantage.
- [x] Save/reload Classic and the selected Right candidate.
- [x] Confirm samples, colors, and playback behavior persist.
- [x] Choose Right as the preferred layout; the improvement is useful but
  modest for this diverse one-shot collection.

### Semantic MIDI comparison

**Format-0 hardware result — fail, August 27, 2026:** Both files were visible
in the MPC Browser, but Load only flickered and neither file created a new
sequence on MPC 3.9.1.2. Do not retry those deployed copies. Format-1
replacements were deployed and checksum-verified on August 27, 2026; their
hardware import was then tested successfully.

**Format-1 hardware result — pass with listening caveat, August 27, 2026:**
The source/Classic comparison is musically close enough to accept. Precise
event-for-event differences are difficult to hear in this varied one-shot
material, so this result proves import and general semantic intent rather than
an isolated audible measurement of every velocity, swing offset, or note.

MPC paths:

- [x] Format-1 source-layout MIDI (deployed and hardware-tested):
  `SD Card / 00 FG Hardware Tests / MIDI / dusty-pocket-source.mid`
- [x] Format-1 Classic-layout MIDI (deployed and hardware-tested):
  `SD Card / 00 FG Hardware Tests / MIDI / dusty-pocket-classic.mid`

Both imports express sufficiently similar kick/snare/hat intent to close the
semantic-layout hardware gate. Exact tempo, swing, velocity, and project-reload
persistence remain available for a stricter future diagnostic if needed.

### Optional Program Designer groove-suggestion regression

Software acceptance passed against the same format-1 `dusty-pocket-source.mid`:
all 28 note-ons map to seven sounds, the right-hand usage model suggests 12
moves, browser draft locks remain fixed, undo is exact, and the exported XPM
uses the already hardware-accepted preservation-safe layout engine. This is a
small integration regression, not a new layout-engine hardware gate.

- [ ] At a future hardware session, package and deploy one browser-authored
  right-hand groove suggestion with its existing ProgramData audio.
- [ ] Load it beside the accepted source/right-handed references and trigger
  every groove-active sound.
- [ ] Confirm suggested placement and explicit colors, then save/reload once.
- [ ] Remove the disposable candidate after recording the result unless it is
  musically better than the accepted Right layout.

### Clip reference audio

**Deployed and checksum-verified — August 27, 2026:**

`SD Card / 00 FG Hardware Tests / Clip Reference / 080 Black Phase Vinyl Breaks Clean.wav`

## 7A. Newly deployed software breadth — August 28, 2026

These are software-accepted and checksum-verified on the card. Hardware
listening remains open; none is promoted to a favorite merely because it loads.

### Cross-library Drum wave

Common MPC path:

`SD Card / 00 FG Hardware Tests / Cross Library Kit Wave 01`

- [ ] `01 FG Dusty Cross-Library 01 / FG Dusty Cross-Library 01.xpm`
- [ ] `02 FG Tight Machine 01 / FG Tight Machine 01.xpm`
- [ ] `03 FG Ambient Percussion 01 / FG Ambient Percussion 01.xpm`
- [ ] `04 FG SP Punch 01 / FG SP Punch 01.xpm`
- [ ] `05 FG Experimental Texture 01 / FG Experimental Texture 01.xpm`

For each program, confirm all 16 pads sound, the semantic colors are useful,
the closed/open hats behave sensibly, and save/reload preserves the program.
Then record whether it is a main candidate, expressive alternate, or redundant.

### Portable workflow fixture

Drum Program:

`SD Card / 00 FG Hardware Tests / Portable Workflow Demo 01 / 01 Cross Kit / FG Portable Cross Kit.xpm`

MIDI and five arrangement variants are beside it under `02 Creative MIDI` and
`03 Arrangements`. The synthetic Drum Program is a workflow/reference fixture,
not a production-sound candidate.

- [ ] Load the Cross Kit and trigger all 16 pads.
- [ ] Confirm A07/A08 behave as a closed/open-hat choke pair.
- [ ] Save/reload and confirm colors and audio references persist.
- [ ] Import `02 Creative MIDI / portable-demo.mid` using the same qualified
  semantic-MIDI procedure already accepted on the Key 37.

### Creative MIDI backlog

Common MPC path:

`SD Card / 00 FG Hardware Tests / Creative MIDI 2026-08-28`

Start with these bounded representatives instead of testing every seed:

- [ ] `01 Generators / workstation / dusty-scratchpad-seed37.mid`
- [ ] `01 Generators / workstation / ambient-scratchpad-seed37.mid`
- [ ] `01 Generators / workstation / house-scratchpad-seed37.mid`
- [ ] `02 Arrangements / dusty-scratchpad-seed37 / main-b.mid`
- [ ] `02 Arrangements / dusty-scratchpad-seed37 / breakdown.mid`
- [ ] One alternative from `03 Seed Batches / dusty-seeds-40-45`.

Judge useful musical starting point, track naming/routing clarity, register,
and whether the import produces a new sequence. JSON and Markdown files are
reproduction evidence for the computer and do not need to be opened on MPC.

## 7B. Deferred: Wurli expressive Keygroup candidates

Prepared and deployed on August 27, 2026. The first write attempt stopped safely
on an SD `fsync` I/O error without publishing a partial destination. After
exFAT repair and read-write remount, deployment resumed from the verified hidden
staging area and completed transactionally.

Local package:
`/home/steve-farrelly/Projects/mpc-keygroup-builder/work/hardware-candidates/wurli-expressive-01`

Full MPC location:
`SD Card / 00 FG Scratchpad / 08 Expressive Candidates / Wurli Expressive 01`

Software preservation passes for all six candidates. Each contains 74
instrument/layer records and 73 checksum-identical ProgramData WAVs. Semantic
simulation covers all 128 notes with no dead or stacked cells and no new
issues. The two outer-range warnings are inherited unchanged from the accepted
Wurli source.

Deployment proof: 446 files, 428,423,434 bytes, no remaining staging directory,
and package SHA-256
`082b51106a1b575a2e82c5b746d70d77aadd9a445da2d0e4ad175d15be74a8f2`.

- [ ] Load `Wurli Clean.xpm` as the level-matched source reference.
- [ ] Compare `Wurli Warm.xpm`: darkness, resonance, attack, and release.
- [ ] Compare `Wurli Pad.xpm`: chord onset, held texture, release tail, and
  voice buildup.
- [ ] Compare `Wurli Pluck.xpm`: transient clarity, decay, useful note length,
  and repeated-note behavior.
- [ ] Compare `Wurli Bass.xpm`: confirm the saved octave change, playable
  register, and whether it adds value beyond Pluck Bass/Sub Smooth.
- [ ] Compare `Wurli Lo-Fi.xpm`: confirm the darker sound remains useful rather
  than merely muffled.
- [ ] On Warm, Pad, and Lo-Fi, move Attack and Cutoff Q-Links and check their
  initial position, pickup, range, and absence of jumps.
- [ ] Save/reload the strongest three and confirm program identity, audio,
  envelopes, filter, transpose where applicable, and Q-Links persist.
- [ ] Record pass/warn/fail and concise listening notes; promote only genuinely
  distinct, reusable profiles.

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

The September 3 capture confirms six Components Custom Modes and 81 MIDI Learn
assignments saved in the newer `SD Card / Projects / Boot.xpj` startup
template. See `inventory/launch-control-capture-2026-09-03.md` for the exact
channel/control inventory and read-only audit results.

The offline `site/plugin-mapping-companion.html` now provides the recommended
control-by-control interface for the plugin portion of this test. Results stay
in browser-local storage until exported as fingerprinted JSON or flat CSV.

- [ ] Check/update Launch Control XL 3 firmware with Novation Components.
- [x] Confirm standalone USB connection to the Key 37.
- [x] Save six named Components Custom Modes and capture their control messages.
- [ ] Confirm faders 4–7 are intentionally unlearned in the Boot template.
- [ ] Verify every intended control's musical result; capture parsing alone is
  not a listening or usability pass.
- [ ] Map faders 1–8 to track volume 1–8.
- [ ] Map top encoders to tone/brightness.
- [ ] Map middle encoders to delay/movement.
- [ ] Map bottom encoders to reverb/space.
- [ ] Map upper buttons to track mute.
- [ ] Try lower buttons as record arm; keep only if safe and useful.
- [ ] Check for disruptive value jumps when first touching each control.
- [x] Save the controller Custom Modes and MPC project.
- [ ] Power-cycle both devices and confirm persistence.
- [ ] Clone the Scratchpad project and confirm Universal Mix meanings persist.
- [ ] Perform a ten-minute jam with minimal touchscreen navigation.
- [ ] Run the nine one-control plugin probes in the companion before learning
  any complete page: Iona Cutoff, Flavor Global Depth, Trigger FX Half Speed,
  Multitap Delay, Vintage Filter Cutoff, Chorus Rate, Expander Threshold,
  Color Compressor Amount, and Analog Wear Tape Wow.
- [ ] Export the companion JSON after the probe pass so results can be matched
  to this exact profile revision.

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
- [x] Layered concept accepted; `FG Vinyl Layered Main 02` is retained as the
  expressive alternate while Vinyl SP remains main. Pad/boundary/reload and
  clearer choke tests remain technical follow-up only.
- [x] All 32 Ableton Wave 01 programs have results: five Keygroup range warnings,
  25 Drum passes, and two accepted source-choke Drum warnings.
- [ ] Revised Scratchpad Master saves/reloads with a recorded lead phrase.
- [x] Cold-start timing explicitly deferred; no failure is implied.
- [ ] Minimal Clip reference pair deferred; MPC Pro Pack is not owned.
- [x] Layout package deployed and tested; Right is selected and save/reload
  color persistence passes.
- [x] Semantic MIDI source/Classic pair tested on hardware; qualified pass
  because the varied one-shots make exact audible comparison difficult.
- [x] Plugin persistence accepted without a dedicated audit project; Fabric
  and Jura are confirmed internal, while Mini D and Studio Strings are deferred
  purchases.
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
