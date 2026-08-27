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

- [ ] Chromatic Analog Tom — roots MIDI 27–42; status: untested; favorite: ; notes:
- [ ] Chromatic Chimes — roots MIDI 35–50; status: untested; favorite: ; notes:
- [ ] Chromatic Cowbell — roots MIDI 29–44; status: untested; favorite: ; notes:
- [ ] Chromatic Tom — roots MIDI 25–40; status: untested; favorite: ; notes:
- [ ] Chromatic Tone — roots MIDI 33–48; status: untested; favorite: ; notes:

## Drum bracket A — vinyl and SP-1200

- [ ] Vinyl Drums / Big Break Kit — 16 pads; status: untested; favorite: ; notes:
- [ ] Vinyl Drums / Hand Break Kit — 16 pads; status: untested; favorite: ; notes:
- [ ] SP-1200 / Factory Kit 1 — 12 pads; status: untested; favorite: ; notes:
- [ ] SP-1200 / Factory Kit 2 — 12 pads; status: untested; favorite: ; notes:

## Drum bracket B — classic machines

- [ ] 505 / Clean Kit — status: untested; favorite: ; notes:
- [ ] 505 / SP-1200 Glitch Kit — status: untested; favorite: ; notes:
- [ ] 606 / Clean Kit — status: untested; favorite: ; notes:
- [ ] 606 / Blender Kit — status: untested; favorite: ; notes:
- [ ] 626 / Clean Kit 1 — status: untested; favorite: ; notes:
- [ ] 626 / Color Kit 1 — status: untested; favorite: ; notes:
- [ ] 707 / Mod Combo Kit — status: untested; favorite: ; notes:
- [ ] 707 / SP-1200 Dark Kit — status: untested; favorite: ; notes:
- [ ] 808 / Clean Kit 01 — status: untested; favorite: ; notes:
- [ ] 808 / Distorted Kit — status: untested; favorite: ; notes:
- [ ] 909 / Clean Kit — status: untested; favorite: ; notes:
- [ ] 909 / Dirt Kit — status: untested; favorite: ; notes:
- [ ] CR-78 / Kit 1 — status: untested; favorite: ; notes:
- [ ] CR-78 / Kit 2 — status: untested; favorite: ; notes:
- [ ] DMX / Clean Kit 01 — status: untested; favorite: ; notes:
- [ ] DMX / S612 Boogie Kit — status: untested; favorite: ; notes:
- [ ] Drumtrax / Kit 1 — status: untested; favorite: ; notes:
- [ ] Drumulator / Clean Kit — status: untested; favorite: ; notes:
- [ ] LM-1 / Computer Love Kit — status: untested; favorite: ; notes:

## Drum bracket C — character and texture

- [ ] S950 Snacks / Club 8 Kit — status: untested; favorite: ; notes:
- [ ] S950 Snacks / Hard Glitch Kit — source-choke warning; status: untested; favorite: ; notes:
- [ ] Modern Oddities / Hardware Glitch Kit — source-choke warning; status: untested; favorite: ; notes:
- [ ] Found Sounds / Body Kit — 32 pads across Banks A–B; status: untested; favorite: ; notes:

## Acceptance decision

- Keep only musically distinct winners in the permanent library.
- Compare clean/color pairs before retaining both.
- Promote one or two favorite classic-machine kits into an A–H bank collection.
- Preserve unusual character kits as standalone programs when their pad layout
  is part of their identity.
- Revisit Ableton gain/effect translation only where the raw MPC version loses
  an important part of the sound.
