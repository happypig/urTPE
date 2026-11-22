## 1. Tests first

- [x] 1.1 `tests/test_links.py`: a ghost node's per-case dict emits as `milestones_taipei_case` (no `milestones_national` key on the orphan)
- [x] 1.2 `tests/test_links.py`: `merge_stage_milestones` keeps the first credit for an equal value and keeps last-write-wins for a different value
- [x] 1.3 `tests/test_links.py`: `pick_implementation_payload` credits the first plan case for an equal date (榮星53 shape: 09001120 + 09001123 both hold 建照 2006/07/11 → source 09001120)
- [x] 1.4 `tests/test_cli.py`: `--from-js` loads an old orphan `milestones_national` as `milestones_taipei_case`; a project-level `milestones_national` is NOT aliased
- [x] 1.5 `tests/test_viewer_labels.py`: the viewer virtual-node build reads `milestones_taipei_case`
- [x] 1.6 Run the new tests; record the expected failures

## 2. Implementation

- [x] 2.1 `urtpe/links.py`: emit the orphan per-case dict as `milestones_taipei_case`
- [x] 2.2 `urtpe/links.py`: `merge_stage_milestones` equal-value first credit; `pick_implementation_payload` source stays with the first plan case on an equal date
- [x] 2.3 `urtpe/cli.py`: the `--from-js` load alias (orphan nodes only)
- [x] 2.4 `viewer/app.js`: read `milestones_taipei_case` at the orphan read site
- [x] 2.5 Full suite green; smoke harness green

## 3. Re-emit and corpus checks

- [x] 3.1 Re-emit under the lock (`--from-js … --viewer viewer --links`); read the ledger and coverage reports
- [x] 3.2 Corpus check: orphan dicts carry the new key; the 15-date acceptance list re-credited (榮星53 → 09001120, 蘭雅52 → 10210081, 寶清353-2 → 10001251, 懷生16 → 09503203, …); no project_id changed; no date changed
- [x] 3.3 Viewer re-measure: only 南港729 keeps a recno → 使照 edge (D4a complete)
- [x] 3.4 Commit the emitted state; board D1 + D4a-pipeline marked done
