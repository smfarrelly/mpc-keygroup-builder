# MPC Program Catalog

The catalog turns the structural ledger and XPM metadata into a portable,
audio-free index. It never reads sample contents and never copies licensed
audio.

Build it from an SD card, immutable backup, or another directory whose layout
matches the ledger paths:

```bash
uv run mpc-catalog build inventory/program-status.csv \
  --program-root "/path/to/MPC media root" \
  --output work/program-catalog.json
```

Each program entry contains:

- ledger path, collection, and category;
- normalized name, Drum/Keygroup type, and source format;
- zone, layer, and unique sample-reference counts;
- Keygroup note range or Drum pad range and populated banks;
- semantic role counts;
- model warnings/errors;
- structural, semantic, hardware, favorite, Scratchpad-role, and listening data.

Missing, unreadable, and malformed XPMs are isolated as individual entries so
one bad file cannot abort a library scan. Use `--fail-on-error` in automation
when malformed or unreadable files should fail the command; intentionally
missing entries remain visible in the summary.

Query the saved index without reconnecting the drive:

```bash
uv run mpc-catalog query work/program-catalog.json --type drum --role kick
uv run mpc-catalog query work/program-catalog.json --hardware pass --favorite yes
uv run mpc-catalog query work/program-catalog.json --search "Mirage" --format json
```

Semantic roles accept a complete role such as `hihat.closed` or a family such
as `kick`, `tom`, or `percussion`. Scratchpad-role text is also considered.

## Current full-library proof

The August 26, 2026 scan of the immutable media backup processed all 750 ledger
entries: 746 normalized successfully, comprising 90 Drum Programs and 660
Keygroups. Four intentionally transient `Programs/Keygroups/Testing` files were
absent and remain visible as `missing`. No licensed audio entered the index.

The JSON schema is the intended input to catalog-assisted Scratchpad recipes,
semantic MIDI generation, and the future Program Designer.
