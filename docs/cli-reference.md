# CLI reference

`mpc-tools` is the stable front door for discovery. It keeps the specialist
commands independently scriptable without asking a new user to memorize them.

```bash
mpc-tools commands
mpc-tools commands --category "Creative MIDI"
mpc-tools help mpc-drum-build
mpc-tools doctor
mpc-tools resume
mpc-tools --version
```

Every installed command accepts `-h`, `--help`, and `--version`. Help exits with
status 0. Expected path, permission, parse, and validation errors return status
2 with an `ERROR`, a suggested `NEXT` action, and an opt-in debugging hint.
Set `MPC_DEBUG=1` to see the original Python traceback.

## Workflow categories

- **Start here:** installation diagnosis and the portable demo.
- **Build:** Keygroups, Drum Programs, program colors, and conversions.
- **Inspect:** XPM, XPJ, Ableton, WAV-level, and semantic validation.
- **Layout:** deterministic plans, XPM export, verification, and packages.
- **Creative MIDI:** drums, harmony, melody, workstations, arrangements,
  bounded idea batches, and multi-family review waves.
- **MIDI control:** declarative maps, role-based plugin page compilation,
  read-only Launch Control capture inspection, plugin-parameter search, and MPC
  MIDI Learn cross-checking.
- **Catalog:** normalized program inventory and deterministic kit selection.
- **Hardware:** listening ledgers, Scratchpad gates, rig reports, and captures.
- **Deploy:** additive, transactional copies to removable storage.
- **Browser:** self-contained Program Designer pages, plugin-mapping companions,
  and the synthetic demo.
- **Reference:** licensed personal-copy document caching, packaged schemas, and
  semantic validation.

`mpc-tools commands --json` is the machine-readable catalog. It includes the
focused documentation file for every command.

## Argument conventions

New user-facing workflows use explicit long options and `--output` for one
destination. Booleans use positive names such as `--dry-run`, `--json`, and
`--force`. Paths may be relative, but absolute paths are clearest for mounted
SD cards and external drives.

The original specialist commands evolved before the umbrella interface, so
some retain compatible positional outputs, `--output-dir`, `--output-prefix`,
or paired JSON/CSV destinations. Their `--help` output is authoritative. Those
forms are intentionally retained so existing scripts do not break; new aliases
should be additive and old forms should receive a documented deprecation period
before removal.

## Safe output behavior

Builders normally refuse to replace a populated output directory. Deployment
commands separate planning from applying and verify hashes. Inspectors and
audits are read-only unless their help explicitly names an output. A `--force`
flag, where present, applies only to the command's named output—not source
audio.

## Useful first commands

```bash
mpc-tools doctor
mpc-tools new workstation --name "My Scratchpad" --output my-scratchpad
mpc-tools demo --output my-mpc-demo
mpc-showcase --output my-mpc-showcase
mpc-workstation-wave recipes --families all --seeds-per-family 4 --output my-wave
mpc-tools web-demo --output program-designer-demo.html
mpc-tools help mpc-drum-build
mpc-schema list
```

See [Troubleshooting](troubleshooting.md) for common recovery steps and the
[documentation map](index.md) for task-specific examples.
