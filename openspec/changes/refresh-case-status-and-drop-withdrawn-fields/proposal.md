## Why

The maintainer checked the 13 cases the awaiting-approval refresh reported as
"still awaiting approval" (2026-11-02, §33) against the city platform's own
基本資料 / data1 辦理進度 / data2 階段辦理過程 tabs, and the viewer's 相關連結
badges disagreed with the platform for 8 of them. Measured live the same day:

- **The status mapper reads an in-review case as approved.**
  `schedule_from_top({"NAME": "權利變換計畫階段─申請報府核定中"})` returns
  `已核准`, because the `"核定" in name` test fires on 申請報府**核定**中. The
  viewer omits the 已核准 badge as the default state, so a case the city lists as
  審查中 (search list, live: 10406283, 10304127) shows no status at all. Corpus:
  exactly 8 cached `case_schedules` entries are 已核准 on a case that carries an
  application and no approval date — the 8 the maintainer found. Which writer
  stored them cannot be proven (every `.link_cache_backup_*` predates the
  `case_schedules` field); the values are *consistent with* this mapping defect
  (the 2026-08-29 top-up sweep wrote `case_schedules` through it), not proven
  caused by it.
- **The refresh never re-reads a case's status.** `refresh_project` re-fetches
  milestones only; `case_schedules` freezes at first discovery (caches dated
  2026-08-30) while the platform moves on.
- **The refresh keeps dates the city withdrew.** The merge is
  `{**before, **fetched}`, so a field the city removed survives forever:
  士林區-光華段四小段-282's 11408032 carries 申請核定日期 2026/08/18 in the cache;
  the live data2 tab no longer has it.
- **The report miscounts closed cases as awaiting.** 3 of the 13 (南海段一小段-687
  11012301 and 信義段二小段-142 11105301 自行撤回; 三玉段一小段-672 09812232
  駁回) can never be approved, yet each refresh re-selects and re-fetches them;
  85 of the 176 projects the widened selector picks have only such cases.
- **One status, two renderings.** The city's search list now uses both 已核准 and
  已核定 for approved cases (cache: 739 / 14). The viewer hides only 已核准, so an
  approved case renders `[已核定]` in one project and nothing in the next.

## What Changes

- `schedule_from_top`: a NAME that is *pending* approval (`…核定中`) maps to
  審查中, checked before the approved rule; an unknown NAME (`無`, empty) still
  maps to `""`.
- `refresh_project` refreshes each case's `case_schedules` entry from
  `get_project168_top.ashx` `NAME` by a merge rule that never downgrades a later
  cached stage (施工中/已完工/完成成果備查 survive an "approved" NAME), keeps the
  cached value when the NAME is unknown, and drops a cached approved-family value
  only when the case's own milestones contradict it (no approval date) and the
  NAME gives nothing.
- `refresh_project` replaces a case's milestones with a successful non-empty
  fetch instead of merging over them, and reports every removed label. A removed
  **approval** date is NOT applied silently: it is kept and reported as a
  conflict. An empty reply or an exception leaves the case unchanged (as today).
- The refresh selector skips a case whose cached status is terminal
  (自行撤回 / 已駁回 / 已失效); a project stays selected while any awaiting case is
  non-terminal. The run report separates "closed without approval" from
  "still awaiting approval".
- The viewer omits the schedule badge for both 已核准 and 已核定 (the
  approved-family default state).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `official-link-discovery`: "Capture per-case schedule from the search
  response" — the top.ashx derivation distinguishes pending approval (審查中)
  from approved.
- `cache-freshness`: "The targeted refresh selects caches awaiting an approval" —
  terminal cases are not selected, the refresh re-derives the case status,
  replaces milestones with the platform's current set, and reports closed cases
  apart from awaiting ones.
- `viewer-related-links`: "相關連結 resolves case names…" — the badge rule treats
  已核定 as the default approved state, like 已核准.

## Impact

- Code: `urtpe/links.py` (`schedule_from_top`, `refresh_project`,
  `cached_cases_awaiting_approval`, a top.ashx status adapter),
  `scripts/refresh_awaiting_caches.py` (report taxonomy), `viewer/app.js`
  (`scheduleBadgeText`).
- Data: a live refresh rewrites the selected `data/.link_cache/*/result.json`
  (backed up first — the directory is not in git), and a re-emission rewrites
  the tracked `data/*` files and `viewer/projects.data.js` (~23 MB diff).
- Network: +1 `get_project168_top.ashx` call per refreshed case; −85 projects
  no longer re-fetched (terminal-only).
- No gate, exit code or merge/identity rule changes. The node binding can move
  only where a refreshed approval date appears, which is the existing behaviour.
