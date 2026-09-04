# MPC plugin content audit

## SD snapshot — August 27, 2026

The reusable command below scanned the mounted card without modifying it:

```bash
uv run mpc-plugin-audit "/media/steve-farrelly/3561-6538/Synths" \
  --format markdown \
  --output work/sd-plugin-content-audit.md
```

The `Synths` directory contains 14 top-level content directories, 1,947 files,
962 `.xpl` presets, and 177,090,208 logical bytes. ExFAT allocation reports
approximately 398 MiB on disk.

Strong preset/content evidence:

- Iona: 104 presets; no `version.xml` marker in its content directory.
- OPx-4: 672 presets and 68 additional `Content` files; no `version.xml` marker.
- AIR Flavor Pro: 101 presets; content marker version `1.0.0.0`.
- AIR Chorus: 33 presets; version `1.0.0.0`.
- AIR Multitap Delay: 19 presets; version `1.0.0.0`.
- AIR Vintage Filter: 21 presets; version `1.0.0.0`.
- AIR Expander: 11 presets; no `version.xml` marker.
- Trigger FX: one preset plus UI content; no `version.xml` marker.

Asset/UI evidence without standalone preset files is also present for Color
Compressor, Tape Emulator, Vintage, and Vinyl Emulator.

No matching plugin-content directories were found for Jura, Mini D, Studio
Strings, or Fabric/Fabric Collection. Files whose names contain `Jura` under
`Features/.../FactoryOscillators` are generic wavetable/single-cycle assets and
must not be treated as proof that the Jura plugin is installed.

Subsequent on-device status clarifies the filesystem result: Fabric and Jura
are installed on MPC internal storage, so they are not expected in this SD-only
audit. Mini D and Studio Strings are not purchased and remain deferred.

## Interpretation boundary

Content on the SD supports the conclusion that presets/assets have been
downloaded. It does not prove that the executable plugin is present in internal
storage, licensed/activated, visible in the Plugin selector, playable, or
restored with a project. Those remain on-device checks.

For Iona, OPx-4, and AIR Flavor Pro:

1. Create the appropriate Plugin or insert-effect slot.
2. Confirm the plugin appears by name.
3. Load at least the Init preset and one musical preset.
4. Save a small disposable project, power-cycle, reload, and confirm the plugin,
   preset, and edited parameter return.
5. Record whether it earns a reusable Scratchpad role.

## Parameter metadata audit — September 3, 2026

The SD content contains readable `Plugin Skins/*.json` UI metadata for 12
plugin/effect directories. The read-only `mpc-plugin-params` scanner finds 401
meaningful visible controls across those directories. OPx-4 contributes 145
controls and 672 presets. Cross-referencing `Boot.xpj` verifies 33 OPx-4
control-to-MPC-parameter IDs and their learned channel/CC pairs.

This exposes a materially better performance shortlist than the MPC's long
undifferentiated target list. In particular, OPx-4 Filter Cutoff 1/2, Filter
Resonance 1/2, and Filter Drive 1/2 are present in the UI metadata and have
Q-Link locations, but are not part of the 33 currently learned OPx-4 controls.
They are strong candidates for a focused tone page.

Jura remains different: its content is internal-only and unavailable to this
filesystem scan, but `Boot.xpj` preserves 36 named, verified Jura MIDI Learn
assignments. A complete Jura catalog requires either its readable plugin
content or additional MPC-authored capture evidence.
