# Play a drum take with a rhythm section

Use a [saved drum take](../../docs/pad-recorder.md) as the starting point. The builder repeats the complete take, preserving its timing and velocities, and adds two parts from an existing harmony recipe. Akai’s SDK Simple Synth plays the bass and chord notes on separate instances. The renderer compiles the local SDK example with a C++17 compiler on Linux or macOS.

From the toolkit checkout, point `sdk` at the SDK root, then run:

```bash
uv run python plugins/SimpleSynthStudy/build.py "/path/to/Kit.xpm" "/path/to/My groove.take.json" \
  --sdk "$sdk" --harmony recipes/harmony/dusty-dorian.toml \
  --bass "Fat Bass" --chords "Soft Pad" --output "work/My rhythm section"
uv run mpc-bundle-verify "work/My rhythm section"
```

Open `index.html` to play the arrangement. Switch between **Full mix**, **Drums**, **Bass** and **Chords** to hear each part at the same point in the phrase. All four WAVs share one tempo, start frame and loop end. Individual stems retain their rendered level. The full mix uses 50% drums, 30% bass and 20% chords.

**Sketch.mid** carries three named tracks plus a tempo track. Separate MIDI files make it possible to keep just the bass line or use a different sound for the chords. The take supplies the drum channel, and the harmony recipe supplies the other two channels. Choose the destination sound on the MPC. The MIDI files carry notes, velocities, timing and gates.

The arrangement repeats the two phrases to their first common bar boundary, up to 64 bars. For example, a two-bar take and four-bar recipe produce four bars. Available SDK presets are **Init Saw**, **Fat Bass**, **Soft Pad** and **Pluck**. Change `--seed` to vary the velocities allowed by the harmony recipe. The output includes that recipe, the editable original take, sample timing evidence, and the synth/host source hashes. Audio ends at the loop boundary.

Run the [SDK smoke test](smoke.py) with an eight-pad XML Drum Program and a trusted SDK checkout. It checks a note starting 137 frames into the render, its release, two presets, two velocities, and a complete three-track sketch at 103 BPM. Hardware listening is deferred.
