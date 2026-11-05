## Why

The emitted `links.permit` names the **first** permit of a tie, and a tie is
common. `match_project_permits` returns every permit whose parcel overlap ties
for the highest count, sorted by permit number — so `permits[0]` is the
alphabetically first number, which is the **oldest** permit on that parcel, not
the one the project's own 使照 came from.

The permit index keys on the **mono** parcel (the sub-parcel is stripped), so a
section that redeveloped over time accumulates one permit per building phase.
Measured over 681 projects against the live permit index (19,216 keys):

| Outcome | Count |
|---|---|
| City's 使照 == the first matched permit | 271 |
| City's 使照 == a later matched permit (**the witness is wrong**) | **20** |
| City's 使照 matches no matched permit | 23 |
| **Emitted `links.permit.date` differs from the city's 使照** | **43** |

The wrong witness is **silent**: `permit_review_flags` fires only when the
city and national dates disagree, and these projects have no national
使用核發日期 at all — the flag needs two portal values and only one exists.

The two cases the user named: `松山區-寶清段一小段-57-13地號等1筆` (case
`10212211`) shows `使照核發日期 2025/06/25` beside `執照093使字第0294號
(2004-09-14)`, but the city also reports 開工 `2020/05/06`, and the permit
with that 開工 is `114使字第0094號` — the right one, the last of four.
`大安區-金華段一小段-719地號等1筆` (case `10308211`) shows the witness
`096使字第0079號 (2007-03-01)` from parcel 739, while the city's 開工
`2021/12/23` names `115使字第0018號` on parcel 719 — the anchor's own parcel.

## What Changes

- When more than one permit matches, the emitted witness is the permit whose
  **開工日期** (`construction_start`) equals the city's 開工日期.
- When that leaves exactly one permit, it is the witness.
- When it leaves none or several, **no single permit is emitted**: the payload
  carries `links.permit.ambiguous` with the candidate list, and `links.permit`
  is absent.
- The city 使照 date is **never** used to choose the permit. The permit exists
  to check that date; matching it would make the witness copy the value it
  exists to check.
- The 開工 date is read from the **source map** (`milestones_source`), not from
  the merged `milestones_taipei` dict — the merged dict can be stale, and the
  source map names the case that holds each value.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `official-link-discovery`: the permit witness is selected by the city's 開工
  date, and an unresolved tie is marked ambiguous rather than answered by
  order.

## Impact

- `urtpe/permit_sources.py` — the selection function.
- `urtpe/links.py` — the call site reads the 開工 date from the source map and
  emits `links.permit.ambiguous`.
- `data/projects.json`, `viewer/projects.data.js` — one re-emit.
- The disagreement flag reads the merged dict, which the D7 fix repairs; this
  change therefore lands after D7's re-emit.
