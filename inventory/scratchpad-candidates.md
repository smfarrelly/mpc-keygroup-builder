# FG Vinyl Scratchpad v0.1 candidates

These programs pass structural and semantic tests and produced non-silent local
audition renders. The three Drum Programs have loaded and triggered expected
samples on the Key 37; the four melodic Keygroups still require hardware
listening tests.

## Provisional core for the routing capture

- Main drums: `Vinyl SP From Mars 01 FG COLORS` — broad 808-oriented Bank A
  with kick, snare, clap, rim, closed/open hats, percussion, toms, and cymbal.
- Bass: `Fisherman'sFriend` — only shortlisted bass; final approval depends on
  low-register response and release behavior on the Key 37.
- Keys: `E Piano` — only shortlisted chord/keys sound; final approval depends on
  velocity response and useful range.
- Lead: `HumanMusic` — provisionally preferred over a second pad because the
  core already has E Piano for sustained harmony.

`Provisional` means suitable for tomorrow's two-track routing experiment, not a
final musical-favorite verdict.

## Main drums — choose one after listening

- `Vinyl SP From Mars 01`
- `Vinyl Drums From Mars 01`
- `Vinyl Drum Machines From Mars 1`

## Bass

- `Fisherman'sFriend` — 101 From Mars

Replacement-round hardware results:

- `Mirage Pluck Bass` — current provisional primary bass.
- `Junos Sub Smooth` — pass and provisional additional smooth-sub option.
- `Fisherman'sFriend` — pass, but not a favorite.

## Keys

- `E Piano` — 360 From Mars

## Lead or pad — choose one after listening

- `OneFiftySeven` — 2600 From Mars
- `HumanMusic` — 101 From Mars

Replacement-round hardware result:

- `Dark FM` — Emulator From Mars; pass and provisional additional lead.
- `Muted Guitar` — Emulator From Mars; pass and provisional pad/texture track.

## Key 37 listening order

For each program, load it from `Programs`, play it for at least one minute, then
reload it once before recording the result.

1. `Vinyl SP From Mars 01 FG COLORS`
2. `Vinyl Drums From Mars 01 FG COLORS`
3. `Vinyl Drum Machines From Mars 1 FG COLORS`
4. `Fisherman'sFriend`
5. `E Piano`
6. `HumanMusic`
7. `OneFiftySeven`

For Drum Programs, test Bank A, at least two pads from Banks B–D, repeated hats,
and the visible type colors. For Keygroups, test the full physical keybed, both
octave directions, soft/hard velocity, held notes, repeated notes, pitch bend,
and modulation. Use `pass` for fully usable behavior, `warn` for a usable sound
with a documented quirk, and `fail` for silence, missing samples, bad mapping,
or unreliable reload behavior. Set `favorite` independently from technical
status.

## Local audition locations

The ignored `work/auditions/` directory contains one WAV and one JSON event
manifest for every candidate. Keygroup auditions alternate medium and high
velocity across a fixed ten-note phrase. Drum auditions trigger the first 16
populated instruments at velocity 100.

The renders approximate dry sample choice and pitch only. They intentionally
omit MPC envelopes, filters, inserts, sends, warp, mute behavior, and voice
allocation.
