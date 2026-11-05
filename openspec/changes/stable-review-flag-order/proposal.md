## Why

A node's `review_flags` are emitted in the order the pipeline raised them, and
the order depends on the order the pipeline happened to visit its cases. The
D5 ledger's 吉林676 merge changed one family's member order, and that changed
the order three `孤兒案件未達相似度門檻` flags appear in on
`大同區-大龍段一小段-265-7地號等2筆` (node 1242). The flag texts do not change
— only their positions do — but the viewer joins them with `、`, so the change
is visible on screen.

The same order dependency exists wherever the pipeline iterates a set of case
ids: the orphan sweep reads `disc.city_case_ids` (a list), but the fragment
flag and the conflict flags are raised over sets derived from it. A merge that
reorders a family therefore reorders flags on any node it touches, with no
signal that anything changed.

## What Changes

- The emitter sorts a node's `review_flags` by a **stable key** before writing
  them: the case id the flag names (ascending, as text), then the flag text.
- A flag that names no case id sorts before the ones that do, by its text.
- The flag SET on a node is unchanged. Only the order changes.
- The sort happens in the emitter (`urtpe/graph.py`), not at each flag-raising
  site, so a flag raised by any path lands in the same place.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `data-cleansing`: the emitted review flags carry a stable order.

## Impact

- `urtpe/graph.py` — the emitter sorts the flags it writes.
- `data/projects.json`, `data/merged.tsv`, `viewer/projects.data.js` — 20
  nodes' flag order changes (measured offline on the 2026-10-15 payload).
  No flag text changes and no flag is added or lost.
- The rider is step 2's re-emit (D9g). The change adds no write of its own.
