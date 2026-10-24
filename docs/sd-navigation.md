# Finding instruments on the MPC SD card

Updated October 23, 2026. Paths below start at the SD card in the MPC Browser.
They were checked on the mounted card, not accepted through new hardware tests.

## Start with a project

- Everyday composition: `Projects/FG Scratchpad/FG Vinyl Scratchpad v02 Master.xpj`
- MPC and Launch Control starting point: `Projects/Boot.xpj`
- Volca routing test: `Projects/Volca/Base.xpj`
- Focused Jura mapping test: `Projects/Jura/1-Jura.xpj`

Save variations under a new name. Do not overwrite these baselines. Old guides
disagree on Volca channels; inspect the loaded project's routing and verify on
hardware rather than relying on an old folder index.

## Load an individual Scratchpad instrument

- Main drums: `00 FG Scratchpad/01 Main Drums/Vinyl SP From Mars 01 FG COLORS.xpm`
- Shots: `00 FG Scratchpad/02 Vinyl Shots/FG Vinyl Shots 04 Eight Bank.xpm`
- Bass: `00 FG Scratchpad/03 Bass/Pluck Bass.xpm`
- Keys: `00 FG Scratchpad/04 Keys/Wurli.xpm`
- Lead: `00 FG Scratchpad/05 Lead/Dark FM.xpm`
- Pad: `00 FG Scratchpad/06 Pad/Glass Howl.xpm`
- Bass pad: `00 FG Scratchpad/07 Bass Pad/Sub Smooth.xpm`

## Browse the wider library

- Colored vendor drum programs: `Samples/Samples From Mars/<collection>/<original name> FG COLORS.xpm`
- Alternate favorites: `01 FG Favorites`
- Reference instruments: `Programs/Keygroups/SFM REFERENCE INSTRUMENTS`

The 88 colored vendor drum copies retain their original sample fields and live
beside their WAVs. Do not relocate them. Only the Cassette color-only pilot is
hardware-confirmed for this new batch. The two relocated XML-reference methods
failed to load samples; their files have been removed with local backups.

## Current test entry point

Use `00 FG Hardware Tests/00 ACTIVE TESTS.txt`. The historical master checklist
is [here](../inventory/mpc-key37-remaining-hardware-checklist.md); its older
unchecked boxes are not automatically current failures or untested work.

`00 READY SMALL TEST` is a partial navigation experiment, not the complete
library and not the project home. Four abandoned hidden staging trees were
removed after verification on October 23, freeing approximately 1.97 GB.
Recovery locations for all 9,604 files are recorded locally in
`work/sd-organization-2026-10-23/staging-retirement.json`: 9,080 exact duplicates
remain in the local Ready to Play package and 524 differing files have separate
backups. Keep that package and the backup folder for recovery. No live project,
original sample library, or active hardware-test package was moved.
Text guides are also readable on the laptop; this does not imply
that the MPC Browser can display text files.
