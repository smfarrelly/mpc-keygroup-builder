# Build a pitched Keygroup

The Keygroup builder converts a folder of pitched WAV files into an MPC 3
Keygroup while preserving a known-working MPC-generated XPM as the schema
template. It supports one sample per note and up to eight velocity layers per
note.

## Prepare the source

1. Work on a copy of audio you are licensed to use.
2. Put one instrument's WAV files in a dedicated directory.
3. Include a note name in every file name: `C3`, `F#3`, and `Bb4` are examples.
4. When using layers, give samples for the same note consistently sortable
   velocity labels or provide the workflow's explicit layer information.
5. Save one minimal, working Keygroup on your MPC to use as the template.

The tool never infers redistribution rights. Commercial audio and generated
programs belong on ignored local storage, an external drive, or the SD card—not
in this repository.

## Inspect the interface

```bash
mpc-keygroup --help
```

The help text is authoritative for the installed version. A typical build is:

```bash
mpc-keygroup "/absolute/path/to/source-wavs" \
  --template "/absolute/path/to/known-working-template.xpm" \
  --output "/absolute/path/to/output/My Instrument.xpm"
```

Use the exact options shown by `--help`; legacy releases may use a positional
source or output rather than the illustrative long form above. Run a dry run
when offered and read the inferred notes, roots, layers, and output paths before
writing.

## Batch conversion

For repeatable libraries, define sources and outputs in a manifest and inspect:

```bash
mpc-keygroup-batch MANIFEST.toml --dry-run
mpc-keygroup-batch MANIFEST.toml
```

Manifest-driven builds make it possible to reproduce the program without
checking licensed audio into Git. Keep paths environment-specific and record
the source product, license, download date, and hashes separately.

## Validate the result

```bash
mpc-program-test "/absolute/path/to/output/My Instrument.xpm"
mpc-xpm inspect "/absolute/path/to/output/My Instrument.xpm"
```

Software checks verify structure, range coverage, layers, sample references,
and invariants. They cannot verify feel, tuning, timbre, key range, or behavior
after save/reload. Copy the complete XPM plus its companion ProgramData folder
to the MPC, listen across the keyboard and velocities, then record the hardware
result.

## Range and variant workflows

Nearest-neighbor root ranges, playable-register shifts, and preservation-first
variants are described in [Range inference](keygroup-range-inference.md) and
[Keygroup variants](keygroup-variants.md). Variants create a new program and
leave the hardware-tested source untouched.

For Drum Programs, pad colors, mute groups, layered pads, and layouts, use
[Program model and semantic layouts](program-model-and-layouts.md) instead.
