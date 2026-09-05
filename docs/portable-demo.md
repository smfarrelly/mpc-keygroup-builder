# Portable MPC workflow demo

`mpc-portable-demo` is a complete public acceptance fixture for musicians who
do not own the project's licensed sample libraries. It creates its WAVs from
deterministic mathematical synthesis and labels the generated audio CC0-1.0.
The repository source remains MIT licensed.

```bash
uv run mpc-portable-demo --output work/fg-portable-demo
```

The command refuses an existing destination and builds in a sibling temporary
directory. The final folder appears only after all stages succeed.

Verify the complete receipt after generation, copying, or moving the folder:

```bash
uv run mpc-portable-demo --verify work/fg-portable-demo
```

Verification is read-only. It rejects missing, changed, unrecorded, or unsafe
receipt paths, reruns the cross-kit software simulation, and confirms that
hardware status remains deferred. It shares its byte-integrity checks with
`mpc-bundle-verify`, which can verify any generated project bundle containing a
complete `checksums.json` receipt.

Paths recorded inside the bundle are relative to its root. Identical inputs
therefore produce byte-identical bundles in different destination directories,
and moving a bundle does not leave stale computer-specific paths in its evidence.

## Included workflow

- 16 mono 44.1 kHz synthetic drum and percussion WAVs;
- an editable source manifest and 128-pad legacy XML Drum template;
- a self-contained, color-coded source Drum Program;
- an audio-enriched catalog containing measurements rather than claims;
- a deterministic semantic cross-kit recipe, selection, and staged-audio set;
- a second self-contained Drum Program with MPC Bank A note mapping;
- a four-track Drums/Bass/Chords/Melody Standard MIDI idea;
- Main, Main B, Breakdown, Build, and Outro MIDI variants;
- complete JSON provenance, software acceptance, and SHA-256 checksums;
- one full-path MPC hardware checklist.

The Bass, Chords, and Melody MIDI tracks intentionally name generic program
roles. A user assigns any locally owned MPC programs; no proprietary preset is
required. The Drum Program and MIDI artifacts can be copied to removable media
for testing, but hardware behavior is never promoted from deferred to pass by
the generator itself.

## Reuse

Edit the included TOML recipes, replace the source WAVs with files you may
legally use, or point the normal catalog/kit-wave commands at a larger local
library. `checksums.json` provides a stable receipt for the delivered demo;
verify it after a copy, and regenerate into a new destination after making
changes rather than overwriting the original evidence.
