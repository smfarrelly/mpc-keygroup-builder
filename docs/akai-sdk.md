# Use Akai SDK plugins with the mapping toolkit

Start with the included Stereo Delay parameter dump. You can search the controls, compile a four-encoder Launch Control XL 3 worksheet, and open the offline companion on your computer. The example uses Sync mode. The encoders set rhythmic division, high cut, feedback and wet/dry mix. All eight faders stay available for the MPC mixer.

From the repository root:

```bash
dump=tests/fixtures/sdk/stereo-delay.json
page=midi/sdk-examples/stereo-delay.toml

uv run mpc-plugin-params "$dump" --query feedback
uv run mpc-plugin-map check "$page" --sdk-dump "$dump"
uv run mpc-plugin-map compile "$page" --sdk-dump "$dump" --output work/sdk-delay/worksheets
uv run mpc-plugin-companion "$page" --sdk-dump "$dump" --output work/sdk-delay/companion.html
```

Open `work/sdk-delay/companion.html` in a browser. The example proposes channel 8 and uses the existing MultiTap worksheet’s slot 10 as an alternate. All fifteen slots in the rig plan already have assignments. Choose a slot when you actually want to change a controller mode.

## Use your own build

Akai's SDK builds trusted plugin source on Linux, macOS or Windows. Its native host simulator exports `build/params.json`. The toolkit reads that JSON as data. You can use the same commands with a dump from another computer. The simulator exposes plugin-local indices, automation flags, startup values, units, and display text. Its control types and choice lists are inferred from displayed values. A blank MPC ID means that a saved MPC MIDI Learn target is still unknown.

For a Linux machine with a C++ compiler, run these commands in the SDK checkout:

```bash
python3 tools/build.py examples/StereoDelay --target native --toolchain gcc
.sdk-tools/host_sim examples/StereoDelay/build/native/stereo-delay.so test
```

The original Key 37 takes an arm32 build on MPC OS 3.10.1 or later with external plugin support enabled. Native simulator results describe desktop behavior. Actual MPC CPU load, controller pickup and project recall need a later device session. The existing XPM instruments and their sample paths have a separate deployment workflow.

- [Akai SDK and installation guide](https://github.com/inmusic-software/mpc-plugin-builder-sdk)
- [SDK simulator and parameter format](https://github.com/inmusic-software/mpc-plugin-builder-sdk/tree/febd2ca5bd9eb16c4a412837196e145566bc981b/tools/host-sim)
- [Stereo Delay example used for the checked-in metadata fixture](https://github.com/inmusic-software/mpc-plugin-builder-sdk/tree/febd2ca5bd9eb16c4a412837196e145566bc981b/examples/StereoDelay)

## Prepare a page and review changes

```bash
uv run mpc-plugin-seed "Stereo Delay" --sdk-dump "$dump" --slot 10 --channel 8 --limit 4 --output work/sdk-delay/draft.toml
uv run mpc-sdk-compare "$dump" /path/to/new/build/params.json --json
```

The seed skips controls the SDK reports as non-automatable, reserves the faders, and pins the plugin’s vendor and signed numeric UID. Edit the seed to select the gestures you want. Each mapping pins its parameter name and index. Compilation checks those pins against the current dump. The comparison checks all indices, including unused ones. It exits with status 2 for changes that need mapping review, including moved or removed parameters, changed choices or units, a different plugin identity, and changed automation flags. An appended control or a new startup value is reported as informational. Two matching dumps establish agreement on the reported fields only.

See the [existing performance pages](plugin-mapping.md) for the commercial plugin workflow and [parameter guide](plugin-parameters.md) for the catalog formats.

## Check a built package on the laptop

```bash
uv run mpc-sdk-package "/path/to/build/MPC SDK Examples - VST - Stereo Delay" \
  --target arm32 --sdk-dump /path/to/build/params.json --json
```

This read-only check follows the package manifest to the binary for the selected CPU. It inspects the ELF header, executable load segments, ARM32 hard-float flags, package name, and portable paths. A supplied simulator dump adds plugin identity, instrument/effect and channel-count comparisons. The result includes the file hash and expected location under `VST2 Plugins`. It works on Ubuntu without the SDK, cross compiler, SD card or MPC. Use Akai’s validator for skins and symbol dependencies, and the simulator for audio processing. [Akai package format](https://github.com/inmusic-software/mpc-plugin-builder-sdk/blob/main/docs/plugin-folder-format.md)

## Try the project's Loop Throw effect

[Loop Throw](../plugins/LoopThrow/README.md) is a drum-submix insert with a dedicated send gesture. Open Throw for the hit you want to repeat and close it while the dry loop keeps playing. Its source, four-encoder worksheet, reference parameter dump and offline impulse tests are in the repository. You can build its companion immediately:

```bash
uv run mpc-plugin-companion midi/sdk-examples/loop-throw.toml \
  --sdk-dump plugins/LoopThrow/params.reference.json --output work/sdk-delay/loop-throw.html
```

## Choose your own controls in a browser

Open [Design an SDK encoder page](../site/sdk-mapping.html) from the offline site. It starts with Loop Throw. Choose another local host simulator dump, search by control name, unit or choice, and select controls in the order you want on encoders 1–8. Download the TOML and validate it with the same dump:

```bash
uv run mpc-plugin-map check my-encoders.toml --sdk-dump /path/to/build/params.json
```

The editor assigns CC 20 through 27 in selection order. Removing a control shifts the later assignments left. Export a draft before leaving the page or switching plugins.

## Save a reproducible software review

After building your trusted plugin, run the simulator, parameter comparison, package check and worksheet compiler together. Set `sdk` to the SDK checkout. Run from the toolkit root:

```bash
plugin=plugins/LoopThrow
uv run mpc-sdk-review "$plugin/build/native/loop-throw.so" \
  --host-sim "$sdk/.sdk-tools/host_sim" \
  --profile midi/sdk-examples/loop-throw.toml \
  --baseline "$plugin/params.reference.json" \
  --package "$plugin/build/FG Scratchpad - VST - Loop Throw" \
  --output work/loop-throw-review-01
```

Open `review.json` for the software result and hashes of the tested desktop binary, simulator, parameter dump and checked ARM binary. The folder also contains the raw simulator log, new dump, worksheets and offline companion. The native library and simulator run as local code. For third-party packages you only want to inspect as files, use `mpc-sdk-package`.

An instrument accepts a comma-separated note list, for example `--notes 36,38,42`. The simulation uses playing transport. Warnings and failures produce exit code 2 and a review for diagnosis when a complete run is available. An unreadable dump or timeout aborts before publication. Use a new output directory per run. Hardware status stays untested.

Supplying a built package also brings its declared screen and program Q-Link assignments into the worksheets and companion. Compare those locations with your proposed XL3 page before dedicating encoders to a control that is already easy to reach. A checked dump detects Q-Link references outside the plugin’s parameter list. The software review writes a checksum receipt over the full packet. Verify a copied or archived packet with `uv run mpc-bundle-verify work/loop-throw-review-01`.

### Find the physical controls affected by an update

```bash
uv run mpc-sdk-compare original/params.json updated/params.json \
  --profile midi/sdk-examples/stereo-delay.toml
```

The comparison first validates the page against the original plugin. It names the affected encoders or buttons with their channels, CCs and changed fields. A changed unit on Mix flags encoder 4 on the example page. A change to its unused free-delay-time control remains visible in the full list and leaves the page compatible. With `--profile`, the exit code follows the page-specific result. A software review with both a profile and baseline uses the same rule.

## Instrument pages for the SDK examples

Two additional four-encoder pages are available as alternatives for the same worksheet slot. Build the corresponding SDK example using the native instructions above, then check the page against its generated dump. Use one page at a time.

- **Drum Articulation** exposes kick decay, snare decay, closed-hat decay and open-hat decay. It suits a drummer who wants to change how much space a repeating groove leaves between hits. [Drum Synth worksheet](../midi/sdk-examples/drum-synth.toml)
- **Bass Movement** exposes cutoff, resonance, filter-envelope amount and glide on Simple Synth. It gives a recorded bass phrase four live gestures. [Simple Synth worksheet](../midi/sdk-examples/simple-synth.toml)

```bash
uv run mpc-plugin-map check midi/sdk-examples/drum-synth.toml --sdk-dump "$sdk/examples/DrumSynth/build/params.json"
uv run mpc-plugin-map check midi/sdk-examples/simple-synth.toml --sdk-dump "$sdk/examples/SimpleSynth/build/params.json"
```

### Listen to a simulator review

Add `--preview` to `mpc-sdk-review` to keep the main stereo pass in the packet. For example, from the checkout with the Drum Synth example already built:

```bash
uv run mpc-sdk-review "$sdk/examples/DrumSynth/build/native/drum-synth.so" \
  --host-sim "$sdk/.sdk-tools/host_sim" --profile midi/sdk-examples/drum-synth.toml \
  --notes 36 --preview --output work/drum-synth-kick
```

Open `work/drum-synth-kick/preview.wav` to hear the synthesized kick. Use note 37 for snare, 39 for closed hat and 40 for open hat. Multiple requested notes sound together. For effects the simulator supplies its own sine and noise input. The file covers the two-second main pass at 44.1 kHz. The packet includes its peak, RMS, near-full-scale fraction and PCM checksum. Preview files are optional and use about 345 KiB each.
