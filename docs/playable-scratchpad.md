# Sit down and play the Scratchpad

For a snare kit, a ghost-note melody and call-and-response on one track, open [Drum Seat](../plugins/DrumHands/README.md). For independently looping hands, try [Split Cycle](../plugins/DrumHands/README.md#split-cycle--play-two-loop-lengths-at-once).

For a drum and bass instrument with its own performance keeper, add [Pocket Duo](../plugins/PocketDuo/README.md) to a Plugin track.

To perform a part first and decide what to keep afterward, [open the retrospective recorder](keep-that-take.md).

On the studio laptop, open `work/Playable Scratchpad/index.html`. Switch between Vinyl SP, Vinyl Layered and Pocket Layers while the four bars loop. The kit changes at the same playhead position. Listen for the quiet snare just before beat four, the open hat at the bar line, and the roll in the last bar. Each version uses its own kick, snare and hat pad assignments. The renders use the same hit times and velocities and share one RMS level with headroom for all three kits.

## Start an idea

After copying the bundle's **Projects** and **VST2 Plugins** directories to the SD root, use the MPC browser to open one of these files. Keep each XPJ beside its matching ProjectData folder.

- **SD / Projects / Playable Scratchpad / 01 Sit Down.xpj** opens a blank four-bar sequence at 120 BPM with Vinyl SP selected. Record the drums, overdub Mirage Pluck Bass, and add the Wurli. Dark FM, Glass Howl, Sub Smooth and Shots are loaded for later parts. Save your idea under a new name.
- **SD / Projects / Playable Scratchpad / 02 Four Bar Jam.xpj** contains the drums, bass and Wurli you recorded on the MPC. It opens with the same sounds and mixer routing. Press play to hear the original note timing and dynamics.

**Pocket Layers Print** and **Bloom Keys Print** are sampled tracks in both projects. The drum print captures the first strike of each velocity layer, with its pad colors and mute groups. The keys print samples every six semitones and captures up to four seconds per root. The native instruments below supply the changing hits, continuous held notes and live macros.

## Play the three plugins

From the plugin instrument browser, add **Pocket Layers** or **Bloom Keys** to a new Plugin track. For **Beat Catch**, open an insert on **Submix 3** and select the effect. The source capture for these projects predates these plugins. A project with saved native instances and their MIDI Learn bindings still needs a save/reopen on the Key 37.

- **Pocket Layers.** Strike the same snare softly, then above velocity 96. Accent Point moves the transition. Repeated hits cycle through sounds of the same family. Shell Ring changes the decay of kicks, toms and snares. Hat Opening lengthens the hat tails while the closed hat still cuts the open hat. The private package uses your layered Vinyl samples. The source builds a synthesized practice kit when installed without that bank. Default MIDI notes 36–51 address the 16 slots in order. Choose Source XPM to follow the original drum note map.
- **Bloom Keys.** Tap middle C for a short pluck, then hold it to hear the body open. Play a second note before releasing the first to glide. Bloom sets the strength of the sustained harmonics, Bloom Time sets their rise, and Glide sets the transition between held notes. Middle C sounds one octave down.
- **Beat Catch.** Play a fill with Catch off. Turn it on at the next downbeat to freeze the preceding beat. Repeat Size selects the full beat or its last half, quarter or eighth. Keep playing over it, then switch Catch off to release the repeats. Tone and Return adjust the repeat. The effect records continuously while processing, so let a beat play before the first catch.

## Launch Control

The saved Boot-template mixer mappings use channel 16. CC5 balances keys on Submix 1, CC6 bass on Submix 2, CC7 drums on Submix 3, and CC12 the MPC stereo output. The L6 controls the overall MPC feed alongside your hardware instruments.

The generated **XL3 controls.csv** is the MIDI Learn worksheet for a custom page. The eight top encoders on channel 8 use CC20–27 for Accent Point, Shell Ring, Hat Opening, Bloom, Bloom Time, Glide, Repeat Size and Tone. Upper button 1 uses CC52 in toggle mode for Catch. Keep your mixer assignments on the faders when preparing that page. Each worksheet row is checked against the plugin's actual parameter dump. Rebuild after editing [controls.toml](../plugins/PlayableScratchpad/controls.toml).

## Rebuild on Linux

Install the project and prepare the [Akai SDK and cross compiler](akai-sdk.md). Use the SDK revision pinned in the repository's SDK workflow. Set `sdk` to the SDK checkout and `zig` to the Zig executable. From the repository root:

```bash
for plugin in PocketLayers BloomKeys BeatCatch; do
  python3 "$sdk/tools/build.py" "plugins/$plugin" --zig "$zig" || exit 1
done
uv run python plugins/PlayableScratchpad/smoke.py "$sdk"
uv run python plugins/PlayableScratchpad/build.py \
  --sdk "$sdk" --vinyl "$vinyl_sp_xpm" --layered "$layered_main_02_xpm" \
  --master "work/project-captures/2026-08-27-scratchpad-v02/FG Vinyl Scratchpad v02 Master.xpj" \
  --jam "work/project-captures/2026-08-26-scratchpad-volca/FG-scratchpad-v0-1-test-Jam.xpj" \
  --boot "work/project-captures/2026-09-03-startup-templates/Boot.xpj" \
  --output "work/Playable Scratchpad"
uv run mpc-bundle-verify "work/Playable Scratchpad"
```

Set the two XPM variables to your source program files. The full private project build uses the named captures and their samples. Use a new output directory on each build. The three plugins and software smoke test build independently of those captures. The builder checks the two ARM binaries for each plugin, runs the native host simulator, resolves both projects' sample paths and verifies the bundle checksums. Private samples, renders and XPJs stay in the local output.

## Next hardware session

1. Open **01 Sit Down**. Play the main kit and the two printed tracks. Record four bars, save under a new name, and reopen.
2. Load the native Pocket Layers and Bloom Keys. Try a ghost-to-accent snare roll, an open-to-closed hat, and a held-to-legato key phrase. Compare the original Vinyl SP by feel.
3. Insert Beat Catch on the drum submix and catch the final beat of a fill. Check that bass and keys continue dry.
4. Learn a drum macro, a keys macro and the Catch button using the worksheet. Move the mixer faders, save this as a separate project, then reopen and check the sound and the mappings. That saved XPJ provides the native identifiers for the next template revision.
