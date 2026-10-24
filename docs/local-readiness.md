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

## What the results mean

- **Archive:** validate the capture manifest, inventory and checksums.
- **Bundle:** validate the `checksums.json` inventory and checksums. This option
  is for that receipt format, not every generated folder in the toolkit.
- **Program:** parse the normalized model, check its structure, and look for
  each sample relative to the XPM or its `Name_[ProgramData]` directory. A
  reference without a suffix also tries `.wav`. No recursive basename search
  is used because that could silently choose the wrong sample.
- **External:** absolute, Windows-style, or escaping paths are not accessed.
  Their availability is unknown, not evidence that the audio was deleted.
- **Missing:** no regular file exists in the allowed lookup locations. MPC
  search behavior may differ; the tool does not claim to emulate the firmware.

Exit codes: 0 means all selected software checks passed; 1 means at least one
failed or needs attention (including external references); 2 means invalid
command usage. JSON has per-input details, overall status, and a separate
`hardware_status: not-evaluated`. A malformed input does not hide other results.

This does not decode audio, check plugin licenses, prove XPJ external-dependency
completeness, or prove generated output matches the latest recipe. A checksum
receipt only proves consistency with that receipt. Regenerate and compare when
recipe freshness matters. Hardware listening remains a separate decision.

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
