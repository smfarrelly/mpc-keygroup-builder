# FG Vinyl Layered Main 02

`FG Vinyl Layered Main 02` is the accepted expressive Drum alternate. It keeps
four complete velocity regions per pad while replacing the first experiment's
broad timbre jumps with related soft-to-hard families.

**Musical decision — August 27, 2026:** the layered program is liked and worth
retaining specifically for expressive playing, but it does not replace
`Vinyl SP From Mars 01` as the Scratchpad main-drums favorite. Boundary, choke,
and save/reload checks below remain useful technical acceptance work; the
main-versus-alternate role decision is closed.

## SD location

`SD Card / 01 FG Favorites / 04 Drum Alternates / 05 FG Vinyl Layered Main 02 / FG Vinyl Layered Main 02.xpm`

The 65-file package was transactionally deployed on August 27, 2026 after a
32 MiB sustained-write probe. A second pass matched every SD file to the local
package by relative path and SHA-256.

## Bank A

- A01: acoustic kick, soft through impact.
- A02: 808 kick, air through long/smooth.
- A03: 909 snare, soft through high/bright.
- A04: acoustic snare, classic through fat.
- A05: electronic clap, dark through standard/bright.
- A06: acoustic/club clap, soft through house.
- A07: acoustic/tape rim.
- A08: CR-78/707/909/808 electronic rim.
- A09/A10: LM-1 and 808 closed/open hats, Mute Group 1.
- A11/A12: 909 closed/open hats, Mute Group 2.
- A13: 808 tom family.
- A14: acoustic tom family.
- A15: 808 cymbal family, mellow/long through brighter variation.
- A16: acoustic shaker family.

Every pad uses velocity regions 0–31, 32–63, 64–95, and 96–127. The committed
manifest contains the complete per-layer source map.

## Clear choke evidence

A10's four open-hat layers are 1.60, 1.20, 0.61, and 0.37 seconds long. A12's
four 909 open-hat layers are 0.36, 0.46, 0.53, and 0.35 seconds long. This makes
the tail interruption much easier to hear than the first kit's short hard-hit
layers.

Test A10 followed by A09 at soft, medium-soft, medium-hard, and hard velocity;
the A10 tail must stop each time. A10 followed by A11 must not choke. Repeat the
same directional and cross-group test with A12/A11 and A12/A09.

## Computer acceptance

- One XPM plus 64 checksum-matched WAVs.
- Program Model: 16 zones and 64 velocity layers, with no errors or warnings.
- Semantic simulation: `pass`; zero dead or stacked trigger cells.
- Drum audit: `pass`; 16 populated pads and valid Mute Groups 1 and 2.
- XPM SHA-256:
  `b6e3297183b8dfdf5c4ab5984878ac148d686ab031d72bab4abdef1b0e68797e`.

## Key 37 acceptance

- [ ] Confirm only Bank A is populated and colors appear after leaving Browser.
- [ ] Test every pad softly, medium-soft, medium-hard, and hard.
- [ ] Check boundaries 31/32, 63/64, and 95/96 for silence, double triggers,
  distracting loudness jumps, or unrelated character changes.
- [ ] Complete both directional choke tests and both cross-group negative tests.
- [ ] Record the same two-bar groove on this kit and Vinyl SP at a fixed master
  level, first naturally and then with Full Level.
- [x] Keep Vinyl SP as the default main kit and retain Layered Main 02 as the
  expressive alternate.
- [ ] Save/reload and repeat A01, A03, A09/A10, A11/A12, A15, and A16.
- [x] Retain as an expressive alternate; do not promote into the Scratchpad
  main-drums slot.
