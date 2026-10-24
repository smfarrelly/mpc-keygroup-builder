# Start with one musical task

You do not need to reconstruct the project history or finish the hardware test
plan before making music. Run `mpc-tools start` from any directory for a small
menu of workflows. It only prints guidance: no drive discovery, writes, or
commands are executed. `--json` exposes the same guidance to other interfaces.

For one browser page with favorites, saved ideas, and readiness evidence, use
[the local home-page generator](local-home.md). You explicitly choose its inputs;
it never searches connected drives automatically.

## Find a sound

`mpc-tools start find` starts with favorites in the local listening ledger.
Run its suggested command from the checkout. A ledger path identifies the
library-relative location; it does not prove that today's mounted drive has
that file. See [Catalog](catalog.md) for role and name searches.

## Save an idea, then experiment

`mpc-tools start capture` previews a saved XPJ and its exact ProjectData folder.
Replace the example paths with your local project and choose a new archive
folder. Remove the preview flags only after checking the selected files.

`mpc-tools start experiment` restores that archive into a separate working copy.
The archive stays unchanged. After developing the variation, capture the working
copy into another new archive. See [Idea snapshots](idea-snapshots.md).

## Prepare an update later

First use [local readiness checks](local-readiness.md) to verify selected
archives, bundles, and program sample references without touching a card.

`mpc-tools start prepare` prints a deployment-plan command, not an apply command.
Do not guess a device name from an old chat. Identify the actual mounted card
and verify the intended package first. Hardware listening remains deferred
until you want to do it; software checks never silently change that status.

## Try without any hardware

`mpc-tools start demo` points to the synthetic workflow fixture. For no install
at all, open [the browser home page](../site/index.html).

For installation use [Getting started](getting-started.md). For recovery use
[Troubleshooting](troubleshooting.md). The complete command list is reference
material, not a prerequisite: `mpc-tools commands`.
