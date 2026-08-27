# Samples From Mars MPC conversion roadmap

This is the editorial execution plan for the generated
`inventory/samples-from-mars-mpc-backlog.md`. The generated backlog ranks every
readable Ableton source; this document chooses coherent musical products rather
than promising a literal one-to-one conversion of 1,718 presets.

## Ground rules

- Build programs that add a distinct MPC-native playing experience.
- Prefer one excellent curated program over many near-identical ports.
- Preserve the prepared Ableton zone map when it expresses pitch, velocity,
  looping, or kit membership better than filename inference.
- Use Drum Programs for pad kits, Keygroups for chromatic instruments, Clip
  Programs for tempo-aware loops, and projects only for meaningful multi-track
  setups.
- Do not commit licensed samples, generated programs, or source presets.
- Require structural validation before deployment and Key 37 listening before
  a program becomes a favorite or release baseline.

## Wave 0 — close current playable work

Hardware checkpoint: `FG Vinyl Shots 04 Eight Bank` is accepted as the selected
Track 2 program. `FG Vinyl Kit Banks 01` is complete and retained as a
provisional Drum alternate: the same pattern worked impressively on Banks A,
B, C, and G, save/reload restores expected state, and its source-native layouts
need no stricter normalized variant. `FG Vinyl Layered Kit 01` remains untested.

1. Hardware-test `FG Vinyl Kit Banks 01` and `FG Vinyl Layered Kit 01`.
2. Compare their feel and usefulness with `FG Vinyl Shots 04 Eight Bank`.
3. Preserve the chosen programs in the protected Scratchpad master and a jam
   copy.
4. Capture the smallest MPC-authored Clip Program that proves launch,
   quantization, tempo, warp, mute, and project-link fields.
5. Use that reference to implement and validate `FG Vinyl Breaks` rather than
   guessing the Clip format from an Ableton Live Set.

## Wave 1 — highest new musical value

### SP-1200 chromatic instruments

Build five Keygroups from the prepared chromatic sources:

- Chromatic Analog Tom
- Chromatic Chimes
- Chromatic Cowbell
- Chromatic Tom
- Chromatic Tone

These are the five highest-ranked uncovered melodic programs and complement
the pad kits instead of duplicating them.

Software status: all five are built and locally validated in Ableton Wave 01;
Key 37 listening remains pending.

### Vinyl Drums breakbeat programs

Translate Big Break Kit and Hand Break Kit as Drum Programs. Source inspection
confirms that both are 16-pad, unwarped Drum Racks; “Break” describes their
musical style rather than a tempo-warped Clip source.

Software status: both are built with source pad order and choke groups in
Ableton Wave 01. The same wave adds 25 diverse machine/character Drum Programs
to make the next hardware session more informative.

### Curated Vinyl Synths favorites

Do not bulk-export all 215 instrument racks. Start with sounds already favored
on hardware—Sub Smooth and the selected Scratchpad voices—then audition a
small role-balanced bracket of bass, keys, lead, and pad candidates. Preserve
only mappings or behaviors that improve on the existing generated Keygroups.

## Wave 2 — character kits and loop instruments

1. Build curated Drum Program families for uncovered classic machines: 505,
   606, 626, 707, 808, 909, CR-78, DMX, Drumtrax, Drumulator, LM-1, and MPC60.
2. Reuse the bank composer to make a few contrasting A–H collections instead
   of exporting every Ableton kit as a separate browser entry.
3. Build S950 Snacks and Found Sounds performance kits for texture, glitch,
   Foley, and transition duties.
4. Convert Acid loops only after the Clip exporter passes Vinyl Breaks hardware
   acceptance.
5. Evaluate Tape Fragments, Trumpet Fragments, and Databenders as expressive
   Keygroups or one-shot programs, prioritizing playability over source count.

## Wave 3 — improve already-covered families

The catalog already has substantial Keygroup coverage for DX100, Emulator,
Mirage, OB, S612, SH-5, SID, SYS100M, VP-330, Wasp, and related synth packs.
For these, create a new MPC version only when Ableton metadata proves added
value such as:

- better root notes or useful key ranges;
- genuine velocity layers;
- musically important sample loops;
- purposeful splits or parallel layers;
- a clear Q-Link or Launch Control performance mapping;
- a distinct role missing from the Scratchpad favorites.

## Deferred/reference work

- Full `.als` sessions remain project references unless their multi-track
  structure serves the hardware workflow.
- Large Individual Hits racks remain searchable source catalogs for the kit
  and bank composers.
- Plug-in-dependent or unmapped sources remain reference-only until a legal,
  owned-audio MPC substitute is designed.
- `modern_oddities_from_mars(1)` is retained in audit output for provenance but
  its 12 byte-identical files must not be converted separately.

## Definition of done for each backlog item

- Source intent inspected and target program type justified.
- Output is reproducible from a manifest or recorded conversion recipe.
- Licensed audio stays in ignored local storage.
- Structural checks, program simulation, sample-reference checks, and repository
  guard pass.
- Program loads, plays, saves, and reloads on the MPC Key 37.
- Hardware result and concise listening notes are recorded in the program
  ledger.
- Only accepted favorites enter a Scratchpad or curated A–H collection.
