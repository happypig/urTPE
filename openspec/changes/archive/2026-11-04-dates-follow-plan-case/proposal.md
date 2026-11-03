## Why

The city keeps 建照核發日期 (data2) and 開工日期 / 使照核發日期 (data3) on the
first 擬訂 plan case — the user rule decided 2026-11-04. `select_best_payload`
(urtpe/links.py:2078) keeps ONE data3 payload per project, chosen by key count,
so the plan case's 開工/使照 are dropped when a later case has more statistics
(measured C8: 9 of the 13 "national-only 使照" projects; 德惠573 09710240 holds
開工 2012/07/13 and 使照 2015/07/13 in its cache, never emitted).

Measured over all 726 caches: on the first 擬訂 plan case 535; on a later 擬訂
plan case of an area split 14; echoed on another case 16; on another case with
no plan case carrying the field 3.

## What Changes

- The implementation (data3) dates are read from the FIRST 擬訂 plan case of
  the project (per area in an area split: each area's own 擬訂 plan case
  carries its own building's dates); that case is the `milestones_source`.
- `select_best_payload` keeps its one-payload rule for the STATISTICS only
  (D5); the date fields route by the rule above.
- A construction date taken from a non-plan case (no plan case carries the
  field — 3 cases) keeps a review flag.
- Emit-side, no fetch: recovers 開工/使照 on 8 national-only projects at once
  (the remaining 3 need S10's discovery of their missing plan cases).

## Capabilities

### Modified Capabilities
- `official-link-discovery`: the implementation date fields SHALL follow the
  first 擬訂 plan case (per area), with the statistics keeping the
  one-payload rule.

## Impact

- `urtpe/links.py`: the attach path picks the plan case's data3 payload.
- Re-emit; no API call.
