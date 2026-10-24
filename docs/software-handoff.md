# Software handoff — 2026-10-24

This is a dated development checkpoint, not a claim about what is merged or
installed on the MPC. All hardware acceptance remains deferred. No SD content
was changed in this batch.

## Start with the user workflow

Use `mpc-tools start` for one focused task. Use `mpc-tools check` to validate
explicit local inputs. Capture an idea, restore an independent variation, then
capture and compare that variation. The source archive stays unchanged.

The offline archive browser is generated with
`mpc-idea-archive list work/ideas --html work/reports/ideas-01.html`. It is a
private, point-in-time report, not a live filesystem interface. Its generation
and escaping are tested; visual browser acceptance is still pending because
the available browser tool rejected local file URLs.

## Review and integration order

The review audit found passing CI, no unresolved review threads, and no merge
conflicts on PRs 62–68. No PR was merged as part of this batch.

- Independent main-based work: [#62](https://github.com/smfarrelly/mpc-keygroup-builder/pull/62)
  (colocated colors), [#63](https://github.com/smfarrelly/mpc-keygroup-builder/pull/63)
  (safe staging), [#64](https://github.com/smfarrelly/mpc-keygroup-builder/pull/64)
  (Ableton guards), [#66](https://github.com/smfarrelly/mpc-keygroup-builder/pull/66)
  (resume checkpoint), and [#67](https://github.com/smfarrelly/mpc-keygroup-builder/pull/67)
  (offline resume).
- Archive dependency chain: [#65](https://github.com/smfarrelly/mpc-keygroup-builder/pull/65)
  → [#68](https://github.com/smfarrelly/mpc-keygroup-builder/pull/68).
- Start/readiness chain after #68:
  [#69](https://github.com/smfarrelly/mpc-keygroup-builder/pull/69)
  → [#70](https://github.com/smfarrelly/mpc-keygroup-builder/pull/70)
  → [#72](https://github.com/smfarrelly/mpc-keygroup-builder/pull/72)
  (installed workflow/recovery checks).
- [#71](https://github.com/smfarrelly/mpc-keygroup-builder/pull/71)
  (archive browser) depends directly on #68, independently of #69/#70.

Stacked PR bases name their dependency branches. When accepting them, preserve
that ordering and review/retarget each remaining PR after its base lands; do
not assume a green check on an old base proves a rebased result. Use a temporary
integration checkout for combined testing rather than merging unfinished work
into main just to test it.

## Acceptance boundaries and remaining work

- Installed-wheel smoke checks exercise all command help/version entry points
  and synthetic capture/restore recovery outside the checkout.
- Readiness checks detect mismatches with recorded receipts; recipe freshness
  tracking is not implemented. An old but internally consistent receipt passes.
- Sample lookup is bounded and conservative, not a firmware emulator. It does
  not decode audio, search the entire library, repair references, or inspect
  plugin licenses.
- Browser runtime/visual acceptance and all MPC listening tests remain deferred.
- Recheck GitHub review/CI state before merging; this document is not live status.
