## Context

Actors: the city platform (gis.uro.taipei — `Get_updcase_list` search list,
`get_project168_top.ashx` case header = 基本資料 目前辦理情形, `Get_project168_First`
= data1 辦理進度, `Get_project168_second` = data2 階段辦理過程), the operator who
runs `scripts/refresh_awaiting_caches.py`, the per-project link cache
(`data/.link_cache/<pid>/result.json`, the durable middle layer, not in git), the
emission (`--from-js … --links --recover-truncated`) and the static viewer.

Flow touched: PDF → … → merged.tsv → projects.json (+ viewer). This change lives
entirely in the link layer *beside* that flow: refresh (adapter: platform API →
cache) → emission reads the cache → payload `links.case_schedules` → viewer
相關連結 badge / status chip. No cleansing, merge, identity or gate is touched.

Measured 2026-11-02 for the 13 cases §33 reported: top `NAME` and data1
`name_progress_no` are identical for all 13, so one header call suffices; the
search list's `schedule` agrees with the corrected mapping on every case it
returned (68, 128 → 審查中; 687 → 自行撤回; 163-2 → 審查中).

## Goals / Non-Goals

**Goals:**
- A refreshed case's status agrees with the platform's own header.
- A refreshed case's milestones equal the platform's current set (withdrawn
  dates leave), without a silent loss of an approval date.
- Closed cases stop being re-fetched and stop being reported as awaiting.
- One approved state renders one way in the viewer.

**Non-Goals:**
- A corpus-wide status sweep. Only refresh-selected projects get re-derived
  status; the other ~520 caches keep their discovery-time values (a cached
  審查中 on a since-approved case is a known residual — 4 measured).
- Re-running the parcel search during refresh (the search list is the second
  status source; the header is per case and needs no section/parcel parsing).
- Changing node binding, row order or the never-approved rule.

## Decisions

### D1 — Fix the mapper by order, keep its vocabulary

`schedule_from_top` checks the pending phrase (`核定中`) before the approved test
and maps it to 審查中. Vocabulary is unchanged (the search list's words). The
pure function stays in `links.py` beside its only callers. Alternative —
mapping to a new word like 報府核定中 — rejected: the viewer, `neverApproved`
and `statusChip` already key on 審查中, and the city's own list says 審查中.

### D2 — A pure merge rule for the refreshed status

`refreshed_schedule(cached, derived, milestones) -> str`, pure:

| derived (from NAME) | result |
|---|---|
| terminal / 審查中 / 施工中 | derived |
| 已核准 | cached if cached ∈ {施工中, 已完工, 完成成果備查, 已核定, 已核准} else 已核准 |
| "" (無 / empty) | "" if cached ∈ {已核准, 已核定} and milestones carry no approval date, else cached |

Rationale per row: the header is the platform's current per-case word; a later
stage the search list knows (施工中) is more specific than the header's
"approved"; an outcome-less header is no evidence, except that the case's own
milestones can contradict a cached approved word (虎林 10806141). Clearing
gives honest silence rather than a wrong badge.

### D3 — Replace milestones on a non-empty reply; guard approval fields

`refresh_project`: if `fetched` is empty (or the call raises) → case unchanged
(existing behaviour). Otherwise `new = dict(fetched)`; for each approval field
in `before` that `fetched` lacks → keep it in `new` and add a `conflicts` entry;
every other label in `before` but not in `fetched` → `removed` entry. All cached
labels are second.ashx labels (measured: 0 labels outside `STAGE_FIELD_MAP`), so
replacement drops nothing a different adapter wrote.

### D4 — Status fetch is a default adapter, injectable

`refresh_project(cache_dir, pid, fetch=None, fetch_status=None)`. When both are
None (the production call) the defaults are the live milestone and header
adapters. When a test injects `fetch` only, status refresh is off — existing
offline tests stay offline and unchanged. A dedicated test drives the
**default** path with both module adapters monkeypatched, so a regression to a
milestone-only production refresh fails (the §33 "inert in production" class).

### D5 — Selector skips terminal cases; report has three buckets

`cached_cases_awaiting_approval(case_milestones, case_schedules=None)` ignores
an awaiting case whose cached status is terminal. The refresh report gains
`closed` (case header reads terminal after refresh) beside `still_awaiting`,
plus `status_changes`, `removed`, `conflicts`. The script prints each.

### D6 — Viewer: one approved family

`scheduleBadgeText` omits the badge for 已核准 and 已核定. The literal
`s === "已核准"` the label test pins stays in the expression.

## Risks / Trade-offs

- [Replacement drops a date the city removed by mistake] → reported per case;
  approval dates are never dropped; the cache is backed up before the live run.
- [Clearing a contradicted 已核准 could flip a project to never-approved] →
  clearing yields "", and `neverApproved` requires *every* schedule terminal, so
  "" cannot add a project to it; `statusChip` counts are compared before/after
  re-emission as an invariant.
- [A terminal case revived by the city] → would no longer be selected. The city
  files a new case id for a new attempt (observed on 民生段140-9), so the risk is
  accepted.
- [+1 API call per refreshed case] → offset by the 85 terminal-only projects no
  longer fetched; paced like the existing refresh.
