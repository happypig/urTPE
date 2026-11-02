# tasks — refresh-awaiting-approval-caches

## 1. Test-writing group (red first; all checked before any implementation task)

- [x] 1.1 `tests/test_cache_freshness.py`:
      (a) `cache_is_stale_for(cache, gazette_date)` is True when the cached
      `published_date` is earlier, False when equal, False when no cache exists;
      (b) the awaiting-approval selector picks a cache whose case has
      `申請核定日期` and no approval date, and skips one whose cases are all
      resolved;
      (c) the selector skips a cache with no cases at all;
      (d) `refresh_project(cache_dir, project_id, fetch=stub)` merges the fetched
      milestones into the cached case_milestones, preserves every other field, and
      returns a before/after report;
      (e) a project still awaiting approval after the fetch is reported unchanged.
- [x] 1.2 `tests/test_refresh_binding_effect.py`: after a refresh that supplies the
      missing approval date, `_match_case_by_date(node_date, disc)` binds the node
      to the recovered case — pinned on the 336 shape (node 2026-10-15 →
      11501034 once its 核定日期 2026/10/15 is present).

## 2. Implementation (after group 1 is fully checked)

- [x] 2.1 `urtpe/links.py`: `cache_is_stale_for(cache_dir, project_id, gazette_date)`
      and `cached_cases_awaiting_approval(case_milestones)` (pure selectors).
- [x] 2.2 `urtpe/links.py`: `refresh_project(cache_dir, project_id, fetch=...)` —
      thin merge-preserving refresh returning a before/after report.
- [x] 2.3 `scripts/refresh_awaiting_caches.py`: durable undated tool — select,
      refresh each, print the per-project report, exit non-zero only on a hard
      failure; single-writer aware.
- [x] 2.4 `urtpe/cli.py` `_run_locked`: one summary line reporting how many
      caches predate the gazette being emitted (informational).

## 3. Acceptance

- [x] 3.1 Full suite green; smoke passes.
- [x] 3.2 Run the refresh against the live cache: report the per-project
      before/after; confirm 336's 11501034 gains 核定日期 2026/10/15.
- [x] 3.3 Re-emit with `--links`: the 336 order is 453 → 370 → 1 with bindings
      10011271 → 10011273 → 11501034.
- [x] 3.4 Live-viewer check on the deployed page after the push: same order, and
      the three node badges name the three cases.
- [x] 3.5 `openspec validate` passes; the main spec synced; both boards updated;
      commit.

---

Test-group note (2026-11-02): 1.1's tests are RED (the three helpers do not exist).
1.2's tests PASS against the current matcher — deliberately: they pin that the
matcher is already correct and that the refresh (not a matcher change) is what
supplies the missing date. Recorded here rather than described as red.

---

Completed 2026-11-02. 3.1: suite 774 passed / 1 skipped; smoke passes.
3.2: the live refresh updated 8 case approval dates across 21 candidates
(13 genuinely still awaiting); 336's `11501034: (none) -> 2026/10/15`.
3.3: re-emission exit 0, tripwire PASS, 1,442/694, and the 336 order is exactly
the user's target — 453 (2022-08-02) -> 10011271, 370 (2023-03-21) -> 10011273,
1 (2026-10-15) -> 11501034; rendered top-to-bottom 453, 370, 建照 2023/04/27,
開工 2023/07/03, 1. The CLI reported "684 of 694 link caches predate this
gazette", the new freshness line.
3.4: live-viewer check pending the push (the deploy is fresh at fbece0c; this
emission's viewer bytes are uncommitted until the closing commit).
3.5: validate passes; spec synced; boards updated; closing commit.

Design correction recorded: D3's first draft compared a stored `published_date`,
which no real cache carries (all 726 measured) — corrected to the cache file's
mtime before implementation, with a test that fails if the check reverts to the
inert field-based form.
