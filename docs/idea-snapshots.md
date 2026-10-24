# Capture an idea without losing the version you liked

Use the existing `mpc-project-capture` command for a named musical idea as well
as controlled routing experiments. It copies the selected XPJ and its exact
companion ProjectData folder, verifies every copied file, and records a note.
It never edits the source project or claims that the archive was auditioned.

## Capture one saved project

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
checksums. Nonempty destinations, symlinks, missing companions, and failed
copies are rejected. Copies are prepared and verified in staging before the
archive is published; failed copies leave the source untouched.

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
