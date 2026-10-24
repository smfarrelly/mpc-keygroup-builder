# One local starting page

Generate a private HTML page that combines workflow guidance with the evidence
you choose. No inputs are automatically discovered and nothing is uploaded.

```bash
mpc-tools home --output work/reports/home-01.html \
  --ledger inventory/program-status.csv \
  --program-root "/path/to/local/library" \
  --archive-library work/ideas \
  --bundle work/my-wave --recipe-root recipes
```

All inputs are optional; omit unavailable ones. Only `--output` is required.

## Save your input selection

Copy `home.example.toml` to a private `home.local.toml`, edit its paths, then use:

```bash
mpc-tools home --config home.local.toml --output work/reports/home-02.html
```

Paths are relative to the config file, not your current directory. The file is
strictly declarative: unknown fields, invalid types, and executable command
fields are rejected. Do not combine `--config` with individual input flags.
Keep the config private because it identifies personal storage locations.
The output is deliberately not saved in the config: choose a new report filename
each time to avoid replacing a useful earlier view.

## Input and output boundaries

`--bundle` may be repeated. `--program-root` requires a ledger and `--recipe-root`
requires a bundle. The output must be a new filename outside the selected input
libraries, bundles, and recipe trees. It never changes those inputs.

Open the generated HTML in your browser. The page has four linked sections:

- One-task workflow instructions, with commands to run yourself.
- Confirmed favorites from the listening ledger. With a program root, it shows
  absolute local XPM paths and whether those files exist. Historical listening
  status is separate from current availability; sample loading is not inferred.
- Archived ideas with notes, integrity results, and exact recheck commands.
- Bundle integrity and optional recipe freshness, including detailed evidence.

The page works without JavaScript and uses native keyboard-accessible links and
disclosures. It is a dated report, not a live filesystem application. Regenerate
into a new filename when your library changes. No audio or XPJ payload is embedded,
but personal notes and paths are: keep it private.

Exit 0 means generation completed without detected issues in selected evidence;
it does not mean absent inputs passed. Exit 1 writes the report but signals
attention (such as damaged archives, missing favorite paths, stale recipes, or
failed bundle checks). Invalid arguments or unreadable selected ledgers/libraries
stop generation with the normal CLI error status. No input selected produces
only guidance and explicit not-checked messages.

Browser visual/runtime acceptance remains separate from software generation and
markup safety tests. The toolkit does not launch projects, execute displayed
commands, or mark MPC hardware tests passed from this page.
Use the [browser acceptance checklist](browser-acceptance.md) for the remaining
visual/runtime checks; static tests alone do not mark these complete.
