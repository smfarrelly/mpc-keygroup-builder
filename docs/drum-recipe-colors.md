# Declare pad colors in a Drum recipe

Use `color_category` when a sample's name does not describe its musical role,
or when a pad should have a deliberate color regardless of its filenames:

```toml
name = "Transition Kit"

[[pads]]
pad = 1
sample = "BigImpact-Clean.wav"
color_category = "fx"
```

Build with `mpc-drum-build` as usual. The category selects the established
semantic palette: `kick`, `snare`, `clap`, `rim`, `closed_hat`, `open_hat`,
`cymbal`, `tom`, `percussion`, `fx`, or `unknown`. Category names are exact,
lowercase strings. An invalid category reports the affected recipe entry and
allowed choices before writing a package.

Omit `color_category` to retain existing filename detection. `unknown` is an
explicit gray choice, not a request for automatic detection. The option works
on single-sample and velocity-layered pads, and inherited recipes retain it.
One color applies to the whole pad, regardless of which velocity layer plays.
Empty pads remain unlit.

This controls appearance only. It does not rename samples, change note maps,
alter playback, assign mute groups, or override the semantic classifier used
by other tools. A filename-only audit can still call an explicitly colored FX
voice `unknown`; the generated XPM and manifest model retain the chosen color.

The [Found Transitions recipe](../inventory/fg-found-transitions-01.toml) is a
complete example. Its eight purple FX pads now rebuild in one command.

The published `drum-manifest` JSON schema includes the same optional field and
category choices for editor assistance. Inspect it with
`mpc-schema show drum-manifest`, or validate a recipe with
`mpc-schema validate drum-manifest inventory/fg-found-transitions-01.toml`.
