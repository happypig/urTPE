## Context

§7 of docs/viewer-UX.md: 基本資料 / 目前辦理情形 for three measured cases
(11110171, 11410008, 09607081) shows [審查中] although the platform carries no state
word. The cache holds 審查中 from the parcel-search list; the header refresh never ran
(no case_headers key). When it does run and reads 無, refreshed_schedule clears it to
"" (supersede-headerless-cases D1), losing honest state.

The pipeline flow for links: discover -> harvest milestones -> attach_links_to_projects ->
refresh_cache_milestones -> emit.

## Goals / Non-Goals

**Goals:**
- Render [無] for 無 and [NA] for empty 目前辦理情形 on the per-case badge.
- Keep family-level readers (statusChip, neverApproved, 未曾核定 note) unchanged by
  skipping 無 / NA.
- Re-emit once under the single-writer lock.

**Non-Goals:**
- Changing what 審查中 means for other cases.
- Changing the family chip vocabulary beyond skipping 無 / NA.
- Creating corrections.jsonl (the ledger is deliberately unused per AGENTS.md).

## Decisions

### 1. Add a pure helper stateOfHeader(header) -> "無" | "NA" | ""

header_has_no_state already treats 無 and empty as no-state for the supersede trigger.
Add a separate pure helper that distinguishes them so the badge can show the right
label while header_has_no_state keeps its supersede behavior.

### 2. Keep 無 as a readable state

refreshed_schedule stores "無" / "NA" instead of clearing to "". A missing header row
still keeps the cached state (no evidence).

### 3. Skip 無 / NA in family-level readers

statusChip, neverApproved, and the 相關連結 未曾核定 note all use every(...) over
case_schedules. Add the same skip so 無 / NA do not change them. A supersessed case
shows [無] 已由 <successor> 取代 (both).

### 4. Commit order

Task order per repo pattern (feat then chore then openspec archive):
1. feat: pipeline helper + storage + viewer label + family-reader skip, with tests.
2. Run header refresh under the single-writer lock on caches lacking case_headers.
3. chore: re-emit data/ and viewer/projects.data.js (~23 MB diff).
4. openspec: archive change B.

## Risks / Trade-offs

- [Risk] 無 / NA on an approved unit could put a wrong badge (the reason D1 chose
  silence; measured 立農163-2).
  [Mitigation] Decision: show 無 / NA wherever the platform reading is 無 / empty,
  including 立農163-2's 11211211 (header 無). D1's other effect stays: no 審查中 chip
  returns.
- [Risk] re-emit rewrites data/ and viewer/projects.data.js (~23 MB).
  [Mitigation] stage in its own chore commit; review deliberately.
