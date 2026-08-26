# FG Vinyl Shots 01

Track 2 needs a deliberately different vocabulary from the main drum kit.
`FG Vinyl Shots 01` is a self-contained 32-pad Drum Program generated from the
owned Vinyl SP From Mars one-shot library:

- Bank A: bongos, congas, cowbell, cabasa, maraca, clave, rim, percussion,
  rides, and crash.
- Bank B: chord/stab, vocal, glitch, chime, texture, and transition FX.
- Banks C–H: empty by design.

The source manifest is `inventory/fg-vinyl-shots.toml`. Build it with:

```bash
uv run mpc-drum-build inventory/fg-vinyl-shots.toml \
  --template "/path/to/a/128-pad-legacy-drum-template.xpm" \
  --source-root "/path/to/Vinyl SP From Mars" \
  --output "work/generated-drum-programs/FG Vinyl Shots 01"
```

The builder validates all source WAVs, writes inclusive sample endpoints,
forces one-shot/monophonic playback, clears unused pads and layers, applies the
semantic color palette, and copies only referenced WAVs beside the XPM. It
refuses to write into a non-empty output directory.

Current SD test deployment:

`Programs/Drum Programs/FG Scratchpad Candidates/FG Vinyl Shots 01/FG Vinyl Shots 01.xpm`

The generated folder contains 32 referenced WAVs. Local simulation and the
post-copy SD-card simulation both pass with zero missing samples, dead trigger
cells, or stacked trigger cells. Hardware listening remains required.

## Expanded four-bank variant

`inventory/fg-vinyl-shots-expanded.toml` inherits Banks A and B without
duplicating their definitions, then adds:

- Bank C: 16 additional bongos, cabasa, cowbells, shakers, clave, congas, and
  electronic percussion.
- Bank D: 16 bass/guitar fragments, transitions, vocal/reverse hits, laser/tom
  accents, a metallic cymbal, noise clap, and tape rim.

The expanded program deliberately leaves Banks E–H open for future layout
experiments or user customization. It is deployed alongside—not over—the
32-pad version at:

`Programs/Drum Programs/FG Scratchpad Candidates/FG Vinyl Shots 02 Expanded/FG Vinyl Shots 02 Expanded.xpm`

The post-copy SD simulation passes with 64 playable pads, zero missing samples,
dead trigger cells, stacked layers, or Drum Program audit warnings. Hardware
comparison must still establish which program size is faster to navigate.

## Six-bank variant

`inventory/fg-vinyl-shots-six-bank.toml` inherits Banks A–D unchanged and adds:

- Bank E: claps, snaps, rims, tape/crunch textures, reverse-style movement,
  laser snares, and acoustic flutter.
- Bank F: tom families, metallic cymbals, and resonant electronic percussion.

Banks G and H remain empty for user customization, alternate layouts, or a
future source pack. Version 03 is an additive hardware comparison rather than a
replacement for the smaller programs. It is deployed on the SD at:

`Programs/Drum Programs/FG Scratchpad Candidates/FG Vinyl Shots 03 Six Bank/FG Vinyl Shots 03 Six Bank.xpm`

The six-bank program is assigned to Track 2 `Shots` in the version-controlled
Scratchpad rig profile. The saved MPC XPJ still needs the program loaded on
Track 2 and saved from the Key 37; the project file is not rewritten off-device.

The local and SD XPM SHA-256 values both equal
`08d3599b5e1ad597e2275197d3991959d0419cc52aec37d1ed65718a50496e6a`.
Post-copy semantic simulation finds 96 playable pads and zero missing, dead, or
stacked triggers; the Drum audit reports no issues. Banks A–D remain
semantically identical to version 02.

## Hardware acceptance

- [ ] Load the program, then leave the Browser so assigned pad colors appear.
- [ ] Bank A pads A01–A13 are percussion/rim sounds; A14–A16 are cymbals.
- [ ] Bank B pads B01–B16 are FX/stabs/vocal fragments.
- [ ] Confirm every populated pad triggers exactly one sound.
- [ ] Test Bank C: additional percussion.
- [ ] Test Bank D: character and transition hits.
- [ ] Test Bank E: claps, snaps, rims, and textured snares.
- [ ] Test Bank F: toms, metallic cymbals, and resonant percussion.
- [ ] Confirm Banks G–H are silent and dark.
- [ ] Confirm teal percussion, white rim, orange cymbals, and purple FX are
  easy to distinguish.
- [ ] Record a two-bar fill using both banks, save/reload, and replay it.
- [ ] Decide `favorite=yes`, `favorite=no`, or revise the manifest by pad.
