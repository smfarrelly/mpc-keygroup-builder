# Play a four-bar hook

On the Key 37 open **SD / Projects / Hook Rehearsal / 02 Hear the hook.xpj**. Press Play. Use Next Sequence to move through **Hook → Verse → Return**. Listen for the hats to drop out, the Wurli to leave space, and the pickup to lead back into Hook. The Mirage Pluck Bass keeps playing throughout.

To record your own take, open **SD / Projects / Hook Rehearsal / 01 Play your hook.xpj**. Record drums on pads **A01 kick, A02 snare, A03 hat, A04 pickup**. Overdub **Pluck Bass** and **Wurli** on the keyboard. Save under a new name with its samples. The drum track uses four sampled Break Relay hits in a common mute group. Load the full plugin separately for live source switching and slice cycling.

On the laptop, with the recorded sequence selected in the saved project, run:

```bash
uv run mpc-hook-rehearsal "/path/to/My Take.xpj" --output "work/My Take Sections"
```

Copy the entire output folder to **SD / Projects**. Open **SD / Projects / My Take Sections / My Take.xpj**. Hook retains your original events. Verse removes MIDI 38 hats and keeps the Wurli through the end of its first played bar. Return adds MIDI 39 in the last beat after the other drum hits, unless you already played a pickup there. Use a four-bar 4/4 take with full-length clips. Extra tracks play through all three sections. If you renamed the tracks, pass their saved names with `--drums` and `--keys`.

## Rebuild the private starter and demo

From the repository root, use the performed Playable Scratchpad XPJ, your own packed Break Relay bank, and Akai's SDK. The two outputs each carry the WAVs for all three instruments. Keep each XPJ beside its matching ProjectData folder.

```bash
python3 /path/to/mpc-plugin-builder-sdk/tools/build.py plugins/BreakRelay --target native --toolchain gcc
uv run python plugins/BreakRelay/hook_project.py "/path/to/02 Four Bar Jam.xpj" \
  --sdk /path/to/mpc-plugin-builder-sdk --content "/path/to/Break Relay/Content" \
  --output "work/Hook Rehearsal"
```
