# FG Found Transitions 01

An eight-pad Drum candidate for punctuation and transitions over an existing
groove. It complements the accepted Body Kit/S950 texture banks rather than
replacing the main kit. Hardware acceptance is pending.

## Load location

Deployed October 30, 2026, with an 8 MiB write probe and checksum-verified
publication. SD destination:

`00 FG Hardware Tests/Found Transitions 01/FG Found Transitions 01.xpm`

Local package: `work/generated-drum-programs/FG Found Transitions 01`.

## Play it

- A01: Big Impact, 6.63 seconds.
- A02: Pipe Impact, 5.26 seconds.
- A03: Depth Charge, 2.58 seconds.
- A04: Tape Rewind, 6.82 seconds.
- A05: Reverse Pipe, 1.62 seconds.
- A06: Reverse Bottle, 1.56 seconds.
- A07: Reverse Glass, 2.27 seconds.
- A08: Fire Woosh, 0.60 seconds.

A01-A04 have no shared choke group. A05-A08 share Mute Group 1. Each pad
restarts its own one-shot on retrigger; holding a pad does not sustain a loop.
All eight populated pads use the established purple FX color. A09-A16 and
Banks B-H are intentionally empty. This is a one-shot Drum Program, not a
tempo-warped Clip Program; reverse sweeps must be played early enough to land
their endings where you want them.

When ready for a short audition, play A05 then A08 to check sweep interruption,
then A01 followed by A08 to confirm the impact continues. Record a transition
over a loop and save/reload under a new project name. Judge timing, useful
levels, and whether this adds a role worth retaining. No new hardware testing
is required before continuing software work.

## Source coverage and selection

The local source index contains 60 Tape/Trumpet Fragments records, including
57 software-built Keygroups. Databenders has 16 records, with 11 deferred
Keygroups and only two software-built Keygroups; deferred records are not safe
automatic conversion targets. Found Sounds has 16 records classified as 13
Drum and three Clip sources. Those classifications do not prove that every
Drum source is missing from the card.

The October 30 card inventory already includes Dr Sample texture programs,
Tape Fragments/Vinyl Synths FX Keygroups, and the accepted Found Sounds Body Kit
inside Breaks Texture. It does not list a dedicated Found Sounds FX Textures
program. This candidate therefore creates a focused pad layout from its Clean
one-shots. It is not a claim that these audio files have never appeared in any
other package or project. No duplicate vendor conversion is needed for the
already-present texture families.

## Rebuild from owned source files

Obtain Found Sounds From Mars from Samples From Mars and use its
`WAV/FX Textures/Clean` folder as `--source-root`. The repository does not
distribute its licensed WAVs or generated programs. From the repository root:

```bash
uv run mpc-drum-build inventory/fg-found-transitions-01.toml \
  --template "/path/to/FG Vinyl Layered Main 02.xpm" \
  --source-root "/path/to/Found Sounds From Mars/WAV/FX Textures/Clean" \
  --output "work/generated-drum-programs/FG Found Transitions 01"
```

The template must be an XML Drum Program with 128 instrument slots. The builder
copies the eight source WAVs beside the XPM and rewrites the populated sample
references. It refuses a nonempty output directory. Each pad declares
`color_category = "fx"` in the recipe, since vendor names such as `BigImpact`
do not match generic filename classification. The single build command now
sets the intended colors without a postprocessing script. See
[declarative pad colors](../docs/drum-recipe-colors.md) for other categories.

## Software validation

The initial package contains nine files, 8,890,849 bytes. Eight active pads,
eight single layers, one-shot playback, Mute Group 1 only on A05-A08, and purple
colors were checked. Model, sample-reference, and Drum audit checks pass. The
Drum audit still reports filename categories as `unknown`; explicit FX colors
were verified separately. The initial deployment used a color-only pass that
changed only ProgramPads; subsequent builds declare the same colors directly
in the recipe. No update to the already deployed candidate is required.

All copied WAV bytes match the source; full PCM reads are nonempty and complete.
Source peaks are approximately -6 dBFS; no normalization or processing was
applied. Simultaneous voices can still sum above that level. These checks do
not establish perceived loudness, musical quality, or hardware choke behavior.
Private validation evidence is in
`work/instrument-audit-2026-10-30/transitions-validation.json`.
