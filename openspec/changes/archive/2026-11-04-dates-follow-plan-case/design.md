## Context

`select_best_payload` picks one data3 payload by key count (D5: never
field-merge). The city puts the construction dates on the first 擬訂 plan
case; a later 變更 case can carry more F0–F5 statistics, so the key-count
pick drops the plan case's dates.

## Goals / Non-Goals

**Goals:**
- 建照 (data2), 開工 and 使照 (data3) follow the first 擬訂 plan case, per area.
- Statistics (F0–F5, 實施方式 …) keep the one-payload rule.
- Every date taken from a non-plan case is flagged.

**Non-Goals:**
- No change to data2's own harvest (建照核發日期 already sits on the plan
  case in the merged milestones; the rule re-points only the data3 selection).
- No discovery here (the 3 missing plan cases wait for S10).

## Decisions

### 1. Plan-case-first selection for the date fields

`pick_implementation_payload(payloads, candidate_names)`:
plan_cases = payloads whose case name matches
`^擬訂.*都市更新(事業計畫|事業計畫及權利變換計畫)案`. If several (area
split), each area's case carries its own building's dates: take the union of
the date fields from ALL plan cases, keyed per field — a field present on 2+
plan cases with different values is a conflict flag (area cases hold
different buildings, so a shared field with differing values is a data
question, not a rule question). If no plan case carries a field, fall back to
the best-populated payload (D5) for that field and flag it.

### 2. Statistics keep D5

The emitted `implementation` object stays the best-populated payload (case_id
= its case), so every consumer of the statistics keeps its provenance. The
date fields additionally surface in `milestones_taipei` with the plan case as
`milestones_source`.
