## 1. Test writing (stateOfHeader & family readers) — fully checked before implementation

- [x] 1.1 Add unit tests for state_of_header: header NAME "無" -> "無", header NAME "" -> "NA",
  missing row ({} / None) -> "".
- [x] 1.2 Add unit tests for refreshed_schedule: 無 input yields "無", empty input yields "NA",
  missing header keeps cached state, a normal state still overrides.
- [x] 1.3 Add viewer smoke checks: 11110171 / 11410008 / 09607081 show [無] or [NA] per their
  基本資料 / 目前辦理情形; 立農163-2's 11211211 shows [無]; family status chip and
  未曾核定 readers unchanged on all 693 projects.
- [x] 1.4 Confirm these tests fail on the current pipeline/viewer before the fix (confirmed:
  refreshed_schedule("審查中", "", header_state="無") previously returned "").

## 2. Pipeline implementation

- [ ] 2.1 Add pure helper stateOfHeader(header) -> "無" | "NA" | "" in urtpe/links.py.
- [ ] 2.2 Store case_headers CASE_NAME during header refresh.
- [ ] 2.3 In refreshed_schedule, keep "無" / "NA" instead of clearing to ""; missing header
  row keeps cached state.
- [ ] 2.4 Skip 無 / NA in statusChip, neverApproved, and the 相關連結 未曾核定 note.

## 3. Viewer implementation

- [ ] 3.1 scheduleBadgeText renders [無] for "無" and [NA] for "NA".

## 4. Cache refresh + re-emit

- [ ] 4.1 Run header refresh under the single-writer lock on caches lacking case_headers.
- [ ] 4.2 Re-emit data/ and viewer/projects.data.js as a separate chore commit (~23 MB diff).

## 5. Verification

- [ ] 5.1 pytest passes.
- [ ] 5.2 scripts/viewer_smoke.js checks pass on all three reported cases and 立農163-2.
