# When a storage operation fails

The command line reports `ERROR`, a contextual `NEXT` step, and an optional debug
hint. Expected storage failures return status 2 without a Python traceback.
Ctrl-C returns status 130 with a reminder to verify any output before retrying.
No automatic retry, remount, filesystem repair, or deletion is attempted.

- **Full disk or quota:** preserve the source and inspect staging. Make space
  before retrying; do not assume an incomplete copy is usable.
- **Read-only storage:** confirm you selected the intended destination and
  investigate its health. Do not blindly remount a possibly damaged card.
- **Unsupported filesystem operation:** use supported local storage. Publication
  does not fall back to an overwriting rename.
- **Different filesystems:** staging and final publication must stay on the
  same filesystem. Review the paths rather than forcing a move.
- **Other I/O failures:** stop, preserve the originals, and inspect outputs and
  connections. A missing or incomplete destination is not proof of source loss.

Capture/restore clean only their own staging on handled failures before
publication. Package deployment deliberately retains staging for an explicit
`--resume` after review. A failure or interruption after publication can leave a
complete final output; verify it before choosing a new destination or retrying.
Forced process termination/power loss can leave staging behind. Unknown staging
folders may belong to earlier work: do not delete them automatically.

`MPC_DEBUG=1` retains the original exception/traceback for diagnosis. Debug logs
can include private paths; review them before sharing. See
[idea snapshots](idea-snapshots.md), [publication safety](archive-publication-safety.md),
and [package deployment](hardware-workflow-tools.md) for operation-specific rules.
