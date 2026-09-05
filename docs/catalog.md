# MPC Program Catalog

The catalog turns the structural ledger and XPM metadata into a portable
index. Its default mode is metadata-only: it never reads sample contents and
never copies licensed audio. An explicit enrichment mode measures referenced
local WAVs while still writing only numeric descriptors and provenance to the
catalog.

The lightweight `mpc-library` command queries the CSV ledger directly. It
validates the required headers and row widths before applying filters, so a
damaged hand edit reports the header or row to repair instead of returning
partial results. Hardware filters accept `untested`, `pass`, `warn`, or `fail`;
favorite filters accept `yes`, `no`, or `provisional`. Unknown values are
reported as input errors rather than successful empty queries.

Build it from an SD card, immutable backup, or another directory whose layout
matches the ledger paths:

```bash
uv run mpc-catalog build inventory/program-status.csv \
  --program-root "/path/to/MPC media root" \
  --output work/program-catalog.json
```

Add duration, RMS/crest, onset contrast, and attack facets when the licensed
audio is locally available:

```bash
uv run mpc-catalog build inventory/program-status.csv \
  --program-root "/path/to/MPC media root" \
  --audio-facets \
  --output work/program-catalog-audio.json
```

Audio lookup is confined to the declared program root. Missing or unreadable
samples are recorded per program and do not abort the scan.

Each program entry contains:

- ledger path, collection, and category;
- normalized name, Drum/Keygroup type, and source format;
- zone, layer, and unique sample-reference counts;
- Keygroup note range or Drum pad range and populated banks;
- semantic role counts;
- model warnings/errors;
- structural, semantic, hardware, favorite, Scratchpad-role, and listening data.

Missing, unreadable, and malformed XPMs are isolated as individual entries so
one bad file cannot abort a library scan. Use `--fail-on-error` in automation
when malformed or unreadable files should fail the command; intentionally
missing entries remain visible in the summary.

Query the saved index without reconnecting the drive:

```bash
uv run mpc-catalog query work/program-catalog.json --type drum --role kick
uv run mpc-catalog query work/program-catalog.json --hardware pass --favorite yes
uv run mpc-catalog query work/program-catalog.json --search "Mirage" --format json
uv run mpc-catalog query work/program-catalog-audio.json \
  --type drum --role kick --duration short --transient sharp --loudness loud
```

Semantic roles accept a complete role such as `hihat.closed` or a family such
as `kick`, `tom`, or `percussion`. Scratchpad-role text is also considered.
Keygroup searches can also constrain the measured/modelled note span with
`--note-low-at-most`, `--note-low-at-least`, `--note-high-at-most`, and
`--note-high-at-least`.

## Deterministic cross-library kits

An audio-enriched catalog can feed a strict, seeded kit recipe. The selector
scores semantic role, preferred duration/loudness/transient descriptors,
hardware status, favorite status, and source diversity. It emits provenance
and a basename-only Drum manifest without placing licensed WAVs in Git:

```bash
uv run mpc-kit-select recipes/kits/dusty-cross-library.toml \
  work/program-catalog-audio.json \
  --manifest-output work/dusty-cross-library.toml \
  --report-output work/dusty-cross-library.json \
  --markdown-output work/dusty-cross-library.md \
  --seed 37
```

Use `--stage-output` and `--stage-report` only in ignored/local storage to copy
the selected source WAVs into a flat build staging directory. Every staged file
is SHA-256 verified. Ambiguous duplicate basenames are rejected so the result
remains safe for `mpc-drum-build`.

## Transactional recipe waves

`mpc-kit-wave` turns an ordered `[[kits]]` document into a complete listening
wave. With `--ledger`, audio is measured once and the enriched catalog is
shared by every recipe. The command preflights every selection before copying,
refuses two recipes that resolve to the same source set, records all pairwise
sample overlap, and publishes only after every program passes model validation,
semantic simulation, Drum audit, and source/destination checksum comparison.

```bash
uv run mpc-kit-wave recipes/kit-waves/fg-vinyl-cross-library-wave-01.toml \
  --ledger inventory/fg-cross-kit-source-programs.csv \
  --program-root "/path/to/local MPC media mirror" \
  --template "/path/to/known-good-drum-template.xpm" \
  --output work/cross-library-wave-01
```

The output is immutable-by-default: an existing target is refused. Each kit
has its manifest, selection prose, complete provenance, staged checksums,
self-contained Program folder, and software-acceptance report. The wave root
adds JSON/CSV indexes, pairwise distinctness evidence, and one checklist whose
MPC paths are absolute. Licensed WAVs belong only in ignored or external local
storage.

The first maintained wave contains Dusty Cross-Library, Tight Machine, Ambient
Percussion, SP Punch, and Experimental Texture recipes. Their musical names are
intent; the descriptor match and source provenance remain the auditable facts.

## Current full-library proof

The August 26, 2026 scan of the immutable media backup processed all 750 ledger
entries: 746 normalized successfully, comprising 90 Drum Programs and 660
Keygroups. Four intentionally transient `Programs/Keygroups/Testing` files were
absent and remain visible as `missing`. No licensed audio entered the index.

The JSON schema is the intended input to catalog-assisted Scratchpad recipes,
semantic MIDI generation, and the future Program Designer.
