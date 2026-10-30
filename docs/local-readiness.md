# Check local work before reconnecting the MPC

`mpc-tools check` combines existing integrity checks with bounded sample-reference
checks. It only reads inputs you explicitly select. It does not discover a card,
repair references, copy files, update a ledger, or grant hardware acceptance.

```bash
mpc-tools check \
  --archive work/ideas/take-01 \
  --bundle work/verified-package \
  --program "/path/to/library/Programs/Kit.xpm" \
  --sample-root "/path/to/library" --json
```

Each input option can be repeated. Use just the options you need; an empty request
is rejected rather than scanning your drives. `--sample-root` only applies to
programs and must contain each selected program. Without it, lookup is confined
to each program's parent folder. Paths with spaces must be quoted.

## Check the audio bytes too

Reference checks alone do not read the audio payload. Opt in when preparing a
program for transfer or investigating a file that exists but does not play:

```bash
mpc-tools check --program "/path/to/Kit.xpm" --verify-audio --json
```

This streams every resolved PCM WAV in small blocks, checking declared frame
counts and recording a PCM checksum, channel count, width, rate, and frame
count. It supports mono/stereo 8/16/24/32-bit PCM WAV. Incomplete audio fails;
other file formats remain explicitly unsupported rather than receiving a pass.
A vendor WAV with complete chunks but a stale outer RIFF length is read through
an adjusted view and marked `riff_length_adjusted`; its bytes are not rewritten.

A second known vendor quirk counts the RIFF alignment byte inside the data
chunk. For odd-length mono 24-bit PCM only, one extra zero byte is treated as
padding and recorded as `data_padding_ignored`. The complete frames verify,
but the program report retains a warning. Other trailing partial frames still
fail. This rule also lets dry auditions read those full frames without altering
the original file; it does not synthesize missing audio.

After verifying PCM, the checker compares each normalized layer's inclusive
start/end region with that file's frame count. Out-of-range regions identify
the zone, layer, sample, and bounds in `region_issues`. Missing end markers use
the full file. `regions_checked` records coverage, while `audio_verification`
continues to describe PCM integrity: readable audio can coexist with an invalid
program region. Loop playback and musical intent are not inferred.

Only samples already resolved within the selected root are opened. Missing,
ambiguous, and external references are not searched elsewhere. This option
requires `--program`; it does not inspect audio inside archives or bundles.
Reports distinguish `not-requested`, `pass`, `fail`, and `incomplete` audio
verification. A readable PCM payload can still be silent, wrong for the part,
or programmed poorly. Listening and MPC acceptance remain separate.

## What the results mean

- **Archive:** validate the capture manifest, inventory and checksums.
- **Bundle:** validate the `checksums.json` inventory and checksums. This option
  is for that receipt format, not every generated folder in the toolkit.
- **Program:** parse the normalized model, check its structure, and look for
  each sample relative to the XPM or its `Name_[ProgramData]` directory. A
  sample name without a recognized audio suffix also tries an appended `.wav`
  (dots inside sample names are preserved). Unique case-insensitive matches
  support vendor `.WAV` files and directory casing. No recursive basename search
  is used because that could silently choose the wrong sample.
- **External:** absolute, Windows-style, or escaping paths are not accessed.
  Their availability is unknown, not evidence that the audio was deleted.
- **Missing:** no regular file exists in the allowed lookup locations. MPC
  search behavior may differ; the tool does not claim to emulate the firmware.
- **Ambiguous:** more than one allowed path matches, including case collisions
  or duplicates between sibling and companion folders. Nothing is selected;
  inspect the files before deciding what the MPC should use.

Sample symlinks are not followed, including links inside the selected root.
They report external/unknown when no regular candidate resolves. The JSON
records whether a found path needed case-insensitive lookup; this does not
rename files or repair the XPM.

Exit codes: 0 means all selected software checks passed; 1 means at least one
failed or needs attention (including external references); 2 means invalid
command usage. JSON has per-input details, overall status, and a separate
`hardware_status: not-evaluated`. A malformed input does not hide other results.

This does not decode audio, check plugin licenses, prove XPJ external-dependency
completeness. A checksum receipt only proves consistency with that receipt.
Hardware listening remains a separate decision.

### Program inspection bounds

The XPM model and inspector read at most 32 MiB of source bytes and expand at
most 64 MiB of gzip data. XML is limited to 128 levels and 200,000 elements;
document types/entities are rejected. JSON is limited to 128 levels and 500,000
values. Duplicate serialized JSON fields and
invalid top-level/container shapes are rejected rather than interpreted with
last-value-wins behavior. These are inspection safety limits, not MPC format
capacity claims. Inputs exceeding them fail with a readable error; other selected
readiness inputs remain visible. No input is modified to fit a limit.

## Are the recipes still current?

New `mpc-workstation-wave` bundles record `recipe-inputs.json` at build time,
covered by bundle checksums. Compare with an explicitly selected current tree:

```bash
mpc-tools check --bundle work/my-wave --recipe-root recipes --json
```

Integrity and freshness are separate. Intact outputs can be `stale` when recipe
files were added, removed, or changed. Both `stale` and `unknown` return status 1;
`current` returns 0 if all other selected checks pass. Older bundles without a
build-time receipt report `unknown`. Do not retrofit receipts onto old builds:
regenerate into a new output folder instead.

The scope is exact bytes of top-level `*.toml` files in drums, harmony, melody,
kits, and workstation categories, including unselected families. Comments and
whitespace changes count. Moving an unchanged tree does not. Nested files and
other categories are outside this scope. Source changes detected during a build
abort publication and clean up staging. This is not a filesystem lock.

This is conservative recipe-input freshness, not a claim about changed tool
versions, command-line options, source audio, or plugin installations. Checks
without `--recipe-root` retain their integrity-only behavior.

## Recover without destroying the evidence

If a file is missing, first verify that you selected the correct local library
root. Do not rewrite paths merely to make the report green. Compare a known-good
original and preserve it before rebuilding a variant.

If archive verification fails, keep the damaged archive for investigation and
capture again from a known-good source into a new folder. Do not regenerate its
manifest to conceal the change. See [Idea snapshots](idea-snapshots.md).

If a copy was interrupted, preserve the source and inspect the error before
retrying into a new output. Do not delete unknown staging folders or unrelated
files. Package deployment has a separate explicit `--resume` workflow; archive
capture/restore does not promise resumable copies.
