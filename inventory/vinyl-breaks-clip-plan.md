# Vinyl Breaks Clip Program plan

## Source audit — August 27, 2026

Vinyl Breaks From Mars contains 200 stereo 44.1 kHz WAV loops and one Ableton
Live project. It contains no MPC XPM, XPN, or XPJ reference from which to infer
Clip Program serialization safely.

`mpc-loop-inventory` indexed the complete WAV folder with no unreadable files,
unparseable BPM names, or timing deviations greater than 0.05 beats:

- BPM range: 73–200 across 51 distinct tempos.
- 36 full breaks, 41 no-percussion variants, 20 no-snare variants, 50
  percussion loops, nine explicitly pitched variants, and 44 clean, colored,
  degraded, or other variants.
- 30 loops estimate to 16 beats, 157 to 32 beats, two to 34 beats, eight to 36
  beats, and three to 64 beats.

The ignored reports are:

- `work/vinyl-breaks-inventory.json`
- `work/vinyl-breaks-inventory.csv`

The 34- and 36-beat files are internally consistent with their filename BPM,
but their unusual musical lengths should be auditioned before inclusion in a
quantized Clip layout.

## Safe implementation boundary

Do not relabel a Drum Program or invent an XPM `type` value and call it a Clip
Program. The first exporter must be based on a minimal MPC-authored capture so
unknown launch, quantization, warp, tempo, mute, and project-link fields are
preserved instead of guessed.

## Required Key 37 reference capture

After the SD filesystem is repaired:

1. Start an empty disposable project.
2. Create one Clip track/program using the MPC interface.
3. Assign one short Vinyl Breaks WAV to A01.
4. Set only the desired baseline behaviors: one-bar launch quantization,
   tempo/warp synchronization if available, and exclusive switching if Clip
   Programs support it directly.
5. Save the project as `Key37_Clip_Reference_01.xpj`.
6. Save/export the Clip Program itself as `Key37_Clip_Reference_01.xpm` if the
   MPC exposes that operation.
7. Copy the XPJ, XPM, and companion ProjectData without opening or resaving
   them off-device.
8. Make one controlled setting change, save `Key37_Clip_Reference_02`, and use
   the XPJ/XPM comparison tools to isolate the changed field.

## First musical layout after capture

- Bank A: full breaks around 80–95 BPM.
- Bank B: full breaks around 96–107 BPM.
- Bank C: full breaks around 108–123 BPM.
- Bank D: high-energy 160–200 BPM breaks.
- Banks E–F: matched no-percussion and no-snare alternatives.
- Bank G: percussion-only loops.
- Bank H: pitched, colored, degraded, and transition variants.

Track 8 remains reserved for this Clip Program. A temporary one-shot Drum
Program may be generated for auditioning, but it must be labeled as an
unsynchronized audition tool and must not replace the Clip Program milestone.
