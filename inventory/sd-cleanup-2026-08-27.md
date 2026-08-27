# SD cleanup — August 27, 2026

The cleanup reduced completed-test clutter while preserving every removed item
in a verified, recoverable external-drive archive. No licensed audio or MPC
project capture is committed to Git.

## Protected content retained on SD

- `00 FG Scratchpad` remains self-contained and contains Main Drums, Vinyl
  Shots, Pluck Bass, Wurli, Dark FM, Glass Howl, and Sub Smooth.
- The sole retained project is
  `Projects / FG Scratchpad / FG Vinyl Scratchpad v02 Master.xpj` plus its
  companion ProjectData folder.
- The protected Master and its ProjectData were not modified.
- `00 TRACK LAYOUT.txt` now identifies Track 8 as a placeholder Keygroup to
  remove or repurpose only in a disposable Jam copy. Pro Pack Clip Workflow is
  deferred and the placeholder is not represented as a Clip track.

## Recoverable external archive

The complete pre-cleanup snapshot is:

`/media/steve-farrelly/Storage/MPC Transfer/SD Cleanup Archive 2026-08-27`

Copies of Scratchpad content, the protected Master, completed hardware tests,
and the old Vinyl Kit Banks test project were checksum-verified before any
move. Items removed from the live card are retained under:

`/media/steve-farrelly/Storage/MPC Transfer/SD Cleanup Archive 2026-08-27/Quarantined From SD`

The quarantine contains:

- the completed `00 FG Hardware Tests` tree;
- `Key37-Vinyl-kit-banks-test.xpj` and its ProjectData;
- the empty `Projects/FG Clip Reference` and `Programs/Clips` directories;
- obsolete SD Trash copies of Vinyl Kit Banks 01 and Vinyl Layered Kit 01.

The live `.Trash-1000` folders are empty. Restore by copying an exact quarantined
path back to its former SD location; do not restore the entire archive over the
card.

## Deferred work

- Cold-start timing is explicitly deferred at the user's request.
- Clip reference capture remains purchase-gated because MPC Pro Pack is not
  owned.
- Optional routing baselines remain in the external/Ubuntu captures and can be
  redeployed if that research resumes.
