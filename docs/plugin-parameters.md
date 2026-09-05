# Plugin parameter catalog

`mpc-plugin-params` turns the MPC UI metadata shipped with some downloaded
plugin content into a searchable control catalog. It is intended to replace
scrolling through hundreds of undifferentiated MIDI Learn targets when planning
a controller page.

The command is read-only. Point it at either one plugin content directory or
the SD card's `Synths` directory:

```bash
mpc-plugin-params "/media/user/CARD/Synths" \
  --plugin OPx-4 \
  --query cutoff \
  --recommended
```

Add a saved MPC 3 project to cross-reference controls that have already been
learned:

```bash
mpc-plugin-params "/media/user/CARD/Synths" \
  --plugin OPx-4 \
  --project "/media/user/CARD/Projects/Boot.xpj" \
  --recommended \
  --format csv \
  --output opx4-controller-candidates.csv
```

The report includes the human-facing control name and type, plugin UI
parameter number, Q-Link locations, inferred MPC parameter ID, matching learned
MIDI channel/CC evidence, and a usefulness score that promotes macros, filters,
envelopes, levels, motion, and effects.

## Evidence boundary

For the captured OPx-4 project, the MPC parameter ID is consistently the UI
parameter number plus 4096. A row is marked `verified` only when that exact ID
is present on the matching plugin track in the supplied XPJ. Other rows are
marked `inferred:+4096` and remain mapping candidates until tested on hardware.
Plugins without any same-plugin XPJ evidence are more cautiously marked
`hypothesis:+4096`.

Downloaded `.xpl` presets are XML wrappers containing opaque plugin-state
blobs. They prove preset content is present but do not expose a named parameter
list. The useful names come from `Plugin Skins/*.json`; plugins installed only
on MPC internal storage cannot be cataloged until their content or a sufficiently
complete MPC project capture is available to the computer.

Use JSON for another tool, CSV for a controller worksheet, or Markdown for a
review document. `--query` accepts space-separated terms and `--limit 0` emits
all matching controls.

After discovery, use [`mpc-plugin-map`](plugin-mapping.md) to validate curated
role-based profiles and compile predictable Launch Control Components and MPC
MIDI Learn worksheets. Catalog discovery remains broad; a performance profile
is intentionally selective.

## Audit alternate UI skins

The catalog prefers `GUI-Popout.json`, then `GUI.json`, then `TUI.json`. Before
assuming that preference contains the plugin's complete parameter surface,
compare every available skin:

```bash
mpc-plugin-skin-audit "/media/user/CARD/Synths" \
  --output work/plugin-skin-audit
```

The transactional JSON, CSV, and Markdown report records controls found only in
an alternate skin, one normalized control name bound to different parameter
numbers, name/type variants, and malformed skin documents. Use
`--fail-on-issue` in automation when warnings should produce a nonzero exit.

Name and control-type variants can be harmless adaptations to different screen
sizes. Missing controls and conflicting bindings deserve review before
expanding a performance profile. Even perfect skin agreement does not prove a
parameter accepts MIDI Learn; an MPC-authored XPJ remains the stronger evidence.
