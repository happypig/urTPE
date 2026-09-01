# Design: normalize-plan-abbreviation

## Context

Actors: planners reading the viewer (track labels), and the pipeline's
cleanse/merge stages that derive `track` from the 案名. Domain event: the
gazette PDF c.2009-2011 printed some 案名 as `土地都市更新計畫案` — the
platform's own `CASE_NAME` for the same units writes
`土地都市更新事業計畫案` (18/18 cross-referenced, 0 abbreviations on the
platform side; census `data/_gengxin_plan_census.json`, cross-reference
`data/_gengxin_plan_crossref.json`). System boundary: this change touches only
the cleanse stage (`urtpe/cleanse.py`); merge, graph emission and the viewer
consume the corrected name downstream without modification.

## Goals

- Affected records derive track `事業計畫` (10 nodes / 6 families today) with
  an auditable `auto_fixes` entry — no silent rewrite.
- The synthetic `都市更新計畫` track stops appearing in new emissions.

## Non-Goals

- No viewer change (`trackPosition` already maps both tracks to column 1;
  the mapping stays for old caches).
- No historical re-classification of the `都市更新計畫` track beyond the
  affected records (if a genuine non-事業 「都市更新計畫」 plan class ever
  surfaces, it would be a new finding — none seen in the corpus or on the
  platform).

## Decisions

- **D1 — normalize in `cleanse`, at the name-normalization site** (same place
  as 事業換計畫→事業計畫 and the 計劃/ㄧ fixes), not in `_tracks()`. The 案名
  itself is corrected so every downstream consumer (name core, viewer table,
  land-core adjacency) sees the full legal name. Condition: apply only when
  the 案名 lacks 事業計畫 — full names are never touched.
- **D2 — auditable, not silent**: each application appends
  `案名補事業(都市更新計畫案簡寫)` to `auto_fixes`, visible in the detail
  table and review report (config rule: obvious fixes automatic, ambiguous
  flagged).
- **D3 — cache staleness is accepted**: the 6 affected families' caches keep
  their old names until the next full re-run from `source.pdf` (no targeted
  cache patch — the value is display-only and the next pipeline run heals
  them).
