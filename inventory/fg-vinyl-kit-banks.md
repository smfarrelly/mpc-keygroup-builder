# FG Vinyl Kit Banks 01

`FG Vinyl Kit Banks 01` turns eight existing 16-pad Vinyl SP kits into one
self-contained, color-coded, 128-pad Drum Program. It complements `FG Vinyl
Shots 04`: Shots is a broad sound catalog, while Kit Banks makes each physical
bank a playable kit with its source-native performance mapping.

## Bank selection

- Bank A: 808 Standard — `Vinyl SP From Mars 01`, source Bank A.
- Bank B: 909 Standard — `Vinyl SP From Mars 01`, source Bank C.
- Bank C: Machinedrum — `Vinyl SP From Mars 03`, source Bank B.
- Bank D: CR78 — `Vinyl SP From Mars 03`, source Bank D.
- Bank E: LM1 — `Vinyl SP From Mars 03`, source Bank C.
- Bank F: Acoustic Vinyl — `Vinyl SP From Mars 02`, source Bank B.
- Bank G: Old Tape — `Vinyl SP From Mars 04`, source Bank C.
- Bank H: Acoustic Hybrid — `Vinyl SP From Mars 02`, source Bank A.

The source programs already place core kicks and snares at the start of each
bank, hats in the middle, and toms, percussion, or cymbals toward the end.
Machine families without every conventional drum voice retain their supplied
percussion substitutions rather than receiving unrelated samples.

## Reproducible composition

The portable recipe is `inventory/fg-vinyl-kit-banks.toml`. Resolve its bank
references and build the package with:

```bash
uv run mpc-drum-compose inventory/fg-vinyl-kit-banks.toml \
  --source-root "/path/to/Vinyl SP From Mars/Presets/MPC/MPC Live & X/Vinyl SP From Mars" \
  --manifest-output work/fg-vinyl-kit-banks-resolved.toml \
  --template "/path/to/Vinyl SP From Mars 01.xpm" \
  --package-output "work/generated-drum-programs/FG Vinyl Kit Banks 01"
```

`mpc-drum-compose` requires every selected source bank to have all 16 pads. It
resolves extensionless MPC sample references against actual WAV filenames,
refuses ambiguous names or flattened-file collisions, and refuses duplicate
target banks. A source bank may have zero or one mute group. Nonzero groups are
rebased to groups 1–8 by target bank, preventing hats in one kit from choking
hats in another kit.

The resolved 128-pad manifest and licensed hardware package remain ignored.
Only the portable bank recipe, reusable composer, tests, and documentation are
committed.

## Local validation — August 26, 2026

The generated package is:

`work/generated-drum-programs/FG Vinyl Kit Banks 01`

- One XML XPM plus 128 copied WAVs; 8.0 MB total.
- Semantic simulator: pass, 128 playable pads, no missing samples, dead trigger
  cells, or stacked trigger cells.
- Drum audit: pass, with semantic colors and eight isolated mute groups.
- Categories: 18 kicks, 14 snares, 15 closed hats, 13 open hats, 9 claps, 8
  rims, 14 toms, 9 cymbals, 27 percussion sounds, and one FX sound.
- XPM SHA-256:
  `6d6306af36b1c64d64820c4faed683021f8e650e7fcdff99d55fb92a6dcf2477`.

## Key 37 acceptance

- [x] Repair and confirm reliable SD write behavior before deployment.
- [x] Load the program and leave the Browser so assigned colors appear.
- [x] Confirm all 16 pads in every Bank A–H trigger once.
- [x] Confirm each bank sounds like its named kit family.
- [x] Confirm closed/open hats choke within each bank and not across unrelated
  kit banks during normal performance.
- [x] Record the same pattern separately with Banks A, B, C, and G; every bank
  worked and the musical result was reported as very impressive.
- [ ] Save, reload, and confirm colors, samples, and mute behavior persist.
- [ ] Decide whether source-native placement is sufficiently consistent or a
  second strictly normalized role-layout variant is warranted.

### Deployment status — August 27, 2026

The first deployment was interrupted when the USB card reader disconnected
during writeback. After reseating the connection, the card passed offline
repair plus a 64 MiB sustained write/read/hash/delete/sync test. The incomplete
folder was moved to the SD Trash and a clean package was deployed to
`01 FG Favorites/04 Drum Alternates/03 FG Vinyl Kit Banks 01`. All 129 files
match the laptop SHA-256 manifest, semantic simulation passes with zero dead or
stacked trigger cells, and the SD XPM passes Drum audit.

### Hardware result — August 27, 2026

The program loads and works as expected across all eight named kit banks, with
expected pad playback, family character, colors, and bank-local choke behavior:
`pass`, retained as a provisional Drum alternate. The same recorded pattern
worked on Banks A, B, C, and G and made a strong musical impression. Project
save/reload and the final normalized-layout decision remain open.
