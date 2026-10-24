# Capture an idea without losing the version you liked

Use the existing `mpc-project-capture` command for a named musical idea as well
as controlled routing experiments. It copies the selected XPJ and its exact
companion ProjectData folder, verifies every copied file, and records a note.
It never edits the source project or claims that the archive was auditioned.

## Capture one saved project

Preview the selected files and payload size before copying:

```bash
uv run mpc-project-capture "/path/to/SD/Projects" \
  --project "Late Night Groove.xpj" --output work/ideas/take-01 \
  --dry-run --json
```

Dry-run performs no copy, output-directory creation, or checksum verification.
Add `--max-bytes 1073741824` to either preflight or real capture to refuse more
than 1 GiB of project payload. This is a payload limit, not a free-space check;
manifest size, directory overhead, and temporary storage are additional.

Save the project on the MPC first. Stop editing/saving it during the copy and
expose its storage to the computer. Choose a new local folder for every take:

```bash
uv run mpc-project-capture "/path/to/SD/Projects" \
  --project "Late Night Groove.xpj" \
  --note "Keep the swung hats; next try a sparse bass variation" \
  --output "work/ideas/late-night-groove-take-01"
```

Repeat `--project` to capture several distinct saved projects together. Names
are filenames, not paths; ambiguous duplicate filenames below the source are
rejected. Narrow SOURCE to a specific project folder if necessary. A companion
folder belonging to a similarly named project is not substituted.

The output contains unchanged XPJs/ProjectData and `capture-manifest.json`,
including the note, source locations, capture time, file sizes, and SHA-256
checksums. Existing destinations (including empty directories), symlinks, missing companions, and failed
copies are rejected. Copies are prepared and verified in staging before the
archive is published; failed copies leave the source untouched.

Capture inventories and hashes selected files before copying, then checks them
again before publication. Detected edits or additions/removals abort capture.
Stop saving/editing until it finishes: this is not a filesystem-wide lock or
a guarantee against every concurrent edit. Special files such as FIFOs and
sockets are refused rather than read as project data.

## Check the archive later, without the SD

```bash
uv run mpc-project-capture --verify "work/ideas/late-night-groove-take-01"
```

Verification detects changed/missing files, unlisted additions, unsafe manifest
paths, and symlinks. It does not access the original source paths, so the SD
can be disconnected. Keep notes in the manifest as captured; if you add files
inside the archive, strict verification reports them as unlisted. Keep evolving
listening notes beside the archive instead.

Checksums prove consistency with the manifest, not authenticity, musical quality,
or completeness of dependencies stored outside ProjectData. Plugin installations,
licenses, globally referenced samples, and hardware state are not automatically
captured. This is not a replacement for a separate backup of your library.

## Experiment safely

The complete loop is: preflight → capture → inspect/search → restore into a
new experiment folder → make a variation → capture that variation into a new
archive → compare the two archives. Keep the first archive unchanged throughout.
The software regression test exercises this loop through the public commands
using synthetic project bytes; it does not imply MPC load/playback acceptance.

### Find and inspect saved ideas

Generate a private offline browser index when you prefer browsing notes visually:

```bash
uv run mpc-idea-archive list work/ideas --html work/reports/ideas-01.html
```

Open the resulting HTML locally. It provides a search field, notes, paths,
fingerprints, scan warnings, and a recheck command per archive. Nothing is
uploaded; the page cannot inspect your disk or restore files. Verification is
dated at generation time, not live. Regenerate into a new filename after changes.
The output must be outside the archive library and cannot replace an existing
file. Treat it as private because it includes local paths and personal notes.
An invalid archive still produces a report but returns exit status 1. The
browser filter does not hide the full-scan invalid count or scan notices.

```bash
uv run mpc-idea-archive list work/ideas --query "swung hats"
uv run mpc-idea-archive inspect work/ideas/take-01 --json
```

The read-only index verifies every discovered archive before searching its
folder, project names, and note (case-insensitively). Invalid archives and scan
errors are reported even if the query matches only healthy takes; `list` exits
1 when any archive is invalid or a scan fails. Other invalid inputs return the
usual CLI error status 2. Directory symlinks are reported as skipped, not followed.
Large libraries may take time because verification reads all recorded files.

Inspection shows notes, project names, payload size, and `content_sha256`.
The fingerprint hashes sorted relative filenames, sizes, and file hashes; it
does not depend on the archive's location, capture time, or musical note.
Renaming payload files changes the fingerprint. It is an integrity identity,
not a signature or musical similarity score.

### Restore an independent experiment copy

```bash
uv run mpc-idea-archive restore work/ideas/take-01 \
  --output work/experiments/take-01-variation --dry-run
uv run mpc-idea-archive restore work/ideas/take-01 \
  --output work/experiments/take-01-variation
```

Restore requires a new directory, refuses nested/overlapping destinations and
symlinks, copies rather than hardlinks files, verifies staging, then publishes
the copy. The original archive is never edited. A failed ordinary copy leaves
no published experiment. Do not edit the archive or destination during restore,
or disconnect storage; the operation is not a power-loss or concurrency lock.

The restored copy includes the original manifest and initially verifies. Once
you edit the experiment its old manifest will correctly report changed files.
Capture the newly saved XPJ into a new archive to establish a new record; do not
rewrite the original archive's checksums to disguise edits. Restore does not
install plugin licenses or gather external sample dependencies.

### Compare takes

Compare two verified archives without changing either:

```bash
uv run mpc-project-capture --compare work/ideas/take-01 work/ideas/take-02
uv run mpc-project-capture --compare work/ideas/take-01 work/ideas/take-02 --json
```

Both archives must pass verification first. The report lists added, removed,
changed, and unchanged files by exact relative path, and JSON includes each
take's note. Different filenames appear as additions/removals, not inferred
renames. This is a byte-level inventory comparison, not an interpretation of
MPC tracks, notes, or sound. Different capture notes alone do not mark project
content as changed. Reports go to stdout; no archive files are edited.
JSON also includes total byte delta and before/after sizes and hashes for each
changed file, plus each archive's content fingerprint.

1. Preserve the take you like as a snapshot.
2. Use Save As on the MPC for the next variation; do not overwrite your favorite.
3. Capture that new save to another folder with a note describing the change.
4. Verify both archives whenever you copy them to another drive.

The original baseline/changed routing workflow remains supported. Do not mix
`--project` with `--baseline`/`--changed`; use `--changed-setting` only when a
specific controlled change is actually being recorded. Capturing an idea does
not fabricate a Drum Split experiment or a hardware pass.

Keep sample-bearing archives in ignored/private storage, not in Git. No new
hardware acceptance session is required to validate this command's copy and
integrity behavior; tests use synthetic project files.
