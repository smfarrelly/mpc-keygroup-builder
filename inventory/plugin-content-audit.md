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
