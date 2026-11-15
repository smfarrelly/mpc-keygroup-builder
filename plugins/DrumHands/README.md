# Start a groove from the drum seat

Add **Drum Seat** to one Plugin track. Play a backbeat with your right hand and tuck quiet left and right taps around it. At the default setting, those quiet notes carry a second, pitched line. Play two or three hits and leave a beat open to hear an answer. Press Record on the MPC to keep the performance. All five plugins synthesize their sounds and fit in the project without an external sample library.

**Find the first example on the card:** `SD / Projects / Drum Hands / 01 Drum Seat - ghost line.wav`. Listen for eight bars at 100 BPM. The first bar establishes the kit, the second adds ghost notes, and bar six changes the root. The same folder contains the editable pad strokes as `01 Drum Seat - ghost line.mid`.

## Drum Seat · a band on one track

Open **External Plugins → Drum Seat** on a Plugin track. In **PADS**, switch **Learn Hands** on. Tap your preferred left pad, then a different right pad. The switch turns off when both are assigned. Both inputs are stored in the project and survive a sound preset change. Switching Learn off before the second tap cancels the change. A learned note takes priority over that note's usual role. The factory centre notes 36 and 37 are also available unless reassigned.

- **Ghost notes** gives strokes below velocity 60 a clear melodic voice. The backbeat stays on the kit.
- **Sticking** follows alternating hands, doubles, flams and rims. **Accents** voices the hits at velocity 98 and above as dyads.
- **Rests only** lets the pitched response occupy the gaps. **Reply Gap** controls how much space to leave. After a phrase you like, enable **Keep Call** to reuse its rhythm. A single hit followed by a gap cues a kept call.
- Play a key sending MIDI 48–79 to choose the root. Turn **Drum Level** down to hear just the melodic lines. The reply still listens to your strokes. Dry drums, melody and replies share a stereo output.
- Four built-in sounds are available to hosts exposing VST presets: **Ghost Line**, **Accent Stabs**, **Trade Phrases** and **Two Mallets**. The BAND and KIT pages expose their settings directly.

## Split Cycle · play two loop lengths at once

On a Plugin track choose **External Plugins → Split Cycle**. Start transport and strike notes **36** and **37** together. The woody left voice comes around every three eighth notes. The metallic right voice comes around every four. They meet again six quarter notes later. Tap another hit off the downbeat and switch **Write Hits** off to solo over the loops. You hear every tap immediately, even when its stored repeat snaps to the grid.

- **36 / 38 / 40** play the three left-hand pitches. **37 / 39 / 41** play the right. The left and right loops each range from two to eight eighth notes.
- **42 / 43** mute or unmute a lane. **44** undoes the last pattern edit, including a lane clear. **46 / 47** clear left or right. Undo is available in the current editing session.
- **Feel** stores the hit to the nearest 1/96 quarter note. **Sixteenth**, **Eighth** and **Triplet** snap to coarser grids. Replaying the same sound at the same stored position replaces its velocity. Each lane holds 96 distinct sound/position pairs.
- Shortening a lane hides strokes beyond its new end. Lengthening it brings them back. With transport stopped, the first strike starts a local clock. Pressing Play aligns both patterns to song position. A sequence wrap restarts the cycles at that song position. Use a six-beat multiple for a seamless default 3-against-4 return, such as a three-bar 4/4 sequence.
- The project saves both patterns and lane settings. To hear a keeper by itself, save with **Write Hits** off, reopen and press Play on an empty sequence. Rehearsal MIDI 02 is a performance of overdubs, mutes and undo designed to start with **empty lanes** and **Write Hits** on.

## Ghost Wire · two sticks, a kick and a hat pedal

On a Plugin track choose **External Plugins → Ghost Wire**. Alternate left and right centre strokes (36/37), ghost one, then accent a rim (38/39). The two hands excite slightly different shell modes and stereo positions. Velocity changes how much wire and rim you hear.

Hold **40/41** for independent press rolls. A note-off stops new bounces and lets the shell ring. Key pressure changes that hand's roll speed and rebound strength when the controller sends polyphonic pressure. Channel pressure affects both hands. **42/43** are cross-sticks, **44** damps both shells, **45** is the kick and **46/47** are closed and open pedal hats. **Snares** controls wire level, **Tension** tunes the shell, **Damping** shortens the tail and **Buzz Rate** sets the rebound speed.

## Rudiment Keys · a melody from sticking

Choose the instrument and play **L R L L / R L R R** on notes 36/37. Alternating strokes walk through the scale. A double takes a neighboring pitch. A left accent returns to the root and a right accent starts a descent from the fifth. A ghost below velocity 48 plays a short version of the last note without advancing the walk.

Use **38/39** for dyads, **40/41** for flams with a 22 ms grace interval, **42** for bass pedal, **43** to damp, and **44** to return to the beginning of the walk. Choose minor or major pentatonic, Dorian or natural minor. Keys sending MIDI 48–84 change the root. Start a recorded take with an accent or a Home stroke when you want a definite starting pitch.

## Rest Reply · let your existing drum track start a conversation

Put **External Plugins → Rest Reply** in an **insert slot** on an existing kit or drum submix. Play at least two distinct transients closer together than the selected gap, then stop. The effect remembers up to four recent hits. It turns their dynamics into pitches and answers in the space. An incoming stroke fades the answer and cancels unplayed notes. Raise **Sensitivity** for a quiet source. Allow some output headroom when raising **Reply Level**.

**Echo** follows the learned timing, **Reverse** reverses the spacings and accents, and **Double time** halves the spacings. The final note lands on the chosen root. The learned spacing has 1/16-quarter resolution with a maximum 31 steps per interval. **Keep Call** stores the last complete call for reuse at the current tempo. The project stores its rhythm and strengths. A fresh single stroke cues it after reopening. Find the dry and processed comparison in rehearsal 05.

## Find the files

On MPC OS 3.10.1 or later, enable **Enable Enhancements** and **External Plugin Support** in **Preferences → Enhancements (Beta)**. Choose the instruments in the Plugin track selector, and Rest Reply in the insert selector. Each package contains the binaries and its screen layout.

- `SD / VST2 Plugins / FG Scratchpad - VST - Drum Seat /`
- `SD / VST2 Plugins / FG Scratchpad - VST - Split Cycle /`
- `SD / VST2 Plugins / FG Scratchpad - VST - Ghost Wire /`
- `SD / VST2 Plugins / FG Scratchpad - VST - Rudiment Keys /`
- `SD / VST2 Plugins / FG Scratchpad - VST - Rest Reply /`

For the exact paths to all five listening takes and the dry comparison, use [the card's start sheet](START%20HERE.txt). Every performance has a stereo PCM WAV and a matching Standard MIDI format 0 file. Each MIDI contains the **player's gestures**, including roll releases and loop edits. Synthesized replies and loop repetitions are audible in the WAV. To print your own version, record the plugin's audio on the MPC.

## Optional Launch Control page

The [four-encoder worksheet](../../midi/sdk-examples/drum-seat.toml) exposes Follow, Melody Level, Reply Level and Reply Gap. It uses channel 8 and slot 10 as an alternate layout. The faders stay available for the MPC mixer. The SDK indices are verified against the build. MPC MIDI Learn assignments require a device session. To create a local companion without installing a plugin or connecting the controller:

```bash
uv run mpc-plugin-companion midi/sdk-examples/drum-seat.toml --sdk-dump plugins/DrumSeat/params.reference.json --output work/drum-seat-controls.html
```

## Build, rehearse and verify on Linux

From the toolkit root, set `sdk` to a checkout of the [pinned Akai SDK](https://github.com/inmusic-software/mpc-plugin-builder-sdk/tree/febd2ca5bd9eb16c4a412837196e145566bc981b). The build uses the common percussion header and Drum Seat uses the three component instruments' source in this repository.

```bash
for plugin in DrumSeat GhostWire RudimentKeys RestReply SplitCycle; do
  python3 "$sdk/tools/build.py" "plugins/$plugin"
  "$sdk/.sdk-tools/host_sim" plugins/"$plugin"/build/native/*.so test --notes 36,37,40,41 --playing
  for cpu in arm32 arm64; do
    uv run mpc-sdk-package plugins/"$plugin"/build/FG* --target "$cpu" --sdk-dump "plugins/$plugin/build/params.json"
  done
done
c++ -std=c++17 -O2 -I"$sdk/framework" plugins/DrumHands/tests/session.cpp -ldl -o /tmp/drum-hands-test
/tmp/drum-hands-test plugins
uv run python plugins/DrumHands/rehearsal.py --sdk "$sdk" --output "work/Drum Hands Rehearsal"
uv run mpc-bundle-verify "work/Drum Hands Rehearsal"
```

To assemble a card-ready directory, add `--include-plugins` to the rehearsal command and choose a new output folder. Copy the five complete folders under `VST2 Plugins` and the `Projects/Drum Hands` folder onto the card. The bundle contains only the new instruments and their rehearsals.

The test host exercises the native shared objects with timestamped MIDI, stereo audio, transport, plugin presets and opaque project-state chunks. It measures pitches and reply timing, changes audio callback sizes, and reloads new instances. Standalone discovery, pad feel, physical pressure transmission and project recall on the Key 37 still require a listening session.

### Exercise the packaged ARM binaries before a device session

The same host can open the shared objects inside the card's manufacturer-prefixed folders. On Linux, use a Zig cross compiler, QEMU user-mode emulator, and an ARM glibc sysroot. For the original Key 37 package:

```bash
"$zig" c++ -std=c++17 -O2 -UNDEBUG -target arm-linux-gnueabihf.2.31 -mcpu=cortex_a17 \
  -I"$sdk/framework" plugins/DrumHands/tests/session.cpp -ldl -o /tmp/check-drum-hands-arm32
qemu-arm-static -L /usr/arm-linux-gnueabihf /tmp/check-drum-hands-arm32 \
  --packages "$card/VST2 Plugins" arm32
```

For ARM64, use `-target aarch64-linux-gnu.2.31 -mcpu=cortex_a55`, `qemu-aarch64-static`, the AArch64 sysroot and the `arm64` package argument. `-UNDEBUG` enables the assertions in the cross-compiled host. This verifies the deployable binaries' DSP and state behavior under emulation. Device CPU headroom and standalone host behavior remain hardware checks.
