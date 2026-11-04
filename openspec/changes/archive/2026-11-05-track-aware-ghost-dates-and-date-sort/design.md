## Context

Board D2 (`docs/inspection-batchD.md`). D2a fixes the ghost-date echo;
D2b replaces the D12 case_id-first row sort with the own-event date key. The
user decided both on 2026-11-05. One re-emit (D2a) then the viewer change
(D2b); the board's D2b numbers (18 ties, 21 undated, 106 reorders) were
measured on the pre-D2a payload and are re-measured after.

## Goals / Non-Goals

**Goals:**
- A ghost node's date is the case's own event, never a sibling's approval.
- Rows read chronologically; the 51-project non-chronology dissolves.

**Non-Goals:**
- No change to the cluster grouping (stage-key clusters stay).
- No 相關連結 order guarantee in the graph (that D12 Amendment 3 property is
  superseded; the pipeline-side ascending emit stays).

## Decisions

### D1 — `_ghost_node_date` takes the track

The call site derives `track` already (line 3321); pass it in. A 事業概要
track keeps the 核定→權變核定→概要核准 fallback (概要's own approval IS
概要核准). A plan track (事業計畫 / 權利變換 / combined) stops at
核定→權變核定 — 概要核准 on a plan case is the family echo, not its event.
The node renders undated → `(未核定)` (the honest label; the 寶清375 shape).

### D2 — the own-event sort key (D2b)

The viewer's row key becomes: 概要-track members read 概要核准 → 申請概要 →
申請計畫; plan-track members read 核定 → 權變核定 → 申請計畫 → 申請權變 →
申請概要 (never the echoed 概要核准). Ties and the undated tail break by
case_id (D12's attempt order survives as the tie-break — the user kept that
property). The key lives where `effectiveCaseKey` lives (D12 block); the
family-wide interleave and the cluster tie-breaks both switch to it.

The pipeline emits no new field: the per-case milestones already sit in
`links.case_milestones` / the orphan's `milestones_taipei_case`, and the
viewer builds the key from them at render time (the virtual node already
carries the dict after the D1 rename).

### D3 — supersede D12, do not delete it

`docs/viewer_sort_rules.md`'s "do not sort by date" section becomes history;
the delta spec carries the new rule and cites the board decision. The 603
interleave scenario changes: with the echo gone, 603's undated virtuals carry
their own application dates and order by them.

## Risks / Trade-offs

- [Row movement surprises a reader who learned the case_id order] → the
  board's decision; the re-measure records what moved.
- [An application-dated dead attempt renders before a later approval] → the
  row names its kind: `(未核定)` stays beside the date (board cost 1).
- [The viewer key needs per-case milestone access on real nodes] → the
  real node's anchored case_id indexes `links.case_milestones`; a case absent
  there falls back to the node date then case_id (no empty rows).

## Migration Plan

Code + tests → re-emit (D2a) → re-measure (record in this design) → viewer
sort change → corpus checks (the 51-project list dissolves; 逸仙段三小段-34's
orphan lands by date) → commit.

## Open Questions

None.
