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

## Audition a throw on your own loop

On Linux or macOS with a local C++17 compiler, render a dry/processed pair using the actual effect source. Choose a mono or stereo PCM16 loop of up to two minutes. Both outputs use the same gain, sample rate and length. A mono input is duplicated to stereo. The output folder includes the gesture settings, any clipping count, and a checksum receipt.

```bash
uv run python plugins/LoopThrow/tools/audition.py "/path/to/four-bar-loop.wav" \
  --sdk "$sdk" --bpm 120 --beat 15.95 --length 0.25 --division 1/8 \
  --repeats 65 --tail 2 --output work/loop-throw-audition-01
```

Beat numbers begin at 1. For a four-bar 4/4 loop this example opens the send just before the last backbeat, closes it a quarter of a beat later, and leaves two seconds for the echo to ring. Listen to `Dry.wav` and `Loop Throw.wav`. To try a different gesture, choose a fresh output directory. Run the portable renderer check with `uv run python plugins/LoopThrow/tests/audition_smoke.py "$sdk"`.

To capture several hits in one render, add `--also-beat` for each additional send opening. For a two-bar loop at 96 BPM, `--beat 3.97 --also-beat 7.97 --length 0.22` opens just before beat four of each bar. Overlapping windows form one continuous send. Open the output folder’s `index.html`, play **Dry**, then choose **Switch to Loop Throw** during playback. The other player follows the same timestamp and volume. The WAV files and JSON remain usable on their own.
