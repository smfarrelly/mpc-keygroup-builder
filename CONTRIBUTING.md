# Contributing

Thank you for helping improve MPC Instrument Factory. This project welcomes
small, focused changes that preserve source material, make evidence boundaries
clear, and leave workflows reproducible for the next person.

## Set up a development checkout

Install [uv](https://docs.astral.sh/uv/), then clone and verify the repository:

```bash
git clone https://github.com/smfarrelly/mpc-keygroup-builder.git
cd mpc-keygroup-builder
uv sync --locked
uv run mpc-tools doctor
uv run python -m unittest discover -s tests -v
uv run mpc-repository-guard
uv build
```

Use `uv run COMMAND ...` for commands in a development checkout. The project
requires Python 3.12 or newer; uv selects the version declared by the project.

## Keep changes reviewable

- Start from an up-to-date `main` branch and use one focused branch per change.
- Add or update tests for behavior changes and keep user-facing examples in
  sync with `--help` output.
- Prefer the public command entry points over one-off scripts when a workflow
  should be repeatable.
- Run `git diff --check` in addition to the verification commands above.

When adding a command, register it in both `[project.scripts]` in
`pyproject.toml` and `COMMANDS` in `src/mpc_keygroup_builder/entrypoints.py`.
Give it focused documentation and cover its short help, long help, version,
successful path, and expected failures. The entry-point tests check that the
published command catalog remains complete.

## Protect samples and hardware evidence

Do not commit commercial or captured audio, sample-bearing XPM files, XPJ
captures, SysEx dumps, generated program-data folders, or vendor manuals. The
repository guard rejects common artifact types, but contributors remain
responsible for licenses and provenance. Use synthetic fixtures for tests.

Keep these evidence levels distinct in code, documentation, and review notes:

1. structural or software validation;
2. successful transfer or load;
3. human listening on MPC hardware.

Only the last level supports a hardware listening pass. Preserve source
programs and templates, use explicit output paths, and default to dry-run or
additive behavior for mounted media.

## Before opening a pull request

```bash
uv run python -m unittest discover -s tests -v
uv run mpc-repository-guard
uv build
git diff --check
```

In the pull-request description, summarize the user-visible change, list the
checks run, and call out any hardware validation that remains deferred.
