# Keygroup useful-range inference

Sample filenames and Ableton root metadata describe pitch, but they do not
necessarily place the useful voices under the physical Key 37 keys. A fixed
`root_shift` remains available when a hardware-proven correction is already
known. `root_target` handles the more reusable case: declare the desired MIDI
window and let the builder choose an explainable whole-octave shift.

## Single build

```bash
uv run mpc-keygroup "/path/to/pitched-wavs" \
  --template "/path/to/known-good-keygroup.xpm" \
  --velocity-preset "/path/to/source.adg" \
  --root-target 60:96 \
  --name "Chromatic Percussion Auto" \
  --output "work/Chromatic Percussion Auto.xpm"
```

Use `--dry-run` first. The report includes the source span, target, inferred
shift, result span, and number of sampled roots inside the target.

## Batch manifest

```json
{
  "name": "Chromatic Tom",
  "category": "Chromatic Percussion",
  "source": "Chromatic Tom",
  "root_target": [60, 96]
}
```

`root_target` and `root_shift` cannot appear together. Target bounds and every
resulting root must remain within MIDI 0–127.

## Selection rules

The algorithm evaluates every valid whole-octave shift from -120 through +120
semitones. It chooses candidates in this order:

1. maximize the number of distinct sampled roots inside the target;
2. minimize the absolute shift so an already useful broad mapping remains
   unchanged when tied;
3. minimize distance between source-result and target centers;
4. use a stable signed-shift tie break.

Whole octaves preserve every sample's pitch class. Velocity layers, intervals,
sample endpoints, audio, and relative keygroup boundaries remain unchanged.
The tool does not claim to infer musical register from audio timbre.

## Real-data regression

The five SP-1200 NR2 chromatic software fixtures used a manual +36 semitone
correction. Their original root spans are 25–50 in different 16-note windows.
With target 60–96, automatic placement independently returns +36 for all five
and recreates those result spans exactly:

- Analog Tom: 63–78;
- Chimes: 71–86;
- Cowbell: 65–80;
- Tom: 61–76;
- Tone: 69–84.

The real batch inspection passes 80 unique WAVs with no duplicates or mapping
failures. Hardware listening subsequently found seven keys unavailable at the
default keyboard position and requested one additional octave upward. NR3 uses
an explicit +48 shift because that hardware preference intentionally differs
from the target-coverage heuristic. A broad 24–96 mapping, representing an
already useful multisampled instrument such as Wurli, remains at zero shift
because moving it does not increase target coverage.

This is software evidence for repeatable mapping, not permission to overwrite
an accepted program. New target choices still require later hardware listening.
