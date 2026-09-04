# MPC Instrument Factory

Build, inspect, organize, and hardware-test reusable instruments and creative
workflows for MPC 3 standalone systems. The project started as a Keygroup
builder and now also covers Drum Programs, semantic pad layouts, creative MIDI,
MIDI-controller plans, safe SD deployment, and evidence-led hardware testing.

The tools never include commercial sample audio. You point them at samples you
own or may legally use, and generated programs stay on your own storage.

## Start here

Choose the path that matches what you want to do:

- **Try it without installing anything:** open
  [`site/index.html`](site/index.html) in a browser, then launch the synthetic
  Program Designer demo. It contains no licensed audio and never uploads data.
- **Install the commands:** follow the
  [nondeveloper getting-started guide](docs/getting-started.md).
- **Build one pitched instrument:** follow
  [Build a Keygroup](docs/keygroup-building.md).
- **Explore every command:** run `mpc-tools commands` or read the
  [CLI reference](docs/cli-reference.md).
- **Understand the whole project:** use the [documentation map](docs/index.md)
  and [product roadmap](docs/PRODUCT_ROADMAP.md).

After installation, this is the quickest confidence check:

```bash
mpc-tools doctor
mpc-tools demo --output my-mpc-demo
```

When returning to this repository after time away, open
[`RESUME_HERE.md`](RESUME_HERE.md) or run `mpc-tools resume` for the current
checkpoint, mounted-card status, exact project paths, and one next action.

The demo synthesizes its own redistributable WAV files, creates Drum Programs
and creative MIDI, and gives you a hardware checklist. No sample library or MPC
is required for the software portion.

## What it can do

- Build pitched Keygroups from named WAV files, including velocity layers.
- Build, color, audit, compose, and lay out Drum Programs.
- Inspect XPM programs without modifying them.
- Inspect, extract, and compare MPC 3 XPJ projects without modifying them.
- Generate deterministic Drum, Bass, Chords, Melody, and arrangement MIDI.
- Build a redistributable three-composition showcase with deterministic
  evidence, editable recipes, and synthetic CC0 Drum audio.
- Compile declarative MPC, Launch Control XL 3, and Volca routing plans.
- Inspect Components SysEx captures and cross-check them against MPC MIDI Learn.
- Search downloaded plugin controls and rank useful controller targets.
- Compile role-based plugin performance pages into Components and MIDI Learn
  worksheets with installed-content validation.
- Generate an offline visual plugin-mapping companion with local progress,
  hardware notes, and portable JSON/CSV results.
- Validate companion exports into a durable results ledger, generate ranked
  profile seeds, print mode cards, and audit all controller slots and channels.
- Catalog programs and their hardware-listening status.
- Plan additive, checksum-verified SD deployments.
- Create a self-contained browser Program Designer for a prepared program set.
- Capture hardware observations without treating software validation as a
  listening pass.
- Discover packaged schemas, validate declarative files, and initialize a
  complete editable workstation recipe family.

The project deliberately does **not** synthesize undocumented MPC project
schemas, overwrite source programs, commit licensed WAV/XPM/XPJ content, or
claim a hardware pass without a person listening on the device.

## Installation in brief

Install [`uv`](https://docs.astral.sh/uv/), then install the released command
set directly from GitHub:

```bash
uv tool install --python 3.12 git+https://github.com/smfarrelly/mpc-keygroup-builder.git
mpc-tools doctor
```

If the terminal cannot find `mpc-tools`, run `uv tool update-shell`, close the
terminal, and open a new one. Windows, macOS, upgrades, uninstalling, and a
developer checkout are covered in [Getting started](docs/getting-started.md).

Every command supports both `-h` and `--help`; every installed command supports
`--version`. Expected input, path, and permission failures include a suggested
next step. Set `MPC_DEBUG=1` only when you need a Python traceback.

## Samples and licensing

[Samples From Mars](https://samplesfrommars.com/collections) is an excellent
source for local MPC instrument building: its packs include organized WAVs and
many include MPC-ready formats. Its license allows music production but does
not allow repackaging or redistributing the sample products, so this repository
contains manifests and tools—not their audio.

You can also use your own recordings, synthesized audio, and properly licensed
free/open samples. The [sample-source and licensing guide](docs/sample-sources.md)
compares CC0/attribution sources with free-to-use-but-not-redistributable
libraries and explains what provenance to record.

## Browser versus command line

The offline HTML demo supports inspecting two safe synthetic programs,
comparing semantic layouts, editing pad assignments, undoing changes, and
downloading a draft JSON file. It requires no server and makes no network
requests.

Arbitrary XPM import, WAV playback, finished XPM export, SD-card writes, and
batch conversion remain command-line workflows because those operations need
local file access and stronger validation. See [Browser demo](docs/browser-demo.md)
for the exact boundary.

## Documentation

- [Documentation map](docs/index.md)
- [Getting started](docs/getting-started.md)
- [CLI reference](docs/cli-reference.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Build a Keygroup](docs/keygroup-building.md)
- [Program model and semantic layouts](docs/program-model-and-layouts.md)
- [Program Designer](docs/program-designer.md)
- [Portable workflow demo](docs/portable-demo.md)
- [Three-composition showcase](docs/composition-showcase.md)
- [Creative MIDI](docs/creative-midi.md)
- [Declarative MIDI control](docs/declarative-midi-control.md)
- [Plugin parameter catalog](docs/plugin-parameters.md)
- [Declarative plugin performance pages](docs/plugin-mapping.md)
- [XPJ project inspector](docs/xpj-inspector.md)
- [Hardware workflow tools](docs/hardware-workflow-tools.md)
- [MPC Key 37 field review](docs/MPC_KEY37_FIELD_REVIEW.md)
- [Sample sources and licensing](docs/sample-sources.md)
- [Vendor document cache](docs/vendor-documents.md)
- [Declarative schemas and validators](docs/schemas.md)
- [Product roadmap](docs/PRODUCT_ROADMAP.md)

## AI-assisted development

The repository publishes a project skill at
[`skills/mpc-instrument-factory/SKILL.md`](skills/mpc-instrument-factory/SKILL.md).
Compatible coding agents can use it to select the right workflow while
preserving the project's licensing, evidence, and non-destructive-editing
rules. It is guidance for working in this repository, not a requirement for
using the tools.

## Development

```bash
git clone https://github.com/smfarrelly/mpc-keygroup-builder.git
cd mpc-keygroup-builder
uv sync --locked
uv run python -m unittest discover -s tests -v
uv run mpc-repository-guard
uv build
```

Generated instruments, captured MPC projects, licensed samples, and external
device documents do not belong in Git. See the vendor-document and hardware
workflow guides for safe local-storage patterns.

## License

The source code is available under the [MIT License](LICENSE). Sample libraries,
audio files, vendor manuals, and generated MPC programs remain subject to their
respective owners' licenses.
