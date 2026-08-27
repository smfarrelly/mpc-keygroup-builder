# FG expanded Drum banks 01

Four self-contained Drum Programs broaden already accepted source material
without introducing another format or workflow. The first three preserve the
pad order of hardware-passed Ableton conversions and collect eight complete
kits behind Bank buttons. The fourth extends the accepted velocity-layered
concept from one bank to four.

## SD locations

All paths start at `Browser > Places > SD Card`:

- `01 FG Favorites / 04 Drum Alternates / 06 FG Classic Machines Banks 01 / FG Classic Machines Banks 01.xpm`
- `01 FG Favorites / 04 Drum Alternates / 07 FG Character Machines Banks 01 / FG Character Machines Banks 01.xpm`
- `01 FG Favorites / 04 Drum Alternates / 08 FG Breaks Texture Banks 01 / FG Breaks Texture Banks 01.xpm`
- `01 FG Favorites / 04 Drum Alternates / 09 FG Vinyl Layered Banks 03 / FG Vinyl Layered Banks 03.xpm`

The same folder contains `00 DRUM ALTERNATES INDEX.txt`, a shallow on-device
navigation and audition guide.

## Bank maps

`FG Classic Machines Banks 01`:

- A: 505 Clean
- B: 606 Clean
- C: 626 Clean
- D: 707 Mod Combo
- E: 808 Clean
- F: 909 Clean
- G: CR-78 Kit 1
- H: DMX Clean

`FG Character Machines Banks 01`:

- A: 505 SP-1200 Glitch
- B: 606 Blender
- C: 626 Color
- D: 707 SP-1200 Dark
- E: 808 Distorted
- F: 909 Dirt
- G: DMX S612 Boogie
- H: Modern Oddities Hardware Glitch

`FG Breaks Texture Banks 01`:

- A: Vinyl Drums Big Break
- B: Vinyl Drums Hand Break
- C: Drumtrax Kit 1
- D: Drumulator Clean
- E: LM-1 Computer Love
- F: Found Sounds Body Kit, source Bank A
- G: S950 Club 8
- H: S950 Hard Glitch

`FG Vinyl Layered Banks 03`:

- A: the accepted `FG Vinyl Layered Main 02`, unchanged
- B: classic and character drum machines
- C: acoustic, tape, and worn-drum character
- D: club, Machinedrum, Flux, and sound-design material
- E-H: intentionally empty

Every populated Layered Banks pad has four regions: 0-31, 32-63, 64-95, and
96-127. Hats use isolated groups 1-7: A09/A10, A11/A12, B07/B08, B09/B10,
C07/C08, C09/C10, and D07/D08.

## Reproducible inputs

The three bank recipes are:

- `inventory/fg-classic-machines-banks-01.toml`
- `inventory/fg-character-machines-banks-01.toml`
- `inventory/fg-breaks-texture-banks-01.toml`

Their safe relative XPM paths resolve directly below the accepted
`work/hardware-candidates/sfm-ableton-wave-01/02 Drum Programs` root. The
composer resolves each program's samples locally, stages only selected audio
internally, rebases source Bank A into target Banks A-H, and isolates each
nonzero source choke group to its target-bank group. No hand-built flat source
folder is required.

For example:

```bash
uv run mpc-drum-compose inventory/fg-classic-machines-banks-01.toml \
  --source-root "work/hardware-candidates/sfm-ableton-wave-01/02 Drum Programs" \
  --manifest-output work/fg-classic-machines-banks-01.toml \
  --template "/path/to/four-layer-drum-template.xpm" \
  --package-output "work/generated-drum-programs/FG Classic Machines Banks 01"
```

The four-bank velocity recipe is
`inventory/fg-vinyl-layered-banks-03.toml`. It inherits Bank A from
`fg-vinyl-layered-main-02.toml` and contains the complete explicit map for the
three new banks. Build it with any four-layer Drum template and the original
Vinyl SP WAV folder:

```bash
uv run mpc-drum-build inventory/fg-vinyl-layered-banks-03.toml \
  --template "/path/to/four-layer-drum-template.xpm" \
  --source-root "/path/to/Vinyl SP From Mars" \
  --output "work/generated-drum-programs/FG Vinyl Layered Banks 03"
```

Generated XPMs and licensed WAVs remain ignored.

## Computer acceptance — August 27, 2026

All four packages pass Program Model import and semantic simulation with zero
missing samples, dead trigger cells, or stacked trigger cells.

- Classic Machines: 128 populated pads, 129 files, 12.5 MB package, Drum audit
  `pass`; XPM SHA-256
  `73d047a62db9794ab66936ab1773dfaa34d09f5245408fe889f17cce8eca4e19`.
- Character Machines: 128 populated pads, 129 files, 8.2 MB package, Drum audit
  `warn` only because accepted source pad H10 (`10-CH-MO.wav`) has no mute
  group; XPM SHA-256
  `25a78d782f1099956b74b5e010d2e595f8c9f39cd1d54ea95297ed0f33fcbd7d`.
- Breaks Texture: 128 populated pads, 129 files, 14.8 MB package, Drum audit
  `warn` only because accepted source pad H16 (`OH Lindrum Hi S950.wav`) has no
  mute group; XPM SHA-256
  `c2435a94abf91f883f78689957610212b45b5fd85332a1d19887312460610bd6`.
- Vinyl Layered Banks: 64 populated pads, 212 velocity-layer WAVs plus one XPM,
  13.8 MB package, Drum audit `pass`; XPM SHA-256
  `8893d1310c797f03def9bca15549429b32a0e1e3dea2f1598f43721fea9166d5`.

The card passed a 32 MiB sustained write/read/hash/delete probe before the
batch. Transactional deployment verified 600 files and these package digests:

- Classic: `f0503e476b577d630bc29171396f7b769230df2583e2957ba459d877c4f05d1d`
- Character: `4b21caf11afe41faf58ee5cee3579998908edf6768e89e511a9bddb39b2d6999`
- Breaks Texture: `9b4333ae0ea8c115832180ebd210905fce94f85b8dfe874d8a235f3cb2a71ac6`
- Layered Banks: `a35cb49c3d3f6094aae52ea346747b93eb680f6751646f270618b5309417dbb9`

An independently checksum-verified external mirror is at:

`/media/steve-farrelly/Storage/MPC Transfer/FG Expanded Drum Programs 2026-08-27`

## Key 37 acceptance

- [ ] Load each program and leave Browser; confirm semantic colors appear.
- [ ] For Classic, Character, and Breaks Texture, play all pads in Banks A-H
  and confirm each bank matches its label.
- [ ] Record one fixed pattern on at least two contrasting banks in each
  eight-bank program.
- [ ] Treat Character H and Breaks Texture H as known source-choke auditions,
  not new conversion failures.
- [ ] For Layered Banks, play every pad in Banks A-D at soft, medium-soft,
  medium-hard, and hard velocity.
- [ ] Check velocity boundaries 31/32, 63/64, and 95/96 on the two kicks, two
  snares, hats, cymbal, and FX pad in each layered bank.
- [ ] Test all seven closed/open-hat pairs; cross-bank and cross-group hits must
  not choke one another.
- [ ] Save/reload a project with the preferred new program and confirm samples,
  colors, velocity regions, and mute groups persist.
