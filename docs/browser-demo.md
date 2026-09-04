# Offline browser demo

`site/index.html` is the no-install entry point. Open it directly from a local
checkout or downloaded archive; it does not need a web server or internet
connection.

The included Program Designer demo can:

- inspect two synthetic program models;
- switch between the built-in MPC Key 37 and Key 61 device views;
- compare three semantic pad-layout candidates;
- move pad assignments and edit labels;
- undo local edits; and
- download a layout-draft JSON file.

The included Plugin Mapping Companion can:

- display all nine proposed Launch Control XL 3 plugin pages;
- show the exact slot, MIDI channel, CC, target, role, and evidence for each
  assigned control;
- guide a create-mode, one-probe, and save/reload workflow;
- retain pass/warn/fail results and notes in local browser storage; and
- export or import matching JSON results and export a flat CSV ledger.

It cannot:

- read an arbitrary XPM from your computer;
- play or analyze WAV files;
- export a finished, hardware-ready XPM;
- browse or write an SD card; or
- validate sound by listening on MPC hardware.

Those limits are intentional. A standalone HTML file does not receive broad
filesystem access, and finished exports should pass the same schema and
preservation checks as command-line builds.

## Generate another copy

```bash
mpc-tools web-demo --output program-designer-demo.html
```

Use `--force` only to replace that named HTML output. The generated file has no
remote JavaScript, font, analytics, or API dependency and contains synthetic
metadata only.

Generate a companion from installed plugin UI metadata and the declarative
profiles:

```bash
mpc-plugin-companion midi/plugins/*.toml \
  --synth-root "/media/user/CARD/Synths" \
  --project "/media/user/CARD/Projects/Boot.xpj" \
  --output plugin-mapping-companion.html
```

The resulting file embeds only the selected mapping metadata. It never embeds
presets, plugin state, audio, source paths, XPJ data, or SysEx bytes. Browser
progress is keyed to a mapping fingerprint so an import from a different
profile revision is refused rather than silently misapplied.

For real programs, first normalize them with `mpc-program-model`, prepare a
designer data set with `mpc-program-designer`, edit a downloaded draft, and
validate/export it with `mpc-layout-draft` and `mpc-layout-export`. See
[Program Designer](program-designer.md).
