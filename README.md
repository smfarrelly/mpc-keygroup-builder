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
