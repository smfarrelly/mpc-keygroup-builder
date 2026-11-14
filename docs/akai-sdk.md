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
