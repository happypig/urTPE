# Proposal: normalize-plan-abbreviation

## Why

Planners reading the viewer see 6 families (10 nodes) labeled with the track
`都市更新計畫` instead of `事業計畫`. The cause is a PDF-era abbreviation:
gazette rows c.2009-2011 print the 案名 as `土地都市更新計畫案` — dropping
事業 from the legal plan name — while the Taipei platform's own `CASE_NAME`
for the same units always writes `土地都市更新事業計畫案` (live cross-reference:
18/18 linked cases spell 事業計畫案, 0 without; e.g. 09904301, 10112121,
10204032 — data: `data/_gengxin_plan_crossref.json`). `_tracks()` therefore
falls into its fallback branch and assigns the synthetic track
`都市更新計畫`. Affected families: 長春段775 (×3), 南海段41-4, 河堤段263-19,
奇岩段444, 圓環段103-2 (×2), 金華段513-3 (×2).

## What Changes

- **Pipeline (cleanse)**: normalize the 案名 abbreviation `土地都市更新計畫案`
  → `土地都市更新事業計畫案` (only when 事業計畫 is absent), flagging
  `案名補事業(都市更新計畫案簡寫)` — same normalization class as the existing
  權利變換案 == 權利變換計畫案 rule. `_tracks()` then yields `事業計畫`, and
  the synthetic `都市更新計畫` track disappears from new emissions.
- **No viewer change required**: the affected nodes already render in column 1
  beside 事業計畫 (`trackPosition` maps both); only labels and
  `auto_fixes`/flags change.
- **Not BREAKING**: project_ids of the affected families are unaffected (they
  are parcel-based); old caches keep their stored names until the next full
  re-run from the PDF.

## Capabilities

### New Capabilities
<!-- none — this change modifies an existing capability -->

### Modified Capabilities
- `data-cleansing`: "Normalize known data errors" gains the 案名 abbreviation
  class (土地都市更新計畫案 → 土地都市更新事業計畫案), with an auto-fix flag.
