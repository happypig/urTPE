## 1. Tests (test-first group — every task here is checked before any task in group 2)

- [x] 1.1 A stub and a richer aliased directory are merged: the current directory gains the aliased directory's case ids and milestones
- [x] 1.2 A conflict keeps the current directory's value
- [x] 1.3 The current directory's own `project_id` and `land_core` are unchanged by the merge
- [x] 1.4 No aliased directory changes nothing
- [x] 1.5 The merge is reported: the project and what was added
- [x] 1.6 A case id from the 168 list enters the case ids when its header confirms it
- [x] 1.7 An unconfirmed id (empty header) does not enter the case ids and is named in the report
- [x] 1.8 An id the search already returned is not added twice
- [x] 1.9 The existing ids keep their positions when an id is appended
- [x] 1.10 A row naming another unit is not even a candidate (the scope is the section AND the parcel, adjacent)
- [x] 1.11 A bound node does not keep the unplaced flag

## 2. Implementation

- [x] 2.1 `urtpe/links.py` — `load_project_cache` merges an aliased directory into the current one when both exist, keeping the current directory's own content and identity fields, and reports what it added
- [x] 2.2 `urtpe/links.py` — the refresh's search step reads the city's 168 list, scopes it by the project's section and parcel, and appends each id the parcel search did not return whose case header confirms it
- [x] 2.3 `urtpe/links.py` — a node that binds a case drops the unplaced flag it carried forward

## 3. Verification

- [x] 3.1 The full suite passes (`python -m pytest`) — 1069 passed, 1 skipped
- [x] 3.2 The cache merge ran under the single-writer lock; nodes 744 and 1063 bind `10708311` and `10006032`, with their implementation payloads
- [x] 3.3 The re-emit changes **4** projects, all explainable: 南港566 (the merge), 玉成166 (`11412011` added), 玉成253-1 (`10203261`/`10203262` added), 青年130 (node 78 binds `11510008`, so the unplaced flag goes). The unplaced flag falls **16 nodes in 11 projects → 13 in 9**
- [x] 3.4 `node scripts\viewer_smoke.js` passes after the re-emit — all checks passed
- [x] 3.5 The board row for D9g step 6 is marked done with the measured counts

## Measured notes

- **The 168 list's paging is broken.** With `pageSize=50` each page advances
  by exactly ONE row (measured 2026-11-06: page 0 starts at `09503232`, page 1
  at `09503233`, page 2 at `09504081`), so a paged walk gathers 90 of the 466
  rows in 40 requests. Asking for the whole list in one request — with the
  count the endpoint itself reports in `TotalCount` — returns all 466. The
  fetcher reads `TotalCount` from the first row and re-requests with it.
- **The scope is the section AND the parcel, adjacent** (the city writes
  `玉成段二小段166地號`). A section alone names 504 projects and the parcel
  alone names 246; both together, adjacent, name 213 — of which the driver
  refreshes the 39 that carry an unplaced node or a sibling-shaped binding.
- **A bound node drops the unplaced flag.** The flag says the node binds no
  case; a flag carried forward by the `--from-js` loader would read as a live
  finding after the node finds its case.
