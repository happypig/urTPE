## Why

A node whose case was approved *after* its project's link cache was written wears
the wrong case badge, and that wrong case id then drives the graph's row order.
Measured on 通化段四小段-336: node 1 (2026-10-15) binds `10011271` (the 2022 case)
instead of `11501034`. Live API check (`get_project168_top`, cited by the user via
`gis.uro.taipei/r_progress_detail.aspx?case_id=10011271#data2`):
`11501034.uro_chk_date = 2026-10-15` — exactly the node's date — and
`Get_project168_second.ashx` returns `核定日期 = 2026/10/15` for it today. The API
has the answer; the pipeline does not ask.

Root cause: `discover_project_links` returns a cache hit without re-fetching, so a
case's milestone set is frozen at the moment its project was first cached. The 336
cache is dated 2026-08-30, before 11501034 was approved. Then
`_match_case_by_date` finds no case matching the node's date and the per-node
attach falls to the positional fallback (`city_case_ids[0]`), producing both the
wrong badge and — because the wrong key ties with node 453's — the out-of-order
row (`String(a.recno).localeCompare` puts `1` before `453`).

Scope: **724 of 726 project caches predate the 2026-10-15 gazette**, so the lag is
systematic, not incidental. Any approval published after a project was first
cached is invisible until its cache is refreshed by hand.

The maintainer affected: anyone reading the viewer's graph, where a newly approved
stage sorts to the wrong place and points at the wrong case.

## What Changes

- A **targeted refresh pass** (`scripts/refresh_awaiting_caches.py`): select the
  projects whose cached cases carry an application-for-approval date
  (`申請核定日期` / `權變申請核定日期`) but no approval date (`核定日期` /
  `權變核定日期` / `概要核准日期`) — the "awaiting approval at cache time" signal —
  and re-fetch only those. Measured: **21 projects** of 726, so the pass costs
  ~1–3 API calls each rather than a full re-crawl.
- The pass preserves every other cache field (the existing merge-preserving write
  path), reports per-project before/after, and is single-writer safe.
- A **detection signal in the pipeline**: `discover_project_links` reports when a
  cache's stored `published_date` predates the current gazette, so the lag is
  visible in the run output instead of silent. (Refresh stays an explicit act —
  AGENTS.md's acquisition/ingestion separation.)

## Capabilities

### New Capabilities

- `cache-freshness`: how the pipeline detects and reports a link cache that
  predates the gazette it is emitting for, and how a targeted refresh re-derives
  the milestones such a cache is missing.

### Modified Capabilities

(none — `official-link-discovery`'s caching requirement is unchanged; this adds
the freshness dimension beside it)

## Impact

- New `scripts/refresh_awaiting_caches.py` (durable, undated — a standing tool).
- `urtpe/links.py`: a `cache_is_stale_for(gazette_date)` helper + the run-output
  warning; no change to the discovery flow's behaviour.
- `data/.link_cache/` — up to 21 project caches rewritten; the P2.2 backup path
  protects the prior state.
- Emission: the refreshed caches feed the next `--links` run, which re-derives the
  affected per-node bindings and the graph order.
