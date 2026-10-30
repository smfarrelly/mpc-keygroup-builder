# Instrument software review — October 30, 2026

Hardware acceptance remains deferred for new material. This checkpoint records
software evidence and navigation fixes, not new listening verdicts.

## Wider SD reference audit

The saved inventory contains 1,306 XPMs across `Programs`,
`Samples/Samples From Mars`, `00 FG Scratchpad`, `01 FG Favorites`, and
`00 FG Hardware Tests`. Bounded model and local-reference inspection passed
for 1,303 programs initially. Three failed on the same vendor spelling:
`HH 626 Stardard OH Vinyl` instead of the existing `HH 626 Standard OH Vinyl.wav`.

Affected paths, from Browser > Places > SD Card:

- `Samples/Samples From Mars/Instruments/Vinyl Drum Machines From Mars/Vinyl Drum Machines From Mars 5.xpm`
- `Samples/Samples From Mars/Vinyl Drum Machines From Mars/Vinyl Drum Machines From Mars 5.xpm`
- `Samples/Samples From Mars/Vinyl Drum Machines From Mars/Vinyl Drum Machines From Mars 5 FG COLORS.xpm`

Added an exact-byte WAV alias using the expected spelling in each of the two
folders: two files of 88,078 bytes each. The source SHA-256 is
`d6a1dc5e306d869f1375fc7b240d9d3d775f226e63af1bfc9dec0094c6678903`.
Its 14,354 frames match the layer's inclusive SliceEnd of 14,353. All three
programs then passed the same reference check. No XPM, original WAV, pad color,
Boot project, Scratchpad Master, or Volca Base was changed.

Thus all 1,306 inventoried programs have passing reference evidence, with the
three repaired cases rechecked after adding aliases. This does not decode
every WAV, prove instrument intent, or replace hardware listening. The new
Found Transitions and Mechanical Layers packages were checked separately.

## Laptop previews

All eight Vinyl Shots 04 banks render at velocity 100: 128 events. All four
Vinyl Layered Banks 03 banks render at velocities 16, 48, 80, and 112: 256
events. Together these twelve previews cover 384 sample selections. The
program files retain their hashes. Mechanical Layers also renders its eight
Clean/Tube pairs at velocities 48 and 108.

These are dry, mono, capped previews with synthetic fades. They do not render
MPC effects, loops, envelopes, voice/choke behavior, or exact velocity response.
Use [bank and velocity preview commands](../docs/testing-framework.md#deterministic-audition-rendering)
to reproduce them with owned samples.

The previews exposed a vendor WAV metadata defect: inserted MPC metadata left
the outer RIFF size outdated, although the full PCM data was present. The
reader now validates physical chunk boundaries and adjusts only its in-memory
view. The SD files match the original sources; none needed rewriting.
Genuinely incomplete audio is still rejected.

## Current Scratchpad evidence

Use `inventory/scratchpad-current.toml` with `mpc-scratchpad-check`. It points
to the six selected, ledger-backed instruments at their current locations.
The original v0.1 shortlist is explicitly historical. The current deployment,
core, and favorite gates pass using existing ledger evidence. The five
Keygroups retain extreme-key-extrapolation warnings; those warnings describe
far-out notes rather than missing samples.

Expanded shots and expressive alternates remain in their existing review
notes. No new ledger rows, listening results, or favorite promotions were
invented. The [role guide](../docs/instrument-role-guide.md) is also copied to
the SD's top-level `00 INSTRUMENT ROLES.txt`.

## Evidence and next work

Private evidence is under `work/instrument-audit-2026-10-30/`:
`library-reference-checks.jsonl`, `library-reference-summary.json`,
`vendor-alias-repair-receipt.json`, `bank-previews/results.json`,
`current-core-check.json`, and `current-core-guide-update.json`.
The original failed audit remains intact beside the repair receipt.
Licensed WAVs, generated previews, and hardware captures stay out of Git.

Next software work should deepen audio-integrity checks and make evidence
easy to review. Preserve conversion guards for unsupported source offsets,
detune, loops, and overlapping zones. New instrument listening and controller
probes can wait until the user wants hardware work again.
