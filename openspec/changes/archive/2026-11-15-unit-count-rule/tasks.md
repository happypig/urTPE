## 1. Tests first (offline; red before any implementation)

- [x] 1.1 `tests/test_unit_count_rule.py`: the predicate's truth table — an equal count passes; a name's `原N筆` equal to a unit count passes; a count of an earlier approval passes; an unequal count is refused; a matching land core passes with no counts at all; with no `own_counts` only the land core's count counts; a nameless or parcel-less name is refused
- [x] 1.2 Same file: gate parity — verdicts equal the previous rule on every cached name except the set the count test newly refuses; that set is pinned and is empty on the gate-visible ids of the live payload
- [x] 1.3 Same file: the walk uses the single rule (an earlier-approval count joins; an unequal count is held back)
- [x] 1.4 Same file: `own_counts` round-trips; discovery sets it on the fresh and the cached path and writes nothing when equal; `own_counts_of` reads land and original counts; the backfill writes it with a backup; an old cache loads `[]`
- [x] 1.5 Same file: `refresh_project` reports `view_gate_no_counts` for an empty list and nothing when counts exist
- [x] 1.6 `tests/test_admit_unit_cases.py`: the command's dry run issues no request and writes nothing; `--apply` backs up first, admits a passing case with header and milestones; a held or refused id is left in `search_rejected`; a second run changes nothing; the lock refuses a second writer
- [x] 1.7 Confirm the new tests are red for the right reason (missing keyword, field, helper, script), not for a fixture error

## 2. Domain

- [x] 2.1 Add `DiscoveryResult.own_counts`, `own_counts_of`, and set the field on both discovery paths
- [x] 2.2 Give `unit_accepts_case_name` the `own_counts` argument and the count test; remove `require_equal_count`; pass `own_counts` from the gate, `refresh_project` (with the named empty state) and `walk_unit_siblings`
- [x] 2.3 Factor the walk's join into `_join_unit_case`

## 3. Adapters

- [x] 3.1 Extend `scripts/backfill_own_parcels.py` to write `own_counts` from the payload nodes
- [x] 3.2 Add `scripts/admit_unit_cases.py` (dry run, `--apply`, lock, backup `…_admitcases`, report that names each admitted case)

## 4. Data run and measurement

- [x] 4.1 Run the backfill over all caches; check the live pin (every payload project's cache counts equal the payload's)
- [x] 4.2 Measure the live numbers: guard-only pairs that pass the rule (expect 22: 24 before F5's land-core repair, which moved 寶清51-13's two cases to a land-core match), gate-visible (expect 3), held by no project (expect 7); confirm `09012312` is still refused
- [ ] 4.3 Dry-run the admission command and compare with the 7 pairs; run `--apply`
- [x] 4.4 Re-emit; count list entries, node badges, joined nodes and orphan flags before and after; record them on `docs/inspection-batchF.md`; re-pin the affected tests
- [x] 4.5 Add live pins: the 7 admitted ids are held by their projects and by no other; the 22 / 62 / 3 / 7 numbers; run the viewer smoke

## 5. Close

- [x] 5.1 Run the full suite; refresh the counts in `AGENTS.md`
- [x] 5.2 `openspec validate unit-count-rule`; archive on a copy of `openspec/` first
- [x] 5.3 Mark F7 and D1/D2 done on the board; commit
