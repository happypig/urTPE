# Proposal: refresh-whole-corpus (R — B1, B5, B6, C2, §7 task 4.1)

## Why

The per-project caches were written by different runs at different depths.
Measured over the 682 caches (2026-11-04):

- **B1**: new-case discovery covers refresh-selected projects only. The
  awaiting-approval selector picks a project only when a cached case carries
  an application date and no approval date; 大安區-通化段四小段-336 (3 cases,
  all 已核准, no `case_headers`) is never selected, and a case filed on it
  after 2026-11-02 would not be found.
- **B5**: status is re-derived only for selected projects — 1 cached 審查中
  sits on a case that has an approval date (大同764 09605032), 3 cached
  已核准/已核定 have no approval date (臨沂318 10409104, 學府125 10611122,
  直興373 10405293).
- **B6**: a cleared status is removed from `case_schedules` — a project whose
  last open status clears would read as never-approved (measured 3, unchanged).
- **C2**: the view-page absorb has never run corpus-wide — 642 caches hold
  `view.html`, 557 case ids in 435 projects would gain `view_verified_case_ids`.
- **§7 task 4.1** (show-no-state-case-status, reassigned from S0): 628 of 726
  caches had no `case_headers` at the S0 count; the header-refresh pass never
  ran.

One change with one run is cheaper and safer than five runs against a
WAF-capped API (the plan's "the refresh needs one owner" fact).

## What changes

- A resumable whole-corpus refresh driver (`scripts/refresh_whole_corpus.py`),
  run in slices of about 100 projects per the user decision 2026-11-04:
  each slice takes the single-writer lock, writes into `data/.link_cache/`
  only, records a checkpoint (the slice's last project), and releases the
  lock. The tracked `projects.json` and `viewer/projects.data.js` are
  emitted **once, after the last slice**.
- **Change detection** (the board's design, 2026-11-04) — one cheap signal
  per source, a full fetch only when the signal moves:
  1. national page: 資料更新日期 vs the cached page's — fetch only when later;
  2. city parcel search: compare case ids and `schedule` — fetch headers only
     when a case id is new or a `schedule` differs;
  3. case header: `get_project168_top` per case — compare `NAME`,
     `uro_chk_date`, `uro_chk_date2`; a finished case (已完工 / 完成成果備查,
     with a 使照) skips data2/data3 unless steps 1–2 moved.
  Every skip is counted in the run report ("not fetched because unchanged"
  never reads as "fetched and empty").
- Each project's refresh runs the standing `refresh_project` (status
  re-derivation, the view absorb gated by S3a, the parcel search, the header
  dates) plus the resolver's probe/all-parcel steps for any node the date
  matcher cannot place (R reuses S10's resolver — the board's order).

## What does not change

- The single-writer lock, the coverage guard, the §8 rejection records.
- The emission path: `--from-js` re-emit happens after the last slice, once.
- The selector's semantics for the awaiting-approval refresh (this change
  adds a corpus-wide pass beside it, it does not replace it).

## Capabilities

### Modifications

- `cache-freshness`: ADDED requirement — the whole-corpus resumable refresh
  (slices, checkpoint, change detection, the skip counts in the report).

## Risks

- ~2,000–2,500 gis.uro requests at 1 s spacing ≈ 40–70 min of wall clock,
  sliced so an interruption loses at most one slice.
- The WAF: the standing retry/backoff applies; a slice that exhausts its
  retries records the failure and moves to the next project (the report
  names each failure).
