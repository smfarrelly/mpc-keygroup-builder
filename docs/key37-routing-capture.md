# Key 37 two-track routing capture

This is the controlled MPC 3 experiment for simultaneous melodic keys and
physical drum pads. It follows Akai's standalone Key-series procedure while
keeping the two project saves identical except for one Key Ranges action.

Authoritative reference: [Akai Pro — How To Play The Pads And Keys At The Same
Time In Standalone Mode](https://support.akaipro.com/en/support/solutions/articles/69000869260-mpc-key-series-how-to-play-the-pads-and-keys-at-the-same-time-in-standalone-mode).

## Before saving either project

1. Record the MPC OS version in `inventory/program-status.csv` or the progress
   log.
2. Start an empty project and keep its single default sequence empty. Omitting
   note events makes the routing comparison cleaner.
3. Create exactly two tracks:
   - Track 1: Keygroup, `E Piano`.
   - Track 2: Drum, `Vinyl SP From Mars 01 FG COLORS`.
4. In Preferences → Sequencer, set Rec Arm Behaviour to `Multi`.
5. In Track View, hold Shift while enabling Rec Arm on both tracks so both arm
   indicators are red.
6. Do not use Drum Split yet. Do not add effects, automation, tracks, programs,
   or note events after this point.

## Controlled saves

1. Save to the SD card as `Key37_Routing_Baseline.xpj`.
2. Open Menu → Key Ranges.
3. Hold Shift to reveal `Drum Split`, then tap `Drum Split` exactly once.
4. Change nothing else.
5. Save As `Key37_Routing_Changed.xpj` in the same SD-card folder.
6. Confirm the changed state: the physical keys play E Piano while the physical
   pads play the Drum track without manually selecting tracks between gestures.

The one intended difference is the Key Ranges `Drum Split` action. Track order,
programs, sequence, Rec Arm state, tempo, levels, and all other settings must be
identical.

## If Drum Split does not produce the intended behavior

Keep both controlled files. Test fallbacks one at a time and record the outcome:

1. Confirm both tracks remain record-armed with Rec Arm Behaviour set to Multi.
2. In Keyboard Control, test Internal Keyboard Routing values `Global`,
   `Tracks`, and `Global and Tracks`; restore the starting value before each new
   attempt.
3. If track MIDI-input selectors are available, test `MPC Keyboard` for the
   Keygroup track and `MPC Pads` for the Drum track.
4. For every attempt, record the exact setting, whether keys play E Piano,
   whether pads play drums, and whether either controller triggers both tracks.
5. Save the closest known-good project under a distinct filename without
   overwriting the baseline or changed captures.

## Ubuntu capture destination

Copy both XPJ files and both complete companion ProjectData folders without
modification into:

`/home/steve-farrelly/Projects/mpc-keygroup-builder/work/key37-routing-captures/`

The entire `work/` tree is ignored by Git. After copying, calculate SHA-256
hashes and inspect/compare the XPJs using commit `d23ee5c` from the isolated
`mac/xpj-inspector` branch. Do not merge that branch merely to capture files.

The safe capture command performs the copy, byte verification, and hash
manifest atomically:

```bash
uv run mpc-project-capture \
  "/media/steve-farrelly/3561-6538/Projects/FG Scratchpad Routing Tests" \
  --output work/key37-routing-captures
```

It requires both exact XPJ filenames and exactly one sibling ProjectData folder
whose normalized name begins with the corresponding project stem. It refuses a
missing or ambiguous pair, symbolic links, a nonempty destination, and any
source/destination hash mismatch.
