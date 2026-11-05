## Why

`refresh_project` is the pipeline's per-project repair path, and it leaves
three kinds of damage on the table. All three are visible to the user today.

**D7 — the merged milestone projection goes stale.** `taipei_milestones` is
written only by the full discovery path (`urtpe/links.py:694-695`), but
`refresh_project` rewrites `case_milestones[cid]` per case
(`urtpe/links.py:1890`) and never re-merges. Measured offline over the 719
caches that hold per-case milestones (2026-11-06): **85 diverge** from a merge
over their own `city_case_ids`, 84 lose or alter a label, 66 carry a
conflicting value, and **14 projects emit no construction date that a case
actually holds**. The D7b measurement named the 50 that no subset or
permutation explains: 20 stale merges, 16 new labels from a case appended
after the merge, 3 withdrawn, 11 mixed.

The example the user named: `松山區-寶清段四小段-599地號等27筆` shows no 建照核准
date, yet the cache holds `2006/05/12` under case `09303270`. The date is in
the cache and not in the payload.

**D8 — the implementation layer is never re-fetched.** `refresh_project` calls
the data2 endpoint and the case header. It never calls data3 (`third.ashx`,
執行階段) or data4 (`fourth.ashx`, 獎勵資料). A project whose payload was
empty therefore stays empty forever: `文山區-實踐段二小段-641地號等1筆` has no
開工 and no 使照, while the live data3 for case `09009032` holds both
(`2004/09/24` and `2007/10/31`).

**D13 — a case the city emptied keeps its stale state.** The city moved a case
from `11501041` to `11510008` and emptied the old id. The cache still holds
`11501041` as 已核准 with the old payload, so `萬華區-青年段一小段-130地號等3筆`
node 78 loses its `implementation` and stays flagged 節點未能對應平台案件.

The three share one function and one re-emit, so they are one change.

## What Changes

- **`refresh_project` re-derives the merged milestone projection** from
  `case_milestones` over `city_case_ids` after the per-case pass, and writes
  `taipei_milestones` and `milestones_source` from it. The re-derivation
  projects the cases **exactly** (the decided rule): a value no case carries
  any more is dropped.
- **`refresh_project` re-fetches data3 and data4 per case** — every live case
  that carries an approval date and has no `implementation` entry. Measured
  offline on 2026-11-06: **26 cases in 22 projects**.
- **A case whose header row and data2 are both empty is labelled 無.** It
  keeps its id and its cached data (no removal, no `superseded_by` — the city
  states nothing about a removal). The label replaces the stale 已核准.
- **A 無 case's payload never wins either selection layer**: not the key-count
  pick for `implementation` and `rewards`, and not the plan-case date
  collection. The conflict flags that name the 無 case stay.

## The near-empty payload case (defined before the code is written)

The decided rule would replace `信義區-雅祥段一小段-227-4地號等10筆`'s 26-key
implementation payload with the live sibling's **1-key** payload. A 1-key
payload is a statistics answer, not a construction answer: the live case
`11009141` carries one field.

**The rule: the exclusion applies, and the near-empty result is reported.**
The 無 case's payload does not win; the live sibling's payload is used even
when it is near-empty; and the refresh report names the case, the before size
and the after size, so the shrink is visible rather than silent. The
alternative — keeping the 無 case's payload when the live one is smaller —
would let a stale copy keep winning, which is the defect the rule exists to
fix.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `cache-freshness`: the refresh re-derives the merged milestone projection,
  re-fetches the implementation layer per case, and labels an emptied case 無.
- `taipei-implementation-data`: a 無 case's payload never wins the selection.

## Impact

- `urtpe/links.py` — `refresh_project` (three edits), `select_best_payload`
  and `pick_implementation_payload` (the 無 exclusion).
- `data/.link_cache/` — the 22 projects' caches are rewritten by the cache
  pass.
- `data/projects.json`, `data/merged.tsv`, `data/clean.tsv`, `data/raw.tsv`,
  `data/review_report.txt`, `viewer/projects.data.js` — one re-emit.
