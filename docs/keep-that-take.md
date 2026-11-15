# Keep That Take

Open the [laptop studio](http://127.0.0.1:8737/) while the local recorder is running. To start it from the repository root, run `uv run mpc-keep-take --open`. It reads the two-part [Playable Scratchpad bundle](playable-scratchpad.md) on the laptop. The **02 Four Bar Jam** XPJ and its companion folder supply the instruments and the project format.

## Play a melody from drum hits

In a new idea, press **Play with pads**. Tap pad 1 four times, making the second tap soft. With the default Mirage Pluck Bass pitches, you’ll hear **C, C, E-flat, G** alongside the drum. Hits below MIDI velocity 50 repeat the previous pitch with a short gate. The next stronger hit advances the phrase. A rest in your drumming leaves the melody silent. On the computer keyboard, try **A, Shift+A, A, A**.

- **Kick pads only** lets you play hats and snares freely while kicks drive the melody. Select it before starting. On an external pad or single drum trigger, choose **Learn MIDI kick trigger**, then strike it once. The browser remembers that MIDI input, channel and note as the kit’s kick whenever a drum instrument is selected. **Forget trigger** restores the original assignment.
- Choose **Wurli** or another keygroup under **Voice** before starting. Enter up to 16 pitches such as `C3 Eb3 G3 Bb3`, or choose **Play pitches on MIDI**, play the notes at any speed, and finish pitch entry. To work rhythm-first, tap your rhythm, change the pitches, then **Audition new pitches**. The timing and accents come from your original taps.
- **Keep groove** starts a loop with separate drum and melody layers. It starts on your first hit and rounds up to a whole bar. On an existing idea, the two new layers follow its loop length and retain their position against your earlier parts. If you play several passes, the most recent loop ending with your performance is kept. Keep it before pressing Stop or changing drum instruments. The existing take, MIDI and MPC project exports preserve both parts.
- While the kept loop plays and a drum track is selected, choose **Move a melody hit with next kick**. Play one kick where you want the nearest melody note to land. Hear the change on the next pass. **Undo kick move** restores the previous timing.

This mode uses the laptop’s sample playback. A saved MPC project contains the performed notes and samples. Live accompaniment and trigger learning run in the browser.

## Start with Answer Track

Open a new idea, select **Wurli**, then press **Answer**. That starts the clock and listens for one phrase. Hold a chord for about two beats: Pluck Bass plays its notes underneath while you sustain it. Release the chord when you want it to end. For a melody or pad rhythm, leave a short gap to invite the reply.

- Tap a soft, soft, loud pattern on one **Main Drums** pad. Pluck Bass borrows the timing and accent, using a three-pitch bass figure. Busy fills get shorter answers.
- Play two notes on **Pluck Bass**. Wurli answers in its own register using the pitch classes you supplied. A single-note melody on **Dark FM** invites Vinyl SP drums.
- Choose **Again** to hear your original phrase with another answer. Three readings cycle through echoing accents, playing in gaps and reversing the phrase. The generated part plays once per request.
- Choose **Keep both** when you hear something worth developing. Your phrase and that specific reply loop on separate tracks. The gap, velocities and pedal events travel with the pair. You can overdub or use the existing MIDI and XPJ export.

Answer Track uses the local Scratchpad samples. It listens to notes played on the selected instrument through the browser controls or connected MIDI. **Stop** clears an unkept exchange. If the studio reopens on a previous idea, save that take and choose **New idea** first.

## Keep a melody and add drums

1. Select **Wurli**, leave the tempo at 120, and press **Start clock**. The first four bars take eight seconds. Play the on-screen keys, use the computer keyboard, or select **Connect MIDI** for a keyboard connected to the laptop. Space acts as a sustain pedal. Octave changes the on-screen and computer keys.
2. During bar five, press **Keep 4**. The four complete bars immediately before bar five become a layer. Its playback starts at the next downbeat. Held keys and pedal-sustained notes are sounded again at the left edge, and released at the right edge. A new attack at the loop boundary can sound different from a continuous sample tail.
3. Choose **Main Drums**. Play along for a loop, then press **Keep last loop**. In clocked mode this keeps the last four complete bars and lines them up with the original chord progression, even if you press halfway through its second pass. The kit selector beside a drum layer auditions equivalent pad positions on another kit. **Sixteenth-note snap** moves playback toward the grid in proportion to the slider. The exported performance uses your original instrument and timing.
4. **Save take** downloads a small JSON file, including notes, velocities, key releases, pedal changes and playback choices. **Reopen take** restores it. The most recent kept idea also restores in the same browser at the same address. **Undo last layer** stops playback and removes the last overdub.

## Catch something before choosing a tempo

Turn off **Click**, start the clock and play. Open **Keep a free-time phrase** and choose **Find phrase**. Two seconds of silence separates phrases. A held chord or sustained note counts as playing. Adjust **From** and **To** in seconds, choose **Audition selection**, then **Keep phrase**. Its duration becomes the loop length. Once a full loop has played, choose another instrument and press **Keep last loop** to add a part of the same length. Input history covers the most recent two minutes per instrument while the clock runs. Stopping clears unkept history.

## Export the idea

**Export MIDI and MPC project** writes a new folder under `work/Kept Ideas` and displays the absolute path. Repeated exports use numbered folders. Each includes:

- A multitrack MIDI file with a separate track for each kept layer, retaining key releases and CC64 pedal changes in their original order.
- A standalone XPJ with a matching ProjectData folder. The exporter combines overdubs on their Scratchpad instrument tracks and represents pedal sustain as note duration. The source demo's performed notes are replaced by yours. Each project includes its own sample copy, roughly 280 MiB for the studio bundle.
- A small `take.json` that reopens directly in the laptop recorder.

Clocked ideas export as four bars. A free-time loop gets a tempo and bar count that preserve its duration. Phrases shorter than 0.8 seconds retain their note timing and receive trailing silence to fill one MPC bar at 300 BPM. The browser can loop those phrases at their original length.

For a different drive or port, run `uv run mpc-keep-take --project "/path/to/02 Four Bar Jam.xpj" --output "/path/to/Kept Ideas" --port 8738 --open`. The recorder serves the local browser on loopback. Keep the tab in the foreground for live timing. Standalone MPC playback and physical MIDI input remain hardware acceptance items.
