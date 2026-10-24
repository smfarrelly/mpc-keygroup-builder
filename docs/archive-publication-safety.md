# Capture and restore publication safety

Capture and restore copy into an owned sibling staging directory, verify it,
and publish the completed directory under a new name. The final operation uses
an exclusive rename: if another file, directory, or symlink appears at the
destination while copying, it is not replaced—even if the directory is empty.

**Behavior change after v0.1.0:** capture now requires a nonexistent output
directory. An existing empty directory is preserved, not removed. Choose a new
name; you do not need to delete the old directory.

On ordinary errors and Python interruptions such as Ctrl-C before publication,
only the operation's own staging directory is cleaned up. Original projects,
archives, and unrelated staging-looking folders remain untouched. If interruption
occurs after publication, a complete output may already exist: verify it before
retrying. A forced process kill, power loss, or device disconnect can leave
staging behind; do not assume unknown staging folders are safe to delete.

## Platform implementation and limits

- Linux uses `renameat2` with `RENAME_NOREPLACE`, which refuses an existing
  destination. [Linux rename documentation](https://man7.org/linux/man-pages/man2/rename.2.html).
- macOS uses `renamex_np` with `RENAME_EXCL`. The flag and function signature
  are defined in [Apple's published system header](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/stdio.h).
- Windows uses `os.rename`, whose documented Windows behavior refuses an
  existing destination. [Python os.rename documentation](https://docs.python.org/3/library/os.html#os.rename).

The Linux path is exercised on the development machine. macOS and Windows
adapters have mocked contract tests, not live platform acceptance. Filesystems
or platforms without exclusive rename support fail closed with an error;
there is no fallback to an overwriting rename. Choose supported local storage.

The `archive-platforms` GitHub Actions workflow installs a built package on
Linux, macOS, and Windows and exercises native publication plus the installed
capture/restore/recovery commands using disposable synthetic data. Read its
actual results before claiming platform coverage. A passing job covers that
runner's local filesystem, not an SD card, network share, or every command.

This is not a power-loss durability or hostile-filesystem security guarantee.
It does not lock the original project against concurrent saves. Keep the source
and destination parents stable during capture/restore. Checksums validate the
copied file bytes, not external sample/plugin completeness or MPC playback.

## Reproducible recovery stress tests

```bash
python scripts/archive_recovery_matrix.py --output work/recovery-quick.json
python scripts/archive_recovery_matrix.py --full --output work/recovery-full.json
```

The quick run exercises seven scenarios. The full run has 840 combinations:
0/1/16/128/1024 companion files per project, three payload sizes, one/two projects,
four filename styles, and seven healthy/fault modes. It verifies source retention,
independent variations, exact comparisons, interruption cleanup, tamper refusal,
and preservation of concurrent destinations. No actual musical projects or audio
are read. Each disposable case is removed before the next; low temporary disk
space stops the run with an incomplete report rather than claiming success.

Reports checkpoint every 20 cases and separate completeness from pass/fail counts.
Choose a new report filename; reports contain synthetic test evidence, not new
hardware listening results. A failed case must be investigated, not relabeled.
