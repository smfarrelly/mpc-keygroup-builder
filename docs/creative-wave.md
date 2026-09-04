# Creative batch and review

`mpc-workstation-wave` turns a validated recipe library into a bounded set of
reproducible four-part ideas, five-section arrangements, and one offline review
workspace. It is designed for generating a useful MPC test queue without
pretending that software metrics can judge musical taste.

## Generate a portable wave

This command audits every recipe, generates eight unique candidates per family,
and creates a redistributable synthetic Drum Program:

```bash
mpc-workstation-wave recipes \
  --families all \
  --seeds-per-family 8 \
  --output work/creative-wave-01
```

The total is capped at 128 candidates and each family is capped at 32. The
destination must not exist. A structural fingerprint prevents identical event
sets from silently occupying multiple review slots; skipped seeds and their
matching candidate are retained in `wave.json`.

Use a real Drum Program without copying its licensed samples into the wave:

```bash
mpc-workstation-wave recipes \
  --families dusty,house,weird \
  --seeds-per-family 4 \
  --seed-start 40 \
  --program "/full/path/to/My Drum Program.xpm" \
  --lock-track chords \
  --output work/owned-sound-wave-01
```

The real program remains an external reference. Deploy it and its companion
audio separately. Omitting `--program` creates and includes deterministic CC0
audio and a self-contained 16-pad Drum Program.

Family defaults preserve the maintained tempo, Drum density, and arrangement
mutation. `--tempo`, `--density`, and `--mutation` explicitly override those
values for the whole wave. Repeating `--lock-track` preserves selected tracks
through every arrangement section.

## Review without the command line

Open `review.html` directly. It makes no network requests and supports:

- family and verdict filtering;
- pitched-note and semantic Drum previews;
- side-by-side metric comparison;
- pending, keep, provisional, and reject shortlist states;
- local notes stored under a fingerprint unique to the wave;
- explicit JSON and CSV export; and
- matching-fingerprint JSON import.

A keep verdict is a shortlist decision, not an MPC hardware pass. Browser state
does not alter MIDI, recipes, samples, or project files.

Regenerate a standalone companion from an existing report when needed:

```bash
mpc-creative-review work/creative-wave-01/wave.json \
  --output work/creative-wave-review.html
```

The command refuses to replace an existing file unless `--force` names that
exact HTML destination.

## Evidence and MPC transfer

Every wave contains:

- `Candidates/FAMILY/seed-N/idea.mid` with Drums, Bass, Chords, and Melody;
- five MIDI files under each candidate's `Sequences/` folder;
- complete idea and arrangement JSON evidence;
- copied editable TOML recipes;
- `candidate-catalog.csv` and `wave.json` indexes;
- `COPY_MANIFEST.txt` and SHA-256 `checksums.json`;
- a consolidated `HARDWARE_CHECKLIST.md`; and
- the self-contained review companion.

Copy the wave folder as a unit instead of flattening it. The checklist gives the
resulting MPC browser path for every candidate. Sound assignment, MIDI import,
save/reload, listening, and musical promotion remain deferred until a person
tests them on the MPC.

## Exploration score

The ranking is the unweighted mean of seven normalized observations:

1. events per bar;
2. sixteenth-note Drum syncopation;
3. Melody pitch range;
4. Melody variation rather than literal motif repetition;
5. summed movement between neighboring chord voicings;
6. event changes or omissions across arrangement sections; and
7. unique semantic Drum roles.

The raw observations, normalized components, formula meaning, and structural
fingerprint are stored per candidate. A higher number means “inspect this for
more observable variation,” never “this sounds better.”
