## 1. Tests (test-first group — every task here is checked before any task in group 2)

- [ ] 1.1 The refresh re-derives the merged projection: a case appended after the merge reaches it
- [ ] 1.2 A withdrawn label leaves the re-derived projection
- [ ] 1.3 A re-dated label carries the new value
- [ ] 1.4 A project whose cases did not move keeps its projection
- [ ] 1.5 The refresh re-fetches the implementation layer for a live approved case with no entry
- [ ] 1.6 A case that already has an implementation entry is not re-fetched
- [ ] 1.7 An empty implementation reply stores nothing
- [ ] 1.8 A case with an empty header and empty milestones is labelled 無, keeps its id and its cached data, and is named in the report
- [ ] 1.9 A revoked case (業經本府撤銷核准) is not labelled 無 — the 美仁800 `09707196` near-miss
- [ ] 1.10 One empty source is not enough to label a case 無
- [ ] 1.11 青年130: `11501041` → 無, and node 78 binds `11510008` and gets its implementation
- [ ] 1.12 虎林38: `11410001` → 無
- [ ] 1.13 A 無 case's payload does not win the key-count pick, even when it is larger (雅祥227 shape)
- [ ] 1.14 A 無 case supplies no date in the plan-case date collection
- [ ] 1.15 The conflict flag that names a 無 case stays
- [ ] 1.16 A project whose only case is 無 keeps the empty answer

## 2. Implementation

- [ ] 2.1 `urtpe/links.py` — `refresh_project` labels a case 無 when its header row and its milestones are both empty, keeping the id and the cached data, and names it in the report
- [ ] 2.2 `urtpe/links.py` — `refresh_project` re-fetches data3 and data4 for every live approved case with no implementation entry, storing a non-empty reply only
- [ ] 2.3 `urtpe/links.py` — `refresh_project` re-derives `taipei_milestones` and `milestones_source` from `case_milestones` over `city_case_ids`, just before the cache is written
- [ ] 2.4 `urtpe/links.py` — `select_best_payload` and `pick_implementation_payload` exclude the cases recorded as 無, at both selection layers

## 3. Verification

- [ ] 3.1 The full suite passes (`python -m pytest`)
- [ ] 3.2 The cache pass runs under the single-writer lock, and no peer session is writing
- [ ] 3.3 The refresh report lists every case labelled 無, and the before/after payload sizes for 青年130, 虎林38, 雅祥227, 立農163-2, 萬華894, 吉林705-3
- [ ] 3.4 The re-emit's project diff is measured and reported; no project changed beyond what the step explains
- [ ] 3.5 `node scripts\viewer_smoke.js` passes after the re-emit
- [ ] 3.6 The board row for D9g step 2 is marked done with the measured counts
