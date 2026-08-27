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
- [ ] Confirm A09/A10 and A11/A12 choke within their own hat pairs.
- [ ] Record a two-bar groove without Full Level, then inspect whether natural
  playing reaches all four regions.
- [ ] Repeat with Full Level and confirm the hardest layer is predictable.
- [ ] Save/reload and repeat A01, A03, A09, A10, and A15.
- [ ] Mark each pad pass, warn, or revise; keep the concept only if velocity
  variation makes the kit more playable.

### Deployment status — August 27, 2026

The first copy was interrupted by the same USB-reader disconnect as Kit Banks.
After the repaired card passed a sustained write test, the incomplete folder
was moved to the SD Trash and a clean package was deployed to
`01 FG Favorites/04 Drum Alternates/04 FG Vinyl Layered Kit 01`. All 65 files
match the laptop SHA-256 manifest, semantic simulation passes with zero dead or
stacked trigger cells, and the SD XPM passes Drum audit. Hardware velocity and
feel testing remain open.
