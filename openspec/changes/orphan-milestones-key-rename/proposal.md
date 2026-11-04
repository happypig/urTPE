## Why

Every orphan node's payload carries a `milestones_national` dict that actually
holds **Taipei-platform** data (the `Get_project168_second.ashx` milestones;
board D1, verified by code path, date shapes and a live probe). The date
values are right; the key name is false. The genuine national data sits one
level up at project level. A future consumer that trusts the key name joins
Taipei data as if it were national — the 國/北 distinction is exactly what the
key claims to carry. The same re-emit carries D4a's pipeline fix (the first
holder of an equal construction date wins the provenance credit).

## What Changes

- **BREAKING** (payload schema): `orphan_nodes[].milestones_national` is
  renamed `milestones_taipei_case` — the per-case Taipei ashx milestones
  (source-space truth).
- The viewer read site (`viewer/app.js` orphan virtual-node build) reads the
  new key.
- A load-side alias in `--from-js` keeps already-emitted `projects.data.js`
  files rendering (the `emit-stage-index` precedent): an old payload's
  `milestones_national` on an orphan loads as `milestones_taipei_case`.
- D4a pipeline rule (board-decided 2026-11-05): when two cases carry the SAME
  construction date, the FIRST case read wins the `milestones_source` credit —
  `merge_stage_milestones` stops overwriting an existing label, and
  `pick_implementation_payload` stops overwriting `source[label]` (15 dates in
  11 projects credit a later case today, e.g. 榮星53's 建照/使照 → 09001123
  instead of 09001120).
- One payload re-emit covers both.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `orphan-case-anchoring`: the ghost-node milestone requirement names the new
  key (`milestones_taipei_case`) and states the load alias.
- `taipei-implementation-data`: the provenance rule becomes "the first case
  read wins an equal value" for both the stage-milestone merge and the plan
  case date pick.

## Impact

- Code: `urtpe/links.py` (orphan dict key; the two provenance merges),
  `urtpe/cli.py` (`--from-js` alias), `viewer/app.js` (orphan read site).
- Data: one re-emit rewrites the tracked `data/` files and
  `viewer/projects.data.js` (the ~23 MB diff); the coverage guard and
  `project_aliases.json` must accept it (no project_id changes expected from
  D1; D4a changes provenance only, not dates).
- Tests: `tests/test_links.py` (orphan key), `tests/test_milestones_provenance.py`
  (first-holder), a `--from-js` alias test, viewer label test for the read site.
