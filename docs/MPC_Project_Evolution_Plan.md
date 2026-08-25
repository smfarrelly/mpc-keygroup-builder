# MPC Project Evolution Plan

**Owner:** Steve Farrelly  
**Started:** August 25, 2026  
**Status:** Active — Phase 0 preservation and inventory  
**Canonical working copy:** `docs/MPC_Project_Evolution_Plan.md`  
**Primary instrument:** Akai MPC Key 37  

## 1. Project north star

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

All templates should preserve the same eight-strip mental model wherever practical.

| Strip | Standard role | Vinyl Scratchpad | Volca Jam |
|---|---|---|---|
| 1 | Main drums | Vinyl drum kit | Volca Drum |
| 2 | Percussion/one-shots | Stabs, vocals, FX | MPC percussion/one-shots |
| 3 | Bass | Vinyl bass keygroup | Volca Bass |
| 4 | Chords/keys | Vinyl piano, EP, or chords | Volca Keys |
| 5 | Lead/pad | Warbly lead or pad | Internal lead/pad |
| 6 | Loops | Breaks and melodic loops | Loops or additional sequence material |
| 7 | Texture/guest | Crackle, static, ambience | Texture or guest hardware |
| 8 | Capture/transition | Resampling and transitions | Resampling and transitions |

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
- [ ] Select one percussion/one-shot program.
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

- [ ] Inventory Ableton `.adg`, `.als`, and related preset files for the first vinyl pack.
- [ ] Manually inspect five representative presets.
- [ ] Build an analyzer that emits a structured report of samples, zones, chains, macros, playback, and effects.
- [ ] Compare analyzer results against what is visible in Ableton or against readable source metadata.
- [ ] Assign translation-fidelity labels.
- [ ] Produce a translation specification for the pilot pack.

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
- [ ] Use synthetic or freely licensed audio for fixtures and demonstrations.
- [ ] Add deterministic build tests.
- [ ] Add missing-file, invalid-zone, path, and installation validation.
- [ ] Document the bring-your-own-samples licensing model.
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

- [ ] Choose one working vinyl drum kit.
- [ ] Choose one favorite vinyl bass.
- [ ] Choose one favorite vinyl keys/chord sound.
- [ ] Choose one favorite lead, pad, or texture.
- [ ] Create the eight-track project skeleton.
- [ ] Load those four initial sounds into their standard track positions.
- [ ] Set starting levels and one useful shared reverb/delay environment.
- [ ] Save as `FG_Vinyl_Scratchpad_v0_1`.
- [ ] Make a short sequence and perform a few changes to prove the concept.

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
