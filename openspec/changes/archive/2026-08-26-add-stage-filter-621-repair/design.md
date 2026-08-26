# Design — Construction Stage Filter & recno 621 Repair

## Context

Actors: planners filtering the 709-project list in the viewer's left panel.
Domain events in play: stage approvals (recno records) and construction
events (建照/開工/使照) already emitted into `links.milestones_taipei` /
`milestones_national`. System boundary: the filter lives entirely in the
browser-viewer adapter (`viewer/app.js` DIMS/matches); the recno 621 repair
is a one-off targeted data fix following the established backfill/restore
pattern (`scripts/restore_national_links_2026_08_25.py`,
`scripts/backfill_milestones_source_2026_08_26.py`). Pipeline flow untouched:
PDF → parse → cleanse → merge → projects.json (+ viewer). See proposal.md.

## Goals / Non-Goals

**Goals:**

- 施工階段 filter beside 事業種類， sharing the badge's `constructionStage`
  derivation (single source of truth — filter and badge cannot diverge).
- recno 621 renders 事業計畫 with the corrected 案名 immediately.

**Non-Goals:**

- No re-derivation of tracks during `--from-js` loads (that belongs to the
  full pipeline; the repair bridges the gap).
- No per-stage counts in the dropdown (existing dropdowns show selection
  counts only).
- No change to fetch, cache layout, or `schema_version`.

## Decisions

1. **Filter reuses `constructionStage`** — the DIMS entry's predicate calls
   the same function the badge uses. *Alternative rejected:* a parallel
   derivation — two implementations of "latest of three" would drift (the
   §12 #3 dual-implementation lesson).

2. **Fixed options 建照/開工/使照， no 無 option** — selecting any stage
   excludes stage-less projects; clearing the dropdown restores them.
   *Alternative rejected:* a 無 option — no planner asks for "no construction
   data" as a positive filter; the exclusion semantics are the useful ones.

3. **recno 621 repair via targeted script (option B)** — patch
   `viewer/projects.data.js`, `data/projects.json`, and the family cache
   (`data/.link_cache/北投區-大業段三小段-184-1地號等10筆/result.json`):
   track 其他 → 事業計畫， 案名 事業換計畫 → 事業計畫，
   `auto_fixes += 案名錯字→事業計畫`. The next full PDF build reproduces the
   same values (cleanse.py fix is in place, regression-tested).
   *Alternative rejected:* full pipeline rebuild now — heavy, and the repair
   result is identical; *waiting for the scheduled build* — leaves the wrong
   track filterable-wrong today.

## Risks / Trade-offs

- [Repair diverges from a future full-build output] → it cannot: the cleanse
  rule produces exactly the repaired values; verified by the existing
  `test_shiye_huan_jihua_typo_treated_as_shiye_jihua`.
- [Stage filter interacts with the 現況-recno sort] → it does not — filtering
  precedes sorting; the 現況-recno ascending order is preserved within the
  filtered set.
- [Dropdown grows to four] → accepted; the bar wraps on narrow panels.
