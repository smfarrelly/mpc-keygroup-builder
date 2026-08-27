# Samples From Mars Ableton Wave 01 hardware plan

**Status:** SD deployment verified; MPC Key 37 listening pending

**Candidate package:** `work/hardware-candidates/sfm-ableton-wave-01`

**Verified SD destination:** `00 FG Hardware Tests/SFM Ableton Wave 01`

This wave contains 32 MPC programs derived from owned Samples From Mars audio
and readable Ableton source intent: five Keygroups and 27 Drum Programs. The
generated XPMs and 520 WAV copies remain ignored local artifacts.

## Computer validation

- [x] Five SP-1200 Keygroups built from 80 unique WAVs and explicit Ableton
  root notes.
- [x] Twenty-seven Drum Programs built from 440 selected WAVs, Ableton rack
  branch order, and Ableton choke groups.
- [x] All 32 programs have zero dead or stacked trigger cells.
- [x] All 27 Drum Programs pass semantic simulation.
- [x] Twenty-five Drum Programs pass the independent Drum audit.
- [x] Hardware Glitch Kit is a warning because its lone closed hat has no
  Ableton choke group; no open-hat partner exists in that kit.
- [x] S950 Hard Glitch Kit is a warning because pad 16 is an open hat outside
  the source rack's main hat choke group.
- [x] The five Keygroups are warnings only for deliberate extrapolation beyond
  their 16 adjacent source roots; each still has all 128 MIDI notes populated.
- [x] All 552 package files have a verified local SHA-256 manifest.
- [x] Audio was copied bit-for-bit and not normalized. The level scan retains
  43 source clipping flags and 166 relative-level flags for listening review.

Ableton sample membership, pad order, root notes, and choke groups are
preserved. Ableton Rack macros, effects, and non-default sampler gain are not
serialized yet. Treat this as a playable raw-sample translation bracket, not a
claim of exact Ableton effect matching.

## Verified SD deployment — August 27, 2026

The complete package was deployed additively to:

`00 FG Hardware Tests/SFM Ableton Wave 01`

The deployment contains exactly 552 files and 68,579,392 bytes. A second,
independent hash pass compared every file on the SD card with the local package
and reported a byte-for-byte match. The card was synced and cleanly unmounted
before returning it to the MPC.

For a future replacement card, first run a dry plan:

First run a dry plan:

```bash
uv run mpc-package-deploy \
  work/hardware-candidates/sfm-ableton-wave-01 \
  "/media/steve-farrelly/3561-6538/00 FG Hardware Tests/SFM Ableton Wave 01" \
  --report work/sfm-ableton-wave-01-deploy-plan.json
```

After confirming the destination is absent and the card is writable, repeat
with `--apply --probe-mib 32`. Do not merge these programs into the main
Samples From Mars browser tree until hardware acceptance is recorded.

## Listening protocol

For every program:

1. Load it directly from the shallow hardware-test folder.
2. Trigger every populated key or pad at low, medium, and high velocity.
3. Check relative level, tails, unintended silence, clicks, and wrong samples.
4. For Drum Programs, verify semantic colors after leaving the file browser.
5. Check every closed/open-hat relationship and note any unexpected choking.
6. Save and reload one promising program from each family.
7. Record `pass`, `warn`, or `fail`, favorite status, and a concise musical
   note below.

## Keygroup bracket

The first and last samples intentionally extend beyond the 16 recorded roots.
Judge the central source range first, then decide whether the extrapolated
outer octaves are useful or should become silent limits.

- [x] Chromatic Analog Tom — roots MIDI 27–42; status: warn; favorite: pending;
  notes: loads, but the Key 37 must be transposed down several octaves before
  notes trigger. The generated model reports all 128 notes populated, so the
  MPC is not honoring the outer extrapolated ranges as expected; rebuild or
  deliberately constrain/remap the useful range.
- [x] Chromatic Chimes — roots MIDI 35–50; status: warn; favorite: pending;
  notes: repeats Chromatic Analog Tom's hardware behavior and requires
  transposing down several octaves before notes trigger. Treat this as a
  systematic Keygroup outer-range serialization/remapping issue.
- [x] Chromatic Cowbell — roots MIDI 29–44; status: warn; favorite: pending;
  notes: repeats the same octave-down-only trigger behavior; remap required.
- [x] Chromatic Tom — roots MIDI 25–40; status: warn; favorite: pending; notes:
  repeats the same octave-down-only trigger behavior; remap required.
- [x] Chromatic Tone — roots MIDI 33–48; status: warn; favorite: pending;
  notes: repeats the same octave-down-only trigger behavior; remap required.

**Bracket verdict:** all five SP-1200 Keygroups load, but all require
transposing down several octaves before notes trigger. This contradicts the
generated model's full 0–127 coverage and confirms a systematic hardware range
serialization/remapping issue. Build a comparison set with the 16 source roots
explicitly shifted into the Key 37's normal register before promotion.

### Normal-register comparison deployed — August 27, 2026

The reusable Keygroup builder and batch manifest now accept a validated fixed
`root_shift`. Five `NR` comparison programs shift the same 80 source WAVs up
24 semitones without resampling or modifying the audio. Their recorded roots
now occupy MIDI 49–74 instead of 25–50.

Common SD root:

`SD Card / 00 FG Hardware Tests / SFM Keygroup Register Fix 01 / Chromatic Percussion`

- [ ] `Chromatic Analog Tom NR.xpm` — roots 51–66.
- [ ] `Chromatic Chimes NR.xpm` — roots 59–74.
- [ ] `Chromatic Cowbell NR.xpm` — roots 53–68.
- [ ] `Chromatic Tom NR.xpm` — roots 49–64.
- [ ] `Chromatic Tone NR.xpm` — roots 57–72.

All five packages pass Program Model validation and have zero dead or stacked
trigger cells. The simulator retains the known outer-extrapolation advisory;
hardware acceptance is specifically whether the untransposed sample voices now
play in the Key 37's default register. For each program, load it without using
octave transpose, test every source root and neighboring keys, then save/reload
the best one.

**NR1 hardware result:** all five are close and substantially improve the
original mapping, but the complete family should move one more octave to the
right. Retain NR1 as comparison evidence rather than the promotion target.

### Normal-register 02 built; SD deployment pending

`NR2` shifts the same unmodified audio up 36 semitones from the original source,
one octave higher than NR1. All five programs validate with 16 Keygroups, 16
samples, no model errors/warnings, and zero dead or stacked cells:

- Chromatic Analog Tom NR2 — roots 63–78.
- Chromatic Chimes NR2 — roots 71–86.
- Chromatic Cowbell NR2 — roots 65–80.
- Chromatic Tom NR2 — roots 61–76.
- Chromatic Tone NR2 — roots 69–84.

Planned SD root after the next card insertion:

`SD Card / 00 FG Hardware Tests / SFM Keygroup Register Fix 02 / Chromatic Percussion`

Test without octave transpose and compare only against NR1 if a boundary feels
too far right. NR2 is the intended promotion target.

## Drum bracket A — vinyl and SP-1200

- [x] Vinyl Drums / Big Break Kit — 16 pads; status: pass; favorite: pending;
  notes: all pads and expected program behavior pass on the Key 37.
- [x] Vinyl Drums / Hand Break Kit — 16 pads; status: pass; favorite: pending;
  notes: all pads and expected program behavior pass on the Key 37.
- [x] SP-1200 / Factory Kit 1 — 12 pads; status: pass; favorite: pending; notes:
  all 12 source pads pass; A13–A16 are intentionally empty.
- [x] SP-1200 / Factory Kit 2 — 12 pads; status: pass; favorite: pending; notes:
  all 12 source pads pass; A13–A16 are intentionally empty.

## Drum bracket B — classic machines

Most remaining Drum Programs were auditioned with no blocking behavior, and the
complete Drum wave was accepted as done. These ordinary kits are recorded as
`pass (batch accepted)` with favorite selection deferred:

- [x] 505 / Clean Kit
- [x] 505 / SP-1200 Glitch Kit
- [x] 606 / Clean Kit
- [x] 606 / Blender Kit
- [x] 626 / Clean Kit 1
- [x] 626 / Color Kit 1
- [x] 707 / Mod Combo Kit
- [x] 707 / SP-1200 Dark Kit
- [x] 808 / Clean Kit 01
- [x] 808 / Distorted Kit
- [x] 909 / Clean Kit
- [x] 909 / Dirt Kit
- [x] CR-78 / Kit 1
- [x] CR-78 / Kit 2
- [x] DMX / Clean Kit 01
- [x] DMX / S612 Boogie Kit
- [x] Drumtrax / Kit 1
- [x] Drumulator / Clean Kit
- [x] LM-1 / Computer Love Kit

## Drum bracket C — character and texture

- [x] S950 Snacks / Club 8 Kit — status: pass (batch accepted); favorite:
  pending; notes: no blocking behavior in the accepted Drum batch.
- [x] S950 Snacks / Hard Glitch Kit — status: warn (batch accepted); favorite:
  pending; notes: retains the source rack's open hat outside its main choke
  group.
- [x] Modern Oddities / Hardware Glitch Kit — status: warn (batch accepted);
  favorite: pending; notes: retains the source rack's lone closed-hat-labelled
  pad without an open partner or choke assignment.
- [x] Found Sounds / Body Kit — status: pass (batch accepted); favorite:
  pending; notes: accepted as a 32-pad Banks A–B program.

## Hardware wave verdict — August 27, 2026

All 32 programs have a hardware disposition. The five Keygroups are `warn`
pending normal-register remapping. Twenty-five Drum Programs pass, including
the four individually confirmed Vinyl/SP-1200 kits. Hardware Glitch and S950
Hard Glitch remain accepted `warn` for their source-defined choke anomalies.
Favorite curation remains editorial and is not required to close this batch.

## Acceptance decision

- Keep only musically distinct winners in the permanent library.
- Compare clean/color pairs before retaining both.
- Promote one or two favorite classic-machine kits into an A–H bank collection.
- Preserve unusual character kits as standalone programs when their pad layout
  is part of their identity.
- Revisit Ableton gain/effect translation only where the raw MPC version loses
  an important part of the sound.
