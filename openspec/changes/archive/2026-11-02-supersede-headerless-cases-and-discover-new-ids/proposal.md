## Why

After `refresh-case-status-and-drop-withdrawn-fields` (§36) the maintainer
pointed at two cases whose platform header (基本資料 目前辦理情形) reads `無`:
立農段五小段-163-2's 11211211 and 虎林段四小段-38's 10806141. Measured live on
2026-11-02, both are **superseded copies**: the city re-filed the same
application under a new case id with the same 案名 and a data2 history that
contains every date of the old one —

- 11211211 → **11409026** (identical through 申請核定 2026/03/04; 11409026 adds
  核定日期 2026/08/18, header 業經本府核定);
- 10806141 → **11510017** (identical through 權變申請核定 2026/07/31; header
  申請報府核定中).

Three defects follow, and one of them is a claim §36 got wrong:

- **An outcome-less header kept a stale status.** §36's rule kept the cached
  word when `NAME` gave no outcome, so 11211211 still reads `[審查中]` and
  立農163-2's list chip says 審查中 — for a unit the city approved on 2026-08-18.
  §36 and `docs/inspection.md` recorded "立農163-2 correctly stays 審查中"; that
  is wrong.
- **A superseded case is selected forever.** 11211211 and 10806141 carry an
  application and no approval, so every refresh re-selects their projects and
  reports them "still awaiting approval".
- **The refresh cannot see a new case id.** 11510017 — 虎林38's real pending
  case — is not in the project's cache at all: the cache dates from 2026-08-30
  and the refresh re-reads only the case ids it already holds. The parcel
  search (the source discovery used) returns 11510017 today with 審查中.

## What Changes

- A case header that exists and reads `無` (or an empty `NAME`) clears an
  in-review or approved-family status; terminal statuses (自行撤回 / 已駁回 /
  已失效) and later stages (施工中 / 已完工 / 完成成果備查) are kept. A missing
  header row is no evidence and changes nothing.
- The refresh records each header `NAME` it read in the cache (`case_headers`).
  The selector skips a case whose recorded header is `無`.
- The refresh records `superseded_by` for a `無` case when exactly one other case
  of the project has the identical header 案名, a numerically newer id, and a
  data2 history containing every one of the old case's (≥ 3) dated labels.
  Several qualifying candidates → reported ambiguous, nothing recorded. A `無`
  case with no twin is reported by name in its own bucket.
- The refresh re-runs the parcel search discovery used (anchor 地段 + first
  地號 + 案名, read from the emitted payload) before the per-case loop, appends
  every new case id to `city_case_ids` (never re-ordering it — the positional
  fallback reads by index), fetches its milestones and header, and reports each
  added case. A failed search is reported as a failure, not as "no new cases".
- The payload emits `links.superseded_by`; the viewer's 相關連結 entry for a
  superseded case reads `已由 <case_id> 取代` instead of a status badge.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `cache-freshness`: "The targeted refresh selects caches awaiting an approval"
  (the outcome-less-header rule reverses for `無`; superseded and `無` cases are
  not selected; the refresh discovers new case ids) and a new requirement for
  the emitted replaced-case map.
- `viewer-related-links`: the 相關連結 entry names a superseded case's
  replacement.

## Impact

- Code: `urtpe/links.py` (`refreshed_schedule`, `find_superseding_case`,
  `refresh_project`, `cached_cases_awaiting_approval`, `DiscoveryResult` gains
  `case_headers` / `superseded_by`, payload attach and `--from-js` reload),
  `scripts/refresh_awaiting_caches.py` (anchor lookup, new buckets),
  `viewer/app.js` (相關連結 note).
- Data: a live refresh rewrites selected caches (backed up first) and may add
  case ids to them; a re-emission rewrites the tracked `data/*` files and
  `viewer/projects.data.js`.
- Network: +1 parcel search per selected project.
- Not in scope (recorded as residuals): new-case discovery for projects the
  selector does not pick (the 336 shape — a new case on a fully approved
  project); hiding a superseded case's undated virtual node in the graph; a
  `fresh=True` re-discovery drops `case_headers` / `superseded_by`.
