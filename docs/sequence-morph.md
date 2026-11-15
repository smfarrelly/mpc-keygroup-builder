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

Repeat `--track` for several tracks. For Answer and Space, all played Drum, Keygroup, Plugin and MIDI parts participate by default. In these two styles, amount is the percentage chance of changing an eligible onset. Higher amounts with the same seed include the lower amount’s choices. Zero makes an unchanged musical copy. The command reports how many onsets actually changed per track.

Each output folder contains a full independent project copy with its original filename and companion folder. Keep them together when transferring. All variations share that copy of the sample library. The tool accepts MPC 3 projects with locally saved samples and a single meter per processed clip. It works on sequence clip notes. Song arrangements, audio tracks and automation carry through. External instruments and plugin tracks still need their usual hardware or installed plugins.

## Four Bar Jam example

Open `SD / Projects / Sequence Morph / 02 Four Bar Jam.xpj`. Try **Four-bar jam**, **Answer 65%**, **Answer 100%**, then **Space 75%**. The adjacent listening WAV plays those four passes in order, eight seconds each. It is a dry laptop rendering of the saved drum, bass and Wurli samples. Use the XPJ for the MPC mix and editable notes.

## Make the bass and keys follow your hands

Play a drum part with the accents you want to hear in the band. Record the bass or chord part separately. Save the MPC project and list its recorded parts to find their exact track names.

```bash
uv run mpc-sequence-morph "/path/to/My Jam.xpj" --list
uv run mpc-sequence-morph "/path/to/My Jam.xpj" --guide "Main Drums" \
  --track "Pluck Bass" --track "Wurli" --style lock --style accent --style duck \
  --amount 60 100 --output "work/My Jam Groove Transfer"
```

Each style and amount gives you a separate editable sequence derived directly from the selected performance. The guide plays exactly as recorded. Omit `--track` to apply the guide to every other eligible played track.

- **Lock** pulls each nearby target onset toward a guide hit. At 60% it travels partway. At 100% it travels as far as note order and same-pitch gates allow. Chords move together with their original durations.
- **Accent** borrows the velocity of the guide hit. A chord follows its strongest note and keeps the relative levels of its voices. Try this to make a quiet bass pickup follow a soft ghost note.
- **Duck** softens a target onset where the guide plays. At full strength a maximum-velocity guide hit reduces that onset’s velocities by 75%. This edits MIDI note velocities, so the audible result depends on the instrument’s velocity response.

Each target onset matches the closest unmuted guide onset within a quarter beat in the same bar. An exact tie uses the earlier hit. A target with no nearby guide hit keeps its phrasing. These three modes use amount as the strength of every match, and always reproduce the same result regardless of seed. Use clips in the same lane with matching playback ranges, starts and meter.

### Try the prepared comparison

Open `SD / Projects / Groove Transfer / 02 Four Bar Jam.xpj`. Start with **Four-bar jam**, then switch between **Accent 100%** and **Duck 100%**. Listen for the bass and Wurli leaning into the drum accents in the first version and leaving room for them in the second. Use **Lock 100%** to compare timing. The folder’s listening WAV plays original, Lock, Accent and Duck at full strength, eight seconds each, using a dry software rendering.
