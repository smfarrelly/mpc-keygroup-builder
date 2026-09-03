# MPC XPJ inspector

`mpc-xpj` provides read-only inspection and comparison for MPC project files. It detects MPC 2 XML projects and parses MPC 3 gzip/ACVS/JSON projects without dropping unknown fields.

## Inspect a project

```bash
uv run mpc-xpj inspect "/path/to/Key 37 Test.xpj"
```

The summary includes the five ACVS header values, schema versions, tempo, track names and program types, routing channels, sequence metadata, and sample counts.

It also reports MIDI Learn assignment counts by channel and target track. To
export the individual learned controls without the rest of the project:

```bash
uv run mpc-xpj midi-learn "/path/to/Key 37 Test.xpj" \
  --output work/key-37-midi-learn.json
```

## Extract normalized JSON

```bash
uv run mpc-xpj extract "/path/to/Key 37 Test.xpj" \
  --output work/key-37-test.json
```

Normalization means stable, indented JSON with sorted object keys. Array order and every payload value—including unknown fields and opaque plugin-state strings—remain unchanged.

## Compare two saves

```bash
uv run mpc-xpj compare "/path/to/Before.xpj" "/path/to/After.xpj" \
  --output work/before-after.diff.json
```

Each change uses an RFC 6901-style JSON Pointer and is classified as `added`, `removed`, `changed`, or `type`. This is intended for controlled Key 37 experiments: save a baseline project, change one routing or program setting, save again, and inspect the smallest resulting differences.

MPC 2 files are currently detected and summarized by container generation, but structural extraction and comparison require MPC 3 projects.

## Reverse-engineering safety

The inspector does not write XPJ files. Treat field meanings as provisional until a controlled hardware experiment confirms them. Preserve plugin state blobs byte-for-byte in any future writer.
