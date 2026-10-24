# Find local instruments without guessing their identity

Your listening ledger may use SD paths while your laptop library has a different
layout. Reconciliation finds possible local XPM locations without changing the
ledger, programs, WAV references, or hardware verdicts.

```bash
mpc-tools reconcile --ledger inventory/program-status.csv \
  --library-root "/path/to/local/instruments" --favorite yes \
  --verify-samples --output work/reports/favorites-01.json
```

Choose a specific instrument directory, not your entire home or filesystem.
Repeat `--library-root` for separate libraries; overlapping roots are rejected.
The command never discovers drives, follows child symlinks, copies audio, or
repairs references. It scans filenames first; `--verify-samples` explicitly
enables read-only inspection of matching candidates. It does not decode WAVs.

## Understand the result

- **candidate**: one same-name XPM, with an exact relative path or at least two
  matching trailing path components (for example collection + filename).
- **name-only**: a same-name file in a different folder; this is weak evidence.
- **ambiguous**: multiple same-name files, even if one has a better path match.
  Nothing is silently selected or discarded.
- **missing**: no same-name XPM in the selected roots; it might exist elsewhere.
- **unsafe-ledger-path**: an absolute, parent-traversing, or nonportable path was
  not used for matching.

Case-insensitive matching helps compare FAT-style paths with Linux libraries;
case-differing duplicates are still ambiguous. Names and paths do **not** prove
content identity with a previously tested or deployed instrument.

Each candidate separately records sample status: `not-checked`, `pass`, `warn`,
or `fail`. A sample pass means the bounded program-relative / companion lookup
resolved the references and the normalized model validated. It does not mean
the sound was heard, that WAV audio is valid, or that the MPC can load it.
Historical listening notes are retained verbatim, not applied to a new copy.

## Reports and limits

`--json` prints structured evidence. `--output` saves the same evidence to a new
private JSON file outside the input libraries. Existing files are never replaced.
Unmatched local programs, scan errors, and skipped symlinks remain visible.
The default selection includes every ledger row; `--favorite yes` limits it to
confirmed favorites. Unmatched means outside this selection, not safe to delete.

Scans stop with an actionable error above 250,000 entries or 20,000 XPMs. Each
ledger row displays at most 20 candidates, with the full count and an explicit
truncation flag. Narrow the roots to resolve uncertainty. A partial/limited scan
is never presented as an exhaustive successful inventory.

Exit 0 means no issues detected for the selected rows, not hardware acceptance.
Exit 1 means attention: missing/ambiguous/weak matches, sample issues, skipped
symlinks, or scan errors. Invalid inputs use the standard CLI error status.

Keep reports private: they contain personal notes, file locations, and sample
names. No audio or project payload is embedded. Do not use them as deletion or
deployment manifests; review the actual instrument before copying it.
