# MPC helper-project compatibility survey

Surveyed 2026-08-23. This is an engineering and licensing triage, not legal
advice. Repository state and licenses can change, so verify the upstream commit
and license before importing code.

## Executive summary

No surveyed project replaces `mpc-keygroup-builder`. The closest projects concentrate on
drum programs or MPC Sample projects, while `mpc-keygroup-builder` builds and validates MPC
3.9 JSON keygroup programs from licensed multisample libraries.

The most useful upstream references are:

1. `MPC-project-file-definitions` for modern XPJ schema research.
2. `mpcsample-kit-converter` for batch UX and XPJ-template architecture.
3. `MPC-Sample-Toolkit` for a packaged parser/writer API and test layout.
4. `Compa` for device profiles, transfer boundaries, and drum classification.
5. `mpckitcreator` as historical evidence for XML drum-XPM generation.

Only independently verified format facts should enter `mpc-keygroup-builder` tests. Keep an
upstream URL and observed firmware/version beside each derived compatibility
fixture. Do not copy code or templates from an unlicensed repository.

## Project findings

### MPC-project-file-definitions

- Repository: <https://github.com/kurtjcu/MPC-project-file-definitions>
- Scope: reverse-engineered MPC 3.7+ gzip/JSON XPJ projects, including tracks,
  programs, keygroups, samples, events, effects, routing, and automation.
- Evidence base: its documentation says it was derived from 18 real projects
  and warns that some conclusions are unconfirmed.
- Tests/tooling: analysis reports and example objects rather than a reusable
  parser test suite.
- License: no license file or license declaration was visible in the surveyed
  repository. Default copyright therefore applies.
- Decision: use as a research index only. Reconfirm every field against our own
  device-generated fixture before implementing it. Do not copy its examples or
  prose into source fixtures.
- High-value future use: XPJ project templates, track/event construction,
  effect/routing validation, and MPC 2.x versus 3.x format detection.

### mpcsample-kit-converter

- Repository: <https://github.com/ab1428x/mpcsample-kit-converter>
- License: MIT.
- Scope: converts XML drum XPMs and optional SXQ demo sequences from installed
  expansions into self-contained JSON XPJ projects for MPC Sample.
- Architecture: one standard-library Python script; device-exported XPJ used as
  a schema template; adjacent `_[ProjectData]`; single, expansion, and all-pack
  modes; filtering, dry-run, overwrite control, optional WAV copying, and
  parallel workers.
- Tests/tooling: no test directory or CI workflow was visible in the surveyed
  repository. Its README describes device testing and template requirements.
- Decision: do not make it a dependency. Adopt the command separation and batch
  reporting concepts through independent implementation. Consider interoperable
  manifest fields for layer play mode, mute group, BPM, and demo sequence later.
- Important distinction: its source XPMs are older XML drum programs; ours are
  MPC 3.9 gzip/JSON keygroup programs.

### MPC Sample Toolkit (MPCTK)

- Repository: <https://github.com/tarikcampos/MPC-Sample-Toolkit>
- License: MIT.
- Scope: early-stage XPJ reader/writer, project explorer, chromatic instrument
  generator, batch editor, scale generator, and chord generator.
- Architecture: `src`, `tests`, `docs`, `examples`, changelog, and contribution
  guide; structurally closer to a reusable Python package than the one-file
  converters.
- Status: explicitly marked early development by its author.
- Decision: watch for stable parser/writer abstractions and compare round-trip
  behavior. Avoid a dependency until its schema coverage and compatibility are
  demonstrated with the MPC 3.9 Key 37 fixtures we use.
- High-value future use: possible interoperability for XPJ QA templates and
  chromatic test sequences.

### Compa

- Repository: <https://github.com/macdigi/compa>
- License: MIT.
- Scope: Raspberry Pi touchscreen workflow for several samplers. Its MPC/Force
  support covers XML drum-XPM export and USB mass-storage transfer.
- Architecture: separated engine, UI, device profiles, format conversion,
  storage transfer, docs/templates, and tests. Its README recommends stubbing
  hardware interfaces for unit testing.
- Decision: borrow the boundary design, not the application: build artifacts
  independently, represent devices as profiles, and keep installation behind an
  explicit operation. Smart drum-name classification may be useful when drum
  support is added.
- Caution: its bundled golden XPM template is an upstream artifact. Do not copy
  it into this repository without checking provenance; our own synthetic or
  user-supplied MPC-generated templates remain safer.

### MPC Kit Creator

- Repository: <https://github.com/BlackCursive/mpckitcreator>
- License: no license file or license declaration was visible in the surveyed
  repository. Default copyright therefore applies.
- Scope: Python/SoundFile/BeautifulSoup utility that creates and inspects XML
  drum XPM programs for MPC Live/One/X.
- Architecture: small scripts plus a Python template module; no package metadata,
  test directory, or CI workflow was visible.
- Decision: historical/reference value only. Do not copy code or templates.
  Our standard-library WAV reader, synthetic fixtures, JSON serializer, and
  stronger validator already cover the relevant concepts more safely.

## What `mpc-keygroup-builder` should adopt

### Now

- Keep device-generated templates external and gitignored.
- Make format/profile identity explicit: object kind, serializer, firmware
  family, platform header, maximum layers, and known device validation.
- Add declarative manifests with source-relative paths rather than local absolute
  paths.
- Separate `inspect`, `build`, `validate`, and `install`; installation must never
  be an implicit consequence of building.
- Produce a machine-readable build report containing input checksums, template
  checksum, generated files, mapping summary, warnings, and tool version.
- Continue refusing overwrite by default and validate staged output before any
  removable-media operation.

### Next

- Add fixture-based round-trip tests for both JSON XPM and, later, JSON XPJ.
- Add a profile compatibility test that rejects the wrong serializer/object
  type instead of accepting any gzip/JSON file with an ACVS header.
- Add stereo-pair and per-note velocity-schema manifests; never guess ambiguous
  left/right or layer assignments.
- Build the `Multisample Test` XPJ locally from a user-generated MPC 3.9 project
  template, with sequences covering note boundaries and velocity transitions.
- Add pack-level inspection and reports before parallel batch builds.

### Later

- Drum-program manifests and filename classification.
- SXQ/demo-sequence research.
- XPN assembly after independently documenting archive metadata and validating
  it through Akai's supported desktop import/export workflow.
- Optional adapters to other projects only when their APIs stabilize and a real
  interoperability benefit outweighs another dependency.

## Explicit non-goals

- Firmware modification, SSH firmware, or runtime process injection.
- Redistributing licensed WAVs, factory projects, or third-party templates.
- Treating undocumented fields from a single upstream corpus as authoritative.
- Installing directly to mounted MPC media during `build`.
- Using Git LFS as a way to publish commercial sample content.

## Provenance policy for external findings

For every external format claim promoted into implementation:

1. Record the upstream repository URL and commit identifier in the research
   note or issue.
2. Reproduce the field in a locally generated device file where possible.
3. Encode the smallest synthetic regression fixture that proves the behavior.
4. Mark device model, firmware version, serializer (`xml` or `json`), and object
   kind (`SerialisableProgramData` or `SerialisableProjectData`).
5. Keep copyrighted factory/user payloads outside Git.

