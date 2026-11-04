## Why

Board D2 (measured 2026-11-04): `_ghost_node_date` dates a plan-track dead
case with the family's 概要核准 (the city echoes the 概要's approval into every
descendant case's 階段辦理過程 — 吉林717's triple all read 2007/01/30), so 18
of 25 same-date node pairs are one approval echoed, not events. The row sort
then reads those echoes as chronology: 51 projects / 95 pairs read
non-chronologically. The user decided both halves on 2026-11-05 (D2a
track-aware dates; D2b date-first sort with the own-event key).

## What Changes

- **D2a**: `_ghost_node_date` becomes track-aware — a plan-track case skips
  概要核准日期 (the node renders undated, `(未核定)`); a 概要-track case keeps
  it. Expected: the 25 same-date pairs drop to ~7 genuine same-day serials.
- **D2b**: rows sort by the own-event date first, falling back through each
  track's own application dates, case_id breaking ties and ordering the
  undated tail. The D12 case_id-first decision is superseded (the design
  records it as history); `docs/viewer_sort_rules.md` is rewritten.
- One payload re-emit (D2a) + viewer sort change (D2b), one openspec change.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `virtual-milestone-nodes`: the ghost `node_date` requirement (track-aware
  fallback) and the stage-key-cluster ordering requirement (date-first key).
- `history-graph`: the row-order requirement if it repeats the case_id-first
  rule.

## Impact

- Code: `urtpe/links.py` (`_ghost_node_date`), `viewer/app.js`
  (`compareClusterMembers`, the family-wide interleave, `effectiveCaseKey`
  consumers), `docs/viewer_sort_rules.md`.
- Data: one re-emit; the 51-project non-chronology list dissolves; 9
  row-between 概要 orphans move to their date position.
- Measurement after the re-emit is recorded in the change design (the board's
  D2b numbers were measured on the pre-D2a payload).
