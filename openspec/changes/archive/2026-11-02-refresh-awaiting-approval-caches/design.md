# Design — refresh-awaiting-approval-caches

## Context

Flow: `discover_project_links(project, cache_dir, fresh, ...)` returns
`load_project_cache(...)` early on a hit (`urtpe/links.py:568`), so a project's
`case_milestones` are frozen at first cache. `attach_links_to_projects` then binds
each node via `_match_case_by_date(member.date, disc)` (all three approval fields),
falling back to the positional heuristic (`city_case_ids[0]`) when no case matches.
Emission is otherwise correct: the matcher, the ISO padding fix (§30) and the
timeline interleave all work.

Evidence for the 336 case: cache written 2026-08-30; `11501034` has
`申請核定日期 2026/07/30` and no `核定日期` in the cache, while
`Get_project168_second.ashx` and `get_project168_top(...).uro_chk_date` both report
**2026-10-15** today. 724 of 726 caches predate the 10-15 gazette. 21 caches show
the awaiting-approval signal.

## Goals / Non-Goals

Goals:

1. A standing, undated refresh tool that re-fetches only caches awaiting an
   approval (21 projects measured) — cheap, auditable, single-writer safe.
2. A pipeline report line naming stale caches, so the lag is visible per run.
3. After refresh + emission, the 336 order is the user's target:
   453 (2022-08-02 → 10011271), 370 (2023-03-21 → 10011273), 1 (2026-10-15 → 11501034).

Non-Goals:

- Automatic refresh inside emission (AGENTS.md separates acquisition from
  ingestion; a pass that silently re-crawls is the class of thing the 2026-08-24
  incident taught against). The report makes the lag visible; the refresh is an
  explicit command.
- A full `--fresh` re-crawl (726 projects, unnecessary for this signal).
- Changing the matcher or the positional fallback (correct as-is; §31/§32).

## Decisions

### D1 — Selection is the awaiting-approval signal, computed offline

`applied and not approved` per case (`申請核定日期`/`權變申請核定日期` present, no
`核定日期`/`權變核定日期`/`概要核准日期`). Computable from the cache alone — no API
call to select — so the pass is bounded and its candidate set is reviewable before
it runs. Measured: 21 projects.

### D2 — Refresh re-uses the existing fetch-and-merge path

`fetch_taipei_milestones_api(case_id)` per cached case id, merged into the cached
`case_milestones` with the same shape `discover_project_links` writes, then
`save_project_cache`. No new fetch code; the tool is a thin driver over the
existing adapters, matching the repo's port/adapter split.

### D3 — Staleness is the cache file's mtime, reported not acted on

`cache_is_stale_for(cache_dir, project_id, gazette_date)` compares the cache
**file's last-write time** against the gazette date. Corrected during
implementation: the first draft compared a `published_date` field, which no real
cache carries (measured 2026-11-02 on all 726) — such a check would pass its own
test and be inert in production, the exact class of bug this repo keeps finding.
`_run_locked` prints one summary line (`N caches predate this gazette; run
scripts/refresh_awaiting_caches.py`) rather than one line per project.

### D4 — Ordering fixes itself once bindings are right

With node 1 bound to `11501034`, the family's case keys become
`10011271 < 10011273 < 11501034` — ascending, and equal to date order. The
`String(recno).localeCompare` tie-break no longer fires (no two nodes share a key),
so no sort change is needed. Verified against the fixture in the tests.

## Risks / Trade-offs

- **API load.** 21 projects × ~1–4 calls; the existing `_post_taipei_api` retries
  and the pass aborts per-project on failure, reporting the residual.
- **A refreshed cache changes bindings beyond the target node.** Expected: that is
  the fix. The tool reports before/after per project so the diff is reviewable, and
  the emission's coverage guard still applies.
- **The stale-cache report fires on ~all projects today** (724/726). That is
  honest and is why the line is a count plus a pointer, not a per-project list.

## Open Questions

(none)
