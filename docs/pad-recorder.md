# Record a drum take on the laptop

Open a generated recorder’s `index.html`, select **Enable audio**, then **Record**. Play the lower row with **Z X C V**. Hold **Shift** for a quieter hit. The transport loops in 4/4, so you can play kicks on the first pass and add hats on the second. **Finish overdub** keeps the loop playing. **Stop** ends playback. Undo restores the state from before the last overdub.

**Save take** downloads the editable performance. **Open take** restores it in the same kit and bank. **Save MIDI** downloads the notes on the take’s drum channel with its tempo and loop length. Load the matching Drum Program when using this MIDI. A MIDI file contains the performance only. Browser edits live in the tab until you save.

## Build a recorder for a kit

Start with an XML Drum Program with its PCM WAV files in the same folder or below it. The builder embeds the selected bank’s sample regions inside the HTML, including velocity layers. You can disconnect after opening it. A page built from a commercial kit contains that kit’s audio. Keep it in your personal library.

```bash
uv run mpc-pad-recorder build "/path/to/Kit.xpm" \
  --bank A --bars 2 --tempo 96 --output "work/My recorder"
```

Use `--recipe recipes/drums/dusty-pocket.toml` to begin with a groove you can overdub. Its bar count and MIDI channel come from the recipe. Roles resolve inside the selected bank. An empty take defaults to MIDI channel 10.

Pads follow the physical bank order. Hover over a pad to see sample names and velocity splits. Choose Ghost (40), Medium (80), or Accent (112). Snap sets the grid for the **next** recorded hit. Switch it off to retain timing at 480 ticks per quarter note. Replaying a pad at the same snapped tick replaces that hit. You can adjust the tempo and bar count while stopped. Shortening a loop requires that all existing notes fit.

## Render a saved take

```bash
uv run mpc-pad-recorder render "/path/to/Kit.xpm" "$HOME/Downloads/My groove.take.json" \
  --output "work/My groove render"
uv run mpc-bundle-verify "work/My groove render"
```

Listen to `listen.wav` and use `pattern.mid` for the MPC. The folder also holds the editable take, the resolved MIDI notes in `pattern.json`, and the selected sample and frame offset for each hit in `listen.json`. The renderer checks the XPM, bank and sample-region fingerprints before publishing to a new folder.

Both previews implement velocity splits, pitch, note gates, same-pad mono retrigger and mute groups. The browser preserves the source channel count and plays live drum tails. The WAV renderer sums to mono and cuts tails at the loop boundary. MPC effects, envelopes, mixer settings and hardware timing require separate listening.

To hear the groove with a bass line and chords, build a [bass and chord accompaniment](../plugins/SimpleSynthStudy/README.md) from a harmony recipe and the SDK Simple Synth. Use its individual MIDI tracks to try the parts on your Scratchpad sounds.

## Record the velocities from a pad controller

Open **MIDI pad input**, choose **Find MIDI inputs**, then select the controller’s input port. If a keyboard and drum pads share an input, choose an incoming MIDI channel to isolate the drum hits. Hover over an on-screen pad to see its MIDI note. The page uses the selected XPM bank’s actual note map.

Record an overdub as usual. MIDI note-ons retain their 1–127 velocity and arrive on the same snap grid as computer-keyboard hits. The browser displays the received channel, note and velocity. Notes outside the bank and notes shared by multiple pads show a diagnostic. Drum hits use the recorder’s short default gate. The input filter is independent of the channel used by the exported take.

MIDI access starts when you press the button. Choose **Off** to disconnect. In a browser that lacks MIDI access, the computer keyboard and on-screen pads remain available. [Web MIDI API](https://www.w3.org/TR/webmidi/)
