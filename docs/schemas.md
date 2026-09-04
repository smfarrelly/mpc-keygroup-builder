# Declarative schemas

The project publishes JSON Schema documents for its most reusable TOML formats.
They provide editor completion and a language-neutral description of the file
shape. The CLI's native validators remain authoritative because they also check
relationships that JSON Schema cannot express cleanly: unique MIDI messages,
velocity coverage without gaps, referenced devices, inherited manifests, and
MPC-specific capacity limits.

List the available formats:

```bash
mpc-schema list
mpc-schema list --json
```

Print a schema or copy it for an editor or another application:

```bash
mpc-schema show drum-manifest
mpc-schema show plugin-profile --output plugin-profile.schema.json
```

Validate one or many files with the same parser used by the builders:

```bash
mpc-schema validate device-profile devices/mpc-key-37.toml
mpc-schema validate layout-preset layouts/*.toml
mpc-schema validate keygroup-variant variants/keygroups/*.toml
mpc-schema validate midi-device midi/devices/*.toml
mpc-schema validate midi-control-map midi/maps/*.toml
mpc-schema validate plugin-profile midi/plugins/*.toml
mpc-schema validate rig-profile rigs/*.toml
mpc-schema validate controller-capacity midi/controller-capacity.toml
```

Each input receives a separate `PASS` or `FAIL`, so one bad file does not hide
later results. Add `--json` for automation. A failing batch exits with status 2.

## Published formats

- `device-profile` — MPC key count, physical pad matrix, and bank capacity.
- `layout-preset` — semantic or sequential pad-placement strategy.
- `drum-manifest` — pads, samples, velocity layers, inheritance, and mute groups.
- `keygroup-variant` — allowlisted expressive changes to preserved Keygroups.
- `midi-device` — external-device MIDI channel, CC parameters, and trigger notes.
- `midi-control-map` — controller modes, endpoints, messages, routes, and targets.
- `rig-profile` — tracks, devices, controller groups, and acceptance criteria.
- `plugin-profile` — Launch Control endpoints and MPC plugin parameters.
- `controller-capacity` — all 15 Custom Mode slots and reserved MIDI channels.

The canonical schema files are packaged under
`mpc_keygroup_builder.data.schemas`, so `mpc-schema show` works from an installed
wheel without a repository checkout. Every published example is validated in
CI, and the wheel smoke test invokes the command from outside the checkout.

## Compatibility policy

All current formats use `schema_version = 1`. Optional unknown properties are
retained where a format is designed to grow, but native validators may reject
unsafe or contradictory values. A future breaking change will receive a new
schema version rather than silently changing version 1.
