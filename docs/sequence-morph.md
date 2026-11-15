# Evolve a sequence you played

On the Key 37, save the project containing your performance with its samples. On the laptop, give that XPJ to the command below. Open the XPJ in the new output folder on the MPC. The original sequence is still selected. Use the sequence selector to audition the variations, then overdub or edit the one you like.

```bash
uv run mpc-sequence-morph "/path/to/My Jam.xpj" --output "work/My Jam Answers"
```

**Answer** repeats a played note or chord more quietly in a gap. It waits for the same pitches to release, keeps the reply within the bar and stops before the next onset. Long held parts can stay exactly as you played them. **Space** drops entire onsets to open a part up. It keeps the first and loudest sounding onset of each bar, including all notes of an anchored chord.

To thin just the drum part in a named sequence, leaving the other tracks playing alongside it, run

```bash
uv run mpc-sequence-morph "/path/to/My Jam.xpj" --sequence "Four-bar jam" \
  --track "Main Drums" --style space --amount 25 60 90 --seed 12 \
  --output "work/My Jam Drum Variations"
```

Repeat `--track` for several tracks. By default all played Drum, Keygroup, Plugin and MIDI parts participate. Amount is the percentage chance of changing an eligible onset. Higher amounts with the same seed include the lower amount’s choices. Zero makes an unchanged musical copy. The command reports how many onsets actually changed per track.

Each output folder contains a full independent project copy with its original filename and companion folder. Keep them together when transferring. All variations share that copy of the sample library. The tool accepts MPC 3 projects with locally saved samples and a single meter per processed clip. It works on sequence clip notes. Song arrangements, audio tracks and automation carry through. External instruments and plugin tracks still need their usual hardware or installed plugins.

## Four Bar Jam example

Open `SD / Projects / Sequence Morph / 02 Four Bar Jam.xpj`. Try **Four-bar jam**, **Answer 65%**, **Answer 100%**, then **Space 75%**. The adjacent listening WAV plays those four passes in order, eight seconds each. It is a dry laptop rendering of the saved drum, bass and Wurli samples. Use the XPJ for the MPC mix and editable notes.
