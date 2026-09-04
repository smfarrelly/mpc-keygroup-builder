# Getting started

You do not need to be a Python developer to use the installed commands. The
only prerequisite is `uv`, a small tool that installs the correct Python
version and keeps this application isolated from the rest of your computer.

## Try the interface without installing

Download or clone this repository, open `site/index.html` in Chrome, Firefox,
Edge, or Safari, and choose **Open Program Designer demo**. The page is fully
self-contained: it does not start a server, upload a file, or require a sample
library.

The demo uses synthetic metadata. See [Browser demo](browser-demo.md) for what
it can and cannot do.

## Install the commands on macOS or Linux

Install `uv` using its official installer:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Open a new terminal, then install this project and its isolated Python 3.12
runtime:

```bash
uv tool install --python 3.12 git+https://github.com/smfarrelly/mpc-keygroup-builder.git
mpc-tools doctor
```

## Install the commands on Windows

Open PowerShell and install `uv`:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Open a new PowerShell window, then run:

```powershell
uv tool install --python 3.12 git+https://github.com/smfarrelly/mpc-keygroup-builder.git
mpc-tools doctor
```

If `mpc-tools` is not found, run `uv tool update-shell`, close the terminal, and
open a new one. No administrator or `sudo` access is normally required.

## First successful run

List the workflow-oriented commands:

```bash
mpc-tools commands
mpc-tools help mpc-keygroup
mpc-schema list
```

Then build the portable demo in a new directory:

```bash
mpc-tools demo --output my-mpc-demo
```

Open `my-mpc-demo/HARDWARE_CHECKLIST.md`. The generated WAVs are simple
mathematical fixtures intended to verify the workflow, not production sounds.
You can complete all software checks without an MPC and defer the hardware
rows.

To explore three complete musical directions instead of one compact fixture:

```bash
mpc-showcase --output my-mpc-showcase
```

## Return after time away

In a project checkout, run:

```bash
mpc-tools resume
```

If the SD card is mounted somewhere unusual, add `--sd-root /absolute/path`.
The command reads `inventory/session-checkpoint.toml` and prints the current
objective, exact baseline/working/target project paths, mounted-card status,
routing summary, and one next action. Update the small checkpoint when the
working objective changes; detailed roadmaps remain reference material.

## Build with your own samples

For a pitched instrument, collect WAV files whose names contain note labels
such as `C3`, `F#3`, or `Bb4`, obtain one known-good Keygroup XPM created by
your MPC as a schema template, and follow [Build a Keygroup](keygroup-building.md).

For Drum Programs and semantic layouts, start with
[Program model and layouts](program-model-and-layouts.md). Keep commercial
samples and generated instruments outside this Git checkout.

## Upgrade or uninstall

```bash
uv tool upgrade mpc-keygroup-builder
uv tool uninstall mpc-keygroup-builder
```

Upgrading the command does not touch your source audio or output folders.

## Developer installation

Use a checkout when you want to change the code, run the complete test suite,
or use repository recipes directly:

```bash
git clone https://github.com/smfarrelly/mpc-keygroup-builder.git
cd mpc-keygroup-builder
uv sync --locked
uv run mpc-tools doctor
uv run python -m unittest discover -s tests -v
```

Run tools as `uv run COMMAND ...` inside the checkout. The lock file makes the
development environment reproducible.

## Before copying to an SD card

Keep one canonical copy on the computer or external drive. Use the deployment
tools in dry-run mode first, verify the mounted device and free space, then
apply an additive update. Eject cleanly after the copy. The
[hardware workflow guide](hardware-workflow-tools.md) covers checksums,
transactional copies, and evidence ledgers.
