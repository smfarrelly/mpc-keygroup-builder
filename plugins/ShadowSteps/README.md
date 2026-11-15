# Shadow Steps and Common Tone

Start with **Shadow Steps** if you have a rhythm in mind. Start with **Common Tone** if you have one melody note and want to hear where it could go. Both are standalone Plugin-track instruments. The eight-bar duet, its isolated parts and their editable MIDI performances are under `SD / Projects / Shadow Steps /`. Play `03 Two Track Jam.wav` to hear them together.

## Shadow Steps · play a bar, keep it, change it

1. On a Plugin track choose **External Plugins → Shadow Steps**. Start transport. Play a pattern on MIDI notes **36–39** (low skin, middle drum, wood, metal). For a one-pad performance use **47**. Hard strokes play the low drum and progressively softer strokes play the other three sounds.
2. After sixteen sixteenth-note cells, the captured rhythm repeats. Your live taps still sound immediately, and the keeper retains the last velocity on each drum in each cell. Quantization is to the nearest sixteenth. The silent parts of your bar matter.
3. Hold **40** for **Offbeat**. The bottom two instruments keep their positions while the top two move an eighth later, wrapping inside the bar. Hold **41** for **Holes**. The original plays, and empty cells immediately following a stroke get a tuned answer. Hold **42** for **Canon**. Accents return three sixteenths later, voiced a fifth higher than Holes. A strong accent adds another octave. Simultaneous strokes yield one response from the loudest lane.
4. Release the pad to return to the previous held variation, or to the **Scene** control when all pads are released. Try **Kit Level** at zero to hear an answer by itself. Record the scene pad holds into the MPC sequence to perform the changes again.
5. To replace the keeper, tap **44** and play a new phrase. The first drum hit starts the replacement. Tap **45** while capturing to discard it and return to the old one. MIDI **35** starts capture immediately, including leading rests. An empty take preserves the previous keeper. Save the project after the bar completes.

The clock follows MPC tempo and song position. When stopped, the first stroke starts a local clock at the available tempo. A transport stop or seek discards an unfinished take. A reported loop wrap continues the capture across the seam. Use a four-quarter sequence or a multiple for the one-bar variations. The saved project contains the completed bar and the Scene parameter. Root can be set on screen or from keys sending MIDI 48–79. Pad positions depend on the current note layout.

## Common Tone · find the harmony with your left hand

Play **G** on the keys. Hold **36** to put G minor seventh under it, **37** for E-flat major seventh, or **38** for F dominant ninth. G stays on top of all three. Try a different melody note to transpose the choices. Each preview takes the last melody pitch at the instant you press the pad. You can keep improvising above it.

- While holding a chord, tap **42** to store A or **43** to store B. Tap **40** or **41** to recall and sustain the corresponding memory. Both memories save with the project and wait for a recall gesture after reopening.
- Hold a different preview over a recalled chord. Release it to return to the pinned harmony. Pitches common to both voicings keep their phase and envelope through the change.
- Tap **39** to play the current chord as short mallet strokes. Turn **Chord Level** down and play it as syncopated stabs. **44** drops the chord and preserves both memories.
- Keys sending MIDI 48–127 play the lead. Lead note-offs and sustain pedal (CC64) control its tail. The sustained harmony, rhythmic stabs and lead have separate levels and share stereo output.

## Print a rhythm onto editable tracks

On a laptop with the toolkit installed and a C++17 compiler, print a bar from a Standard MIDI file or an MPC 3 XPJ sequence. The printer and plugin use the same arrangement code. The output folder must be new.

```bash
uv run python plugins/ShadowSteps/print_take.py groove.mid \
  --pads 36 38 42 46 --bar 2 --root 43 --tempo 96 --output "work/My variations"
```

For a saved XPJ, select a sequence and track by name. This example uses the Main Drums performance in the private four-bar Scratchpad. Its repeated note 54 spans multiple velocities. Split that one note across the four parts to turn the original dynamics into orchestration:

```bash
uv run python plugins/ShadowSteps/print_take.py \
  "work/Playable Scratchpad/Projects/Playable Scratchpad/02 Four Bar Jam.xpj" \
  --sequence "Four-bar jam" --track "Main Drums" --strike-note 54 --bar 1 \
  --output "work/Four Bar Jam variations"
```

**Original**, **Offbeat**, **Holes** and **Canon** are single-bar format 1 MIDI files. Assign the **Drums** track (channel 10) to a kit and **Answer** (channel 1) to a Keygroup or synth. Four-pad input preserves your selected drum note numbers. Single-note input assigns velocities 105–127, 80–104, 48–79 and 1–47 to output drum notes 36, 38, 42 and 46 respectively. **Play in Shadow Steps.mid** uses the instrument's capture cue and its four internal pad notes. Set its Root to the value you printed.

The XPJ reader uses the selected clip's stored 4/4 note positions and velocities. Muted notes are skipped. Playback probability, ratchets, swing and tempo automation are outside this export. The default output tempo for XPJ is the stored master or sequence BPM. For MIDI it is 100 BPM; use `--tempo` to change it. Use `--channel` to isolate one source channel. The command only reads the source project.

## Package paths and software acceptance

- `SD / VST2 Plugins / FG Scratchpad - VST - Shadow Steps /`
- `SD / VST2 Plugins / FG Scratchpad - VST - Common Tone /`
- `SD / Projects / Shadow Steps / 01 Shadow Steps.mid`
- `SD / Projects / Shadow Steps / 02 Common Tone.mid`
- `SD / Projects / Shadow Steps / 03 Two Track Jam.mid`
- `SD / Projects / Shadow Steps / Editable variations / Canon.mid`

On MPC OS 3.10.1 or later, enable enhancements and external plugin support under **Preferences → Enhancements (Beta)**. Assign the two tracks in the duet MIDI to the named plugins and begin with fresh instances. The matching stereo WAV works as an immediate listening reference.

From the checkout, set `sdk` to the pinned Akai SDK used by the [plugin workflow](../../.github/workflows/sdk-plugin.yml). The default SDK build generates native, ARM32 and ARM64 binaries.

```bash
for p in ShadowSteps CommonTone; do
  python "$sdk/tools/build.py" "plugins/$p"
  "$sdk/.sdk-tools/host_sim" plugins/"$p"/build/native/*.so test --notes 36,37,67 --playing
  c++ -std=c++17 -O2 -I"$sdk/framework" "plugins/$p/tests/session.cpp" -ldl -o "/tmp/$p-test"
  "/tmp/$p-test" plugins/"$p"/build/native/*.so
done
uv run python plugins/ShadowSteps/tests/printer.py
uv run python plugins/ShadowSteps/jam.py --sdk "$sdk" --output "work/Shadow Steps rehearsal"
uv run mpc-bundle-verify "work/Shadow Steps rehearsal"
```

The software tests check note placement, velocity boundaries, canceled replacements, loop wraps, all three chord voicings, sustain, and fresh-instance recall. Physical pad feel, standalone discovery and project recall on the Key 37 remain listening checks.
