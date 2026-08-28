# Expressive Keygroup variants

`mpc-keygroup-variant` makes audition candidates from an existing MPC 3
compressed Keygroup without reconstructing its sound. The source XPM remains
the authority. Export starts from a complete deep copy, changes only declared
fields, writes a new XPM and matching ProgramData folder, then compares the
entire output against the exact expected document and audio checksums.

This is intentionally narrower than a general preset editor. XML Keygroups,
effects, modulation links, polyphony, unison, sample loops, root notes, zone
ranges, and arbitrary raw paths cannot be edited by this command. Unsupported
controls fail rather than being guessed.

## Inspect a source

```bash
uv run mpc-keygroup-variant inspect "/path/to/Wurli.xpm"
```

The JSON report identifies the source shape, current supported values,
instrument and layer counts, registry entries, and companion audio count. An
MPC 3 compressed Keygroup and a non-empty sibling
`NAME_[ProgramData]` folder are required for a normal self-contained export.

## Variant schema

```toml
schema_version = 1
id = "pad"
name = "Pad"
description = "Slow attack and long release candidate for sustained chords."

[parameters]
amp_attack = 0.35
amp_decay = 0.75
amp_sustain = 0.85
amp_release = 0.55
filter_cutoff = 0.72
filter_resonance = 0.10
```

The accepted keys are:

- `transpose`: integer semitones from -24 through 24; both MPC program and
  Keygroup transpose fields are kept in step;
- `amp_attack`, `amp_decay`, `amp_sustain`, `amp_release`: normalized 0–1;
- `filter_attack`, `filter_decay`, `filter_sustain`, `filter_release`:
  normalized 0–1;
- `filter_cutoff`, `filter_resonance`: normalized 0–1 on active filter slot 0;
- `filter_envelope_amount`: bipolar -1 through 1 on active filter slot 0.

Attack, Cutoff, and Filter Attack also update the corresponding stock custom
Q-Link's current control value. Its target, range, behavior, and every other
Q-Link property remain unchanged. A source that lacks exactly one matching
stock link is rejected when that parameter is requested; the exporter does not
guess by numeric parameter ID.

The bundled `clean.toml`, `warm.toml`, `pad.toml`, `pluck.toml`, `bass.toml`,
and `lo-fi.toml` are repeatable starting points. Clean changes only the program
name and acts as the comparison reference. The others are intentionally marked
as candidates because normalized MPC values do not tell us whether a setting is
musically useful for a particular sample set.

## Export and verify one candidate

```bash
uv run mpc-keygroup-variant export "/path/to/Wurli.xpm" \
  --spec variants/keygroups/pad.toml \
  --output work/wurli-pad/Wurli\ Pad.xpm

uv run mpc-keygroup-variant verify "/path/to/Wurli.xpm" \
  work/wurli-pad/Wurli\ Pad.xpm \
  --spec variants/keygroups/pad.toml
```

Existing destinations and in-place writes are refused. `--force` is explicit.
`--xpm-only` exists for software-format diagnostics, but that output is not a
self-contained hardware handoff and should not be used for SD deployment.

## Build a hardware listening package

```bash
uv run mpc-keygroup-variant package "/path/to/Wurli.xpm" \
  --spec variants/keygroups/clean.toml \
  --spec variants/keygroups/warm.toml \
  --spec variants/keygroups/pad.toml \
  --spec variants/keygroups/pluck.toml \
  --spec variants/keygroups/bass.toml \
  --spec variants/keygroups/lo-fi.toml \
  --name-prefix "Wurli" \
  --output work/hardware-candidates/wurli-expressive-01
```

The output contains the six XPM/ProgramData pairs, `manifest.json`, and a short
listening README. Package IDs and filenames must be unique. The manifest records
the exact declared parameters, changed raw paths, source shape, ProgramData
counts and bytes, and separate preservation, semantic, and hardware verdicts.
Semantic issues are compared with the source so newly introduced problems are
visible without concealing inherited warnings.

## Preservation contract

The independent verifier proves all of the following before an export reports
success:

- the MPC serialization prefix is byte-identical;
- the decompressed JSON document equals a fresh source copy plus only the
  declared name, parameter, and matching Q-Link-value edits;
- all instrument records, zone ranges, sample roots, velocity regions, loop
  settings, playback bounds, filters not selected for editing, effects,
  modulation, registries, and unknown fields are otherwise equal;
- the output ProgramData relative file set, size, and SHA-256 checksum map
  exactly match the source companion folder.

This proves structural preservation, not sound quality. It also does not prove
that the MPC firmware uses every named value exactly as its JSON label suggests.
The Key 37 listening pass remains the authority for musical promotion.

## Minimal Key 37 acceptance

For each candidate, load its full XPM path and compare it directly with Clean:

1. Play soft and hard single notes, short chords, and held chords across low,
   middle, and high registers.
2. Listen for the intended attack, tail, brightness, resonance, and useful
   register; reject clipping, clicks, stuck tails, or an unusable range.
3. Move Attack, Cutoff, and Filter Attack Q-Links where relevant and check for
   a value jump or stale starting position.
4. Save a project, reload it, and confirm the chosen program, settings, sample
   resolution, and Q-Link behavior persist.
5. Record pass/warn/fail and concise musical notes. Promote values only after
   they are distinct, useful, and reload correctly.

Clip/slice export remains out of scope until launch, tempo, mute, and transition
behavior has a hardware-tested design. No absent Pro Pack workflow is inferred.
