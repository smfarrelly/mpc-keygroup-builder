# Launch Control XL 3 and startup-template capture — 2026-09-03

## Preserved local evidence

The SD card was exposed by the MPC Key 37 in Controller Mode at
`/media/steve-farrelly/3561-6538`. Read-only copies of `Boot.xpj` and
`Start.xpj` were preserved under the ignored
`work/project-captures/2026-09-03-startup-templates/` directory. Their SHA-256
hashes exactly matched the mounted originals after copying.

Six Novation Components exports were moved from the loose `~/Projects` root to
the ignored `work/hardware-captures/launch-control-xl3/2026-09-03-components/`
directory:

- `1 - OPX.syx`
- `2 - Jura.syx`
- `Volca Bass.syx`
- `Volca Drum 1-3.syx`
- `Volca Drum 4-6.syx`
- `Volca Keys.syx`

The same directory contains generated `components.json`,
`boot-midi-learn-audit.json`, and `start-midi-learn-audit.json` reports. Raw
XPJ, SysEx, ProjectData, and licensed audio remain excluded from Git.

## Project inspection

Both projects were authored by MPC firmware 3.9.1.2 and contain one looping
four-bar sequence.

- `Start.xpj`: three MIDI tracks (`Volca Bass`, `Volca Keys`, `Volca Drum`),
  OPx-4 and Jura plugin tracks, 102 MIDI Learn assignments, and 13 project
  samples. Its sequence tempo is approximately 55.97 BPM.
- `Boot.xpj`: OPx-4 and Jura plugin tracks, `Vinyl SP From Mars` and
  `Vinyl Shots` Drum tracks, `Sub Smooth` and `Medium Muff Bass` Keygroups, 81
  MIDI Learn assignments, and 556 project samples. Its sequence tempo is 120
  BPM. The companion folder currently contains 569 WAV files (134 MiB on the
  mounted exFAT volume).

`Boot.xpj` is the stronger current startup-template reference. `Start.xpj`
remains useful as the earlier external-MIDI routing reference; it is not a
small variation of Boot, so their 4,463-field structural diff should not be
used to infer one isolated setting.

## Captured Custom Modes

The read-only Components parser found these primary channels and enabled
controls:

- `1 - OPX`: channel 9, 41 controls.
- `2 - Jura`: channel 10, 44 controls.
- `Volca Keys`: channel 1, 39 controls.
- `Volca Bass`: channel 2, 40 controls.
- `Volca Drum 1-3`: channel 3, 48 controls.
- `Volca Drum 4-6`: channel 3, 48 controls.

These channels are evidence from the current exports and differ from the older
declarative Volca plan (Bass 1, Keys 2, Drum 10). Do not rewrite the established
plan until the connected Volcas' receive channels and desired routing topology
are confirmed.

Against `Boot.xpj`, 37 of 41 OPx controls and 40 of 44 Jura controls have a
matching saved MIDI Learn channel/controller pair. The eight unmatched entries
are faders 4–7 (channel 16, controller numbers 8–11) in both modes. Boot has
learned faders 1–3 and 8 as Submix 1–3 and Out 1/2 volume. The Volca controls
have no MPC MIDI Learn matches, which is expected when they are routed directly
to external hardware.

## Remaining hardware questions

- Confirm the actual receive channels now configured on Volca Keys, Bass, and
  Drum; reconcile them with the captured 1/2/3 modes or the older 2/1/10 plan.
- Confirm whether faders 4–7 were deliberately left unlearned in Boot.
- Confirm the six Custom Modes survive a Launch Control power cycle.
- Confirm Boot loads automatically after a full MPC cold start and retains all
  81 MIDI Learn assignments.
- Capture the intended live keys-versus-pads routing after the startup template
  is stable; changing keyboard octave must not make the keys address Drum banks.

## Reproduce the audit

```bash
uv run mpc-xpj inspect work/project-captures/2026-09-03-startup-templates/Boot.xpj
uv run mpc-xpj midi-learn work/project-captures/2026-09-03-startup-templates/Boot.xpj
uv run mpc-launch-control inspect \
  work/hardware-captures/launch-control-xl3/2026-09-03-components/*.syx
uv run mpc-launch-control audit \
  work/project-captures/2026-09-03-startup-templates/Boot.xpj \
  work/hardware-captures/launch-control-xl3/2026-09-03-components/*.syx
```
