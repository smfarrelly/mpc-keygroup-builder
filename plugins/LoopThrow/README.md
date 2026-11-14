# Loop Throw

A stereo insert for performing echo throws on a drum track or MPC submix. Leave **Throw** closed while you play. Open it for a snare or fill, then close it. The original drum signal stays at unity, new hits stay dry, and the captured hit repeats in time. The return adds level to the dry signal, so allow headroom on the strip.

- **Throw** controls how much new audio enters the delay. Defaults to zero.
- **Division** selects a sixteenth, eighth, dotted eighth, or quarter note. Defaults to eighths at the project tempo. The delay memory holds four seconds per channel.
- **Repeats** sets feedback from 0 to 85 percent.
- **Tone** sets the low-pass cutoff in the echo path. Each repeat passes through the filter again.

Both channels retain their stereo positions. Parameter recall restores the knob settings. The audio held in the delay clears on reset. Assign an XL3 encoder to Throw through MPC MIDI Learn. Recording the exposed parameter can capture a throw gesture.

## Build and review on a computer

From the toolkit root, point the shell variable at a local checkout of the [Akai plugin SDK](https://github.com/inmusic-software/mpc-plugin-builder-sdk/tree/febd2ca5bd9eb16c4a412837196e145566bc981b). Linux with a C++17 compiler can run the simulator and timing checks locally:

```bash
sdk=/path/to/mpc-plugin-builder-sdk
plugin=plugins/LoopThrow
python3 "$sdk/tools/build.py" "$plugin" --target native --toolchain gcc
"$sdk/.sdk-tools/host_sim" "$plugin/build/native/loop-throw.so" test --playing
c++ -std=c++17 -O2 -I"$sdk/framework" "$plugin/tests/impulse.cpp" -o "$plugin/build/impulse-test"
"$plugin/build/impulse-test"
uv run mpc-sdk-compare "$plugin/params.reference.json" "$plugin/build/params.json"
uv run mpc-plugin-map check midi/sdk-examples/loop-throw.toml --sdk-dump "$plugin/build/params.json"
```

For a standalone package, run the SDK build with its cross compiler, then inspect the output:

```bash
python3 "$sdk/tools/build.py" "$plugin"
uv run mpc-sdk-package "$plugin/build/FG Scratchpad - VST - Loop Throw" --sdk-dump "$plugin/build/params.json"
```

Source, touchscreen layout and a reference parameter dump are included. The SDK supplies its framework and graphics during the build. Device installation, listening and performance acceptance are pending. [Toolkit mapping guide](../../docs/akai-sdk.md)
