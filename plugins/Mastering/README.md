# Master a drum-forward mix on the MPC

On the MPC Key 37, add **Peak Finish** as a stereo insert on the MPC main output. Load **Drum push** and loop the busiest four bars. Toggle **Listen → Matched wet** and **Matched dry**. Listen for the snare attack and the space between bass and kick. Switch back to **Print** for export. The main output processes the internal MPC mix. To work on the full rig, record the stereo mix from the LiveTrak L6 and play that recording through the inserts.

## The three inserts

- **Peak Finish** applies Drive before a soft knee that starts at 80% of the selected sample ceiling. Both channels receive the same instantaneous gain. Reduction displays recent gain reduction in dB and falls by 12 dB per second. Matched wet and dry estimate relative level from stereo mean-square energy over roughly 400 ms and attenuate the louder signal. Let the loop play a couple of seconds before comparing. Print uses the full processed level. The ceiling bounds digital sample peaks in Print mode. Inter-sample peaks and loudness in LUFS require separate measurement.
- **Stereo Focus** narrows the side component below Frequency. Try **Center the sub**, switch Listen to **Mono** to check the bass, then **Sides** to hear what remains at the edges. Turn Bass focus back toward zero if the Wurli loses body. Return Listen to **Stereo** before printing. Focus at zero in Stereo preserves the input. The bass filter has a gradual first-order slope.
- **Section Check** passes stereo audio through unchanged. Set Capture to **A**, play the verse once, then select **Hold**. Select **B** and play the return, then Hold again. Recording follows the running transport, including silence within the section. Selecting A or B again starts a fresh measurement of that slot. The Status page shows **A and B** when both have captured signal. **RMS B-A** measures the difference in average stereo energy, **Peak B-A** the difference in the loudest sample on either channel, and **Crest B-A** the change in peak relative to RMS. If RMS rises 3 dB and peak stays still, crest falls 3 dB. The magnitude of each delta depends on the passage you choose. Measurements are temporary and clear on plugin reset. Read the displayed text for meter values.

For a chain, place **Stereo Focus → Peak Finish → Section Check**. Take section readings with Peak Finish in Print and Stereo Focus in Stereo. To compare a treatment, measure the same two passages again after the change. An MPC insert also affects anything subsequently routed through it during export.

## Install and build

Each effect has a package under **SD / VST2 Plugins /** named **FG Scratchpad - VST - Peak Finish**, **FG Scratchpad - VST - Stereo Focus**, or **FG Scratchpad - VST - Section Check**. Keep the whole package together, including its skins and VST directories. Use the External Plugins effects picker in compatible developer-firmware setups. The packages include arm32 and arm64 builds. The controls, audio and project-state behavior have software coverage. Hardware acceptance includes checking that the meter text refreshes as the Key 37 plays.

From the repository root, with the Akai SDK and cross-compiler configured:

```bash
sdk=/path/to/mpc-plugin-builder-sdk
for plugin in PeakFinish StereoFocus SectionCheck; do
  python3 "$sdk/tools/build.py" "plugins/$plugin" --target all
done
c++ -std=c++17 -O2 -I"$sdk/framework" plugins/Mastering/session.cpp -ldl -o /tmp/mastering-test
/tmp/mastering-test plugins/{PeakFinish,StereoFocus,SectionCheck}/build/native/*.so
```

Copy the named package inside each plugin's build directory to the SD folder above. The native tests cover ceiling behavior, channel linkage, RMS-matched comparisons, mono and side isolation, low-frequency narrowing, section recapture, silence, stopped transport and block-size changes.

Check a bounced mix on the laptop with [Export loudness](../../docs/export-loudness.md).
