# Three ways to start a live jam

Start with a four-bar drum loop in 4/4. Add **Resonant Kit** to the drum track and tune its root to the bass. Add **Turnaround** in the next insert slot. On a separate Plugin track, open **Chord Relay** and tap MIDI note 36 for a C minor seventh chord. Record the chord pads as you would any other MPC performance.

## Turnaround · catch the end of a phrase

While transport plays, choose **Roll**, set **Span** to **Beat**, and switch **Fill** on anywhere in bar three. Listen to the last beat of bar four. Four repeats rise in level and the original groove returns on beat one. **Break** leaves a gap and plays a pickup. **Answer** cuts the captured beat into four slices and reorders them. The effect captures up to one beat of stereo input at 16 kHz.

The grid starts at song position zero and repeats every 16 quarter notes. Span ranges from a sixteenth to four beats. A request made after the start of the selected window waits for the next complete window. Switch Fill off to cancel an armed request. For a repeating sequence use at least four bars. A host that omits song position uses elapsed playing time.

Turn **Keep** on after a fill you like. The next Fill recalls its audio, gesture and span. Save the MPC project with Keep on to recall that combination later. Playback stretches the captured gesture to the current tempo. Keep preserves the source for another trigger. To capture the performed audio directly, use MPC resampling.

## Resonant Kit · play pitched accents from the drums

Play four soft hits followed by an accent. Raise **Wet** to hear the pitched tail beneath the dry hit. **Root** sets the lowest resonator in MIDI note numbers (45 is A2). **Middle Interval** and **Upper Interval** tune the other two voices in semitones above it. Start with the default fifth and minor tenth. **Kick to Snare** shifts excitation from low-frequency body toward attacks. A hard hit also excites more of the upper voice. Shorten **Decay** for tight patterns, or lengthen it to let adjacent hits ring together. Wet adds signal, so allow headroom on the drum track.

## Chord Relay · play two chords from six pads

The initial chords are C minor seventh and A-flat major seventh. Use a note layout that sends the MIDI numbers below. Pad positions depend on the MPC track's note layout.

- **36 / 40** strike chords A / B.
- **37 / 41** cycle through their inner voices. A chord with one or two notes uses its lowest note for this gesture.
- **38 / 42** strum low to high. **Spread** sets the time between the first and last notes.
- On any of the six pads, velocity below 50 picks out the top note. Moving between slots while a common note is sounding sustains it through the change.

To replace a chord, switch **Teach** on, hold your voicing on keys sending MIDI 48 or above, and strike a pad for its slot. Release the keys and switch Teach off. Each slot stores up to six distinct notes, taking the lowest six if you hold more. Tapping a pad with no held keys preserves that chord. **Release** sets the tail and **Brightness** adds a tine-like overtone. Chord Relay generates its own audio. The project stores the two chords in plugin state and the pad performance as MIDI on the MPC track.

## Find them on the Key 37

On MPC OS 3.10.1 or later, enable both **Enable Enhancements** and **External Plugin Support** under **Preferences → Enhancements (Beta)**. Open **External Plugins** from an insert slot for either effect, or from a Plugin track for Chord Relay. The installed package folders are:

- `SD / VST2 Plugins / FG Scratchpad - VST - Turnaround /`
- `SD / VST2 Plugins / FG Scratchpad - VST - Resonant Kit /`
- `SD / VST2 Plugins / FG Scratchpad - VST - Chord Relay /`

## Reproduce the software check

With the SDK revision pinned in the [plugin CI workflow](../../.github/workflows/sdk-plugin.yml), run these commands from the toolkit checkout. Set `sdk` to the SDK checkout. The optional WAV argument writes a 16-second performance at 120 BPM using all three plugins and synthesized drum hits.

```sh
for plugin in Turnaround ResonantKit ChordRelay; do
  python "$sdk/tools/build.py" "plugins/$plugin" --target native --toolchain gcc
  "$sdk/.sdk-tools/host_sim" plugins/"$plugin"/build/native/*.so test --notes 36,40 --playing
done
c++ -std=c++17 -O2 -I"$sdk/framework" plugins/LiveJam/tests/session.cpp -o /tmp/live-jam-test
/tmp/live-jam-test /tmp/live-jam.wav
```

For the Key 37, use the SDK's full build for each plugin and copy its complete manufacturer-prefixed package under `VST2 Plugins`. The standalone checks still to do are discovery in the two browser contexts, arming a fill against the Key 37 transport, playing soft and accented hits, and reopening an MPC project containing the taught chords and a kept fill.
