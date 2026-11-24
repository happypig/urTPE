# Tasks: d11-search-guard-count-rule

## 1. Tests first (the gate: every task in this group is checked before any task in group 2)

- [x] 1.1 `tests/test_membership_verdict.py` — the guard's count test at the policy level: a name admitted by the own-parcel form whose declared count is none of the unit's counts (and not the land-core count) reads `Verdict(False, "count_refused")`; a name whose count matches an `own_counts` member reads `own_parcel` accepted; a name whose count matches only the land-core count reads `own_parcel` accepted; the exact form accepts without a count test; the stem form's verdict is unchanged by the count; a parcel-less corroborated name is unchanged; a caller that passes parcels without counts falls back to the land-core count alone
- [x] 1.2 `tests/test_membership_verdict.py` — the golden table moves by exactly the 65 measured pairs (54 pinned own-parcel + 11 golden-only names), all accept→refuse, at S1 only; S2/S3/S5 and node pairs unchanged. Written as a regeneration harness run, then the fixture re-captured (task 2.5) — the test asserts the count and direction before the fixture changes and the column after
- [x] 1.3 `tests/test_unit_count_rule.py` — the pin test reinterpreted: the frozen 62 stay frozen; a new assertion reads each pinned pair's parcel-rule form and asserts the post-D11 guard refuses the 54 own-parcel pairs and still admits (at the guard) the 8 stem pairs, naming them; the gate's behaviour is unchanged (every existing gate test passes untouched)
- [x] 1.4 `tests/test_links.py` (or a new `tests/test_search_guard_counts.py`) — the search adapter carries counts: `search_taipei_cases_api(..., own_counts=[...], land_core="...")` keeps a count-passing own-parcel case, refuses a count-failing one (it lands in `dropped_out`), and keeps the exact and stem forms; with `own_counts=None` and a land core, the land-core count is the fallback
- [x] 1.5 `tests/test_refresh_awaiting_lock.py` (or `test_search_guard_counts.py`) — `refresh_project` passes the cache's counts and healed land core to its search double: a refresh double recording its kwargs sees `own_counts` and `land_core`; a count-failing search result is not appended to `city_case_ids`
- [x] 1.6 `tests/test_search_guard_counts.py` — `discover_project_links` passes `own_counts_of(project)` and the built land core (a search double records them)
- [x] 1.7 Run the new tests: they fail on the missing interface/behaviour (no `count_refused` reason, adapters take no `own_counts`); record the failures

## 2. Implementation

- [x] 2.1 `urtpe/links.py` — extract the count rule into `_count_rule_passes(name, own_counts, land_core)`; `_unit_membership_reason` calls it (behaviour unchanged, gate tests stay green)
- [x] 2.2 `urtpe/links.py` — the `search_guard` branch: on rule `own_parcel`, apply the count rule; refuse as `count_refused` when it fails; pass the unit's land core and counts
- [x] 2.3 `urtpe/links.py` — `search_taipei_cases_api` and `_search_taipei_raw` gain `own_counts=None` and `land_core=""`; the guard call site builds `Unit(land_core, own_parcels, own_counts, anchor_name)`
- [x] 2.4 `urtpe/links.py` — `discover_project_links` passes `own_counts=own_counts_of(project)`, `land_core=land_core`; `refresh_project` passes `own_counts=cached.own_counts`, `land_core=cached.land_core` on its search call (the post-heal core)
- [x] 2.5 Re-capture the golden fixture's S1 column from the post-change code over the frozen inputs; assert exactly 65 moves, all accept→refuse, other columns untouched; keep the fixture's `about` note updated with the 2026-11-24 D11 re-capture
- [x] 2.6 Update the 62-pair pin test to its post-D11 form (task 1.3's assertions now pass); leave the fixture at 62
- [x] 2.7 Run the full suite offline; every test green; record the counts in `AGENTS.md` only if they changed (2026-11-24: 1756 passed, 1 skipped, 4 xfailed; 1761 collected)

## 3. Acceptance

- [x] 3.1 The board (`docs/inspections/optimization.md` Part II) gains a D11-done note: implemented, the measured populations (54/8, 65 golden moves, tier-1 unchanged), and that no cache or payload moved (no fresh discovery since F3)
- [x] 3.2 `openspec validate` passes; the change is ready to archive on the user's word
