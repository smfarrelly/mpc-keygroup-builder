# mpc-keygroup-builder

`mpc-keygroup-builder` converts a directory of pitched WAV files into an MPC 3.9 JSON
keygroup program. It supports one-shot-per-note instruments and up to eight
velocity layers per note. It uses a known-working MPC-generated XPM as the
schema template and preserves the special universal/audition instrument
record.

## Project setup

The project uses [uv](https://docs.astral.sh/uv/) for Python, environments,
locking, execution, and packaging. From the repository root:

```bash
uv sync --locked
```

Run the tests and build distributable artifacts with:

```bash
uv run python -m unittest discover -s tests -v
uv build
```

Project metadata lives in `pyproject.toml`, the reproducible dependency lock
is `uv.lock`, and uv creates the local environment in the gitignored `.venv/`
directory.

See [the MPC helper-project compatibility survey](docs/mpc-ecosystem-survey.md)
for related open-source work, licensing constraints, and the features selected
for independent implementation in `mpc-keygroup-builder`.

See [the product roadmap](docs/PRODUCT_ROADMAP.md) for the dependency-led path
from the current Drum Program/Layout milestone through the visual Program
Designer, expressive instruments, creative MIDI, project generation,
arrangement, catalog, and live-companion work.

See [the living MPC Key 37 field review](docs/MPC_KEY37_FIELD_REVIEW.md) for the
descriptive hardware findings: practical strengths, routing behavior, program
compatibility, storage lessons, external MIDI results, and explicitly deferred
acceptance work.

## License

The source code is available under the [MIT License](LICENSE). Sample libraries,
audio files, and generated MPC programs are not included and remain subject to
their respective owners' licenses.

## Program types and Drum Program pad colors

`mpc-program-color` detects whether an existing XPM is a Drum Program or a
keygroup. Use `--program-type drum` or `--program-type keygroup` when a workflow
must require a specific type; a mismatch is rejected rather than relabeled.

Drum Programs can be copied with semantic pad colors derived from their sample
names:

```bash
uv run mpc-program-color "Vinyl Drums From Mars 01.xpm" \
  --program-type auto \
  --palette pad-colors.example.toml \
  --name "Vinyl Drums From Mars 01 COLOR TEST" \
  --output "Vinyl Drums From Mars 01 Colored.xpm"
```

Use `--dry-run` to report the detected type and category counts without writing.
The built-in categories are kick, snare, clap/snap, rim, closed hat, open hat,
cymbal, tom, percussion, FX, and unknown. Copy `pad-colors.example.toml` and
change any RGB hex value to create a project-specific palette. The tool stores
readable RGB values in MPC's 24-bit ProgramPads color representation, disables
the program's universal-color override, and selects fixed-color display mode so
the individual category colors remain visible instead of generic velocity colors.
Both legacy XML Drum Programs and compressed programs resaved by MPC 3 are
supported.
For XML Drum Programs, each `Instrument` number is the one-based physical pad
slot, so its sample classification is written to color slot `number - 1`.
`PadNoteMap` controls incoming MIDI notes and does not determine physical pad
colors.
Use the optional `[overrides]` table to assign an unusual exact sample filename
or filename stem to a category without modifying the built-in matching rules.
Leading instrument tokens take precedence over later descriptive tokens, so
names such as `CH 808 Snap` remain closed hats and `Tom 606 BD` remains a tom.

Inspect a Drum Program's populated pads and hat choke behavior without writing:

```bash
uv run mpc-drum-audit "/path/to/Drum Program.xpm"
```

Add `--json` for per-pad sample category, mute group, polyphony, monophonic
state, and playback-mode data. The audit supports legacy XML and MPC 3
compressed Drum Programs and warns about ungrouped or mismatched open/closed
hats.

This operation does not convert a keygroup into a Drum Program. Program-type
selection is validation rather than a type-label rewrite.

Build a self-contained one-shot Drum Program from a TOML pad manifest and a
known-good 128-pad legacy Drum template:

```bash
uv run mpc-drum-build inventory/fg-vinyl-shots.toml \
  --template "/path/to/template.xpm" \
  --source-root "/path/to/source-wavs" \
  --output "work/generated-drum-programs/FG Vinyl Shots 01"
```

The builder validates every WAV, copies only referenced audio, clears unused
pads and velocity layers, sets one-shot playback, writes inclusive endpoints,
and applies the semantic pad-color palette. It refuses a non-empty output
directory so an existing program cannot be silently overwritten.

A pad may replace the `sample` shorthand with one through four
`[[pads.layers]]` tables containing `sample`, `velocity_start`, and
`velocity_end`. Explicit layers must cover velocities 0–127 exactly without
gaps or overlaps. The builder writes each range into the MPC layer, copies each
referenced WAV once, and marks unused template layers inactive. See
`inventory/fg-vinyl-layered-kit.toml` for a complete 16-pad example.

A manifest may set `extends = "base-manifest.toml"` to append new pad banks
without repeating an established layout. Inherited pad numbers are locked:
accidental collisions are rejected rather than silently replacing a tested pad.
Each `[[pads]]` entry may also set `mute_group = 1` through `32`; this is used
for explicit closed/open-hat choking and defaults to no mute group.

Compose complete 16-pad banks from existing Drum Programs before building:

```bash
uv run mpc-drum-compose inventory/fg-vinyl-kit-banks.toml \
  --source-root "/path/to/source-programs-and-wavs" \
  --manifest-output work/fg-vinyl-kit-banks-resolved.toml \
  --template "/path/to/known-good-128-pad-template.xpm" \
  --package-output "work/generated-drum-programs/FG Vinyl Kit Banks 01"
```

The composer requires 16 populated pads in every selected source bank,
accepts safe relative XPM paths into nested self-contained program packages,
resolves samples beside each source before falling back to the common root,
refuses ambiguous or flattened-name collisions, and rebases each bank's single
mute group to an isolated target-bank group. This makes bank-as-kit collections
reproducible without flattening libraries or checking licensed XPM or WAV files
into source control.

Inventory tempo-named loops before designing a Clip Program:

```bash
uv run mpc-loop-inventory "/path/to/loop-wavs" \
  --json work/loop-inventory.json \
  --csv work/loop-inventory.csv
```

The report extracts leading filename BPM, musical variant, WAV shape and
duration, estimated beats, and timing deviations. It is format-independent:
Clip XPM serialization remains gated on a minimal MPC-authored reference
capture rather than a guessed file structure.

Inspect readable musical intent in gzip-compressed or plain XML Ableton racks
and sets:

```bash
uv run mpc-ableton inspect "/path/to/Preset.adg" \
  --json work/ableton-preset.json
uv run mpc-ableton inventory "/path/to/Ableton pack" \
  --json work/ableton-pack.json
```

Reports include device and branch types, named macros, sample references,
key/velocity zones, roots, tuning, sample endpoints, loops, warp state, and a
conservative A–D translation-fidelity suggestion. This is read-only source
analysis; it does not promise literal Ableton-to-MPC effect conversion. See
[Ableton source inspection](docs/ableton-source-inspector.md).

Turn a complete Ableton inventory into a coverage-aware MPC backlog:

```bash
uv run mpc-ableton-backlog work/samples-from-mars-ableton-inventory.json \
  --catalog work/program-catalog.json \
  --json work/samples-from-mars-mpc-backlog.json \
  --markdown inventory/samples-from-mars-mpc-backlog.md
```

The complete JSON retains every source preset. The Markdown view groups work by
pack and lowers priority when the existing MPC catalog already provides the
same program type.

Translate a maintained batch of prepared Ableton Drum Racks into self-contained
MPC Drum Program packages:

```bash
uv run mpc-ableton-drum plan inventory/ableton-drum-wave-01.toml \
  --library-root "/path/to/Samples From Mars" \
  --report work/ableton-drum-plan.json

uv run mpc-ableton-drum build inventory/ableton-drum-wave-01.toml \
  --library-root "/path/to/Samples From Mars" \
  --template "/path/to/known-good-128-pad-drum-template.xpm" \
  --output-root work/ableton-drum-programs \
  --manifest-root work/ableton-drum-manifests
```

The converter preserves Drum Rack document order, sample membership, velocity
layers, receiving-note provenance, and choke groups. It validates every source
before writing the batch and reports Rack macros, effects, gain, loops, tuning,
or warp behavior that are not serialized. Generated manifests, XPMs, and audio
stay in ignored local storage.

## Normalized programs and layout planning

`mpc-program-model` imports legacy XML XPMs, MPC 3 compressed XPMs, and Drum
manifests into the same validated Program Model v1. `mpc-layout` combines that
model with a declarative device profile and a semantic layout preset to render
deterministic Markdown or JSON pad plans. The repository ships a Key 37 profile
plus Classic MPC-ish, right-handed, left-handed, and full-library presets.

Both commands accept `--roles` with a TOML `[roles]` table for exact filename or
stem overrides; see `role-overrides.example.toml`. `mpc-layout-export` creates a
new XML or compressed Drum XPM by permuting complete instrument records and pad
colors; it refuses in-place changes. `mpc-layout-verify` independently confirms
that sample layers and unknown/global settings survived. `mpc-layout-package`
builds self-contained hardware-test variants with audio checksums, pad maps, and
local simulation results. See
[Program Model and layout export](docs/program-model-and-layouts.md).

Render that same model as a self-contained, read-only visual inspector:

```bash
uv run mpc-program-designer "/path/to/program.xpm" \
  --device devices/mpc-key-37.toml \
  --output work/program-designer/program.html
```

The Program Designer switches Drum Banks A–H, renders the physical 4-by-4 pad
surface, displays layers, colors, roles, MIDI notes, playback and mute groups,
and reports sample or velocity problems. Keygroups receive a movable 37-note
range viewer. Repeat `--compare` and `--device` to bundle multiple sources and
hardware profiles with in-view switching and side-by-side comparison. Repeat
`--layout` to add a source-safe Drum layout workspace with swaps, locks, color
editing, handed presets, undo/redo, source-versus-draft inspection, and a
fingerprinted JSON draft download. `mpc-layout-draft` validates that download
against the exact source and device, exports a reusable Drum manifest, or
creates a separately verified XPM while preserving complete instrument records
and global settings. Optional repeatable `--groove` MIDI inputs add per-pad
usage heat, hit/velocity summaries, unmapped-note reporting, and reversible
right- or left-hand usage-compaction suggestions. See
[MPC Program Designer](docs/program-designer.md).

## Expressive Keygroup variants

`mpc-keygroup-variant` creates self-contained, source-preserving candidates from
an MPC 3 compressed Keygroup. It changes only a strict declarative allowlist,
copies the matching ProgramData folder, and independently verifies the complete
output document plus every audio checksum. Six starting specifications live in
`variants/keygroups/`; their musical settings remain listening candidates until
accepted on hardware.

```bash
uv run mpc-keygroup-variant package "/path/to/Wurli.xpm" \
  --spec variants/keygroups/clean.toml \
  --spec variants/keygroups/warm.toml \
  --spec variants/keygroups/pad.toml \
  --output work/wurli-expressive
```

See [Expressive Keygroup variants](docs/keygroup-variants.md) for the schema,
preservation contract, supported parameters, and hardware listening protocol.

## Metadata catalog

`mpc-catalog build` combines the existing hardware ledger with normalized XPM
metadata without reading or copying audio. The resulting JSON records program
type, source format, zones, layers, sample-reference counts, key/pad ranges,
populated banks, semantic roles, favorite status, Scratchpad role, and hardware
notes. `mpc-catalog query` filters that portable index by type, semantic role,
hardware status, favorite status, or text. See [Program catalog](docs/catalog.md).

## Role-addressed drum ideas

`mpc-drum-idea` turns a TOML recipe into reproducible JSON and Standard MIDI.
Recipes name semantic roles such as `kick`, `snare`, or `hihat.closed`; the
generator resolves them through the source or selected layout and reads MIDI
notes from the XPM's own `PadNoteMap`. Seeds, probability, density, swing,
velocity humanization, multi-sound cycling, and random alternates are explicit.
See [Role-addressed drum ideas](docs/drum-ideas.md).

## Hardware workflow helpers

`mpc-hardware-results` validates a batch TOML listening report and updates the
750-row hardware ledger atomically; it is dry-run-only unless `--apply` is
passed. `mpc-project-capture` ingests the controlled Key 37 baseline/changed XPJ
pair and companion ProjectData folders into an ignored local directory, verifies
every copied file with SHA-256, and records a provenance manifest. Neither tool
parses or modifies licensed samples or XPJ contents.

The hardware workflow also includes reusable, dry-run-first utilities:

- `mpc-scratchpad-check` evaluates deployment, listening, core-selection, and
  final-favorite readiness independently from `inventory/scratchpad-candidates.toml`.
- `mpc-hardware-init` creates a complete editable hardware-listening session;
  `mpc-hardware-results` validates and atomically applies it to the ledger.
- `mpc-drum-map` renders a bank-by-bank pad map with sample, inferred role,
  color, choke group, and playback behavior.
- `mpc-drum-build` assembles a self-contained, color-coded one-shot Drum
  Program from a reusable pad manifest and a known-good XML template.
- `mpc-xpm inspect|compare` performs format-aware XPM inspection, including a
  semantic comparison between legacy XML and MPC 3 compressed saves.
- `mpc-sd-deploy` plans additive card updates. It never deletes, requires
  `--include-audio` for companion audio, and requires a checksum-verified
  backup before replacing any existing file.
- `mpc-package-deploy` installs a complete self-contained package through a
  verified sibling staging directory. It runs a sustained write probe, leaves
  interrupted work resumable and hidden from the MPC browser, atomically
  promotes only a complete package, and refuses changed destinations.
- `mpc-audio-levels` measures WAV peak, RMS, crest factor, DC offset, clipping,
  and silence, and flags relative level outliers.
- `mpc-routing-capture` copies and hashes the controlled baseline/changed XPJ
  pair, then runs the detached Mac XPJ inspector without merging its branch.
- `mpc-repository-guard` prevents WAV/XPM/XPJ, companion data folders, and
  unexpectedly large files from entering source control.
- `mpc-plugin-audit` inventories an MPC `Synths` folder by version marker,
  preset count, content assets, files, and bytes. It deliberately reports only
  filesystem evidence; activation and project persistence remain hardware
  tests.

See [the reusable hardware workflow](docs/hardware-workflow-tools.md) for
commands, safety behavior, and the boundary between computer checks and MPC
listening tests.

Reusable setup definitions live in `rigs/`. `mpc-rig check` validates track,
device, MIDI-route, and controller assignments; `mpc-rig plan` renders a
hardware setup sheet. `mpc-library` queries the program ledger, and
`mpc-session-report` consolidates rig validation, candidate readiness, and
optional deployment/routing evidence. See [rig profiles](docs/rig-profiles.md).

WAV filenames may begin with a MIDI note number; the patch name may follow the
number immediately or after `_`, a space, or `-`. When no numeric prefix is
present, a space- or underscore-delimited trailing pitch name is used with the
library convention (`C0` = MIDI 24):

```text
024 Classic Piano Emulator C0.wav
60_StarPiano_DX100_C3.wav
60BreathV_DX100_C3.wav
Sub Bass Dr Sample C1.wav
```

For chromatic percussion or another source whose useful roots fall outside the
controller's normal register, shift the mapping without resampling audio:

```bash
uv run mpc-keygroup "/path/to/pitched-wavs" \
  --template "/path/to/known-good-keygroup.xpm" \
  --velocity-preset "/path/to/source.adg" \
  --root-shift 24 \
  --name "Chromatic Percussion NR" \
  --output "work/Chromatic Percussion NR.xpm"
```

`--root-shift` moves every root and playable range by a fixed semitone offset,
preserving intervals, velocity layers, sample endpoints, and source audio. Batch
manifests accept the same integer as `root_shift`. A shift that would move any
root outside MIDI 0–127 is rejected.

Velocity variants use a four-digit suffix. The unsuffixed file is the first
layer, `_0001` is the second, and so on:

```text
60_DigiPianet_DX100_C3.wav
60_DigiPianet_DX100_C3_0001.wav
```

## Dry run

```bash
uv run mpc-keygroup "/path/to/Star Piano" \
  --template "/path/to/Testing keygroup.xpm" \
  --dry-run
```

## Build

```bash
uv run mpc-keygroup "/path/to/Star Piano" \
  --template "/path/to/Testing keygroup.xpm" \
  --output "/path/to/Programs/Keygroups/Samples From Mars/DX100 From Mars/Star Piano.xpm"
```

The program's WAV files are copied into the adjacent standard directory:

```text
Star Piano.xpm
Star Piano_[ProgramData]/
  024_StarPiano_DX100_C0.wav
  ...
```

## Velocity-layer build

Multilayer folders require the matching Ableton `.adg` preset. The converter
reads the preset's exact instrument-wide velocity zones instead of guessing,
then assigns the unsuffixed WAV to the first zone, `_0001` to the second, and
so on. This also tolerates an isolated incorrect sample reference in a preset
when its velocity schema and source layers remain complete:

```bash
uv run mpc-keygroup "/path/to/Digi Pianet" \
  --template "/path/to/Testing keygroup.xpm" \
  --velocity-preset "/path/to/Digi Pianet.adg" \
  --output "/path/to/Digi Pianet.xpm"
```

The softest Ableton zone starts at velocity 1; the generated MPC zone is
extended to velocity 0 so the complete MPC range remains covered. Every note
must have contiguous velocity coverage through 127. Missing preset zones,
duplicate layer suffixes, gaps, overlaps, and instruments requiring more than
eight layers are rejected.

If a note has only one WAV, that sample covers velocities 0-127 even when the
preset contains a partial zone. This handles incomplete edge-note layers
without borrowing or inventing a sample.

Existing output is refused unless `--force` is supplied. Filenames without a
leading MIDI number and unsupported or ambiguous structures are ignored or

## Manifest-driven batch workflow

Copy `config.example.toml` to the gitignored `config.local.toml` and set the
licensed library, MPC media, known-good template, and local artifact paths.
Create a JSON manifest from `manifests/example.json`. All manifest paths are
relative to their configured roots and path traversal is rejected.

Run each stage explicitly with uv:

```bash
uv run mpc-keygroup-batch --config config.local.toml inspect manifests/my-library.json
uv run mpc-keygroup-batch --config config.local.toml build manifests/my-library.json
uv run mpc-keygroup-batch --config config.local.toml validate manifests/my-library.json
uv run mpc-keygroup-batch --config config.local.toml install manifests/my-library.json
uv run mpc-keygroup-batch --config config.local.toml install manifests/my-library.json --execute
uv run mpc-keygroup-batch --config config.local.toml validate manifests/my-library.json --location installed
```

`inspect` rejects unreadable, ignored, ambiguous, or duplicated audio before a
build. `build` writes only to gitignored artifacts, and `validate` checks the
XPM structure, filenames, nonzero sizes, sample counts, SHA-256 equality with
the read-only library, and duplicate audio. `install` is a dry plan unless
`--execute` is present. Executed installs use atomic copies and a journal, and
can resume partial copies or a relocation interrupted between moving
ProgramData and copying the XPM.

The per-instrument install policy is explicit:

- `copy` keeps any unrelated centralized material and installs from artifacts.
- `relocate` moves a checksum-matched centralized folder into ProgramData.
- `replace_corrupt` installs verified artifacts and removes a centralized
  folder only when every WAV there is zero bytes.

The latter two require `vendor_programs_checked: true`; the workflow also
refuses relocation when it finds an XPM or XPN inside that centralized folder.
This field records a deliberate external dependency check—it cannot prove that
an arbitrary program elsewhere does not reference those WAVs.
A manifest can select explicit filename variants before discovery:

```json
"sample_selection": {
  "include": ["*Clean*.wav"],
  "exclude": ["*_L.wav", "*_R.wav"]
}
```

Patterns apply to WAV basenames using case-sensitive shell-style matching.
`inspect` reports the excluded count and still rejects ambiguous roots,
unmapped selected files, and duplicate selected audio. The manifest itself
records the selection policy; build, validation, checksums, and installation
all use the same selected set. Selection requires `install: "copy"`: excluded
centralized files must remain in place, so the workflow refuses relocation or
folder deletion for a partial selection.


Generated artifacts can be reviewed and removed without touching installed
programs or licensed sources:

```bash
uv run mpc-keygroup-batch --config config.local.toml clean manifests/my-library.json
uv run mpc-keygroup-batch --config config.local.toml clean manifests/my-library.json --execute
```

rejected rather than guessed.

If numeric prefixes collide, a space- or underscore-delimited trailing pitch
may resolve the collision when it uses the library convention (`C0` = MIDI
24) and targets an otherwise-unused note/layer. This repairs adjacent-number
typos such as a `D4` file labeled `073` and repeated lexical prefixes such as
`80s Piano ... C2`. Unique numeric sequences remain authoritative, while
ambiguous pitches, stereo pairs, and random ID suffixes are still rejected.

XPM and WAV files are written through flushed temporary files and atomically
replaced to avoid zero-byte files after removable-media or card-reader stalls.

## Removable-media storage policy

Treat the licensed Samples From Mars library as read-only source material.
Build into the gitignored local `artifacts/` directory, validate there, and
install to the MPC card only as an explicit final step.

An installed keygroup uses one canonical on-card copy of each WAV, adjacent to
its program in MPC's standard layout:

```text
Instrument.xpm
Instrument_[ProgramData]/
  sample.wav
```

Before relocating an existing centralized sample folder, checksum every WAV
against the licensed library and confirm that no vendor-supplied XPM or other
program depends on that folder. Move only the samples used by the new program,
leave unconverted material in place, then validate the installed XPM and repeat
the checksums. This avoids retaining a second copy under both `Samples/` and
`Programs/Keygroups/`.

Akai `.xpn` expansion packages are ZIP archives useful for distribution and
desktop import. MPC standalone export expands their content into ordinary
program and sample files, so XPN compression is not a substitute for the
canonical adjacent `_[ProgramData]` layout on an active standalone card.

The current test card has 34 validated Emulator From Mars keygroups with 1,974
checksum-verified WAVs, 13 Junos From Mars keygroups with 1,226 verified WAVs,
32 101 From Mars keygroups with 2,496 verified WAVs, and 31 2600 From Mars
keygroups with 2,981 verified WAVs. It also has 36 360 From Mars keygroups
with 1,927 verified WAVs, including three velocity-layered multi-filter
programs, plus 14 Kawaii Dreams From Mars keygroups with 892 verified WAVs.
It also has 34 Mirage From Mars keygroups with 2,463 verified WAVs and 34 S612
From Mars synth keygroups with 1,997 verified WAVs, plus 38 Wasp From Mars
keygroups with 2,840 verified WAVs and 14 MS10 From Mars keygroups with 1,368
verified WAVs. It also has 29 SID From Mars keygroups with 2,637 verified
WAVs and 28 SYS100M From Mars keygroups with 2,310 verified WAVs. Emulator
percussion, Body Shots, and Various One Shots remain centralized. The card
also has 31 SH5 From Mars keygroups with 3,451 verified WAVs. Junos Chords and
FX remain centralized because they are one-shot material rather than pitched
keygroups.
Nine 101 folders remain centralized: one indexed one-shot folder and eight
multi-version or stereo patches that require an explicit selection policy.
Four 2600 folders remain centralized: one noise/one-shot set, two stereo
patches, and one duplicated-note patch requiring explicit sample selection.
The 360 Strings Detuned left/right folders remain centralized until stereo
sample-pair support is implemented.
Kawaii Dreams was not previously stored on the card, so its ProgramData
folders are the only on-card copies. White Siren left/right remains excluded
until stereo sample-pair support is implemented.
Mirage was also not previously stored on the card, so its ProgramData folders
are the only on-card copies. Its indexed Various One Shots collection remains
excluded.
The S612 synth collection likewise exists only in ProgramData; the separately
installed Essential WAV S612 drum kit is different material. S612 drum folders
and Various Vocals remain outside the keygroup conversion batch.
Wasp's stereo BuzzWave and inconsistent four-layer EnvelopeAcid folders remain
centralized pending stereo and per-note velocity-schema support.
MS10's AdvancedLazer, MexicanHistory, and SharpEric stereo folders plus the
inconsistent four-layer SuperPulse folder remain centralized for the same
extensions.
SID's SkateOrDieBass stereo folder remains excluded. SID was not previously
stored on the card, so its ProgramData folders are the only on-card copies.
SYS100M's PokemanAreBack and TheClap alternate-version folders remain
centralized pending explicit sample-version selection.
Nine SH5 folders remain centralized because they contain alternate/stereo
versions, missing base layers, or non-pitched recordings. Syn Toms is installed
as a two-layer keygroup program.
The card also has 40 OB From Mars keygroups with 3,946 verified WAVs. Warm
Trumpet and Sassy Stereo remain centralized because they require alternate or
stereo sample selection.
It also has 55 VP330 From Mars keygroups with 2,282 verified WAVs. SVC350 One
Shots remains centralized because it is not a pitched keygroup, and
WalterBeckerCombo remains centralized pending stereo sample-pair support.
The card also has eight Synare From Mars chromatic keygroups with 330 verified
WAVs. Synare's drum hits and non-pitched material remain outside this keygroup
batch.
It also has 14 tuned 808 From Mars Legacy keygroups with 185 verified WAVs:
eight bass-drum variants, three chromatic conga variants, and three chromatic
tom variants. The remaining 808 Legacy drum material stays centralized and
unchanged.
The card also has seven SDS800 From Mars bass keygroups with 125 verified,
non-duplicate WAVs: Digital, four Tape variants, and the low/high chromatic
sets. Existing Essential WAV SDS800 kits and samples remain vendor-managed and
unchanged.
It also has six SDSV From Mars no-bend tuned keygroups with 195 verified,
non-duplicate WAVs: three kick lengths and three tom variants. Bend, noise,
one-shot, and kit material remains outside this keygroup batch; existing
Essential WAV SDSV content remains unchanged.
The card also has the Dr Sample From Mars 80s Piano keygroup with 37 verified
WAVs. Its former centralized card folder contained 37 zero-byte corrupted WAVs;
the installed ProgramData was rebuilt from the checksum-verified licensed
source, and the corrupted folder was removed after validation.
It now also has 20 additional Dr Sample From Mars keygroups with 401 verified,
non-duplicate WAVs: nine basses, four keys, five pads, and two guitars. Four
programs reuse checksum-verified centralized files (including one repaired
zero-byte Overdrive Bass note); 16 were rebuilt from source before their
all-zero centralized folders were removed. Glide Bass remains excluded because
one source filename (`F#.wav`) omits its octave.
The card also has 38 Voyetra From Mars keygroups with 3,183 verified,
non-duplicate WAVs. LFO Synth, Massive Poly, and Rez Bass remain centralized
pending velocity-preset mapping; Noise and the generic Samples folder remain
centralized because they are not pitched keygroup instruments. The installed
ProgramData folders are the only on-card copies of the converted material.
The card also has six Arp Omni From Mars string keygroups with 125 verified,
non-duplicate WAVs. Their former centralized folders contained only zero-byte
corrupt WAVs and were removed after the rebuilt ProgramData passed source
checksum validation. Double Octave remains centralized because that folder is
a mixture of valid and zero-byte WAVs and requires a separate repair policy.
The card also has 23 Mini From Mars keygroups with 2,171 verified,
non-duplicate WAVs across bass, lead, FX, and keys/poly programs. Their
checksum-matched centralized folders were relocated into standard ProgramData,
so these installations do not retain a second on-card copy.
High Speed FX and eight other Mini folders remain centralized pending explicit
alternate-version selection or multilayer review.
The card also has 27 Micro From Mars keygroups with 1,615 verified,
non-duplicate WAVs. Their checksum-matched centralized folders were relocated
into standard ProgramData. Micro FX, Noise, and Panic Attack remain centralized
because their trailing numbers may be event indices rather than chromatic root
notes.
The card also has four Acid From Mars chromatic synth keygroups with 148
verified, non-duplicate WAVs. Their former centralized folders contained only
zero-byte corrupt WAVs and were removed after source checksum validation.
Single-note, velocity/alternate-layer, loop, and drum material remains
centralized.
