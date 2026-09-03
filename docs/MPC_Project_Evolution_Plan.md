# MPC Project Evolution Plan

**Owner:** Steve Farrelly  
**Started:** August 25, 2026  
**Status:** Active — Scratchpad validation and v0.3 Program Designer

**Operational working copy:** `docs/MPC_Project_Evolution_Plan.md`

**Product roadmap:** `docs/PRODUCT_ROADMAP.md`

**Living hardware review:** `docs/MPC_KEY37_FIELD_REVIEW.md`

**Primary instrument:** Akai MPC Key 37

## 1. Project north star

The product milestone sequence, dependency graph, and release gates now live in
`docs/PRODUCT_ROADMAP.md`. This document remains the detailed hardware design,
operational checklist, and chronological progress log.

Build a hardware-first, live-enabled composition system that preserves the immediate fun of the Volca Drum, Volca Keys, and Volca Bass:

> Turn on the MPC, play immediately, capture a short sequence, add layers, reshape the music with knobs, create variations, and perform those variations into a composition—without falling into a computer timeline.

The computer remains useful for library management, analysis, conversion, validation, and backups. The MPC Key 37 remains the place where music is made.

## 2. Definition of success

The project is succeeding when:

- The MPC boots into a useful Scratchpad and produces sound in under one minute.
- Pads immediately provide drums, percussion, one-shots, and loops.
- All 37 keys immediately provide a useful melodic instrument.
- The Novation Launch Control XL 3 provides predictable, hands-on control without frequent touchscreen use.
- The same controller gestures retain similar meanings across templates.
- The MPC can sequence and perform with the Volca Drum, Keys, and Bass.
- Musical sections can be created and performed as MPC sequences rather than drawn on a DAW timeline.
- Samples From Mars libraries become a curated family of MPC-native keygroup, drum, and clip programs.
- A repeatable toolchain can analyze source presets, generate programs, validate them, and install them safely.
- At least three complete compositions are made with the system before the tooling is expanded into a broad public project.

## 3. Guiding principles

1. **Music before infrastructure.** Every one or two work sessions should produce something playable.
2. **Translate musical intent, not merely file formats.** Ableton devices are design documents that reveal how the source material was meant to be played.
3. **Use MPC-native program types.** Keygroups, Drum Programs, and Clip Programs should each be used for the jobs they perform best.
4. **Preserve character.** Vinyl noise, tails, warble, unusual tuning, baked-in effects, and imperfections are often features rather than defects.
5. **Consistency creates instrument-like behavior.** Track positions, pad roles, controller semantics, and naming should remain predictable.
6. **Complete library, curated favorites, tiny startup palette.** Preserve abundance without forcing it into the immediate playing experience.
7. **Use successful MPC programs as ground truth.** Compare generated files against programs saved by the Key 37.
8. **Do not redistribute commercial samples.** A future open-source project will contain code, schemas, documentation, and freely licensed test fixtures—not Samples From Mars audio.

## 4. Current state

### Completed

- [x] Selected the MPC Key 37 as the standalone sequencing, sampling, keyboard, and performance center.
- [x] Built an SD-card structure for expansions, exports, programs, projects, and Samples From Mars content.
- [x] Installed approximately 83 supplied MPC programs from Samples From Mars.
- [x] Generated many additional instrument XPM programs from Samples From Mars source material.
- [x] Tested many generated programs on the MPC Key 37.
- [x] Confirmed that most tested programs load and behave as expected.
- [x] Confirmed playable note coverage across all 37 keys and across octave changes.
- [x] Established keygroup generation as a successful, useful first conversion path.
- [x] Identified the Samples From Mars vinyl libraries as the preferred aesthetic foundation.
- [x] Added the Volca Drum to the Volca Keys and Volca Bass hardware setup.
- [x] Ordered the Novation Launch Control XL 3 for delivery later this week.
- [x] Cloned `smfarrelly/mpc-keygroup-builder` onto the Mac at `~/Projects/mpc-keygroup-builder`.
- [x] Preserved the original 49 GB SD-card backup dated August 24, 2026.
- [x] Created a separate working SD-card mirror for cleanup and eventual card replacement.
- [x] Removed 550 macOS metadata files and 4,749 checksum-identical duplicate files from the working mirror.
- [x] Moved four root-level experimental keygroup bundles into `Programs/Keygroups/Testing` without changing their contents.
- [x] Added a repeatable, dry-run-first SD cleanup script and safety tests.

### Active discoveries

- [ ] Record exactly which generated programs have passed, failed, or shown unusual behavior.
- [ ] Freeze and back up the current working keygroup generator as `keygroup-v0.1`.
- [ ] Confirm the SD card remains reliably writable before the next bulk installation.
- [ ] Record the MPC operating-system version used for validation.
- [ ] Determine which drum sources should remain chromatic keygroups and which should also become Drum Programs.
- [ ] Analyze the Ableton setups included with representative Samples From Mars packs.
- [x] Audit every XPM in the working SD mirror for type, location, companion data, and missing sample references.

## 5. System architecture

The finished system will have three library levels and four template types.

### Library levels

1. **Complete generated library** — every program that can be built and validated successfully.
2. **Favorites collections** — smaller curated groups organized by musical role and character.
3. **Scratchpad palette** — one immediately useful sound for each startup role.

### Template family

1. **FG Vinyl Scratchpad** — vinyl-first internal MPC boot project.
2. **FG Volca Jam** — MPC plus Volca Drum, Keys, and Bass.
3. **FG Mars Lab** — auditioning, resampling, and manipulating Samples From Mars material.
4. **FG Song Builder** — live arrangement through named musical sequences.

All templates should preserve the same first-eight-strip controller vocabulary
wherever practical. The project may add tracks beyond those eight; they are not
an MPC limit.

| Strip | Standard role | Vinyl Scratchpad | Volca Jam |
|---|---|---|---|
| 1 | Main drums | Vinyl drum kit | Volca Drum |
| 2 | Percussion/one-shots | Stabs, vocals, FX | MPC percussion/one-shots |
| 3 | Bass | Vinyl bass keygroup | Volca Bass |
| 4 | Chords/keys | Vinyl piano, EP, or chords | Volca Keys |
| 5 | Lead | Dark FM | Internal lead/pad |
| 6 | Pad | Glass Howl | Additional sequence material |
| 7 | Bass pad/texture | Juno Sub Smooth | Texture or guest hardware |
| 8 | Loops | Loops | Loops |
| 9 | Capture/transition | Resampling and transitions | Resampling and transitions |

## 6. MPC program-type strategy

The current keygroup output is valuable and should not be discarded. The next stage adds alternate MPC-native representations where they create better performance behavior.

| Source material | Preferred MPC target | Intended use |
|---|---|---|
| Multisampled synth, piano, bass, or acoustic instrument | Keygroup Program | Play melodically across the keys |
| A single kick, snare, tom, or other hit at multiple pitches | Keygroup Program | Chromatic or melodic percussion |
| A collection of kicks, snares, hats, and percussion | Drum Program | Finger-drumming on pads |
| Chords, vocal chops, stabs, and effects | Drum Program | Immediate pad triggering |
| Tempo-based loops and variations | Clip Program | Quantized launching and switching |
| Complex layered or split instrument | Rich keygroup or multi-track template | Layers, splits, effects, and performance controls |

A single source pack may produce several complementary outputs—for example, chromatic individual hits, a pad kit, a one-shot bank, and a clip bank.

## 7. Launch Control XL 3 design

### Custom Mode 1: Universal Mix

This mapping should remain stable across every project template.

| Physical control | Default meaning |
|---|---|
| 8 faders | Track volumes 1–8 |
| Top encoder row | Tone, brightness, or filter |
| Middle encoder row | Delay, movement, or modulation amount |
| Bottom encoder row | Reverb, ambience, or space amount |
| Upper button row | Track mute |
| Lower button row | Record-arm, solo, or another consistent performance function—decision pending |

### Custom Mode 2: Vinyl Performance

Create this only after Universal Mix has been played enough to reveal what is missing. Candidate controls include:

- Dirt/saturation
- Vinyl noise or texture level
- Warble/modulation
- Filter resonance
- Envelope decay/release
- Compression/punch
- Delay feedback
- Transition or performance effects

### Controller acceptance tests

- [ ] The Launch Control connects reliably to the MPC in standalone mode.
- [ ] The MPC receives all intended fader, encoder, and button messages.
- [ ] Universal Mix mappings are saved with the Scratchpad project.
- [ ] Physical controls and MPC values do not produce disruptive jumps during ordinary use.
- [ ] A ten-minute jam can be performed with minimal touchscreen navigation.
- [ ] The same Universal Mix mode works after cloning the Scratchpad into another template.

## 8. Ableton analysis and translation

The Ableton material should be analyzed as a description of Samples From Mars' musical intent—not copied literally.

### Information to extract

- Preset, rack, chain, and track names
- Samples referenced
- Root notes and transposition
- Key zones and keyboard splits
- Velocity zones and fades
- Parallel layers and chain-selection behavior
- Drum Rack pad assignments
- Choke groups
- One-shot, gated, and loop playback behavior
- Sample starts, ends, and loop points
- Envelopes, filters, and tuning
- Macro names, destinations, and ranges
- Per-chain or per-pad effects
- Sends and return effects
- Polyphony and voice behavior where discoverable

### Translation-fidelity labels

- **A — Direct:** Can be represented faithfully in one MPC program.
- **B — Close:** Musical behavior can be preserved with a reasonable MPC-native substitution.
- **C — Template:** Requires multiple programs, tracks, routing, or controller mappings.
- **D — Reference only:** Not useful or practical to reproduce on the standalone MPC.

### Likely mappings

| Ableton concept | MPC translation candidate |
|---|---|
| Key zones | Keygroup note ranges |
| Velocity zones | Keygroup sample layers |
| Drum Rack notes | Drum Program pads |
| Drum Rack choke groups | MPC mute groups |
| Simpler one-shot behavior | Drum Program playback settings |
| Simpler looping | Keygroup or Clip Program settings |
| Parallel chains | Keygroup layers or multiple tracks |
| Rack macros | Q-Links and Launch Control mappings |
| Per-chain effects and sends | Pad, program, track, and return processing |
| Chain selector or rack variation | Alternate programs, layers, sequences, or template-level controls |

## 9. Vinyl Suite pilot

The vinyl-family material will be the first end-to-end translation target because it contains the drums, instruments, loops, textures, and character needed by the actual live system.

### Pilot order

1. **Vinyl SP From Mars** — broad one-shot collection and prepared kits; ideal for the first Drum Program and one-shot-bank study.
2. **Vinyl Synths From Mars** — large mapped instrument collection; ideal for keygroup enrichment and favorites curation.
3. **Vinyl Drums From Mars** — dedicated acoustic/percussion material; ideal for standardized pad layouts, layers, and mute behavior.
4. **Vinyl Breaks From Mars** — ideal for the first Clip Program and loop-performance study.
5. **DR Sample From Mars or another broad character pack** — useful stress test containing drums, instruments, chords, and textures.

### Vinyl Suite deliverables

- [ ] `FG Vinyl Drums` — proper MPC Drum Program family.
- [ ] `FG Vinyl Shots` — stabs, chords, vocals, effects, and oddities on pads.
- [ ] `FG Vinyl Breaks` — Clip Program for quantized loop launching.
- [ ] `FG Vinyl Instruments` — complete validated keygroup library.
- [ ] `FG Vinyl Favorites` — curated melodic and rhythmic subset.
- [ ] `FG Vinyl Scratchpad` — eight-track startup project.
- [ ] `FG Vinyl Performance` — Launch Control performance mapping.

## 10. Work phases

### Phase 0 — Preserve the success

**Goal:** Protect the working generator and establish a reliable baseline.

- [x] Copy the current generator and supporting scripts into a clearly named project directory.
- [ ] Label the current working implementation `keygroup-v0.1`.
- [x] Back up the generated XPM programs and their sample-data directories.
- [x] Create the structural program inventory; hardware listening statuses remain to be recorded separately.
- [ ] Record at least ten representative passing programs.
- [x] Record initial structural anomalies in the four experimental root programs; continue musical testing on hardware.
- [ ] Capture the MPC operating-system version.
- [ ] Verify SD-card write behavior and available space.

**Exit test:** The current success could be restored after losing either the SD card or the Ubuntu working directory.

### Phase 1 — FG Vinyl Scratchpad v0.1

**Goal:** Produce the first playable boot environment using programs that already work.

- [ ] Select one favorite working drum kit.
- [x] Build one focused percussion/one-shot candidate: FG Vinyl Shots 01; local
  and SD-card semantic checks pass, hardware listening remains open.
- [ ] Select one bass keygroup.
- [ ] Select one keys/chord keygroup.
- [ ] Select one lead or pad keygroup.
- [ ] Select one loop or texture source.
- [ ] Create the eight-track Scratchpad structure.
- [ ] Set usable starting levels, sends, and effects.
- [ ] Save a protected master copy and a disposable working copy.
- [ ] Test saving a worthwhile jam under a new project name.
- [ ] Configure project autoload only after the Scratchpad has proven stable.

**Exit test:** Power on, begin a drum-and-keys idea within one minute, and save it without visiting a computer.

### Unattended tooling completed August 25, 2026

- [x] Define the seven-program Scratchpad candidate set as validated TOML.
- [x] Generate a complete editable Key 37 listening-session file from the ledger.
- [x] Add candidate readiness gates for SD deployment, hardware listening, core selection, and final favorites.
- [x] Add read-only XPM inspection and semantic legacy/MPC3 comparison.
- [x] Add physical drum-pad maps with inferred roles, colors, choke, and playback behavior.
- [x] Add additive, dry-run-first, checksum-verified SD delta deployment with verified backups.
- [x] Add audition WAV level, silence, clipping, and DC-offset diagnostics.
- [x] Wrap controlled XPJ capture and the detached Mac inspector without merging its branch.
- [x] Add CI and licensed-artifact source-control guards.
- [x] Define reusable Vinyl Scratchpad, Volca Jam, and Launch Control XL 3 rig profiles.
- [x] Add rig/MIDI validation, program-ledger queries, setup-sheet rendering, and consolidated session reports.

These items reduce setup and transcription work; they do not mark any pending
MPC listening or routing acceptance test as passed.

### Phase 2 — Launch Control integration

**Goal:** Restore Volca-like hands-on immediacy.

- [ ] Update the Launch Control XL 3 firmware using Novation Components.
- [ ] Verify direct standalone communication with the MPC.
- [ ] Create Universal Mix Custom Mode.
- [ ] Enable the Launch Control for MPC Control and MIDI Learn as required.
- [ ] Map the eight faders.
- [ ] Map the three encoder rows.
- [ ] Map track mutes.
- [ ] Choose and map the lower button function.
- [ ] Save and back up the controller mode.
- [ ] Save the MPC mappings with the Scratchpad.
- [ ] Perform a ten-minute no-timeline jam and record friction notes.

**Exit test:** Levels, tone, movement, space, and mutes can be performed primarily from physical controls.

### Phase 3 — Ableton source analysis

**Goal:** Understand the richer source designs before expanding the generators.

- [x] Inventory Ableton `.adg`, `.als`, and related preset files for the first vinyl pack.
- [x] Manually inspect five representative presets.
- [x] Build an analyzer that emits a structured report of samples, zones, chains, macros, playback, and effects.
- [x] Compare analyzer results against what is visible in Ableton or against readable source metadata.
- [x] Assign translation-fidelity labels.
- [x] Produce a translation specification for the pilot pack.

**Exit test:** We can explain how the pilot pack's Ableton instruments work and identify the best MPC target for each one.

### Phase 4 — Expand the program factory

#### 4A. Keygroup v0.2

- [ ] Preserve current successful note mapping.
- [ ] Add or validate velocity layers.
- [ ] Preserve intentional loop behavior.
- [ ] Translate useful envelope and filter defaults.
- [ ] Add consistent Q-Link or controller-facing parameters where practical.
- [ ] Improve validation and reporting.

#### 4B. Drum Program v0.1

- [ ] Define the standard 16-pad performance layout.
- [ ] Generate sample-to-pad assignments.
- [ ] Support pad layers where source material warrants them.
- [ ] Support mute groups such as open/closed hats.
- [ ] Preserve one-shot/gated behavior.
- [ ] Add suitable pad or program processing defaults.
- [ ] Generate alternate banks or kits without breaking muscle memory.

#### 4C. Clip Program v0.1

- [ ] Identify loop tempo and length metadata.
- [ ] Define the pad/column layout for musical roles and variations.
- [ ] Configure quantized launching.
- [ ] Configure mute groups for mutually exclusive variations.
- [ ] Test live transitions between loops.

#### 4D. Unified commands

Longer-term command set:

- `scan`
- `analyze-ableton`
- `build-keygroup`
- `build-drum`
- `build-clip`
- `validate`
- `install`
- `report`

**Exit test:** One source pack can produce validated keygroup, drum, and clip outputs without manual XML editing.

### Phase 5 — Template family

#### FG Volca Jam

- [ ] Assign stable MIDI channels and ports for each Volca.
- [ ] Make the MPC master clock and transport where appropriate.
- [ ] Create dedicated MIDI tracks for the Volca Drum, Bass, and Keys.
- [ ] Decide live-monitoring and capture routing through the Moukey mixer and MPC inputs.
- [ ] Save performance-oriented Launch Control mappings.
- [ ] Test a family jam without a computer.

#### FG Mars Lab

- [ ] Provide fast audition tracks for keygroups, drums, one-shots, and clips.
- [ ] Provide a simple resampling track.
- [ ] Provide effects for quickly turning source material into new sounds.
- [ ] Save useful results into the curated library rather than leaving them trapped in a project.

#### FG Song Builder

- [ ] Create named sequences: `Start`, `Groove`, `Lift`, `Break`, `Return`, and `Outro`.
- [ ] Make duplication and variation creation fast.
- [ ] Test live sequence switching.
- [ ] Record knob movements and mutes as performance automation where useful.
- [ ] Establish an export or live-recording workflow that does not require arranging on the DAW timeline.

**Exit test:** The same playing vocabulary and controller muscle memory work across all template types.

### Phase 6 — Creative validation

**Goal:** Prove the system through music rather than configuration completeness.

- [ ] Complete composition 1 using FG Vinyl Scratchpad.
- [ ] Complete composition 2 using FG Volca Jam.
- [ ] Complete composition 3 using a combination of generated programs and live resampling.
- [ ] Make at least one project comfortable for collaborative playing with the kids.
- [ ] Record setup friction after each composition.
- [ ] Rank requested improvements by how often they interrupted playing.

**Exit test:** Three complete compositions exist, and the next tooling priorities are supported by actual use.

### Phase 7 — Open-source release

- [ ] Choose a project name.
- [ ] Create a clean repository structure.
- [ ] Document supported source and target types.
- [x] Use synthetic or freely licensed audio for fixtures and demonstrations.
- [x] Add deterministic build tests.
- [x] Add missing-file, invalid-zone, path, and installation validation.
- [x] Document the bring-your-own-samples licensing model.
- [ ] Publish an initial `v0.1` focused on the proven workflow rather than universal conversion.

**Exit test:** Another MPC owner can supply their own samples, generate a program, validate it, and load it successfully by following the documentation.

## 11. Standard program test checklist

Use this checklist for every representative generated program:

- [ ] Program appears in the expected MPC browser location.
- [ ] Program loads without an error.
- [ ] All referenced samples are found.
- [ ] Expected pads or all 37 keys produce sound.
- [ ] Octave changes behave correctly.
- [ ] Root notes and pitch tracking sound correct.
- [ ] Velocity behavior is usable.
- [ ] One-shot, gated, or loop behavior matches the source intent.
- [ ] Levels are reasonable relative to other Scratchpad instruments.
- [ ] Envelopes and tails do not click or cut off unexpectedly.
- [ ] Mute groups behave correctly where applicable.
- [ ] Program saves and reloads.
- [ ] Program still works after reboot.
- [ ] Q-Link and Launch Control assignments remain available where expected.

## 12. Decisions to make through playing

Do not block initial progress on these decisions. Resolve them after hands-on tests.

- [ ] Final standard 16-pad drum layout.
- [ ] Whether loops live primarily in Clip Programs or one-shot Drum Programs.
- [ ] Lower Launch Control button-row behavior.
- [ ] Which four to eight parameters define the Vinyl Performance mode.
- [ ] Whether the Scratchpad autoloads directly or appears first in the Template/Recent screen.
- [ ] Track 7 and 8 roles across specialized templates.
- [ ] Final Volca MIDI-channel plan.
- [ ] Preferred live-monitoring versus MPC-capture routing.
- [ ] Naming, category, and favorites conventions.

## 13. Explicitly deferred

These are not initial priorities:

- A graphical desktop application
- Universal conversion of every sampler and preset format
- Perfect reproduction of every Ableton effect or chain-selector behavior
- Third-party VST integration in the live workflow
- Buying more controllers before the Launch Control layout is tested
- Converting every sample before a curated library exists
- Large-scale public release before three compositions validate the design

## 14. First work session: Preserve and Play

**Target duration:** 60–90 minutes  
**Deliverable:** A protected working generator plus `FG Vinyl Scratchpad v0.1`.

### Part A — Preserve the generator

- [x] Recover the latest generator and helper files from GitHub onto the Mac.
- [ ] Make a clearly named `keygroup-v0.1` snapshot.
- [ ] Record the names of the programs already tested successfully.
- [x] Back up the generated XPMs and companion sample directories.

### Part B — Assemble the Scratchpad

- [x] Choose one working vinyl drum kit: Vinyl SP.
- [x] Choose one working vinyl bass: Mirage Pluck Bass (selected and proven in
  the captured four-bar sequence).
- [x] Add Juno Sub Smooth as a dedicated Bass Pad Keygroup on Track 7.
- [x] Choose one favorite vinyl keys/chord sound: Mirage Wurli.
- [x] Choose a favorite lead: Emulator Dark FM.
- [x] Choose a dedicated pad: Kawaii Dreams Glass Howl on Track 6.
- [ ] Create the eight-track project skeleton.
- [x] Load the four core sounds into a working Scratchpad project.
- [ ] Set starting levels and one useful shared reverb/delay environment.
- [ ] Save as `FG_Vinyl_Scratchpad_v0_1`.
- [x] Make a short sequence and perform a few changes to prove the concept: a
  captured four-bar drums, Pluck Bass, and Wurli idea passed on the Key 37.
  Dark FM and Glass Howl still need recorded-part save/reload confirmation in
  the revised project.

### Session completion rule

Stop when the Scratchpad is enjoyable to play. Capture additional ideas in the backlog rather than extending the session into a large conversion or mapping exercise.

## 15. Progress log

### August 25, 2026 — Mac recovery and SD cleanup

- Authenticated GitHub as `smfarrelly` and cloned the generator repository.
- Confirmed the MacBook's internal SDXC driver loads, but its built-in slot reports no inserted card; use the working USB-C reader.
- Preserved `/Users/farrelly/Documents/MPC/SD Card Backups/3561-6538 - 2026-08-24` as the immutable baseline.
- Created `/Users/farrelly/Documents/MPC/SD Card Backups/3561-6538 - working` as the writable deployment candidate.
- Removed 550 `.DS_Store` files.
- Removed 4,749 files only after SHA-256 verification against identical retained counterparts, reclaiming 650,513,960 bytes.
- Retained 39,825 unique files from the partially redundant Samples From Mars `Instruments` tree.
- Relocated four complete experimental program bundles from the card root to `Programs/Keygroups/Testing` and verified byte equality against the baseline.
- Confirmed the cleanup is idempotent: a second dry run proposes zero changes.
- Added `scripts/clean_sd_backup.py` and focused tests. Cleanup-specific tests and 18 existing mapping tests pass under the Mac's Python 3.9; the existing workflow suite still requires the project's Python 3.11+ environment.
- Next gate: produce a complete XPM inventory and missing-reference report before writing the working mirror to removable media.

### August 25, 2026 — Program inventory and repair

- Added `scripts/audit_sd_programs.py` with XML Drum and gzip/JSON Keygroup support, focused tests, JSON output, and CSV output.
- Audited 758 programs after the initial duplicate cleanup: 749 passed structural reference checks, eight were unreadable, and one had a missing sample reference.
- Confirmed the eight unreadable Dr Sample XPMs were part of a failed duplicate installation containing 421 zero-byte files. Every relative file had a nonzero authoritative counterpart under `Samples/Samples From Mars/Dr Sample From Mars`.
- Removed that failed duplicate tree from the deployable mirror and retained it in the local ignored quarantine.
- Corrected `HH 626 Stardard OH Vinyl` to match the existing `HH 626 Standard OH Vinyl.wav` reference in `Vinyl Drum Machines From Mars 5.xpm`.
- Re-audited the complete working mirror: 750 of 750 programs pass structural sample-reference checks.
- Final inventory: 660 gzip/JSON Keygroup programs and 90 XML Drum programs; zero unreadable programs, missing references, ambiguous references, or zero-byte referenced samples.
- Structural pass means that the XPM is readable and its declared local samples resolve. It does not replace the MPC hardware listening checklist or mark a program musically approved.
- Created `inventory/program-status.csv` with all 750 programs initialized to hardware status `untested`, plus favorite, Scratchpad role, and notes fields.
- Next gate: test representative programs on the Key 37 and identify the first Scratchpad candidates.

### August 25, 2026 — Local semantic simulation framework

- Added the `mpc-program-test` framework for MPC 3 gzip/JSON Keygroups and legacy XML Drum programs.
- Added schema/container, registry, sample resolution, WAV header, frame boundary, loop boundary, note coverage, velocity coverage, pad-layer, and stack checks.
- Simulated 1,024 representative note/velocity trigger cells for each Keygroup and representative velocity behavior for each populated Drum pad.
- Added production and testing scopes so intentionally incomplete fixtures remain visible without blocking deployment.
- Added severity-coded JSON and CSV reporting plus documentation in `docs/testing-framework.md`.
- Added semantic fields to all 750 rows in `inventory/program-status.csv` while preserving hardware status as `untested`.
- Initial simulation found a stale `SliceEnd` in `Vinyl Synths From Mars.xpm`; repaired it from 49,772 to 33,995 to match the 33,996-frame WAV and the inclusive endpoint convention used by its companion samples.
- Recognized one legacy Perkons endpoint equal to the sample frame count as a compatibility warning rather than a destructive failure.
- Final production result: 746 programs tested, 745 pass, one compatibility warning, and zero failures.
- Isolated testing result: two pass, one warning for WAV extensible format unsupported by Python's standard probe, and one expected failure for the deliberately incomplete five-note `Star Piano TEST` fixture.
- All 26 runnable mapping, cleanup, audit, and simulation tests pass on the Mac. The older workflow suite still awaits the repository's Python 3.12 environment.
- Next gate: install the correct Python environment, capture representative local audition renders, then complete Key 37 listening tests for the first Scratchpad candidates.

### August 25, 2026 — Local audition rendering and Scratchpad shortlist

- Located the bundled Python 3.12.13 runtime and ran the complete repository test suite successfully.
- Added `mpc-program-audition`, a deterministic standard-library renderer for gzip/JSON Keygroups and XML Drum programs.
- Keygroup auditions select layers at alternating velocities, apply approximate root-note pitching, and render a fixed ten-note phrase.
- Drum auditions render the first 16 populated instruments at a fixed velocity.
- Each audition produces a mono 44.1 kHz WAV plus a JSON event manifest documenting every selected sample and pitch transformation.
- Removed the deprecated `audioop` dependency after a partial stereo frame exposed its strictness; explicit frame-aligned PCM decoding now supports 8-, 16-, 24-, and 32-bit mono/stereo sources.
- All 34 repository tests pass under Python 3.12.
- Rendered seven non-silent candidate auditions: three Vinyl drum programs, Fisherman'sFriend bass, 360 E Piano, OneFiftySeven pad, and HumanMusic lead.
- Added the seven programs to `inventory/program-status.csv` as Scratchpad candidates without changing their honest hardware status of `untested`.
- Added `inventory/scratchpad-candidates.md` as the focused Key 37 listening list.
- Next gate: listen to these seven candidates locally and on the Key 37, select one main drum program and one lead/pad, and record hardware results before assembling the Scratchpad project.

### August 25, 2026 — Lean hardware-test SD image

- Chose to build up a small, purpose-specific SD image instead of transferring the complete cleaned backup.
- Added `scripts/package_scratchpad_candidates.py` to create a repeatable MPC directory skeleton and package only the samples referenced by the selected programs.
- Built `FG Vinyl Scratchpad v0.1 - Lean SD Image` on the external `Storage` drive with seven hardware-test candidates: four Keygroups and three Drum programs.
- Made each candidate self-contained to avoid dependence on the full Samples From Mars library during hardware testing.
- Added a root `README.txt` with transfer instructions and `CANDIDATES.json` with source, role, type, and sample-count provenance.
- Audited the external-drive copy itself: all seven programs pass structural and semantic checks, with zero missing, ambiguous, or zero-byte references and zero dead or stacked trigger cells.
- Final transfer footprint is 261 MB and 520 files. The interrupted full-mirror transfer remains separately labeled `INCOMPLETE_DO_NOT_COPY - full mirror attempt` and is not part of the lean image.
- Next gate: copy the contents of the lean image to a blank SD card, audition all seven candidates on the Key 37, and record hardware results before choosing the four-program Scratchpad core.

### August 25, 2026 — Ubuntu Drum Program colors and routing handoff

- Confirmed the three curated Drum Programs load on the Key 37 and trigger their expected samples across pad banks.
- Derived the authoritative 24-bit `0xRRGGBB` pad-color representation from a controlled MPC 3.9.1.2 resave and added semantic kick, snare, clap, rim, hat, cymbal, tom, percussion, FX, and fallback colors.
- Added color support for both legacy XML Drum Programs and compressed Drum Programs resaved by MPC 3; all 43 repository tests pass on Ubuntu.
- Installed and verified clean `FG COLORS` versions of all three kits while retaining the untouched source programs and archiving the seven hardware-test iterations locally.
- Revalidated all seven Scratchpad candidates directly from the mounted SD card and regenerated ignored local audition WAVs/manifests; every candidate passes structural and semantic checks.
- Selected a provisional routing-test core: Vinyl SP drums, Fisherman'sFriend bass, E Piano keys, and HumanMusic lead. These remain subject to final Key 37 listening approval.
- Added a controlled two-project capture procedure in `docs/key37-routing-capture.md`: save an identical two-track baseline, apply only Key Ranges `Drum Split`, then save the changed project for read-only comparison with the isolated Mac XPJ inspector.
- Added a read-only Drum performance audit and confirmed all three curated kits pair their open/closed hats in explicit mute groups; no automatic choke-group rewriting is currently necessary.
- Corrected ambiguous filename classification to prioritize the leading instrument token (`CH 808 Snap` is a closed hat; `Tom 606 BD` is a tom) before descriptive tokens used later in a filename.
- Next gate: complete the four melodic/favorite listening decisions, capture both XPJs and companion data folders, and compare the single Drum Split change.

### August 26, 2026 — Key 37 routing capture and minimal Scratchpad

- Captured and hash-verified the baseline, Drum Split, and dedicated-input MPC
  projects plus their companion ProjectData folders without committing licensed
  samples or project captures.
- Confirmed from the XPJs that Drum Split changes note filters and replaces the
  custom Drum Program pad-note map with an identity map; it is not independent
  physical keyboard/pad routing.
- Confirmed that the dedicated-input project persists `MPC Keyboard` for the
  Wurli track and `MPC Pads` for the Vinyl SP track. The MPC Pads `Global`
  preference is device state and is not stored in the project.
- Established the closest-known-good posture: leave the Drum track selected to
  retain Drum Program pad colors while the armed melodic track receives the
  keyboard.
- Passed the core Minimal Scratchpad acceptance test by quickly recording a
  four-bar part with drums, bass, and lead.
- Passed individual external MIDI routing for Volca Bass on channel 1, Volca
  Keys on channel 2, and Volca Drum in single-channel mode on channel 10.
- Mapped Volca Drum parts 1–6 to adjacent MPC pads A01–A06. Volca Drum follows
  MPC clock, start, stop, and tempo. Later XPJ inspection showed the saved MIDI
  tracks contain no note events; the heard pattern was local to the Volca.
- Captured and inspected protected Scratchpad and Volca master/jam pairs. The
  Scratchpad jam contains drums, Pluck Bass, and Wurli events; OneFiftySeven is
  empty. The Volca projects preserve track routing, names, and the six-pad map.
- Added a distinct four-way lead/pad bracket and a manifest-driven legacy Drum
  Program builder. Generated and SD-deployed `FG Vinyl Shots 01`, with 32
  self-contained percussion/FX pads and passing local/post-copy simulation.
- Next gates: listen to the lead/pad bracket and FG Vinyl Shots, explicitly
  record an MPC-authored Volca note sequence, test Bass and Keys clock
  sequentially, then complete simultaneous Volca acceptance after the MIDI
  thru/splitter arrives.
- The Launch Control XL 3 has arrived, but its firmware, Components custom mode,
  and MPC MIDI Learn setup are intentionally deferred until the current
  Scratchpad and Volca baselines pass save/reload testing.
- A CME MIDI Thru5 WC has been ordered and confirmed as the permanent
  one-input/five-output distributor for the Volca rig. Bass, Keys, and Drum
  retain MIDI channels 1, 2, and 10; simultaneous acceptance begins after it
  arrives.

### August 26, 2026 — six-bank shots and v0.2 software foundation

- Extended the non-destructive Vinyl Shots manifest chain to version 03 with
  96 one-shots across Banks A–F; Banks G–H remain intentionally open.
- Deployed version 03 additively to the SD, matched its local/card XPM checksum,
  and passed post-copy simulation and Drum audit with no missing, dead, stacked,
  or structurally suspect pads.
- Assigned `FG Vinyl Shots 03 Six Bank` to Track 2 in the version-controlled
  Scratchpad rig. The protected MPC project still requires an on-device load
  and Save As; no XPJ was rewritten on Ubuntu.
- Added Program Model v1 adapters for Drum manifests, legacy XML XPMs, and MPC 3
  compressed Drum/Keygroup XPMs.
- Added hierarchical semantic roles with reusable TOML filename/stem overrides,
  a declarative Key 37 device profile, and deterministic Classic, right-handed,
  left-handed, and full-library layout plans.
- Validated 96 Drum zones from Vinyl Shots, 73 Keygroup zones from Mirage Wurli,
  and complete 96-zone placement under all four layouts.
- The next software gate is a non-mutating layout-to-XPM exporter followed by
  load/reload comparison of two generated variants on the Key 37.

### August 26, 2026 — layout export and catalog foundation

- Added non-destructive layout export for both legacy XML and MPC 3 compressed
  Drum Programs. Complete 128-record permutations preserve layers, choke and
  playback settings, unknown fields, note maps, registries, effects, and global
  settings while moving semantic pad colors with each sound.
- Added an independent verifier plus overwrite and in-place mutation refusal.
- Generated a four-variant, self-contained `FG Vinyl Shots 03` hardware package
  in ignored local storage. Classic, right-handed, left-handed, and full-library
  variants each contain 96 checksum-recorded WAVs and pass local simulation.
- Added a metadata-only program catalog with offline querying by type, role,
  hardware status, favorite, and text. The immutable-backup proof indexed all
  750 ledger rows: 746 pass and four old testing artifacts are explicitly
  missing.
- No licensed audio, generated XPM, or hardware package is eligible for source
  control. The next hardware gate is a Classic/handed load-reload comparison;
  the next software slice is role-addressed deterministic drum MIDI.

### August 26, 2026 — deterministic role-addressed Drum MIDI

- Extended Program Model v1 with each Drum Program's actual 128-entry
  `PadNoteMap` for legacy XML and MPC 3 compressed XPMs.
- Added reproducible TOML pattern recipes with role families, probability,
  density, swing, gate, velocity humanization, and deterministic sound
  selection.
- Added source/layout resolution that keeps semantic events fixed while changing
  the MIDI note when a sound moves to a new pad.
- Added format-0 Standard MIDI export at 480 PPQ plus a JSON event/provenance
  sidecar. Existing outputs require explicit replacement.
- Generated a real `dusty-pocket` source/Classic pair from Vinyl SP. Both have
  28 events under seed 37 at 91 BPM; MIDI inspection passes and the moved snare
  follows its Classic pad-note assignment.
- Hardware import and groove acceptance remain open. No generated MIDI or
  licensed program material is committed.

### August 26, 2026 — final internal palette and eight-bank shots

- Selected Mirage Pluck Bass for Track 3, Emulator Dark FM for Track 5 Lead,
  Kawaii Dreams Glass Howl for Track 6 Pad, and Juno Sub Smooth for Track 7
  Bass Pad; Mirage Wurli remains the Track 4 keys favorite.
- Added the dedicated Glass Howl Pad on Track 6 and Juno Sub Smooth Bass Pad on
  Track 7. Restored Loops on Track 8 and moved audio capture/resampling to Track
  9; eight tracks were only a controller vocabulary, not an MPC limit.
- Extended Vinyl Shots to version 04 with all 128 pads populated. Bank G holds
  eight kicks and eight snares; Bank H holds eight matched closed/open hat
  pairs.
- Added declarative per-pad mute groups to the Drum manifest builder. All eight
  Bank H hat pairs pass the independent choke-group audit.
- Generated the self-contained 128-WAV hardware package in ignored local
  storage. Semantic simulation and Drum audit pass. It is now deployed in the
  shallow SD folder `00 FG Scratchpad/02 Vinyl Shots`; Key 37 load/reload
  acceptance remains open.

### August 26, 2026 — reusable kit-bank composition

- Added a portable Drum bank recipe and `mpc-drum-compose`, which selects
  complete 16-pad banks from existing XPMs, resolves extensionless MPC sample
  references, and refuses incomplete banks, ambiguous audio, duplicate targets,
  or flattened filename collisions.
- Rebased each selected bank's single mute group to isolated groups 1–8 so hat
  choking remains local to the kit bank.
- Generated `FG Vinyl Kit Banks 01` from 808 Standard, 909 Standard,
  Machinedrum, CR78, LM1, Acoustic Vinyl, Old Tape, and Acoustic Hybrid source
  banks. The ignored package contains one XPM and 128 WAVs.
- Real-data simulation and the independent Drum audit pass with all 128 pads,
  semantic colors, zero missing/dead/stacked triggers, and eight valid mute
  groups. SD deployment waits for the card filesystem to be repaired and
  confirmed reliably writable.

### August 27, 2026 — explicit Drum velocity layers

- Extended the Drum manifest and builder with one through four explicit layers
  per pad, strict complete 0–127 velocity coverage, per-layer sample endpoints,
  and inactive clearing for unused template layers.
- Preserved the single-sample manifest shorthand and all existing one-shot
  output behavior.
- Created `FG Vinyl Layered Kit 01`, a 16-pad timbre-morph kit using four
  velocity-selected Vinyl SP hits per pad. It deliberately distinguishes
  curated timbre morphing from true multisampled acoustic dynamics.
- The ignored 64-WAV package passes Program Model validation, semantic
  simulation, and Drum audit with zero missing, dead, or stacked velocity cells
  and two valid closed/open-hat mute groups. Hardware feel and transition
  acceptance wait for SD repair.

### August 27, 2026 — Vinyl Breaks Clip groundwork

- Audited Vinyl Breaks From Mars: 200 stereo 44.1 kHz WAV loops and one Ableton
  project, but no MPC XPM/XPJ/XPN Clip reference.
- Added `mpc-loop-inventory` for leading BPM, musical variant, audio shape,
  duration, estimated beats, and timing-deviation reports.
- Indexed all 200 real loops without parse, audio, or timing errors. The library
  spans 73–200 BPM and contains full, no-percussion, no-snare, percussion,
  pitched, clean, colored, and degraded material.
- Defined the minimal Key 37 Clip capture needed before serialization. A true
  Clip exporter remains gated on evidence for launch, quantization, warp,
  tempo, mute, and project-link fields rather than guessed XPM values.

### August 27, 2026 — transaction-safe deployment and Ableton intent

- Added resumable, transaction-safe self-contained package deployment with a
  sustained write probe, per-file and aggregate hashes, hidden verified
  staging, atomic promotion, and strict conflict/symlink refusal.
- Simulated a mid-copy device disconnect: the final browser path remains absent
  and the verified stage resumes without recopying completed files.
- Added read-only gzip/plain XML Ableton `.adg` and `.als` inspection for
  devices, branches, macros, sample maps, zones, endpoints, loops, and warp
  state, plus conservative A–D translation suggestions.
- Indexed all 23 Vinyl SP Ableton presets without errors. The two Live sets are
  Close translations; the individual-hits and 20 prepared Rack presets are
  Template translations because their Drum/instrument/effect branch structure
  exceeds a literal one-program mapping.
- Reviewed Individual Hits, 808 Standard, Acoustic Hybrid, Old Tape, and Flux
  against raw XML counts and wrote the Vinyl SP pilot translation
  specification. Prepared kits share a 16-zone unwarped one-shot topology and
  a stable Tune/Decay/Drive/Cutoff/Comp/Reverb vocabulary; their curated sample
  membership is the primary musical difference.

### August 27, 2026 — complete Ableton corpus audit and MPC backlog

- Audited all 1,718 readable `.adg` and `.als` sources across 82 Samples From
  Mars packs with zero parse failures: 1,612 device groups and 106 Live sets.
- Added bounded parallel inventory so the complete local library can be
  rescanned reproducibly without changing serial ordering or output.
- Added a catalog-aware backlog generator that classifies Drum, Keygroup, Clip,
  and project targets; scores P0–P3 priority; and preserves the complete
  preset-level queue in ignored local JSON.
- Hashed every source preset and found 12 byte-identical files in the duplicate
  `modern_oddities_from_mars(1)` tree. They remain visible for provenance but
  are automatically demoted and linked to the canonical files.
- Generated a committed 82-pack queue and a curated execution roadmap. The five
  P0 candidates are SP-1200 chromatic Keygroups; the unwarped 16-pad Big Break
  and Hand Break racks lead the next Drum Program wave. Vinyl Breaks remains
  intentionally gated on the MPC-authored Clip reference.

### August 27, 2026 — first unattended Ableton-to-MPC build wave

- Added a conservative Ableton Drum Rack translator and reproducible batch
  recipe. It preserves branch order, samples, velocity layers, receiving-note
  provenance, and choke groups while reporting unimplemented Rack behavior.
- Built five SP-1200 chromatic Keygroups from 80 unique WAVs and explicit
  Ableton roots: Analog Tom, Chimes, Cowbell, Tom, and Tone.
- Built 27 self-contained Drum Programs from 440 WAV copies across Vinyl Drums,
  SP-1200, 505, 606, 626, 707, 808, 909, CR-78, DMX, Drumtrax, Drumulator,
  LM-1, S950, Modern Oddities, and Found Sounds.
- All 32 programs have zero dead or stacked trigger cells. Every Drum Program
  passes semantic simulation; 25 pass the independent choke audit and two
  retain explicit source-choke warnings. The five Keygroups retain deliberate
  outer-range extrapolation warnings for hardware judgment.
- The ignored 67 MB hardware package contains 552 checksum-verified files,
  complete pad maps, audio-level reports, and a committed listening plan. No
  licensed WAV or generated XPM is tracked.

### August 27, 2026 — Scratchpad v02 capture and Clip reference deployment

- Copied the new `FG Vinyl Scratchpad v02 Master` and its companion ProjectData
  read-only from SD into ignored local capture storage and verified every
  source/capture hash.
- Confirmed the seven selected programs and nine musical tracks are present,
  but the project contains no sequence. The track named `Clip` is currently a
  Keygroup, not an MPC Clip track; the Audio track remains `Audio 001`.
- Deployed the 80 BPM `080 Black Phase Vinyl Breaks Clean.wav` reference loop
  to the shallow SD hardware-test folder with a sustained-write probe and
  byte-for-byte verification.
- The next hardware gate is a minimal MPC-authored Clip baseline/changed pair,
  followed by replacing the Scratchpad's placeholder Track 8 in a Jam copy.

### August 27, 2026 — normal-register Keygroups and layered main drums

- Added a reusable fixed root-shift operation to single and batch Keygroup
  builds, including MIDI-bound validation and preservation tests for layers,
  endpoints, intervals, and source audio.
- Rebuilt the five SP-1200 chromatic instruments two octaves higher. Their 80
  unmodified WAVs now map roots to MIDI 49–74; all five packages have zero dead
  or stacked cells and were checksum-verified after SD deployment.
- Built `FG Vinyl Layered Main 02` from 64 curated Vinyl SP layers. Its 16 pads
  use coherent families and the two choke pairs use open hats with audible tails
  at every velocity region.
- The refined Drum Program passes Program Model validation, semantic simulation,
  and independent Drum audit, then matched all 65 local files after SD deployment.
- Hardware listening retains `FG Vinyl Layered Main 02` as an expressive Drum
  alternate rather than the Scratchpad main kit; `Vinyl SP From Mars 01`
  remains the main-drums favorite.
- The first +24-semitone SP-1200 register fix is close on hardware but should
  move one more octave right. NR2 at +36 semitones preserved the same 80 WAVs
  and passed structural/model checks, but hardware still found seven keys
  unavailable at the default position. Built and externally preserved NR3 at
  +48 semitones with roots MIDI 73–98; SD transfer was safely deferred when the
  card was removed before transactional staging began.
- Hardware layout comparison selects the right-handed performance variant over
  Classic. The improvement is modest because the source has many varied
  one-shots instead of a compact kick/snare/cymbal kit. Both variants reload
  with samples, playback, and semantic colors intact, closing the v0.2 layout
  hardware gate.
- Deployed the complete v2 layout bracket—Classic, right-handed, left-handed,
  and full-library—plus the source/classic `dusty-pocket` MIDI pair. All four
  XPMs pass directly from SD, both MIDI files remain valid format-0 data, and
  all 396 transferred files match their local sources by SHA-256.
- Added a reusable read-only plugin-content audit. The current SD exposes 962
  presets across its Synths tree, including Iona (104), OPx-4 (672), and AIR
  Flavor Pro (101), while explicitly withholding activation claims until the
  MPC selector and project-reload tests pass.
- Hardware rejected both format-0 `dusty-pocket` files on MPC 3.9.1.2: Load
  flickered, but no sequence was created. Changed the generator's MPC-targeted
  default to format 1 with separate conductor and note tracks, retained an
  explicit format-0 option, generated a local replacement pair, and left
  format-1 import as the next hardware gate. The replacement pair subsequently
  imported and played successfully; hardware listening judged its semantic
  source/Classic correspondence close enough, with an explicit caveat that the
  varied one-shots make exact audible comparison difficult.
- Confirmed Fabric and Jura are installed on MPC internal storage; Mini D and
  Studio Strings remain unpurchased and deferred. The user accepted ordinary
  plugin project persistence without a dedicated power-cycle audit, to be
  reopened only if a real project reports missing state.
- Deferred the modern Clip reference because MPC Pro Pack is not owned on the
  Key 37. Clip Matrix is therefore an optional purchase-gated capability, and
  a Keygroup named `Clip` will not be treated as a substitute.

### August 27, 2026 — recoverable SD cleanup and broad Drum expansion

- Snapshotted and checksum-verified the live Scratchpad, protected project,
  completed hardware tests, and legacy test project to the external drive.
  Completed-test clutter, empty Clip placeholders, the old test XPJ, and stale
  Trash copies were moved into a recoverable quarantine; the protected
  Scratchpad master and ProjectData were not modified.
- Updated the shallow Scratchpad layout guide to identify the Track 8 Keygroup
  placeholder accurately and explicitly deferred cold-start timing.
- Recombined 24 hardware-accepted Ableton Drum Programs into three 128-pad
  performance collections: Classic Machines, Character Machines, and
  Breaks/Texture. Source pad order is preserved and bank choke groups are
  isolated.
- Expanded the accepted velocity-layer architecture into `FG Vinyl Layered
  Banks 03`: 64 pads, 212 copied WAVs, four complete velocity regions per pad,
  and seven independent hat pairs across refined, machine, acoustic/tape, and
  experimental banks.
- All four new packages pass Program Model import and semantic simulation with
  zero missing samples, dead cells, or stacked cells. Classic and Layered pass
  Drum audit; Character and Breaks/Texture retain only their already accepted
  source-choke warnings.
- Mirrored the 600-file batch to the external drive, passed a 32 MiB sustained
  SD write probe, transactionally deployed it as Drum Alternates 06-09, and
  added an on-card bank/test index.
- Removed the bank composer's flat-staging prerequisite. Recipes can now use
  safe relative XPM paths into nested self-contained packages; audio resolves
  beside each source first, path and symlink escapes are rejected, and selected
  WAVs are staged internally only for the final package build. All three A-H
  programs rebuilt directly from the accepted nested package tree with
  byte-identical XPM and package output.
- Consolidated the completed hands-on evidence into a living descriptive Key 37
  field review. New hardware acceptance is deferred while software development
  continues; the existing checklist remains a ready-to-resume protocol rather
  than the immediate work queue.
- Delivered the first v0.3 Program Designer slice as a self-contained, read-only
  HTML/JSON generator. It imports manifests plus XML/compressed XPMs, renders
  physical Drum banks or a movable 37-note Keygroup view, exposes layers and
  playback metadata, and reports sample, velocity, device, loop, and mute-group
  findings. Real layered-drum and Wurli viewers passed interactive browser
  checks without source writes or console errors.
- Expanded Program Designer bundles to multiple sources and device profiles,
  with in-view switching and deterministic side-by-side Drum/Keygroup
  comparisons. Comparison JSON records changed locations and fields plus
  zone, layer, warning, and error deltas; the bundled UI never accesses or
  rewrites source files. Added an Akai-specification-backed Key 61 profile.
- Added a source-safe Drum layout workspace using the existing reusable preset
  definitions. It supports cross-bank drag/click swaps, position locks, pad
  colors, bank mirroring, handed semantic layouts, undo/redo and resets,
  source-versus-draft comparison, and deterministic assignment preview. Drafts
  remain in memory and isolated per program/device; export stays a separate
  explicitly validated step.
- Added fingerprinted draft downloads plus a strict `mpc-layout-draft` adapter.
  It requires exact source/model/device identity, emits builder-compatible
  manifests, and delegates XML or compressed XPM writes to the independently
  verified complete-record permutation engine. Browser-generated real-data
  manifest and XPM round trips passed without tracking generated programs or
  licensed audio.
- Added optional Standard MIDI groove analysis to Program Designer. Format 0/1
  note-ons map through each kit's own PadNoteMap into heat, velocity/share, and
  unmapped-note evidence. Deterministic left/right lower-corner reach models
  produce reversible suggestions while preserving source and current-draft
  locks. The accepted 28-note `dusty-pocket` file mapped completely across
  seven sounds in the 64-pad layered XPM; browser toggle, apply, undo, and
  uniqueness checks passed with no console warnings.
- Started v0.4 with a preservation-first expressive Keygroup exporter. A strict
  TOML allowlist changes proven MPC 3 transpose, amp/filter envelope, cutoff,
  and resonance fields, while the complete raw source document and companion
  audio remain the authority. Independent verification rejects any undeclared
  document change or ProgramData checksum mismatch. Clean, Warm, Pad, Pluck,
  Bass, and Lo-Fi candidate specs can be packaged together in one command;
  their musical values remain pending Key 37 listening rather than being
  silently promoted from software inspection.
- Exercised that exporter against the accepted Mirage Wurli. The ignored local
  package contains six self-contained candidates and 438 checksum-verified
  ProgramData copies. All candidates retain 74 instrument/layer records, 73
  registry entries, full 128-note coverage, and no dead or stacked cells. They
  introduce no semantic issues; the two reported outer-register extrapolation
  warnings are identical to the accepted source and remain clearly labeled as
  inherited rather than new variant failures.
- Recovered safely from an SD `fsync` I/O error without publishing a partial
  package. After exFAT repair and read-write remount, the transaction resumed
  from 159 checksum-checked staged files and atomically deployed all 446 files
  under package hash `082b51106a1b575a2e82c5b746d70d77aadd9a445da2d0e4ad175d15be74a8f2`.
  A second full inventory returned unchanged, the staging directory was
  cleared, and an on-card semantic scan found the same inherited warnings with
  no dead or stacked cells.
- Replaced the next manual-register guess with reusable octave-only useful-range
  inference. Single builds accept `--root-target LOW:HIGH`; batch manifests use
  `root_target`. The decision report exposes source, target, shift, result, and
  coverage, while strict validation prevents simultaneous fixed/automatic
  shifts and MIDI overflow. The NR2 software regression fixture declares
  target 60–96 and infers the same +36 correction for all five programs across
  80 unique WAVs; broad already-useful mappings remain unchanged on ties.

### August 27–28, 2026 — unattended creative workstation software

- Completed deterministic chord and harmonic-rhythm generation with
  scale-degree progressions, nearest voice leading, strict chord/bass note
  ranges, configurable three- or four-note voicings, and chord-following bass
  patterns. Each run writes named format-1 tracks and full JSON evidence.
- Added scale-safe motifs whose literal first statement receives seeded
  neighbor, octave, and rest variation on later repetitions. Useful range is a
  hard boundary and every event records its origin and variation decision.
- Combined semantic Drums, Bass, Chords, and Melody into four-track workstation
  bundles. The generator fingerprints the real Drum Program used for note-map
  resolution and writes MIDI, JSON, and exact program-assignment guidance.
- Expanded the initial dusty, ambient, and electro setups with complete 80s
  funk, house, and weird families. All six have independent drum, harmony,
  bass, and melody behavior and were generated successfully against real Drum
  Programs on the external-drive mirror.
- Added a reversible arrangement outline: Main, Main B, Breakdown, Build, and
  Outro remain separate MIDI candidates. Main B changes velocity on an exact
  seeded percentage, locked tracks survive every section unchanged, and stable
  source IDs plus omitted-ID lists retain a path back to the complete base.
- Added bounded seed batches as the reproducible `Surprise Me` path. Ranking is
  explicitly limited to observable event diversity and never presented as a
  substitute for musical listening.
- The dependency-free test suite now passes 213 tests. Repository artifact
  guards confirm no licensed WAV, XPM, or XPJ entered Git. Six complete
  workstation candidates, a five-section arrangement, six additional dusty
  seeds, standalone components, guides, and recipes were byte-compared after
  mirroring to `MPC Transfer/FG Software Candidates 2026-08-28` on the external
  drive. All MPC import/listening status remains deliberately deferred.

### August 28, 2026 — cross-library wave and reusable release fixture

- Added four contrasting descriptor-driven kit recipes alongside Dusty
  Cross-Library: Tight Machine, Ambient Percussion, SP Punch, and Experimental
  Texture. One transactional wave command measures the source catalog once,
  preflights all recipes, rejects identical source sets, publishes pairwise
  overlap evidence, and atomically builds each independently audited Program.
- Built the five-program licensed-local wave from the three hardware-accepted
  vinyl source kits on the external mirror. All 80 sample copies and five XPMs
  pass checksum, model, semantic, and Drum-audit gates. The highest pairwise
  overlap is 6/16 samples; hardware listening remains deferred.
- Added a freely redistributable portable demo that deterministically
  synthesizes 16 CC0 WAVs and exercises source Drum Program, enriched catalog,
  cross-kit selection, final Drum Program, four-track MIDI, and five-section
  arrangement workflows. It includes recipes, provenance, checksums, licensing,
  and a full-path hardware checklist.
- Expanded the Launch Control compiler with a hardware checklist, editable
  results ledger, and semantic map comparison. The conservative and USB-DIN
  bridge variants change three mode outputs and three MPC routes while changing
  zero control assignments.
- Deployed the five-program cross-library Drum wave, the five-program NR2
  Keygroup package, the portable workflow Drum/MIDI fixture, and the generated
  creative-MIDI/arrangement backlog to a new shallow `00 FG Hardware Tests`
  tree. A 64 MiB sustained-write probe and all 266 package checksums passed;
  hardware listening remains deliberately open. The previously laptop-only NR2
  source package now also has a checksum-verified canonical external-drive copy.
- The dependency-free suite now passes 242 tests, the wheel/sdist build passes,
  and the licensed-artifact repository guard remains clean.

### September 3, 2026 — XPJ inspection joins the main toolset

- Integrated the previously isolated read-only MPC 2/MPC 3 XPJ inspector after
  real MPC 3.9.1.2 startup-template captures made project-level MIDI Learn
  inspection directly useful to the Launch Control workflow.
- The inspector detects project generation by content, summarizes tracks and
  sequences, losslessly extracts MPC 3 JSON, and compares captures with JSON
  Pointer paths. It never writes an XPJ.
- Unknown fields and opaque plugin state remain preserved. Project captures,
  ProjectData, licensed audio, and controller SysEx exports remain local
  evidence rather than repository source.
- Added read-only Launch Control XL 3 Components capture inspection plus an XPJ
  MIDI Learn cross-check. Six real Custom Modes parse successfully; the newer
  Boot template matches 37/41 OPx and 40/44 Jura channel/controller pairs.

## 16. Reference material

- [Akai: Understanding and Loading MPC Programs](https://support.akaipro.com/en/support/solutions/articles/69000804211-akai-pro-mpc-series-understanding-and-loading-programs)
- [Akai: MPC Key 37 pads and keys routing](https://support.akaipro.com/en/support/solutions/articles/69000871268-akai-pro-mpc-key-37-using-the-mpc-key-37-as-a-midi-controller)
- [Akai: MIDI Learn for instruments, effects, and mixer controls](https://support.akaipro.com/en/support/solutions/articles/69000858700-akai-pro-mpc-series-mapping-plugin-instruments-fx-parameters-via-midi-learn)
- [Akai: Automatically loading a project](https://support.akaipro.com/en/support/solutions/articles/69000859016-mpc-2-standalone-how-to-load-a-project)
- [Novation: Launch Control XL 3 Custom Modes](https://support.novationmusic.com/hc/en-gb/articles/27203903097362-Launch-Control-XL-3-Components-guide)
- [Ableton: Instrument, Drum, and Effect Racks](https://www.ableton.com/en/manual/instrument-drum-and-effect-racks/)
- [Samples From Mars: Vinyl SP From Mars](https://samplesfrommars.com/products/vinyl-sp-from-mars)
- [Samples From Mars: Vinyl Synths From Mars](https://samplesfrommars.com/products/vinyl-synths-from-mars)
- [Samples From Mars: Vinyl Drums From Mars](https://samplesfrommars.com/products/vinyl-drums-from-mars)
