# MPC Instrument Factory Product Roadmap

**Status:** Active

**Current milestone:** v0.3 — MPC Program Designer

**Primary hardware:** Akai MPC Key 37

**Roadmap source:** [MPC kit ideas shared conversation](https://chatgpt.com/share/6a8f6397-6abc-83ea-898a-98c9bf1f5c6b)

**Operational plan:** `docs/MPC_Project_Evolution_Plan.md`

## North star

Build a reusable, hardware-first instrument factory that turns owned sample
libraries and source-preset metadata into playable MPC programs, predictable
pad layouts, useful projects, and reproducible musical ideas. The computer
prepares, validates, previews, and safely deploys assets; the MPC remains the
place where music is played and captured.

Every milestone must leave the hardware setup more useful than it was before.
Architecture work does not count as complete until it produces a playable,
inspectable, or safer result.

## Proven baseline

The project is not starting from zero. The following capabilities are already
working and tested:

- Keygroup generation with note inference, velocity layers, structural checks,
  semantic simulation, and local audition rendering.
- XML and MPC 3 compressed XPM inspection, program-type detection, and semantic
  comparison.
- Drum Program classification, fixed pad colors, pad maps, mute-group auditing,
  and a manifest-driven 128-slot one-shot Drum Program builder.
- Hardware-deployed 32-, 64-, and 96-pad `FG Vinyl Shots` candidates generated
  from inherited reusable manifests. Version 03 fills Banks A–F.
- Safe SD deployment, checksum verification, licensed-artifact repository
  guards, program inventory, and hardware-result ledgers.
- Reusable Scratchpad, Volca, and Launch Control rig definitions.
- Captured MPC 3.9.1.2 projects proving internal Scratchpad routing, Volca MIDI
  channels, and a custom six-pad Volca Drum map.

## Dependency spine

The roadmap follows this dependency order:

```text
Normalized Program Model
  ├── semantic sound roles ── layout engine ── device profiles
  │                                  └──────── Program Designer
  ├── source importers ───────── expressive program exporters
  └── catalog/index ───────────── creative MIDI engine
                                      └── project generator
                                             └── mutation/arrangement

Network discovery is an early research spike. OTA deployment and live control
remain late-stage features until a supported, safe transport is proven.
```

## v0.2 — Drum Programs + Layout Engine

**Why now:** This delivers immediate pad-muscle-memory improvements while
creating the abstractions required by the visual editor, cross-library kits,
and semantic pattern generation.

### Already delivered

- [x] Generate a self-contained Drum Program from a TOML pad manifest.
- [x] Support 128 slots/Banks A–H in the builder and validation model.
- [x] Infer broad kick, snare, hat, clap, rim, tom, cymbal, percussion, and FX
  roles from filenames.
- [x] Apply customizable semantic colors.
- [x] Validate sample presence, endpoints, layers, dead pads, and stacked
  velocity cells.
- [x] Deploy and validate the first focused percussion/FX program on the SD.

### Current slices

1. **Hardware closeout.** `FG Vinyl Shots 04 Eight Bank` passes all eight banks
   and is the selected Track 2 program. Preserve it in the revised Scratchpad
   master and jam copy. Pluck Bass, Wurli, Dark FM, Glass Howl, and Sub Smooth
   have final track roles.
2. **Normalized Program Model v1.** Represent samples, zones, velocity layers,
   playback mode, semantic roles, pads, colors, mute groups, and source
   provenance independently from XPM serialization.
3. **Role taxonomy v1.** Expand broad categories into stable identities such as
   `kick.primary`, `snare.primary`, `hihat.closed`, `tom.low`, `perc.shaker`,
   `fx.stab`, and `vocal.one_shot`, with explicit filename overrides.
4. **Layout model v1.** Separate sound identity from physical placement and
   support mirroring, bank allocation, locked pads, alternates, and empty slots.
5. **Stock layout library.** Ship Classic MPC-ish, right-handed performance,
   left-handed performance, GM-ish, original-machine, and full-library layouts.
6. **Device profile v1.** Describe Key 37 pads, banks, keys, controls, and MIDI
   note behavior without hardcoding them into the layout engine.

### Software foundation completed August 26, 2026

- [x] Program Model v1 imports Drum manifests, legacy XML XPMs, and MPC 3
  compressed Drum/Keygroup XPMs with validation.
- [x] Hierarchical semantic roles support exact, case-insensitive filename and
  stem overrides loaded from TOML.
- [x] A device-independent layout planner honors locked pads and renders
  deterministic JSON or Markdown assignments.
- [x] Classic MPC-ish, right-handed, left-handed, and full-library presets run
  against the declarative 37-key, 16-pad, eight-bank Key 37 profile.
- [x] The selected 128-zone eight-bank Vinyl Shots manifest and 73-zone Mirage
  Wurli XPM pass real-data normalization; the prior 96-zone layout remains the
  basis of the generated layout-comparison package.
- [x] A non-destructive XML/compressed XPM exporter permutes complete 128-record
  Drum layouts, moves colors with records, refuses in-place writes, and verifies
  global/unknown-field preservation independently.
- [x] A hardware-package builder produces self-contained variants with licensed
  audio kept in ignored storage, pad maps, checksums, and passing simulations.
- [x] A metadata-only catalog indexes all 750 ledger entries; 746 programs from
  the immutable backup normalize successfully and four transient testing files
  are explicitly missing.
- [x] A reusable bank composer selects complete 16-pad banks from existing Drum
  Programs, resolves their WAV references, isolates bank mute groups, and can
  build a self-contained package. `FG Vinyl Kit Banks 01` combines eight
  source-native kits across Banks A–H and passes real-data simulation and Drum
  audit with all 128 pads populated.
- [x] Drum manifests support one through four explicit velocity layers per pad,
  require complete non-overlapping 0–127 coverage, write layer endpoints into
  legacy XPMs, and deactivate unused template layers. `FG Vinyl Layered Kit 01`
  exercises 64 timbre layers across 16 pads and passes real-data simulation
  with zero dead or stacked velocity cells.
- [x] `FG Vinyl Layered Main 02` refines that idea into coherent acoustic,
  808, 909, and character families with long-tail open hats at all velocity
  regions. Its 65-file SD package passes simulation, model validation, Drum
  audit, and checksum comparison. Hardware listening selects it as an
  expressive alternate; Vinyl SP remains the Scratchpad main-drums favorite.
- [x] Broaden the proven builders before adding another subsystem: three A-H
  collections reuse 24 accepted Ableton-converted kits as Classic Machines,
  Character Machines, and Breaks/Texture programs. A fourth program expands
  the velocity-layered idea to 64 pads across refined, machine, acoustic/tape,
  and experimental banks. All four are deployed, checksum-verified, and ready
  for hardware listening.
- [x] Reduce SD navigation debt without destructive loss: retain only the
  protected Scratchpad master under Projects, quarantine completed tests and
  obsolete test projects to a verified external archive, and add shallow
  on-card Scratchpad and Drum Alternates guides.
- [x] A format-independent loop inventory extracts BPM, variant, WAV shape,
  duration, estimated beats, and timing deviations. The complete 200-loop
  Vinyl Breaks library indexes cleanly from 73–200 BPM; Clip serialization is
  correctly gated on a minimal MPC-authored reference capture.
- [x] Transaction-safe package deployment uses a sustained write probe,
  verified resumable staging, per-file and aggregate SHA-256 identities,
  atomic promotion, and strict conflict/symlink refusal. Reader disconnects
  can no longer expose a partially copied package under its final browser name.
- [x] A read-only plugin-content auditor reports version markers, preset/content
  counts, files, and bytes while preserving the distinction between SD assets
  and actual on-device activation/playability.

Software export is complete. Key 37 listening selects the right-handed layout,
and save/reload restores its samples, playback, and semantic colors.

The four-variant v2 package and its source/classic semantic MIDI pair are now
deployed and checksum-verified on the SD. Right wins the hardware layout choice,
with a modest advantage because the source contains many diverse one-shots.
**Passed August 27, 2026:** both comparison programs reload correctly with
samples, playback, and colors intact, and Right remains the accepted default.

**Exit gate — passed:** One source kit can reproducibly generate Classic, right-handed,
left-handed, and full A–H variants. At least two variants load correctly on the
Key 37, retain colors after reload, and pass a short playing comparison.

## v0.3 — MPC Program Designer

Start with a local, read-only viewer and add editing in small usable releases:

1. [x] Import an XPM or build manifest and show all populated pads.
2. [x] Switch Banks A–H and preview the Key 37's 16-pad surface and a movable
   37-note Keygroup range.
3. [x] Show semantic role, sample status, color, MIDI note, layers, velocity
   coverage, mute group, and playback behavior for the selection.
4. [x] Emit self-contained HTML and machine-readable JSON without changing the
   source; accept declarative device profiles at generation time.
5. [x] Add in-view source/device switching and side-by-side comparison.
6. [x] Add drag/drop rearrangement, locked pads, palette editing, handedness
   conversion, and layout comparison.
7. [x] Export a manifest first; export a validated XPM only through the tested
   engine used by the CLI.
8. [ ] Add optional MIDI-groove heat maps and ergonomic layout suggestions after
   deterministic layouts are trusted.

**Read-only slice delivered August 27, 2026:** real `FG Vinyl Layered Banks 03`
and compressed Wurli data render successfully. Bank/note switching, selection
details, sample checks, velocity findings, physical orientation, responsive
layout, and browser console behavior are tested. Generated viewers contain
metadata only and remain in ignored local storage.

**Draft export slice delivered August 27, 2026:** the browser downloads a
deterministic JSON draft containing exact source and normalized-model hashes.
`mpc-layout-draft` rejects stale, incomplete, duplicate, out-of-capacity, or
metadata-tampered drafts; emits builder-compatible manifests; and delegates XPM
writes to the preservation-safe record exporter with independent verification
of declared placement and color changes.

**Portable comparison slice delivered August 27, 2026:** repeated source and
device arguments now create one self-contained viewer with toolbar switching,
bank-aware side-by-side program alignment, changed-field labels, summary
deltas, and the same deterministic comparisons in JSON. The reusable device
library now also includes an Akai-specification-backed MPC Key 61 profile.

**Layout draft slice delivered August 27, 2026:** Drum viewers now support
isolated in-memory drafts with drag or accessible click-to-move swaps, position
locks, pad colors, bank mirroring, reusable semantic presets, undo/redo,
bank/all reset, source-versus-draft comparison, and deterministic assignment
JSON. No browser action writes or exports a source or audio file.

**Exit gate:** A user can inspect a kit, create a handed layout, preview every
bank, export it, and load the result on hardware without manually editing XML.

## v0.4 — Expressive Instrument Factory

- Preserve the current reliable Keygroup mapping path.
- Improve root-note and useful-range inference.
- Preserve and validate velocity layers, loops, envelopes, filters, polyphony,
  and Q-Link-facing parameters.
- Generate purposeful variants such as Clean, Warm, Pad, Pluck, Bass, and
  Lo-Fi from a single normalized source instrument.
- Add Clip/slice output only after loop tempo, launch, mute, and transition
  behavior has a hardware-tested design.

**Exit gate:** One source instrument produces at least three musically distinct,
validated variants, and one loop collection produces a useful MPC-native
performance program.

## v0.5 — Source Intelligence

- Import Ableton racks and Drum Racks into the normalized model.
- Extract sample references, roots, zones, layers, playback, loops, envelopes,
  macros, choke groups, and effects where readable.
- Label each translation as Direct, Close, Template, or Reference-only.
- Add Kontakt or Maschine import only when a representative pack demonstrates
  value beyond WAV/Ableton metadata.

### Read-only foundation delivered early

- [x] `mpc-ableton` reads gzip or plain XML `.adg`/`.als` files and extracts
  device/branch types, macros, sample references, zones, roots, velocity/key
  ranges, endpoints, loop settings, tuning, and warp state.
- [x] Pack inventory skips macOS metadata, preserves parse issues, and assigns
  conservative Direct, Close, Template, or Reference-only suggestions.
- [x] The complete Vinyl SP Ableton source set inventories 23 presets with zero
  errors: two Close sets and 21 Template racks, totaling 2,884 zone instances.
- [x] The complete owned Samples From Mars tree inventories 1,718 Ableton
  sources across 82 packs with zero parse failures. A catalog-aware backlog
  assigns MPC targets and P0–P3 priorities, records source hashes, and demotes
  12 byte-identical duplicate presets.
- [x] The first generated queue identifies five P0 candidates: uncovered
  SP-1200 chromatic Keygroups. Big Break and Hand Break are confirmed as
  unwarped 16-pad Drum Racks and lead the immediate Drum Program wave. The
  editorial roadmap groups the remaining work into curated product waves.
- [x] Ableton Wave 01 builds those five Keygroups plus 27 source-ordered Drum
  Programs spanning vinyl, classic machines, and character kits. All source
  preflights and semantic simulations pass. Key 37 listening is active;
  all five SP-1200 chromatic Keygroups expose the same hardware range warning:
  they load but trigger only after several octave-down transpositions even
  though the generated model declares outer-note coverage. Rebuild the batch
  with its 16 roots explicitly remapped into the normal Key 37 register before
  promotion. The Wave 01 Vinyl Big Break and Hand Break Drum Programs pass, as
  do both intentionally 12-pad SP-1200 Factory kits. Most remaining Drum
  Programs were auditioned without blocking behavior and the full 27-program
  Drum wave is accepted: 25 pass, while Hardware Glitch and S950 Hard Glitch
  retain their documented source-choke warnings.
- [x] Keygroup construction now supports a validated fixed `root_shift` in the
  CLI and batch manifests. The five SP-1200 comparison programs were rebuilt
  two octaves higher, placing their source roots at MIDI 49–74, and deployed
  for default-register hardware verification.
- [x] NR1 hardware listening found the direction correct but one octave too far
  left. A separate NR2 batch shifts the same 80 WAVs three octaves above the
  originals, placing roots at MIDI 61–86; computer acceptance passes and SD
  deployment is the next gate.

Normalized-model import and exporter behavior remain gated on manual source
comparison and representative MPC target captures. The Clip subset remains
gated on the minimal MPC-authored Clip reference.

**Exit gate:** The utility can explain a representative Ableton preset and
generate an MPC result that preserves more intent than filename inference alone.

## v0.6 — Creative MIDI Engine

Implement deterministic, seed-reproducible generators in this order:

1. Chords and harmonic rhythm.
2. Drum patterns addressed by semantic roles, not fixed pad numbers.
3. Bass lines constrained by the chord model and useful instrument range.
4. Melodies and motifs with controllable repetition and variation.

### Foundation delivered early

- [x] TOML Drum recipes address hierarchical semantic roles instead of fixed
  pads.
- [x] Generation is reproducible by seed and supports probability, density,
  swing, gate, velocity humanization, sound cycling, and random alternates.
- [x] Source and planned layouts resolve through the XPM's own `PadNoteMap`.
- [x] Each run writes inspectable JSON plus MPC-targeted format-1 Standard MIDI
  at 480 PPQ; format 0 remains an explicit compatibility option.
- [x] A real source/Classic comparison preserves events and velocities while
  changing the moved snare's MIDI note.

Format-1 hardware import and qualified musical acceptance pass on MPC 3.9.1.2;
chords, bass, and melody generators are not yet implemented.

Later controls include density, swing, syncopation, octave range, harmonic
adventurousness, repetition, and variation. Generated events must resolve
through the active layout so the same pattern works across handed or device
layouts.

**Exit gate:** A saved seed recreates the same four-part musical idea, and the
drum pattern survives translation between two pad layouts.

## v0.7 — Creative Workstation Generator

- Combine selected programs, layouts, device profiles, templates, and MIDI
  generators into ready-to-play MPC projects.
- Ship recipe families such as dusty jazz, electro, ambient, 80s funk, house,
  and weird.
- Generate a restrained starting sequence with deliberate room for live play.
- Preserve the eight-strip Scratchpad/Volca mental model.
- Add a `Surprise Me` path only after recipes remain reproducible by seed.

**Exit gate:** One command or Program Designer action creates a validated,
recoverable project that reaches first playable sound in under one minute.

## v0.8 — Mutation + Arrangement

- Mutate one musical dimension by a controlled percentage while preserving the
  project's identity.
- Generate named Main, Main B, Breakdown, Build, and Outro sequences.
- Preserve locked tracks, notes, pads, and user performances.
- Make every mutation reversible and reproducible by seed.

**Exit gate:** A useful four-bar idea becomes a coherent multi-sequence song
outline without editing a computer timeline.

## v0.9 — Catalog + Cross-library Kits

- Index the owned library by pack, program type, semantic role, range, duration,
  loudness, and later spectral/transient features.
- Search for musical descriptions such as `warm electric piano`, `dirty short
  kick`, or `glassy pad`.
- Build deterministic cross-pack kits from style recipes before adding learned
  or open-ended recommendations.
- Record provenance for every selected sample and generated asset.

**Exit gate:** A query returns useful candidates and a cross-library recipe
builds a licensed-local, reproducible kit without copying audio into source
control.

## v1.0 — Live Companion + Reusable Release

### Early research, late productization

- Safely discover what the Key 37 exposes over supported Wi-Fi/network MIDI.
- Determine whether a documented, non-destructive file-transfer route exists.
- Do not modify the MPC operating system or depend on unsupported services.
- If reliable, support live MIDI generation and mutation while the MPC remains
  the active instrument.
- Keep SD/USB deployment as the supported fallback.

### Release readiness

- Use synthetic or freely licensed fixtures and demonstrations.
- Document bring-your-own-samples licensing boundaries.
- Publish schemas, device profiles, layouts, recipes, validators, and tests.
- Prove the workflow through at least three completed compositions.
- Confirm another MPC owner can generate, validate, preview, install, and play
  a program by following the documentation.

**Exit gate:** The project is useful to another musician without access to this
specific SD card, sample library, or development history.

## Parallel hardware track

Hardware work continues alongside software milestones and provides the truth
for release gates:

- Finalize the Scratchpad lead/pad and Track 2 shots choices; primary bass and
  Bass Pad are selected.
- Record and reload an actual MPC-authored Volca MIDI sequence.
- Complete three-device Volca isolation and sync after the CME MIDI Thru5 WC
  arrives.
- Establish practical audio gain and capture routing.
- Defer Launch Control XL 3 mapping until Scratchpad and Volca restore behavior
  is stable, then preserve one universal eight-track control vocabulary.

## Immediate next three increments

1. **Program Designer:** begin the v0.3 read-only viewer with program import,
   Bank A–H switching, pad roles, samples, colors, layers, and mute groups.
2. **Creative MIDI:** build chord and bass generators on the accepted format-1
   MIDI path and keep their output inspectable without requiring an immediate
   Key 37 acceptance session.
3. **Hardware, deferred:** preserve Drum Alternates 06-09, NR2 Keygroups, Volca
   integration, and Launch Control mapping as ready-to-resume test batches.
   Record completed observations in the living Key 37 field review; cold-start
   timing remains deferred.
