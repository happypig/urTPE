## 1. Tests first

- [ ] 1.1 `tests/test_links.py`: `_ghost_node_date` with track — a plan-track dict holding only 概要核准日期 yields ""; a 概要-track dict yields its 概要核准日期; a plan-track 核定日期 still wins
- [ ] 1.2 `tests/test_links.py`: the orphan builder passes the derived track (吉林717 triple shape → plan ghosts undated, the 概要 ghost keeps 2007/01/30)
- [ ] 1.3 `tests/test_virtual_node_ordering.py`: the own-event key — plan-track members with different 核定 dates order by date; same-date members by case_id; an application-dated dead attempt sits at its application date (viewer helpers in a VM)
- [ ] 1.4 `tests/test_viewer_labels.py`: the sort key never reads 概要核准日期 for a plan-track member
- [ ] 1.5 Run the new tests; record the expected failures

## 2. D2a implementation (pipeline)

- [ ] 2.1 `urtpe/links.py`: `_ghost_node_date(own_milestones, track)`; the call site passes the derived track
- [ ] 2.2 Full suite green
- [ ] 2.3 Re-emit under the lock; verify: the 25 same-date pairs drop to ~7; no other node_date changed except echo removals; 682 project_ids unchanged
- [ ] 2.4 Commit the re-emit

## 3. D2b implementation (viewer sort)

- [ ] 3.1 `viewer/app.js`: the own-event key in the D12 block (design D2); the family-wide interleave and cluster tie-breaks switch to it
- [ ] 3.2 Full suite green; smoke harness green
- [ ] 3.3 Corpus re-measure: the 51-project/95-pair non-chronology dissolves; 逸仙段三小段-34's orphan lands by date; record the numbers in design.md
- [ ] 3.4 `docs/viewer_sort_rules.md` rewritten (the "do not sort by date" section becomes history)

## 4. Archive

- [ ] 4.1 `openspec archive track-aware-ghost-dates-and-date-sort`
- [ ] 4.2 Board D2 marked done with the commit SHAs
