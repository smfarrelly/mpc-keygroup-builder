# Troubleshooting

## `mpc-tools: command not found`

Run `uv tool update-shell`, close the terminal, and open a new one. Confirm that
`uv tool list` includes `mpc-keygroup-builder`. In a developer checkout, use
`uv run mpc-tools ...` instead.

## Python is missing or too old

Use `uv tool install --python 3.12 ...`. `uv` downloads and isolates a supported
runtime; you do not have to replace the operating system's Python.

## A file cannot be found

Use an absolute path, especially on removable media. On Linux, `findmnt` shows
the mounted source and destination. File names are case-sensitive on many
systems. Quote paths that contain spaces:

```bash
mpc-xpm inspect "/media/user/CARD/Programs/My Program.xpm"
```

## An SD card is read-only

Stop before copying. Unmount it, run the filesystem-specific repair tool, mount
it again, and confirm the mount options contain `rw`. Verify the exact block
device first; never infer it from an earlier session. Keep a canonical computer
or external-drive copy because removable media is a deployment target, not the
only source of truth.

## The output already exists

Builders refuse accidental replacement. Choose a new output directory or read
the command's help to see whether it offers a narrowly scoped `--force` option.
Do not delete a working program until the replacement has passed software and
hardware checks.

## A sample name is not recognized

Pitched Keygroups need parseable note labels in the file names. Drum color and
role inference uses semantic words such as kick, snare, clap, closed hat, and
tom. Rename a working copy or use the workflow's explicit override/manifest
field; preserve the original audio.

## A template is rejected

Use an XPM saved by the target MPC software family and verify that its program
type matches the requested build. Type selection is validation, not a way to
turn a Keygroup schema into a Drum Program schema.

## Software passes but hardware behaves differently

Record a warning in the listening ledger rather than changing software evidence
to `pass`. Note the MPC OS version, exact program path, track type, MIDI input,
pad bank, keyboard transpose, and save/reload result. The field-review and
routing-capture guides preserve those observations.

## I need the Python traceback

Friendly errors suppress tracebacks for expected user mistakes. Re-run exactly
the same command with debugging enabled:

```bash
MPC_DEBUG=1 mpc-drum-build ...
```

Include the command, traceback, operating system, and `mpc-tools doctor` output
in a bug report. Do not attach licensed samples or private project captures.
