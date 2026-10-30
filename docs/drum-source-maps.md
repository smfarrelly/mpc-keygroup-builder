# Build Drum kits from samples in different folders

A Drum manifest can map its packaged sample names to explicit files below
`--source-root`. This avoids manual flattening and disambiguates two source
files with the same basename:

```toml
name = "Two Timbres"

[sources]
"Hit Clean.wav" = "Clean/Hit.wav"
"Hit Tube.wav" = "Tube/Hit.wav"

[[pads]]
pad = 1
color_category = "percussion"
layers = [
  {sample = "Hit Clean.wav", velocity_start = 0, velocity_end = 63},
  {sample = "Hit Tube.wav", velocity_start = 64, velocity_end = 127},
]
```

Run `mpc-drum-build` with the common parent folder as `--source-root`. The
result contains the XPM, `Hit Clean.wav`, and `Hit Tube.wav`, with references
using those packaged names. Audio bytes are copied unchanged; the source
library is not renamed or edited. There is no recursive basename search.

An unmapped sample name still resolves directly below `--source-root`, so
existing recipes retain their behavior. Inherited recipes keep the base
source map; a child can explicitly replace an alias's source path. Paths are
relative to the selected source root, not the manifest file.

Aliases must be basenames. Source values must be relative paths without parent
traversal, drive prefixes, or backslashes. Symlinks that resolve outside the
source root are rejected. Used names that differ only in case are rejected so
the package does not become ambiguous on an SD card. The schema documents the
map; native validation checks path semantics and the build verifies sources
before creating the output package.

The [Mechanical Layers recipe](../inventory/fg-mechanical-layers-01.toml) is a
complete example using Clean and Tube subfolders. It is a creative layered kit,
not a promise of exact Ableton rack conversion or acoustic velocity dynamics.
