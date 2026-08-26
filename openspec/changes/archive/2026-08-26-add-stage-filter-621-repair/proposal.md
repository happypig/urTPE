# Add Construction Stage Filter & Repair recno 621 Track

## Why

Planners scanning the project list cannot filter by construction progress —
the list badges (建照/開工/使照， added in refine-event-source-edges) are
visible but not queryable, so finding "all projects with 使用執照 issued"
means eyeballing 709 items. The filter dropdowns (地區/年度/事業種類) sit right
there; a 施工階段 filter belongs beside 事業種類.

Separately, recno 621 (北投區-大業段三小段-184-1地號等10筆) still renders as
track 其他 with the scrambled 案名 事業換計畫 — the cleanse.py normalization
(fixed in refine-event-source-edges) only applies during full PDF builds,
while the viewer data was regenerated via `--from-js`, which copies tracks
verbatim. The wrong track breaks 事業種類 filtering for this family today.

## What Changes

- Add a 施工階段 filter dropdown next to 事業種類 in the left-list filters:
  fixed options 建照 / 開工 / 使照， deriving each project's stage from the
  same `constructionStage` derivation the list badge uses (latest of the
  three construction dates, 使照 falls back to national 使用核發日期).
  Selecting any stage excludes projects without a construction stage.
- Repair recno 621 via targeted data repair (option B): patch the emitted
  `viewer/projects.data.js` + `data/projects.json` + the family cache —
  track 其他 → 事業計畫， 案名 事業換計畫 → 事業計畫，
  `auto_fixes += 案名錯字→事業計畫`. The next full PDF build reproduces the
  same result (the cleanse rule is already in place and regression-tested).
- No change to fetch, cache layout, or `schema_version`.
- No part of this scope is gated on the PDF-parsing/similarity POC findings —
  neither the parsing nor the merge/threshold surface is touched.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `viewer-filtering`: add requirement — the left-list filters SHALL include a
  construction-stage dimension (建照/開工/使照) whose derivation matches the
  list badge, combinable with the existing 地區/年度/事業種類 dimensions.

## Impact

- `viewer/app.js`: one DIMS entry + one `matches()` clause (derivation
  reuses `constructionStage`).
- `scripts/repair_621_track_2026_08_26.py`: one-off targeted repair
  (backfill/restore pattern).
- Data: `viewer/projects.data.js`, `data/projects.json`,
  `data/.link_cache/北投區-大業段三小段-184-1地號等10筆/result.json`.
- Tests: structural filter test in `tests/test_viewer_labels.py`; repair
  verified by re-reading the patched files.
