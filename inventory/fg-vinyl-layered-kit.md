# FG Vinyl Layered Kit 01

`FG Vinyl Layered Kit 01` is a focused 16-pad performance Drum Program with
four explicit velocity regions on every pad:

- velocity 0–31: softest, lightest, or darkest timbre;
- velocity 32–63: light/medium timbre;
- velocity 64–95: medium/hard timbre;
- velocity 96–127: hardest, brightest, or most characterful timbre.

These are curated timbre morphs assembled from related Vinyl SP hits, not four
round-robin recordings of the same physical drum. Hardware testing must judge
whether each transition feels expressive or merely abrupt.

## Bank A layout

- A01–A02: layered kicks.
- A03–A04: layered electronic and acoustic snares.
- A05–A06: layered electronic and textured claps.
- A07–A08: layered clean and character rims.
- A09–A10: first closed/open hat pair, mute group 1.
- A11–A12: second closed/open hat pair, mute group 2.
- A13–A14: layered low/dark and high/bright tom voices.
- A15: layered cymbal/ride/crash voice.
- A16: layered shaker, maraca, cowbell, and metallic percussion voice.

## Manifest syntax

The portable recipe is `inventory/fg-vinyl-layered-kit.toml`. A pad may use the
existing `sample = "Hit.wav"` shorthand or one through four explicit
`[[pads.layers]]` tables:

```toml
[[pads]]
pad = 1

[[pads.layers]]
sample = "BD Soft.wav"
velocity_start = 0
velocity_end = 63

[[pads.layers]]
sample = "BD Hard.wav"
velocity_start = 64
velocity_end = 127
```

Layered pads cannot also set the single-sample shorthand. Their velocity ranges
must cover 0–127 exactly, without gaps or overlaps, and a known-good template
must expose at least as many layers as the manifest requests. Unused template
layers are cleared and marked inactive.

## Local validation — August 27, 2026

The ignored hardware package is:

`work/generated-drum-programs/FG Vinyl Layered Kit 01`

- One XML XPM plus 64 copied WAVs; 3.9 MB total.
- Program Model: 16 zones and 64 explicit velocity layers.
- Semantic simulator: pass, zero missing samples, dead velocity cells, or
  stacked velocity cells.
- Drum audit: pass, 16 populated pads and two valid hat mute groups.
- XPM SHA-256:
  `1dec7b9c499b2ad94d88d9594f29dffd56a853ec0c50521d8768576ab61f9847`.

## Key 37 acceptance

- [x] Repair and confirm reliable SD write behavior before deployment.
- [ ] Load the program and confirm only Bank A is populated.
- [ ] Strike every pad softly, medium-soft, medium-hard, and hard.
- [ ] Confirm every velocity produces exactly one sound with no silent band.
- [ ] Listen specifically at velocities 31/32, 63/64, and 95/96 for disruptive
  jumps in pitch, loudness, or character.
- [ ] Confirm A09/A10 and A11/A12 choke within their own hat pairs. The first
  hardware audition was inconclusive. Turn Full Level off, strike A12 at
  velocity 32–63 to select its 1.60-second `OH LM1 Standard` layer, then strike
  A11; the A12 tail should stop. A12 followed by A09 must not choke.
- [ ] Record a two-bar groove without Full Level, then inspect whether natural
  playing reaches all four regions.
- [ ] Repeat with Full Level and confirm the hardest layer is predictable.
- [ ] Save/reload and repeat A01, A03, A09, A10, and A15.
- [x] Keep and develop the velocity-layered-pad concept; the initial hardware
  audition found it excellent. Individual pad and boundary verdicts remain
  open.

### Deployment status — August 27, 2026

The first copy was interrupted by the same USB-reader disconnect as Kit Banks.
After the repaired card passed a sustained write test, the incomplete folder
was moved to the SD Trash and a clean package was deployed to
`01 FG Favorites/04 Drum Alternates/04 FG Vinyl Layered Kit 01`. All 65 files
match the laptop SHA-256 manifest, semantic simulation passes with zero dead or
stacked trigger cells, and the SD XPM passes Drum audit. Hardware velocity and
feel testing remain open.

### Initial hardware result — August 27, 2026

The velocity-layered-pad concept is excellent and is promoted to a provisional
main-drum candidate. Hat choking was difficult to hear and may not be working,
despite the XPM carrying Mute Group 1 on A09/A10 and Mute Group 2 on A11/A12
using the same serialized field as the accepted Shots program. The hardest
open-hat layers are short, so the corrected acceptance test uses A12's
1.60-second velocity-32–63 LM1 layer. Retain a technical `warn` until that
controlled test passes; full pad, boundary, groove, and reload testing also
remain open.

## Follow-up main-drum candidate

Build `FG Vinyl Layered Main 02` as a focused follow-up rather than replacing
the current Vinyl SP main-drums favorite prematurely:

- Keep a single immediate 16-pad Bank A performance layout.
- Retain four complete velocity regions on every pad: 0–31, 32–63, 64–95, and
  96–127.
- Curate each pad's four timbres as a coherent soft-to-hard voice progression,
  with better perceived-level matching at every boundary.
- Prefer related drum families where that makes the velocity change feel like
  articulation rather than an unrelated sample swap; preserve hybrid choices
  where the morph itself is musically compelling.
- Choose longer open-hat layers for an unmistakable choke test and compare
  Mute Group behavior with explicit directional Mute Targets if necessary.
- Produce pad/layer maps, boundary-level analysis, semantic simulation, Drum
  audit, checksums, and a self-contained ignored hardware package.
- Compare the refined kit directly with `Vinyl SP From Mars 01 FG COLORS` using
  the same groove, fixed master level, natural velocity, Full Level, and
  save/reload. Promote it to the Scratchpad main-drum slot only if it wins that
  musical comparison.
