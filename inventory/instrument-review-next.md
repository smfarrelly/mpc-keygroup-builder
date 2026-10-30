# Next instrument review: expression, texture, and keys

October 30, 2026. This is a small listening session, not a replacement for the
historical ledger. Keep Vinyl SP as the main kit and Pluck Bass, Wurli, Dark FM,
Glass Howl, and Sub Smooth in their current roles. Save experiments under a new
project name. Do not overwrite the Scratchpad Master.

All paths below start at **Browser > Places > SD Card**. Text guides are useful
on the laptop; the MPC is not assumed to display Markdown or text files.

## Software checkpoint

The October 30 mounted-card scan found 1,306 XPMs in the five selected roots:
`Samples/Samples From Mars`, `Programs`, `00 FG Scratchpad`, `01 FG Favorites`,
and `00 FG Hardware Tests`. There were no scan errors. Project-private copies
and other roots were outside this inventory.

All 88 colocated colored vendor programs and their 88 original programs match
the saved deployment checksums. All 28 XPMs in Scratchpad and Favorites pass
bounded sample-reference and model checks. This does not validate every sample
reference in the wider library, decode audio, or establish hardware acceptance.

All 468 local artifact XPM filenames occur somewhere in the selected SD roots.
That is name coverage only: it does not prove byte identity, equivalent
programming, or that every owned source preset has an MPC conversion. The
older conversion backlog must not be used as a current missing-file list.

Private reproducible evidence lives in `work/instrument-audit-2026-10-30/`:
`audit.py`, `inventory.json`, `colored-coverage.json`,
`curated-readiness.json`, and `local-name-candidates.json`. No program or audio
was moved or rewritten by this audit. The next useful creation decision should
follow a specific musical gap, rather than another bulk export.

## 1. Expressive drum alternate

Load:

`01 FG Favorites/04 Drum Alternates/09 FG Vinyl Layered Banks 03/FG Vinyl Layered Banks 03.xpm`

- Play Banks A-D softly and firmly. Each populated pad has four velocity
  regions: 0-31, 32-63, 64-95, 96-127. E-H are deliberately empty.
- Record one short groove and audition it on A-D. Choose the most useful bank
  for your playing; do not assume switching banks remaps recorded notes.
- For a clear choke test, hit A10 then A09: the open hat should stop. A10 then
  A11 should leave its tail alone. Repeat A12/A11, with A12/A09 as the control.
- Other isolated hat pairs: B07/B08, B09/B10, C07/C08, C09/C10, D07/D08.
- Listen for abrupt level jumps between velocity regions. These are related
  timbres, not a promise of acoustically sampled dynamics or round robin.

Result to record: pass/warn/fail, preferred bank, useful velocity response,
choke observation, and whether this earns a place as an expressive alternate.
Do not promote it to the main kit by default.

## 2. Texture and transition kit

Load:

`01 FG Favorites/04 Drum Alternates/08 FG Breaks Texture Banks 01/FG Breaks Texture Banks 01.xpm`

- Start with F (Found Sounds Body Kit), G (S950 Club 8), and H (S950 Hard Glitch).
- Add a few accents over an existing loop. Decide whether these serve a
  separate texture/transition role or simply duplicate your main kit.
- A/B contain Big Break/Hand Break, C Drumtrax, D Drumulator, E LM-1.
- Empty pads inherited from a source kit are not automatically missing samples.
  Note the exact bank/pad if a populated voice is silent.

Result to record: pass/warn/fail, favorite bank/pad, role, and any silent voice
or unexpectedly long tail. This collection already covers the older roadmap's
Found Sounds and S950 starting points.

## 3. A useful keys variation

Compare these exact files at similar perceived volume:

- `00 FG Scratchpad/08 Expressive Candidates/Wurli Expressive 01/Wurli Clean.xpm`
- `00 FG Scratchpad/08 Expressive Candidates/Wurli Expressive 01/Wurli Warm.xpm`
- `00 FG Scratchpad/08 Expressive Candidates/Wurli Expressive 01/Wurli Pad.xpm`

Clean is the reference, Warm changes filter character, and Pad changes the
envelope for sustained chords. Play the same chord and melody in the normal
keyboard register; listen to both attack and release. Check Q-Link pickup if
you use those controls. Retain the original Wurli unless a variation earns a
distinct role.

## Finish only the candidates worth keeping

Save/reload the experiment and check samples, chosen sound, and pad colors.
Record one concise observation per candidate, including full XPM path and
bank/pad when relevant. Software sample-reference checks cannot settle choke
behavior, musical preference, or hardware persistence. Existing accepted
Vinyl Shots and Vinyl Kit Banks results do not need repeating for this review.

Next creation decision: use the listening notes to select one genuinely absent
role. Do not generate more variants merely because source material exists.
