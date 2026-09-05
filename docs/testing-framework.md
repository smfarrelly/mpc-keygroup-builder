# Local MPC program testing framework

The local test framework validates and semantically simulates MPC XPM programs
before they are copied to removable media. It supports MPC 3 gzip/JSON Keygroup
programs and legacy XML Drum programs.

Run it with the project environment:

```bash
uv run mpc-program-test "/path/to/SD mirror" \
  --json work/semantic-test-report.json \
  --csv work/semantic-test-report.csv
```

## What a local production pass means

- The XPM parses and has the expected container structure.
- Every declared sample resolves to one nonzero local audio file.
- Keygroup record and sample-registry relationships are consistent.
- Sample root notes, slice endpoints, and enabled loops are within valid bounds.
- The Keygroup produces at least one layer for every tested combination of MIDI
  note 0–127 and representative velocity 0–127 values.
- Populated Drum pads produce at least one layer at every representative
  velocity.
- Layer stacks, legacy exclusive endpoints, and audio encodings unsupported by
  Python's standard WAV reader are reported as warnings.

Programs under `Programs/Keygroups/Testing/` use `testing` scope. Their results
remain visible, but failures do not fail the production deployment gate.

## What it does not prove

The framework does not emulate the MPC's proprietary interpolation, filters,
envelopes, effects, warp algorithms, voice stealing, controller mappings,
track routing, or converters. It cannot decide whether a sound is tuned,
balanced, expressive, or musically useful. Those remain Key 37 hardware and
listening tests recorded in `inventory/program-status.csv`.

## Verdicts

- `pass`: no semantic issues found.
- `warn`: structurally playable with a compatibility or behavior warning.
- `fail`: dead trigger coverage, invalid data, or missing/invalid audio.

The command exits unsuccessfully only when a production-scope program fails.

## Verify a complete workflow bundle

Generated workstation waves, creative shortlists, Ableton conversion waves,
showcases, and the portable demo include a root `checksums.json` receipt. Verify
one after generating, copying, downloading, or moving it:

```bash
mpc-bundle-verify "/path/to/complete bundle"
```

The verifier is read-only. It requires the receipt to list every regular file
except itself, rejects missing and unrecorded files, validates every SHA-256,
and refuses absolute, ambiguous, traversal, Windows-incompatible, or symbolic
link paths. `--json` prints a stable machine-readable report. A receipt in a
different location can be selected with a relative POSIX `--receipt` path.

A generic bundle pass proves byte integrity only. It reports hardware status as
`not-evaluated` and does not replace program simulation or listening. The
portable-demo-specific `mpc-portable-demo --verify` command calls this verifier
and then additionally reruns its cross-kit simulation and checks the demo's
deferred-hardware evidence.

## Deterministic audition rendering

Generate a dry local preview with:

```bash
uv run mpc-program-audition "/path/to/Program.xpm" \
  --output work/auditions/program.wav
```

The renderer writes a mono 44.1 kHz WAV and a neighboring JSON event manifest.
Keygroups use a fixed ten-note phrase with alternating medium and high
velocities, select the corresponding layer, and apply approximate root-note
pitching. Drum programs trigger the first 16 populated instruments. Source
clips are capped and faded for quick comparison.

Auditions are intentionally dry and approximate. They help detect silence,
wrong source selection, extreme pitch mapping, corrupt PCM data, and obvious
level differences; they do not emulate the MPC audio engine.

## Drum performance audit

Inspect pad classification, playback fields, and hat mute groups with:

```bash
uv run mpc-drum-audit "/path/to/Drum Program.xpm"
```

The command is read-only and supports legacy XML plus MPC 3 compressed Drum
Programs. Its compact report shows category counts and mute-group membership;
`--json` includes every populated pad's sample, category, mute group, polyphony,
monophonic flag, and playback mode. It warns when open/closed hats lack a group,
when a hat group lacks its open or closed counterpart, or when a hat group also
contains a non-hat category.
