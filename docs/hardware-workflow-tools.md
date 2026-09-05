# Reusable MPC hardware workflow

These tools turn MPC program preparation into repeatable evidence while keeping
commercial audio and hardware captures outside Git. They do not substitute for
listening on the MPC Key 37.

## Candidate and listening session

```bash
uv run mpc-scratchpad-check inventory/scratchpad-candidates.toml \
  --ledger inventory/program-status.csv --json
uv run mpc-hardware-init inventory/program-status.csv \
  inventory/scratchpad-candidates.toml --output work/key37-hardware-results.toml
uv run mpc-hardware-results inventory/program-status.csv \
  work/key37-hardware-results.toml
uv run mpc-hardware-results inventory/program-status.csv \
  work/key37-hardware-results.toml --apply
```

The first results command is a dry run. A pass or warning requires concise
listening notes. The readiness checker keeps deployment, all-candidate hardware
testing, selected core viability, and final favorite selection as separate
gates. Deployment is reported as `NOT CHECKED` unless `--sd-root` is supplied;
an omitted card path is never treated as a pass.

## Maps, program diffs, and audio triage

```bash
uv run mpc-drum-map "/path/to/kit.xpm" --format markdown --output work/kit-map.md
uv run mpc-xpm inspect "/path/to/program.xpm"
uv run mpc-xpm compare before.xpm after.xpm
uv run mpc-audio-levels artifacts/auditions --output work/levels.json
```

The XPM comparison normalizes the fields we currently understand across legacy
XML and MPC 3 compressed formats. Unknown fields remain visible in same-format
structural comparisons. Level flags are triage signals, not mastering targets.

## Safe SD-card delta deployment

Candidate manifest fields `id`, `ledger_path`, `sd_path`, and `role` must be
nonempty strings; `selected` must be a boolean. Validation errors identify the
candidate number and field before any SD-card operation begins.

Always preview first:

```bash
uv run mpc-sd-deploy inventory/scratchpad-candidates.toml \
  --local-root "/path/to/local/sd-image" \
  --target-root "/media/$USER/MPC_SD" \
  --report work/sd-deploy-plan.json
```

Add `--include-audio` only when the licensed companion data really must be
copied. Apply with both `--apply` and a backup directory whenever any target
would be replaced:

```bash
uv run mpc-sd-deploy inventory/scratchpad-candidates.toml \
  --local-root "/path/to/local/sd-image" \
  --target-root "/media/$USER/MPC_SD" \
  --include-audio --backup-dir "/path/to/dated-backup" --apply \
  --report work/sd-deploy-applied.json
```

The deployer is additive: it does not remove unrelated card content. Each copy
uses a temporary file, SHA-256 verification, and atomic replacement. An
existing changed target is backed up and verified before replacement.

### Transaction-safe self-contained packages

Use `mpc-package-deploy` when the source is already a complete package folder
containing its XPM and copied audio. Preview the exact inventory and aggregate
package digest first:

```bash
uv run mpc-package-deploy \
  "work/generated-drum-programs/FG Vinyl Kit Banks 01" \
  "/media/$USER/MPC_SD/01 FG Favorites/04 Drum Alternates/03 FG Vinyl Kit Banks 01" \
  --report work/package-deploy-plan.json
```

Apply only when the action is `CREATE`:

```bash
uv run mpc-package-deploy \
  "work/generated-drum-programs/FG Vinyl Kit Banks 01" \
  "/media/$USER/MPC_SD/01 FG Favorites/04 Drum Alternates/03 FG Vinyl Kit Banks 01" \
  --apply --report work/package-deploy-applied.json
```

Apply runs a temporary 64 MiB sustained write/read/hash/delete probe by
default. Set `--probe-mib 0` only when another write test has already passed.
Files are copied and fsynced into a hidden sibling staging directory, verified
individually, then promoted with one same-filesystem rename. A disconnect
leaves the final destination absent and the stage available for inspection.
After reconnecting and repairing the filesystem, rerun the same command with
`--apply --resume`; verified staged files are reused and incomplete files are
replaced. Unexpected stage files, symbolic links, and changed final
destinations are refused rather than deleted or overwritten.
The canonical source, hidden staging directory, and final destination must be
separate trees. The command rejects identical or nested paths before creating
any deployment files, preventing recursive copies into the source package.

## Controlled Key 37 routing capture

On the MPC, save exactly `Key37_Routing_Baseline.xpj` and
`Key37_Routing_Changed.xpj`, each with its companion ProjectData folder. Change
one named routing setting only. Then run:

```bash
uv run mpc-routing-capture "/media/$USER/MPC_SD/Projects/FG Scratchpad Routing Tests" \
  --output work/key37-routing-captures/session-001 \
  --inspector-root work/mac-xpj-inspector \
  --changed-setting "Key Ranges: Drum Split"
```

The destination must be new or empty. The tool verifies every copied file,
records source provenance, runs the detached `mac/xpj-inspector` worktree, and
writes inspect and comparison JSON beside the untouched capture. XPJ files and
ProjectData folders are deliberately ignored and rejected by the repository
guard.

## What remains a hardware test

Computer checks can establish readable structure, resolvable samples,
consistent colors, likely choke behavior, and exact save-file differences.
Only hardware listening can establish sound quality, useful keyboard range,
velocity feel, perceived level, pad/keyboard routing, controller pickup, MIDI
clock behavior, and whether a setup is enjoyable to play.
