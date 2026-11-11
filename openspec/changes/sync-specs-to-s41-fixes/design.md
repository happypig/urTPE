## Context

The fixes themselves shipped on 2026-11-10 in commit `9d1eeaf` (interleave key and
callout width model) plus the stylesheet cache-bust in `viewer/index.html`; the ops
log records both in §41. This change documents the spec side only: the code is the
reference implementation, and the deltas in `specs/` must describe exactly what it
does. Actors: the viewer render path (`viewer/app.js`, plain JS, no framework) and
the emission path (`urtpe/viewer.py` rewriting `?v=` into `index.html`). System
boundary unchanged: static `file://` bundle, published to GitHub Pages from `main`,
verified by `scripts/check_deploy.py`.

## Goals / Non-Goals

**Goals:**

- Pin the interleave key rule (member sort key, never the cluster `effDate`
  sentinel) in `viewer-graph-layout`, so a regression to the sentinel shape cannot
  pass the spec.
- Pin the every-cacheable-reference rule (scripts and stylesheets) in
  `pdf-tsv-extraction`, so a future asset reference without `?v=` reads as a fault.
- Carry every existing scenario of both MODIFIED requirements verbatim — the
  archive guard compares scenario names only, but the repo convention is that a
  MODIFIED delta carries the live body too.

**Non-Goals:**

- No code changes. The pinned tests already exist in `tests/test_viewer_labels.py`
  (commit `9d1eeaf`); this change asserts them, it does not add behavior.
- No new capability, no removal: both requirements continue under their current
  names.
- The callout width model (cjkUnits/implBoxW) is *not* spec'd here: the existing
  `history-graph` callout requirement already demands "no part clipped or
  covered", and the fix restored compliance rather than changing the contract.

## Decisions

- **D1 — Spec the interleave key as "the key that ordered the approval rows",
  not as a function name.** The spec text names the observable rule (own date,
  else own event key) and forbids the cluster date, but does not name
  `ownEventDate` in the requirement body; the scenario cites the measured shape
  (桃源424-8) instead. The viewer's internal helper names may churn; the rule
  cannot. Rationale: specs describe externally observable behavior, and the
  smoke harness observes row order, not call graphs.
- **D2 — Describe the unversioned-stylesheet fault as "reported", not as a
  crash.** `_asset_version`'s rewrite matching nothing (the old failure) and a
  future explicit check both satisfy "reported"; the spec pins the outcome, the
  implementation keeps its current shape. Alternative considered: require the
  rewrite to fail the run on an unversioned reference — rejected as a behavior
  change beyond the shipped fix.
- **D3 — One change for both deltas.** They share one incident (§41), one
  verification sweep (browser check of all 681 projects: 0 inverted pairs, 0
  clipped boxes), and one user request. Two changes would double the archive
  ceremony for no separate verification evidence.

## Risks / Trade-offs

- [The MODIFIED requirement bodies drift from the live specs before archive]
  → The archive copies the delta over the live spec wholesale for MODIFIED
  requirements; tasks include a pre-archive diff of the delta bodies against
  `openspec/specs/` on a temp copy, per the repo's archive guard convention.
- [The interleave scenario names one project shape, and a reader reads it as the
  only protected shape] → The requirement body states the general rule; the
  scenario is an instance of it, and the corpus-wide sweep (681 projects) is the
  real coverage.
- [A future asset type (e.g. a favicon or font reference) reopens the gap] → The
  spec says "every cacheable asset reference", not "scripts and stylesheets";
  the scenario instances the measured failure.
