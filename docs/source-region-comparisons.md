# Compare source sample regions before converting

`mpc-source-regions` creates paired audio excerpts from an owned Ableton sample
preset: one starts at the WAV beginning, and one uses the preset's inclusive
sample-start/end bounds. This helps inspect attacks that a conversion might
otherwise discard. It creates no XPM and does not change the source library.

```bash
mpc-source-regions "/path/to/library/pack/Preset.adg" \
  --source-root "/path/to/library" \
  --output "/path/to/new-comparison-folder"
```

The output directory must be new and outside the source library. Use
`mpc-tools help mpc-source-regions` for command help. In a source checkout,
`uv run python -m mpc_keygroup_builder.source_regions` accepts the same arguments.

## What to listen for

For each active zone, compare `01-full.wav` with `01-region.wav`, then the next
numbered pair. Both use the same fixed gain. A preset's start offset can remove
a transient or move directly into a sustained texture. The region endpoint can
also shorten the source. `comparison.json` records the offsets, source WAV
hashes, and source detune, panorama, volume, loop, and warp settings.

These are unpitched mono excerpts capped at three seconds. They do not render
Ableton or MPC envelopes, filters, effects, loops, detune, warp, or voice
behavior. The two files can have different lengths. An excerpt sounding useful
does not prove that an instrument conversion is faithful or hardware accepted.

The tool accepts 1–16 active zones, WAVs up to 32 MiB and 2,000,000 frames per
zone, and sample paths contained within the inferred pack and selected source
root. Invalid regions fail without publishing a partial folder. Outputs are
staged and published without overwriting an existing destination.

## Current preservation research

The local MPC project captures checked on October 30 contain no nonzero sample
starts; they do not establish the hardware's edited-region behavior. The
Databenders Bowed Bytes source starts at frame 5029 and also has release-loop
metadata. Chaos and Far East have enabled loop settings. A region-only export
would not establish preservation of those instruments.

Use these comparisons as supporting evidence while conversion remains guarded.
When hardware work resumes, capture one MPC-authored Keygroup before and after
changing only its sample start. Preserve both XPMs and their audio unchanged,
then compare the serialized fields and audition the result. Endpoints, loops,
and detune need their own controlled comparisons before bulk conversion.

Generated audio may contain licensed material. Keep comparison folders private;
do not commit or distribute them with the toolkit.
