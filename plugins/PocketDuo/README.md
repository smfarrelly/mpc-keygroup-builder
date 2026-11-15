# Pocket Duo

Pocket Duo is a standalone MPC plugin instrument. One track synthesizes a 16-pad drum kit and a monophonic bass voice. The kick supplies the timing. The plugin remembers the notes it actually played, including ghost hits and generated pickups. Both instruments share a stereo output and have independent level controls.

## First four hits

1. On a Plugin track choose **External Plugins → Pocket Duo**. The package lives at **SD / VST2 Plugins / FG Scratchpad - VST - Pocket Duo /**. On MPC OS 3.10.1 or later, external plugins require both switches under **Preferences → Enhancements (Beta)**.
2. With **Keep Pass** off, strike the kick four times, making the second hit soft. The default bass phrase plays C, C, G, E-flat. Each stronger hit advances the pitch order. A hit below velocity 50 repeats the previous pitch with a short gate. MIDI notes 36 and 37 are the kicks. Notes 38–51 play the other kit pieces. Notes 42 and 43 choke each other's hat tails. You can start playing with the transport stopped.
3. Turn on **Keep Pass**. It takes the most recent completed, nonempty pass. Before the first pass finishes, it takes the partial phrase with space to the end of the bar. Play the transport to hear the loop from the project timeline. With the transport stopped, engaging Keep starts local playback immediately.
4. Leave **Keep Pass** on, save the MPC project under a new name, reopen it and press Play. Listen for the same timing, ghost hit and bass pitches. Turn on **Live Drums** to replace the kept drum part with your own playing while the captured bass loops. Turn Live Drums off to hear the saved kit again.

## Shape the phrase

- **Learn Pitches** accepts up to eight note-ons in order. Turn it on, play a few keys, then turn it off to return to the kit. Repeated pitches are allowed. The two kicks share a pitch cursor.
- **Bass Activity** below 30 leaves space on alternating kick strikes. The middle range follows your played accents. At 75 and above, kicks of velocity 100 or greater can add an eighth-note pickup on the next learned pitch. Another kick before that pickup replaces it. Changing Activity after keeping a pass preserves its bass notes.
- **Pass Length** sets one, two or four 4/4 bars for new captures. The clock follows host tempo where available and uses 120 BPM otherwise. During free play the first pad strike starts the local clock. With the transport running the plugin follows the host's quarter-note position when available. The keeper stores onset and gate in beats, so the loop follows tempo changes.
- **Bass Level** and **Drum Level** balance the two voices. Try bass alone to hear how a quiet pickup changes the groove.

The project stores one keeper and the learned pitches in the plugin state. Turning Keep off resumes live capture; keeping another pass replaces the old one. Save another project version to retain both. A pass can hold 1,024 drum and bass events combined. Keep declines a pass exceeding that capacity. Save with Keep on for immediate recall on Play. The kept notes play inside this plugin. The browser studio remains the route to separate, editable MIDI and MPC tracks.

## Software checks

Use the SDK revision pinned in the repository's SDK workflow. From the repository root, set `sdk` to that checkout and `zig` to the Zig executable:

```bash
plugin=plugins/PocketDuo
python3 "$sdk/tools/build.py" "$plugin" --zig "$zig"
"$sdk/.sdk-tools/host_sim" "$plugin/build/native/pocket-duo.so" test --notes 36,38,42 --playing
c++ -std=c++17 -O2 -I"$sdk/framework" "$plugin/tests/session.cpp" -o "$plugin/build/session"
"$plugin/build/session" "$plugin/build/Three passes.wav"
c++ -std=c++17 -O2 -I"$sdk/framework" "$plugin/tests/reopen.cpp" -ldl -o "$plugin/build/reopen"
"$plugin/build/reopen" "$plugin/build/native/pocket-duo.so"
```

The audio example is six seconds: a performed bar, the recalled bar, then the retained bass with a new drum hit. The Linux binary test saves through the VST host interface, unloads the library, loads a fresh instance and compares its stereo render and state bytes. First load, pad mapping, timing feel and actual project save/reopen on the Key 37 remain hardware checks.
