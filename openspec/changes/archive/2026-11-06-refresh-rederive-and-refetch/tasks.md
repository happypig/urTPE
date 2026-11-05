## 1. Tests (test-first group — every task here is checked before any task in group 2)

- [x] 1.1 The refresh re-derives the merged projection: a case appended after the merge reaches it
- [x] 1.2 A withdrawn label leaves the re-derived projection
- [x] 1.3 A re-dated label carries the new value
- [x] 1.4 A project whose cases did not move keeps its projection
- [x] 1.5 The refresh re-fetches the implementation layer for a live approved case with no entry
- [x] 1.6 A case that already has an implementation entry is not re-fetched
- [x] 1.7 An empty implementation reply stores nothing
- [x] 1.8 A case with an empty header and empty milestones is labelled 無, keeps its id and its cached data, and is named in the report
- [x] 1.9 A revoked case (業經本府撤銷核准) is not labelled 無 — the 美仁800 `09707196` near-miss
- [x] 1.10 One empty source is not enough to label a case 無
- [x] 1.11 青年130: `11501041` → 無, and node 78 binds `11510008` and gets its implementation
- [x] 1.12 虎林38: `11410001` → 無
- [x] 1.13 A 無 case's payload does not win the key-count pick, even when it is larger (雅祥227 shape)
- [x] 1.14 A 無 case supplies no date in the plan-case date collection
- [x] 1.15 The conflict flag that names the 無 case stays
- [x] 1.16 A project whose only case is 無 keeps the empty answer

## 2. Implementation

- [x] 2.1 `urtpe/links.py` — `refresh_project` labels a case 無 when its header row and its milestones are both empty, keeping the id and the cached data, and names it in the report
- [x] 2.2 `urtpe/links.py` — `refresh_project` re-fetches data3 and data4 for every live approved case with no implementation entry, storing a non-empty reply only
- [x] 2.3 `urtpe/links.py` — `refresh_project` re-derives `taipei_milestones` and `milestones_source` from `case_milestones` over `city_case_ids`, just before the cache is written
- [x] 2.4 `urtpe/links.py` — `select_best_payload` and `pick_implementation_payload` exclude the cases recorded as 無, at both selection layers

## 3. Verification

- [x] 3.1 The full suite passes (`python -m pytest`) — 1056 passed, 1 skipped
- [x] 3.2 The cache pass ran under the single-writer lock (`scripts/refresh_rederive_pass.py`), with no peer session writing; 726 projects, 0 errors. A backup of the cache is at `data/.link_cache_backup_20261106_rederive`
- [x] 3.3 The refresh report names **3** cases labelled 無 (`11501041` 青年130, `11410001` 虎林38, `10310102` 雅祥349) and **41** implementation cases re-fetched. The before/after payload sizes are in `data/refresh_rederive_pass2.log`
- [x] 3.4 The re-emit's project diff is measured: **380 of 681** projects changed, and `scripts/probe_step2_explain.py` attributes every one (D7 274, D8 31, D10 30, REFRESH_STATUS 12, D15 19, D15b 11, D13 3) — **0 with no explained cause**
- [x] 3.5 `node scripts\viewer_smoke.js` passes after the re-emit — all checks passed
- [x] 3.6 The board row for D9g step 2 is marked done with the measured counts

## Measured notes

- **The D8 scope is 37 cases in 32 projects**, not the board's 26 in 22. The
  board's probe used the approval list `核定日期 / 核准日期 / 核備日期 /
  審議通過日期`; the pipeline's own `_APPROVAL_FIELDS` is `核定日期 /
  權變核定日期 / 概要核准日期`. The 13 cases the board's list missed all carry
  `權變核定日期` (7) or `概要核准日期` (6) — real approvals the city
  published. The 2 cases the board's list holds and the pipeline's does not
  are in-review (their only "approval" is `審議通過日期`, a
  deliberation-pass date, and their state is 審查中) and are correctly not
  selected. The live pass re-fetched **41** cases: the 37 plus 4 the D7
  re-derivation and the D13 labelling freed.
- **The D13 population is 3 cases**, all confirmed live (empty header AND
  empty data2 on both endpoints): `11501041`, `11410001`, `10310102`. The
  board's offline count was 2 (`11501041`, `11410001`); `10310102` (雅祥349)
  is a third that the offline count missed because its cached milestones were
  already empty.
- **A case with no `case_milestones` entry is never visited by the
  per-case pass**, so it cannot be labelled 無 (內湖東湖's `100904` is the
  shape). It is a pre-existing gap, unchanged by this step.
