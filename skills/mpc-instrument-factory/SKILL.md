---
name: mpc-instrument-factory
description: "Build, inspect, document, or deploy MPC Keygroup and Drum Program workflows in this repository. Use for XPM programs, semantic pad layouts and colors, creative MIDI, MPC/Launch Control/Volca maps, SD deployment, catalog work, or MPC hardware acceptance evidence."
---

# MPC Instrument Factory

Use the repository's maintained tools and evidence boundaries instead of
inventing MPC schemas or treating generated output as hardware-tested.

## Begin safely

1. Run `git status --short` and preserve all existing user changes.
2. Read `docs/index.md`, then open only the guide for the active workflow.
3. Run `mpc-tools commands` or the leaf command's `--help` before composing a
   new invocation.
4. Locate source audio, templates, generated artifacts, and mounted media with
   read-only checks before writing.

## Route the task

- For installation, command discovery, or user-facing failures, use
  `docs/getting-started.md`, `docs/cli-reference.md`, and
  `docs/troubleshooting.md`.
- For pitched WAV conversion, use `docs/keygroup-building.md` and
  `docs/keygroup-range-inference.md`.
- For Drum Programs, colors, pad roles, layouts, and variants, use
  `docs/program-model-and-layouts.md`, `docs/catalog.md`, and
  `docs/keygroup-variants.md`.
- For generative sequences, use `docs/creative-midi.md` and
  `docs/drum-ideas.md`. Use `docs/composition-showcase.md` for the
  redistributable six-composition proof, and run `mpc-recipe-audit` before
  generating a library-wide batch. Use `docs/creative-wave.md` and
  `mpc-workstation-wave` for multi-family generation and offline shortlisting.
- For declarative formats, semantic validation, or editable recipe starters,
  use `docs/schemas.md`, `mpc-schema`, and `mpc-tools new`.
- For MPC, Launch Control XL 3, or Volca routing, use
  `docs/declarative-midi-control.md` and `docs/rig-profiles.md`.
- For plugin parameter discovery, performance-page seeds, controller capacity,
  the offline companion, and result imports, use `docs/plugin-mapping.md`.
- For SD copies and hardware evidence, use `docs/hardware-workflow-tools.md`
  and `docs/key37-routing-capture.md`.

## Preserve the evidence boundary

- Never commit licensed WAVs, generated sample-bearing XPMs, XPJ captures, or
  vendor PDFs. Use ignored local storage, mounted media, or an external drive.
- Treat sample licenses separately from code licensing. Record source URL,
  license, download date, hashes, attribution, and redistribution status.
- Preserve the source program and template. Create named variants and refuse
  ambiguous overwrite operations.
- Use dry runs, explicit destinations, checksums, staging, and verification for
  deployment. An SD card is a target, not the only canonical copy.
- Mark hardware `pass` only from human listening on the device. Software
  validation, a successful copy, and a successful load are separate evidence.
- Do not guess undocumented XPJ, SysEx, or MIDI behavior. Use official charts,
  declared assumptions, and paired before/after captures.

## Verify proportionally

Run focused unit tests during development, then before handoff run:

```bash
uv run python -m unittest discover -s tests -v
uv run mpc-repository-guard
uv build
git diff --check
```

For command UX changes, also verify `-h`, `--help`, `--version`, one expected
failure, and an installed-tool run from outside the repository. Report software
and hardware status separately and include absolute hardware-test paths.
