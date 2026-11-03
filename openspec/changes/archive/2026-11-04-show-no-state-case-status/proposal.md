## Why

When 基本資料 / 目前辦理情形 for a city case is 無 (no current state) or empty,
the viewer still renders [審查中] on that case's node and in 相關連結. Three cases
were measured: 11110171, 11410008 (信義區-雅祥段一小段-599地號等22筆) and
09607081 (中正區-永昌段五小段-248地號等47筆), each shown [審查中] although the
platform carries no state word for them.

The cache stores 審查中 from the parcel-search list, and the header refresh that reads
目前辦理情形 never ran on these caches (no case_headers key). When the refresh does
read 無, refreshed_schedule clears it to "" (supersede-headerless-cases D1), so the
viewer shows no badge — losing honest information the platform provides.

## What Changes

- Run the case-header refresh on caches that lack case_headers (under the single-writer
  lock), then re-emit.
- Store 無 as its own state instead of clearing it; render [無] for a 無 reading and
  [NA] for an empty 目前辦理情形 reading.
- Skip 無 / NA in the family-level readers (status chip statusChip, neverApproved,
  相關連結 未曾核定 note) so they read exactly as before; only the per-case badge changes.
- A superseded case shows both: [無] 已由 <successor> 取代.

## Capabilities

### Modified Capabilities
- `cache-freshness`: case refresh accepts 無 / empty 目前辦理情形 as a readable state
  instead of clearing it; adds `case_headers` persistence of CASE_NAME.
- `history-graph`: status-chip vocabulary gains 無 / NA per-case labels; family chip
  (審查中 / 撤回) and never-approved logic skip them.

### New Capabilities
None.

## Impact

- Pipeline (`urtpe/links.py`): refreshed_schedule, header_has_no_state, and a new pure
  helper mapping 基本資料 reading → 「無」/「NA」/「".
- Cache (`data/.link_cache/*/result.json`): gains case_headers for refreshed caches and
  新增「無」/「NA」 case_schedules values.
- Viewer (`viewer/app.js`): scheduleBadgeText renders [無] / [NA]; statusChip /
  neverApproved / link-list badge skip them.
- Emission (~23 MB diff in data/ and viewer/projects.data.js) runs once under the
  single-writer lock.
