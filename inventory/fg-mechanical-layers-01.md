# FG Mechanical Layers 01

An optional mechanical-percussion Drum candidate, separate from the accepted
Scratchpad. Eight pads switch between the original Clean and Tube one-shots:
velocities 0–63 use Clean; 64–127 use Tube. This is a deliberate timbre switch,
not true sampled dynamics, round robin, or an exact Ableton conversion.

## Location and pad map

Deployed October 30, 2026, using an 8 MiB write probe and checksum verification.
SD location:

`00 FG Hardware Tests/Mechanical Layers 01/FG Mechanical Layers 01.xpm`

Local package: `work/generated-drum-programs/FG Mechanical Layers 01`.

- A01: Elevator Impact.
- A02: Fridge Door Slam Attack.
- A03: Tape Clunk.
- A04: CD Tray Attack.
- A05: Ratchet 1.
- A06: Shears.
- A07: Electric Spark.
- A08: Drill Burst 2.

A01-A06 use the percussion color; A07-A08 use purple FX. A09-A16 and Banks B-H
are intentionally empty. Pads use one-shot playback and can overlap one
another; there are no cross-pad choke groups. Retriggering the same pad restarts
its voice. Only layer selection is velocity-switched; source audio is unchanged.

## Rebuild

Use the owned Found Sounds From Mars `WAV/Mechanical` folder:

```bash
uv run mpc-drum-build inventory/fg-mechanical-layers-01.toml \
  --template "/path/to/FG Vinyl Layered Main 02.xpm" \
  --source-root "/path/to/Found Sounds From Mars/WAV/Mechanical" \
  --output "work/generated-drum-programs/FG Mechanical Layers 01"
```

The recipe's [source map](../docs/drum-source-maps.md) selects both subfolders
without staging or renaming the originals. The output is self-contained.
Licensed audio and generated XPMs are not repository assets.

## Software checks and deferred listening

The initial package is 17 files, 3,756,747 bytes. The model and sample-reference
checks pass: eight populated pads, two complete non-overlapping velocity layers
per pad, expected colors, and no cross-pad mute groups. Every packaged WAV
matches its original source bytes. Each Clean/Tube pair differs by less than
1.3 dB RMS; that does not establish equal perceived loudness. Both Elevator
Impact layers are level outliers against the full 16-file median at the default
6 dB threshold. No automatic normalization was applied.

Hardware listening is pending. When convenient, play soft/hard hits across
A01-A08, check the 63/64 switch for useful contrast, record a short percussion
part over the main kit, and save/reload in a new project. The main kit and
existing favorites remain unchanged. Private validation evidence is in
`work/instrument-audit-2026-10-30/mechanical-validation.json`.

## Laptop soft/hard preview

A dry preview can exercise both layers before hardware listening:

```bash
uv run mpc-program-audition \
  "work/generated-drum-programs/FG Mechanical Layers 01/FG Mechanical Layers 01.xpm" \
  --output work/auditions/mechanical-soft-hard.wav --drum-velocities 48 108
```

Listen in pad order A01–A08, two hits per pad. Use `63 64` instead to check
selection at the switch. This checks source selection; it does not establish
hardware playback, choke/retrigger behavior, or equal perceived loudness.
