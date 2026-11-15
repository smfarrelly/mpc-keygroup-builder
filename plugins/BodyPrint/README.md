# Body Print

On the Key 37, put **External Plugins → Body Print** in an insert on a Wurli, held synth or drum track. Select **Play both bodies**. Play softly, then repeat the note with a strong attack. The insert measures the incoming stereo attack over eight milliseconds. A soft attack selects A, a hard attack selects B, and the blend stays on the chosen color through the decay. Instrument velocity response and insert input level determine how far the gesture travels.

The private card bank uses **Rim CR78 Vinyl SP 01** for A and **Clap Tape Crunch Vinyl SP** for B. Listen at **SD / Projects / Body Print / 01 Wurli - Dry, Rim, Tape Clap, Touch.wav**. Each pass is four seconds, rendered through the native insert for the three processed passes.

- **Body** manually blends A and B. At zero **Touch** this is the entire A/B control.
- **Touch** blends in the attack-driven choice. At full Touch it follows input peaks from roughly 0.08 to 0.60 of digital full scale. Sustains hold their color until a fresh rise is detected.
- **Length** changes the spacing of the reflections from one quarter to twice the captured duration.
- **Blend** mixes the colored signal with the live stereo input. Zero is dry.

Each donor contributes up to 48 signed reflections from roughly 3–63 ms after its attack. The instrument you play supplies the audio to the filter. The filters have unit-energy weights and a soft-limited wet path. The original offline study loudness-matched a complete recording; a live insert responds to the input as you play.

```bash
uv run mpc-body-print-bank "/my/samples/rim.wav" "/my/samples/tape-clap.wav" \
  --output "work/My bodies/Content"
```

Copy **Content/bodies.bin** to **SD / VST2 Plugins / FG Scratchpad - VST - Body Print /** and reopen the insert. **Sample body A** in the preset list confirms the bank loaded. **Factory body A** uses two built-in reflection patterns. For the same sound on another MPC, copy the same Content folder with the package. [Original listening study](../PerformanceEffects/README.md#next-uses-for-samples-from-mars)
