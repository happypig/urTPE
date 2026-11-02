# tasks — supersede-headerless-cases-and-discover-new-ids

## 1. Test-writing group (red first; all checked before any implementation task)

- [x] 1.1 `tests/test_case_status_refresh.py` (domain, D1): the archived
      `test_an_outcome_less_header_keeps_a_consistent_status` reverses on
      purpose — 審查中 + `無` → ""; 已核准 + `無` → ""; 自行撤回 / 施工中 + `無` →
      kept; an unrecognised NAME keeps 審查中 and clears a contradicted 已核准.
      RED: the 審查中 case.
- [x] 1.2 `tests/test_supersede.py` (new, domain, D2): `find_superseding_case` —
      the 11211211 → 11409026 shape; the 10806141 → 11510017 shape; a different
      case name → none; two qualifying → ambiguous; < 3 dated labels → none; a
      smaller id → none. RED: the function does not exist.
- [x] 1.3 `tests/test_cache_freshness.py` (selector, D5): a project whose only
      awaiting case has header `無`, or is superseded, is not selected; an
      unrelated open case keeps it selected. RED.
- [x] 1.4 `tests/test_supersede.py` (adapter, D3/D4): `refresh_project` with
      injected `fetch`, `fetch_status`, `search` and a `search_key` — the 虎林
      shape appends 11510017 after the old ids in their old order, reads it,
      records `superseded_by {10806141: 11510017}`, `case_headers`, and reports
      `added` / `superseded`; a `無` case with no twin lands in `no_successor`;
      a raising search returns an error and leaves the cache file unchanged;
      no `search_key` reports `not_searched`. RED.
- [x] 1.5 `tests/test_supersede.py` (default path, D4): no fetcher injected, the
      module adapters monkeypatched — the search runs and the twin is recorded.
      RED.
- [x] 1.6 `tests/test_supersede.py` (payload, D6, acceptance): the attach emits
      `links.superseded_by`; a payload reloaded through the `--from-js` path and
      re-attached keeps it; a legacy result emits without the key. RED.
- [x] 1.7 `tests/test_viewer_schedule_badge.py` (viewer, D6, acceptance): the
      相關連結 code renders `已由 ` + successor for a key of
      `links.superseded_by` (structural, plus the smoke harness on a fixture
      carrying the map). RED.

## 2. Implementation (after group 1 is fully checked)

- [x] 2.1 `refreshed_schedule` `no_state` (D1).
- [x] 2.2 `find_superseding_case` (D2).
- [x] 2.3 `DiscoveryResult.case_headers` / `superseded_by`; `refresh_project`
      search step, header recording, twin pass, new report buckets (D3/D4).
- [x] 2.4 Selector parameters; the script reads the anchor search key from the
      payload and prints the new buckets (D5).
- [x] 2.5 Attach + `--from-js` reload of `superseded_by`; viewer 相關連結 note (D6).
- [x] 2.6 Full suite, smoke, `openspec validate --all`. Result: 838 passed /
      1 skipped; smoke passes; 26 items valid. The view-page absorb also moved
      out of the per-case loop (once per project — the §36 residual).

## 3. Live acceptance

- [x] 3.1 Backup `data/.link_cache` → `data/.link_cache_backup_20261102_supersede`;
      record counts (records, projects, never-approved, 審查中 chips, total
      `links.taipei` ids, orphan nodes).
- [x] 3.2 Live refresh: record added cases (per project, search status +
      NAME), superseded, no-successor, ambiguous; 11211211 → 11409026 and
      10806141 → 11510017 recorded; 11510017 added to 虎林38.
- [x] 3.3 Re-emit; records / projects / never-approved unchanged; `links.taipei`
      growth equals the added count; a dry-run shows fewer than 91 candidates.
- [x] 3.4 Chrome (local server): 立農163-2 has no 審查中 chip and 11211211 reads
      `已由 11409026 取代`; 虎林38 shows 11510017 `[審查中]`, a 審查中 chip, and
      10806141 `已由 11510017 取代`.
      Results (3.1-3.4): backup `.link_cache_backup_20261102_supersede`; live
      refresh 90 projects / 0 failures — 4 added (吉林705-3 11503012, 福和472-1
      11208191, 虎林38 11510017, 雅祥227-4 11510001), 2 superseded (as targeted),
      2 無 without successor (雅祥227-4 11009142, 吉林705-3 10410012 — each has a
      same-named newer case differing in one or two dates, refused by the strict
      rule), 4 not searched (stranded cache ids absent from the payload), 0
      conflicts. Re-emission exit 0, 1,442 / 693, never-approved 3 → 3,
      links.taipei 1993 → 1997 (= 4 added), orphan nodes 593 → 596 (11208191
      bound gazette node 219, which had no case before), dry-run 90 → 89. Chrome
      on 127.0.0.1, DOM-verified, all targets met.
- [ ] 3.5 Commit, push, `check_deploy.py` FRESH, repeat 3.4 on the live page.
- [ ] 3.6 Books: archive with spec sync; §37 states that §36's "立農163-2
      correctly stays 審查中" was wrong and why; correct `docs/inspection.md`.
