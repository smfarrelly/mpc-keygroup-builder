# Break Relay

On a Plugin track choose **External Plugins → Break Relay**. Play kick, hat, snare, hat on MIDI **36, 38, 37, 38**. Each stroke starts a slice immediately. The second hat comes from a different point in the recording when the source has another hat after the snare. Tap **39** to play a pickup. A new stroke cuts the previous slice with a short crossfade.

Open **SD / Projects / Break Relay / 01 Same hands - Home, Borrow, Away.wav**. The same two-bar take plays three times at 120 BPM. The first four seconds use CR-78 Beguine. The next four borrow hits from Brighton 808. The last four use Brighton alone. The adjacent MIDI file contains the drum strokes, Home cues and variation pad holds. Assign it to Break Relay for an editable take.

## Pad and key gestures

- **36, 37, 38, 39** request kick, snare, hat and pickup respectively. The pad’s velocity controls level. A pickup may contain more than one hit from the break.
- **40 Home** resets the source position and random seed. Record Home just before the first stroke to get repeatable loop playback.
- Hold **41 Borrow** for a 50% chance of using the second break per stroke. Hold **42 Away** to use only the second break. Away takes priority when both are held. Release both to follow **Wander** again.
- Hold keys sending MIDI **48–127** to tune new slices. MIDI **60** plays at original pitch. Last held key wins. **Tune** supplies an additional semitone offset; the combined range is ±36 semitones. Changing pitch also changes slice duration.
- Set **Wander** to zero for the first break, 100 for the second. **Seed** selects a repeatable sequence of source choices. The host saves the settings. Home gives a recorded part its starting point. Pad numbers here are MIDI notes; your MPC pad layout determines which physical pad sends them.

After each stroke the cursor advances to the end of its slice. Each new pad finds the next occurrence of its role, wrapping if necessary. When changing breaks, the search starts at the corresponding fraction of the other phrase. This preserves some of the recorded order while allowing you to change the timing live. Tempo comes from your hands or the recorded MPC notes.

## Build a bank from two loops you own

```bash
uv run mpc-break-relay-bank plugins/BreakRelay/mars-pair.toml \
  --source-root "/path/to/Samples From Mars/Loops" --output "work/Relay bank/Content"
```

Copy **Content/pair.brk** inside **SD / VST2 Plugins / FG Scratchpad - VST - Break Relay /** and load a fresh instance. The preset list shows **Recorded pair - Home** if the bank loaded, or **Factory pair - Home** for the built-in synthesized pair. Keep the bank with the package when moving projects. Replacing it changes the sound of projects using that copy of the instrument.

The example manifest lists ten CR-78 slices and fourteen Brighton slices in source order. To use different loops, edit their WAV paths, tempos, phrase lengths and slice lists. Each entry has a role, start beat and exclusive end beat, measured in quarter notes from zero. Overlapping pickups can span neighboring hits. The packer retains stereo, converts to signed 16-bit PCM and preserves the source sample rate. Each break needs all four roles, 4–64 slices, at most two seconds per slice and 16 MiB for the complete bank. Use personal sample banks locally.

For a software audition, build with Akai’s SDK, then render the score on Linux:

```bash
python3 /path/to/mpc-plugin-builder-sdk/tools/build.py plugins/BreakRelay --target all
uv run python plugins/BreakRelay/rehearsal.py --sdk /path/to/mpc-plugin-builder-sdk \
  --content "work/Relay bank/Content" --output "work/My Relay audition"
```

Omit `--content` to hear the factory pair. Select a new output directory for each build.
