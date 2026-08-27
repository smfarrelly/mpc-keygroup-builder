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

The six-bank program was the prior Track 2 `Shots` selection and remains a
comparison candidate. The saved MPC XPJ still needs the selected version loaded
on Track 2 and saved from the Key 37; the project file is not rewritten
off-device.

The local and SD XPM SHA-256 values both equal
`08d3599b5e1ad597e2275197d3991959d0419cc52aec37d1ed65718a50496e6a`.
Post-copy semantic simulation finds 96 playable pads and zero missing, dead, or
stacked triggers; the Drum audit reports no issues. Banks A–D remain
semantically identical to version 02.

## Selected eight-bank variant

`inventory/fg-vinyl-shots-eight-bank.toml` inherits Banks A–F unchanged and
fills the final two banks:

- Bank G: eight contrasting kicks followed by eight snares.
- Bank H: eight closed hats followed by eight open hats, using matched 707,
  808, 909, acoustic, CR78, LM1, Machinedrum, and tape families.

Version 04 is the selected Track 2 program. It remains additive: versions
01–03 are preserved for navigation and hardware comparisons. Its intended SD
path is:

`Programs/Drum Programs/FG Scratchpad Candidates/FG Vinyl Shots 04 Eight Bank/FG Vinyl Shots 04 Eight Bank.xpm`

The repository stores only the manifest. The generated XPM and its 128 licensed
WAVs remain ignored at:

`work/generated-drum-programs/FG Vinyl Shots 04 Eight Bank/`

Local semantic simulation passes with zero missing samples, dead trigger cells,
or stacked trigger cells. The Drum audit passes with eight matched closed/open
hat choke groups. The XPM SHA-256 is
`0e3587cb52bf4f6acdfae509b066c0a6521b6ef0c4bdbef5038939f66d53bcd7`.
SD deployment remains additive and waits until the card is mounted and idle.

## Hardware acceptance

- [ ] Load the program, then leave the Browser so assigned pad colors appear.
- [ ] Bank A pads A01–A13 are percussion/rim sounds; A14–A16 are cymbals.
- [ ] Bank B pads B01–B16 are FX/stabs/vocal fragments.
- [ ] Confirm every populated pad triggers exactly one sound.
- [ ] Test Bank C: additional percussion.
- [ ] Test Bank D: character and transition hits.
- [ ] Test Bank E: claps, snaps, rims, and textured snares.
- [ ] Test Bank F: toms, metallic cymbals, and resonant percussion.
- [ ] Test Bank G: kicks on G01–G08 and snares on G09–G16.
- [ ] Test Bank H: closed hats on H01–H08 and open hats on H09–H16.
- [ ] Confirm teal percussion, white rim, orange cymbals, and purple FX are
  easy to distinguish.
- [ ] Record a two-bar fill using both banks, save/reload, and replay it.
- [ ] Decide `favorite=yes`, `favorite=no`, or revise the manifest by pad.
